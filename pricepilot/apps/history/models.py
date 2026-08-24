from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.products.models import Product


class PriceHistory(TimeStampedModel):
    """One row per detected price and/or stock change on a product.

    Deliberately immutable and append-only (inherits TimeStampedModel,
    not SoftDeleteModel) — per the blueprint's "never delete important
    data / audit everything" standard, history rows are never edited or
    deleted, only ever created.

    Only written when something actually changed — a scrape that finds
    no difference doesn't produce a row here (see
    PriceMonitorService.check_product), so this table stays a genuine
    change log rather than a per-check audit trail.
    """

    class Reason(models.TextChoices):
        SCRAPE = "scrape", "Automatic scrape"
        MANUAL = "manual", "Manual edit"
        PRICING_RULE = "pricing_rule", "Pricing rule recompute"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="price_history")
    # Denormalized like Product.owner / Supplier.owner — keeps ownership
    # queries join-free and gives Phase 4 tenant scoping one obvious field.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="price_history"
    )

    old_price = models.DecimalField(max_digits=12, decimal_places=2)
    new_price = models.DecimalField(max_digits=12, decimal_places=2)
    old_stock = models.IntegerField(null=True, blank=True)
    new_stock = models.IntegerField(null=True, blank=True)

    price_changed = models.BooleanField(default=False)
    stock_changed = models.BooleanField(default=False)

    source = models.CharField(max_length=100, blank=True, help_text="Scraper key, e.g. 'catlog'.")
    reason = models.CharField(max_length=20, choices=Reason.choices, default=Reason.SCRAPE)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "-created_at"]),
            models.Index(fields=["owner", "-created_at"]),
        ]
        verbose_name_plural = "price histories"

    def __str__(self) -> str:
        return f"{self.product.name}: {self.old_price} -> {self.new_price} ({self.created_at:%Y-%m-%d})"
