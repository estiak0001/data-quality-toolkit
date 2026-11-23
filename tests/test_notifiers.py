from unittest.mock import patch

from dqtk.checks.base import CheckResult, Status
from dqtk.notifiers.slack import SlackNotifier


def test_slack_notifier_skips_empty_results():
    notifier = SlackNotifier("https://hooks.slack.com/fake")
    with patch("dqtk.notifiers.slack.requests.post") as mock_post:
        notifier.notify("orders", [])
    mock_post.assert_not_called()


def test_slack_notifier_posts_failures():
    notifier = SlackNotifier("https://hooks.slack.com/fake")
    result = CheckResult(check_name="row_count", table="orders", status=Status.FAIL, message="dropped 90%")

    with patch("dqtk.notifiers.slack.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        notifier.notify("orders", [result])

    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert "row_count" in kwargs["json"]["text"]
    assert "orders" in kwargs["json"]["text"]
