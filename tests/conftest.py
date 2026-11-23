from typing import Any

import pytest

from dqtk.adapters.base import Adapter, ColumnInfo


class FakeAdapter(Adapter):
    """An in-memory stand-in for a real warehouse, for check unit tests."""

    def __init__(
        self,
        row_counts: dict[str, int] | None = None,
        max_values: dict[tuple[str, str], Any] | None = None,
        null_rates: dict[tuple[str, str], float] | None = None,
        schemas: dict[str, list[ColumnInfo]] | None = None,
    ):
        self._row_counts = row_counts or {}
        self._max_values = max_values or {}
        self._null_rates = null_rates or {}
        self._schemas = schemas or {}
        self.closed = False

    def row_count(self, table: str) -> int:
        return self._row_counts[table]

    def max_value(self, table: str, column: str) -> Any:
        return self._max_values[(table, column)]

    def null_rate(self, table: str, column: str) -> float:
        return self._null_rates[(table, column)]

    def columns(self, table: str) -> list[ColumnInfo]:
        return self._schemas[table]

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_adapter() -> FakeAdapter:
    return FakeAdapter()
