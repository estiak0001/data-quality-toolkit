from datetime import datetime
from typing import Any

from dqtk.adapters.base import Adapter, coerce_to_datetime

from .base import Check, CheckResult, Status


class FreshnessCheck(Check):
    """Fails when the newest row in `column` is older than `max_age_minutes`."""

    name = "freshness"

    def __init__(self, column: str, max_age_minutes: float):
        self.column = column
        self.max_age_minutes = max_age_minutes

    def run(self, adapter: Adapter, table: str, **context: Any) -> CheckResult:
        raw_max = adapter.max_value(table, self.column)
        latest = coerce_to_datetime(raw_max)
        if latest is None:
            return self._result(
                table,
                Status.ERROR,
                f"could not parse max({self.column}) value: {raw_max!r}",
            )

        now = datetime.now(latest.tzinfo) if latest.tzinfo else datetime.now()
        age_minutes = (now - latest).total_seconds() / 60.0

        if age_minutes > self.max_age_minutes:
            return self._result(
                table,
                Status.FAIL,
                f"{table}.{self.column} is {age_minutes:.1f}m stale "
                f"(threshold {self.max_age_minutes}m)",
                age_minutes=age_minutes,
                latest=str(latest),
            )
        return self._result(
            table,
            Status.PASS,
            f"{table}.{self.column} is fresh ({age_minutes:.1f}m old)",
            age_minutes=age_minutes,
            latest=str(latest),
        )
