import logging

from celery import shared_task

from apps.sync.services import StoreSyncService, is_configured

logger = logging.getLogger(__name__)


@shared_task
def sync_all_to_store() -> dict:
    """Reconcile all store-bound products with the merchant store.

    Runs daily (see CELERY_BEAT_SCHEDULE). The per-change sync in
    PriceMonitorService keeps the store fresh in real time; this task is the
    safety net for products added manually in PricePilot and for drift
    caused by a failed per-change push.
    """
    if not is_configured():
        return {"action": "skipped", "reason": "store sync not configured"}
    tally = StoreSyncService.sync_all()
    logger.info("Store sync reconcile finished: %s", tally)
    return tally
