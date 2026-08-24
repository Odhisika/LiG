import logging
from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.db.models import (
    Case,
    DateTimeField,
    DurationField,
    ExpressionWrapper,
    F,
    IntegerField,
    Q,
    When,
)
from django.db.models.functions import Cast
from django.utils import timezone

from apps.common.exceptions import NotFoundError, ProductNotFoundOnSupplier, ScraperError, ValidationError
from apps.notifications.models import NotificationEvent
from apps.notifications.services import NotificationService
from apps.products.models import Product
from apps.products.services import PriceMonitorService

logger = logging.getLogger(__name__)

# Safety window for the per-product lock: must comfortably exceed how
# long a single check can realistically take, so a slow scrape doesn't
# get enqueued a second time by the next beat tick before it finishes.
LOCK_TTL_SECONDS = 300

# How many times to retry a failed scrape before marking the product
# scrape_failed, and the backoff schedule between attempts.
MAX_SCRAPE_RETRIES = 3
RETRY_BACKOFF_SECONDS = 60


def _lock_key(product_id) -> str:
    return f"scheduler:product-check-lock:{product_id}"


def _mark_scrape_failed(product_id: str, reason: str) -> None:
    """Marks a product scrape_failed and records a notification event —
    shared by both failure branches below so the two stay consistent.
    """
    product = Product.objects.select_related("owner").filter(id=product_id).first()
    if product is None:
        return
    product.status = Product.Status.SCRAPE_FAILED
    product.last_checked_at = timezone.now()
    product.save(update_fields=["status", "last_checked_at"])
    NotificationService.record_event(
        product.owner,
        NotificationEvent.EventType.SCRAPE_FAILED,
        product=product,
        payload={"reason": reason},
    )


def _mark_product_not_found(product_id: str, reason: str) -> None:
    """Marks a product as out-of-stock when the supplier returns 404/410,
    and fires a SUPPLIER_UNAVAILABLE notification. This is distinct from
    SCRAPE_FAILED because a 404 means the product was likely removed
    from the supplier's catalog — not a transient network error.
    """
    product = Product.objects.select_related("owner").filter(id=product_id).first()
    if product is None:
        return
    product.status = Product.Status.OUT_OF_STOCK
    product.stock = 0
    product.last_checked_at = timezone.now()
    product.save(update_fields=["status", "stock", "last_checked_at"])
    NotificationService.record_event(
        product.owner,
        NotificationEvent.EventType.SUPPLIER_UNAVAILABLE,
        product=product,
        payload={"reason": reason},
    )


def _due_products():
    """Products whose check window has elapsed since last_checked_at
    (or that have never been checked).

    ACTIVE products use their per-product `check_frequency_minutes`.
    SCRAPE_FAILED and OUT_OF_STOCK products are retried every 6 hours
    so they can recover when a supplier restores a page or a network
    issue resolves.

    Deliberately expressed as a single annotated queryset rather than a
    Python loop — the blueprint's scalability goals go up to 1,000,000
    products, and a per-row Python comparison across the whole active
    set would be the first thing to fall over at that volume.
    """
    now = timezone.now()
    retry_interval = timedelta(hours=6)

    return (
        Product.objects.filter(
            status__in=[
                Product.Status.ACTIVE,
                Product.Status.SCRAPE_FAILED,
                Product.Status.OUT_OF_STOCK,
            ]
        )
        .annotate(
            check_interval=ExpressionWrapper(
                Case(
                    When(status=Product.Status.ACTIVE, then=Cast(
                        F("check_frequency_minutes"), output_field=IntegerField()
                    ) * timedelta(minutes=1)),
                    default=retry_interval,
                    output_field=DurationField(),
                ),
                output_field=DurationField(),
            )
        )
        .annotate(
            next_check_at=ExpressionWrapper(
                F("last_checked_at") + F("check_interval"),
                output_field=DateTimeField(),
            )
        )
        .filter(Q(last_checked_at__isnull=True) | Q(next_check_at__lte=now))
    )


@shared_task(name="apps.scheduler.tasks.enqueue_due_product_checks")
def enqueue_due_product_checks() -> int:
    """Runs on a fixed beat interval (CELERY_BEAT_SCHEDULE). Finds every
    due product and enqueues a check for it.

    Idempotency here is about not double-*enqueuing* the same product
    before its previous check has finished — a short cache lock handles
    that. Idempotency for the actual PriceHistory write belongs to Step
    2.2's Price Monitor Engine, since two genuinely separate scrapes
    that both detect a change should both be allowed to write history.
    """
    enqueued = 0
    for product in _due_products().iterator():
        if not cache.add(_lock_key(product.id), "1", timeout=LOCK_TTL_SECONDS):
            logger.debug("Skipping product %s — check already in flight.", product.id)
            continue
        check_product_task.delay(str(product.id))
        enqueued += 1

    logger.info("Scheduler enqueued %d product check(s).", enqueued)
    return enqueued


@shared_task(
    name="apps.scheduler.tasks.check_product_task", bind=True, max_retries=MAX_SCRAPE_RETRIES
)
def check_product_task(self, product_id: str) -> None:
    """Runs one product through the Price Monitor Engine
    (PriceMonitorService.check_product) — scrape, compare, and record +
    apply any change.

    A scrape failure is retried with backoff up to MAX_SCRAPE_RETRIES
    times (transient network hiccups shouldn't immediately flag a
    product) before the product is marked `scrape_failed` — nothing
    fails silently either way, per the blueprint's logging standard.
    """
    try:
        PriceMonitorService.check_product(product_id)
    except NotFoundError:
        # Product was deleted between being enqueued and this task running.
        logger.info("check_product_task: product %s no longer exists.", product_id)
    except ProductNotFoundOnSupplier as exc:
        # 404/410 — product was removed from the supplier's catalog.
        # Mark it out-of-stock immediately; no point retrying.
        logger.warning(
            "check_product_task: product %s not found on supplier (404/410): %s",
            product_id,
            exc.message,
        )
        _mark_product_not_found(product_id, exc.message)
    except ValidationError as exc:
        # Misconfiguration (e.g. no scraper set on the supplier) — not
        # transient, retrying won't help. Mark failed immediately.
        logger.error("check_product_task: config error for %s: %s", product_id, exc.message)
        _mark_scrape_failed(product_id, exc.message)
    except ScraperError as exc:
        if self.request.retries >= self.max_retries:
            logger.error(
                "check_product_task: %s failed after %d retries: %s",
                product_id,
                self.request.retries,
                exc.message,
            )
            _mark_scrape_failed(product_id, exc.message)
        else:
            logger.warning(
                "check_product_task: %s scrape failed (attempt %d/%d): %s",
                product_id,
                self.request.retries + 1,
                self.max_retries,
                exc.message,
            )
            raise self.retry(
                exc=exc, countdown=RETRY_BACKOFF_SECONDS * (2**self.request.retries)
            ) from exc
    finally:
        cache.delete(_lock_key(product_id))
