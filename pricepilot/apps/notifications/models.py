from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.products.models import Product
from apps.suppliers.models import Supplier


class NotificationEvent(TimeStampedModel):
    """A notification-worthy thing that happened, waiting to be batched
    into a digest and sent. Recorded by PriceMonitorService (product
    updated / out of stock) and the scheduler's failure handling
    (scrape failed), never sent individually — see NotificationService
    for the batching, per the blueprint's explicit guidance against
    firing one message per change.
    """

    class EventType(models.TextChoices):
        PRODUCT_UPDATED = "product_updated", "Product updated"
        OUT_OF_STOCK = "out_of_stock", "Out of stock"
        LOW_STOCK = "low_stock", "Low stock"
        SCRAPE_FAILED = "scrape_failed", "Scrape failed"
        NEW_PRODUCTS_FOUND = "new_products_found", "New products found"
        SUPPLIER_UNAVAILABLE = "supplier_unavailable", "Supplier unavailable"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_events"
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_events",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_events",
    )
    payload = models.JSONField(default=dict, blank=True)

    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "sent"])]

    def __str__(self) -> str:
        state = "sent" if self.sent else "pending"
        return f"{self.event_type} for {self.owner} ({state})"
