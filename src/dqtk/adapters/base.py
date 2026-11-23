from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ColumnInfo:
    name: str
    type: str


class Adapter(ABC):
    """Common interface every warehouse backend implements.

    Checks are written against this interface only, so a new backend
    (Snowflake, BigQuery, ...) just needs to implement these five methods.
    """

    @abstractmethod
    def row_count(self, table: str) -> int:
        ...

    @abstractmethod
    def max_value(self, table: str, column: str) -> Any:
        ...

    @abstractmethod
    def null_rate(self, table: str, column: str) -> float:
        ...

    @abstractmethod
    def columns(self, table: str) -> list[ColumnInfo]:
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    def __enter__(self) -> "Adapter":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


def coerce_to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None
