from abc import ABC, abstractmethod

from dqtk.checks.base import CheckResult


class Notifier(ABC):
    """Sends a batch of check results somewhere. Called once per run with
    only the non-passing results — passing silently is the common case."""

    @abstractmethod
    def notify(self, table: str, results: list[CheckResult]) -> None:
        ...
