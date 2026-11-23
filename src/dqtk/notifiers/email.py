import smtplib
from email.mime.text import MIMEText

from dqtk.checks.base import CheckResult

from .base import Notifier


class EmailNotifier(Notifier):
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        sender: str,
        recipients: list[str],
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender = sender
        self.recipients = recipients
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def notify(self, table: str, results: list[CheckResult]) -> None:
        if not results:
            return
        body_lines = [f"Data quality alert for {table}:", ""]
        for r in results:
            body_lines.append(f"[{r.status.value.upper()}] {r.check_name}: {r.message}")

        message = MIMEText("\n".join(body_lines))
        message["Subject"] = f"[dqtk] data quality failures on {table}"
        message["From"] = self.sender
        message["To"] = ", ".join(self.recipients)

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)
            server.sendmail(self.sender, self.recipients, message.as_string())
