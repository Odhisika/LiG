from django.conf import settings
from django.db import models


class ActivityEvent(models.Model):
    """Append-only audit trail for every scraper action: checks, price
    changes, store syncs, product removals, discoveries.

    Scoped to `owner` for query performance. `payload` holds flexible
    event-specific details (old/new price, sync action, error reason, etc.).
    Never edited or deleted — like PriceHistory, this is an immutable log.
    """

    class EventType(models.TextChoices):
        CHECK_OK = "check_ok", "Scrape completed (no change)"
        PRICE_CHANGE = "price_change", "Price changed"
        STOCK_CHANGE = "stock_change", "Stock changed"
        SCRAPE_FAILED = "scrape_failed", "Scrape failed"
        REMOVED = "removed", "Product removed from supplier"
        STORE_SYNCED = "store_synced", "Store product synced"
        STORE_DELETED = "store_deleted", "Store product deleted"
        DISCOVERED = "discovered", "New product discovered"
        IMPORTED = "imported", "Discovery imported"
        STATUS_CHANGE = "status_change", "Product status changed"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activity_events",
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices, db_index=True)
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_events",
    )
    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_events",
    )
    payload = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
            models.Index(fields=["owner", "event_type", "-created_at"]),
        ]

    def __str__(self) -> str:
        target = self.product_id or self.supplier_id or ""
        return f"{self.event_type} {target} @ {self.created_at:%Y-%m-%d %H:%M}"
