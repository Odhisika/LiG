import logging

from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.models import NotificationEvent
from apps.notifications.registry import NotificationChannelRegistry
from apps.notifications.types import DigestSummary

logger = logging.getLogger(__name__)

MAX_SAMPLE_PRODUCT_NAMES = 10


class NotificationService:
    """Records notification-worthy events and periodically batches them
    into one digest per owner. Deliberately never sends anything at the
    moment an event happens — see send_pending_digests, called on a
    fixed beat interval (CELERY_BEAT_SCHEDULE), which is what actually
    dispatches messages.
    """

    @staticmethod
    def record_event(
        owner: User,
        event_type: str,
        *,
        product=None,
        supplier=None,
        payload: dict | None = None,
    ) -> NotificationEvent:
        return NotificationEvent.objects.create(
            owner=owner,
            event_type=event_type,
            product=product,
            supplier=supplier,
            payload=payload or {},
        )

    @staticmethod
    def _build_summary(events: list[NotificationEvent]) -> DigestSummary:
        summary = DigestSummary()
        names: list[str] = []
        for event in events:
            if event.event_type == NotificationEvent.EventType.PRODUCT_UPDATED:
                summary.products_updated += 1
            elif event.event_type == NotificationEvent.EventType.OUT_OF_STOCK:
                summary.out_of_stock += 1
            elif event.event_type == NotificationEvent.EventType.LOW_STOCK:
                summary.low_stock += 1
            elif event.event_type == NotificationEvent.EventType.SCRAPE_FAILED:
                summary.scrape_failed += 1
            elif event.event_type == NotificationEvent.EventType.SUPPLIER_UNAVAILABLE:
                summary.supplier_unavailable += 1
            elif event.event_type == NotificationEvent.EventType.NEW_PRODUCTS_FOUND:
                summary.new_products_found += 1

            if event.product_id and len(names) < MAX_SAMPLE_PRODUCT_NAMES:
                if event.product and event.product.name not in names:
                    names.append(event.product.name)

        summary.product_names = names
        return summary

    @staticmethod
    def send_pending_digests(channel_key: str = "email") -> int:
        """Groups unsent events by owner, sends one digest per owner that
        has pending events, and marks them sent. Returns how many
        digests were actually sent.

        A failure sending to one owner is logged and skipped, not
        allowed to block digests for everyone else — per "nothing fails
        silently," but also "one bad address shouldn't take the whole
        run down."
        """
        pending_owner_ids = (
            NotificationEvent.objects.filter(sent=False)
            .values_list("owner_id", flat=True)
            .distinct()
        )

        channel = NotificationChannelRegistry.get(channel_key)
        sent_count = 0

        for owner_id in pending_owner_ids:
            events = list(
                NotificationEvent.objects.filter(owner_id=owner_id, sent=False).select_related(
                    "owner", "product"
                )
            )
            if not events:
                continue

            summary = NotificationService._build_summary(events)
            if summary.is_empty:
                continue

            owner = events[0].owner
            try:
                channel.send_digest(owner, summary)
            except Exception:
                logger.exception("Failed to send notification digest to %s", owner.email)
                continue

            NotificationEvent.objects.filter(id__in=[e.id for e in events]).update(
                sent=True, sent_at=timezone.now()
            )
            sent_count += 1

        return sent_count
