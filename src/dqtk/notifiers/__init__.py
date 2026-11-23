from .base import Notifier
from .email import EmailNotifier
from .slack import SlackNotifier

__all__ = ["Notifier", "SlackNotifier", "EmailNotifier"]

REGISTRY = {
    "slack": SlackNotifier,
    "email": EmailNotifier,
}
