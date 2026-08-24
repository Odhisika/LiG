import pytest

from apps.common.exceptions import NotFoundError
from apps.notifications.channels.email import EmailChannel
from apps.notifications.registry import NotificationChannelRegistry


class TestRegistry:
    def test_email_is_registered(self):
        channel = NotificationChannelRegistry.get("email")
        assert isinstance(channel, EmailChannel)

    def test_unknown_key_raises_not_found(self):
        with pytest.raises(NotFoundError):
            NotificationChannelRegistry.get("does-not-exist")

    def test_available_keys_includes_email(self):
        assert "email" in NotificationChannelRegistry.available_keys()
