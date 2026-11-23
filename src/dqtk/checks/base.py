from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from dqtk.adapters.base import Adapter


class Status(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    ERROR = "error"


@dataclass
class CheckResult:
    check_name: str
    table: str
    status: Status
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class Check(ABC):
    """A single, named data-quality rule applied to one table.

    Subclasses implement `run`. Checks never talk to storage directly —
    anything they need from history (a row-count baseline, a prior schema
    snapshot) is passed in by the caller, so checks stay unit-testable
    against a fake Adapter with no database involved.
    """

    name: str

    @abstractmethod
    def run(self, adapter: Adapter, table: str, **context: Any) -> CheckResult:
        ...

    def _result(self, table: str, status: Status, message: str, **details: Any) -> CheckResult:
        return CheckResult(
            check_name=self.name, table=table, status=status, message=message, details=details
        )
