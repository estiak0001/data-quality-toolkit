import requests

from dqtk.checks.base import CheckResult

from .base import Notifier


class SlackNotifier(Notifier):
    def __init__(self, webhook_url: str, timeout: float = 5.0):
        self.webhook_url = webhook_url
        self.timeout = timeout

    def notify(self, table: str, results: list[CheckResult]) -> None:
        if not results:
            return
        lines = [f"*Data quality alert — `{table}`*"]
        for r in results:
            lines.append(f"• [{r.status.value.upper()}] {r.check_name}: {r.message}")
        payload = {"text": "\n".join(lines)}
        response = requests.post(self.webhook_url, json=payload, timeout=self.timeout)
        response.raise_for_status()
