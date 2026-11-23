from typing import Any

from dqtk.adapters.base import Adapter

from .base import Check, CheckResult, Status


class NullRateCheck(Check):
    """Fails when the fraction of NULLs in `column` exceeds `max_null_rate`."""

    name = "null_rate"

    def __init__(self, column: str, max_null_rate: float):
        self.column = column
        self.max_null_rate = max_null_rate

    def run(self, adapter: Adapter, table: str, **context: Any) -> CheckResult:
        rate = adapter.null_rate(table, self.column)

        if rate > self.max_null_rate:
            return self._result(
                table,
                Status.FAIL,
                f"{table}.{self.column} null rate {rate:.2%} exceeds "
                f"threshold {self.max_null_rate:.2%}",
                null_rate=rate,
                threshold=self.max_null_rate,
            )
        return self._result(
            table,
            Status.PASS,
            f"{table}.{self.column} null rate {rate:.2%} within threshold",
            null_rate=rate,
            threshold=self.max_null_rate,
        )
