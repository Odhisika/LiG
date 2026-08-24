from abc import ABC, abstractmethod

from apps.accounts.models import User
from apps.notifications.types import DigestSummary


class NotificationChannel(ABC):
    """Every notification channel implements this. Same plugin shape as
    apps.scrapers.base.BaseScraper — adding WhatsApp/Slack/Telegram later
    is a new class + registration, not a change to NotificationService.
    """

    key: str

    @abstractmethod
    def send_digest(self, owner: User, summary: DigestSummary) -> None:
        raise NotImplementedError
