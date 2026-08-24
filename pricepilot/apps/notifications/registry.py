from apps.common.exceptions import NotFoundError
from apps.notifications.channels.base import NotificationChannel


class NotificationChannelRegistry:
    """Maps a channel key (e.g. "email") to a concrete NotificationChannel
    class. Mirrors apps.scrapers.registry.ScraperRegistry.
    """

    _registry: dict[str, type[NotificationChannel]] = {}

    @classmethod
    def register(cls, channel_cls: type[NotificationChannel]) -> type[NotificationChannel]:
        cls._registry[channel_cls.key] = channel_cls
        return channel_cls

    @classmethod
    def get(cls, key: str) -> NotificationChannel:
        channel_cls = cls._registry.get(key)
        if channel_cls is None:
            raise NotFoundError(f"No notification channel registered for key '{key}'.")
        return channel_cls()

    @classmethod
    def available_keys(cls) -> list[str]:
        return sorted(cls._registry.keys())
