import logging

from celery import shared_task

from apps.notifications.services import NotificationService

logger = logging.getLogger(__name__)


@shared_task(name="apps.notifications.tasks.send_pending_digests")
def send_pending_digests() -> int:
    count = NotificationService.send_pending_digests()
    logger.info("Sent %d notification digest(s).", count)
    return count
