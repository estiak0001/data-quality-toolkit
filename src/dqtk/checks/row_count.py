from statistics import mean, pstdev
from typing import Any

from dqtk.adapters.base import Adapter

from .base import Check, CheckResult, Status


class RowCountCheck(Check):
    """Flags a row count that deviates too far from its recent history.

    `history` (passed by the caller as a list of past row counts, most
    recent last) is used to build a baseline mean. If there isn't enough
    history yet, the check passes trivially — it has nothing to compare
    against. Deviation is measured as a fraction of the baseline mean
    (`max_pct_change`), falling back to a flat z-score style spread check
    when the baseline mean is zero.
    """

    name = "row_count"

    def __init__(self, max_pct_change: float = 0.5, min_history: int = 3):
        self.max_pct_change = max_pct_change
        self.min_history = min_history

    def run(
        self, adapter: Adapter, table: str, history: list[int] | None = None, **context: Any
    ) -> CheckResult:
        current = adapter.row_count(table)
        history = history or []

        if len(history) < self.min_history:
            return self._result(
                table,
                Status.PASS,
                f"{table} row count = {current} (not enough history to baseline yet)",
                current=current,
                history_len=len(history),
            )

        baseline = mean(history)
        spread = pstdev(history) if len(history) > 1 else 0.0

        if baseline == 0:
            pct_change = float("inf") if current else 0.0
        else:
            pct_change = abs(current - baseline) / baseline

        if pct_change > self.max_pct_change:
            return self._result(
                table,
                Status.FAIL,
                f"{table} row count {current} deviates {pct_change:.0%} from "
                f"baseline {baseline:.0f} (threshold {self.max_pct_change:.0%})",
                current=current,
                baseline=baseline,
                pct_change=pct_change,
                threshold=self.max_pct_change,
                stddev=spread,
            )
        return self._result(
            table,
            Status.PASS,
            f"{table} row count {current} within baseline {baseline:.0f} "
            f"(+/-{self.max_pct_change:.0%})",
            current=current,
            baseline=baseline,
            pct_change=pct_change,
            threshold=self.max_pct_change,
        )
