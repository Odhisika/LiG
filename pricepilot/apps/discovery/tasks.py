import logging

from celery import shared_task

from apps.discovery.services import DiscoveryService
from apps.suppliers.models import Supplier

logger = logging.getLogger(__name__)


@shared_task(name="apps.discovery.tasks.scan_all_suppliers")
def scan_all_suppliers() -> dict:
    """Runs on a fixed (daily — see CELERY_BEAT_SCHEDULE) beat interval.
    New products don't appear nearly as often as prices change, so this
    is deliberately a much slower cadence than the price-check scheduler.

    One supplier's scan failing is handled inside
    DiscoveryService.scan_supplier itself and doesn't stop the others.
    """
    total_created = 0
    total_removed = 0
    suppliers = Supplier.objects.filter(is_active=True).exclude(default_scraper="")
    for supplier in suppliers.iterator():
        result = DiscoveryService.scan_supplier(supplier)
        total_created += result["created"]
        total_removed += result["removed"]

    logger.info(
        "Discovery scan complete: %d new, %d removed across all suppliers.",
        total_created,
        total_removed,
    )
    return {"created": total_created, "removed": total_removed}
