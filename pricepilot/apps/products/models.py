from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import SoftDeleteModel
from apps.suppliers.models import Supplier


class Product(SoftDeleteModel):
    """A single monitored product on a supplier's site.

    Owner-scoped the same way Supplier is (Step 1.2) — `owner` is
    denormalized onto Product rather than derived via `supplier.owner`
    so that ownership queries never require a join, and so a future
    tenant-scoping pass (Phase 4) touches one obvious field per model.
    """

    class Currency(models.TextChoices):
        USD = "USD", "US Dollar"
        EUR = "EUR", "Euro"
        GBP = "GBP", "British Pound"
        CNY = "CNY", "Chinese Yuan"
        GHS = "GHS", "Ghanaian Cedi"
        NGN = "NGN", "Nigerian Naira"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        OUT_OF_STOCK = "out_of_stock", "Out of stock"
        SCRAPE_FAILED = "scrape_failed", "Scrape failed"
        ARCHIVED = "archived", "Archived"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="products",
    )

    name = models.CharField(max_length=255)
    # Catlog product slugs embed the full product name — the longest
    # seen is 622 chars (one even embeds a description/footer), so
    # don't rely on URLField's 200-char default.
    supplier_url = models.URLField(max_length=2000)
    sku = models.CharField(max_length=100, blank=True)

    supplier_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Auto-computed from pricing_rule when set; otherwise set manually.",
    )
    pricing_rule = models.ForeignKey(
        "pricing.PricingRule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        help_text="When set, PriceMonitorService recomputes selling_price from this "
        "rule whenever supplier_price changes.",
    )
    currency = models.CharField(max_length=10, choices=Currency.choices, default=Currency.USD)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    stock = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])

    images = models.JSONField(default=list, blank=True, help_text="List of image URLs.")
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)

    check_frequency_minutes = models.PositiveIntegerField(
        default=60,
        help_text="How often the Price Monitor Engine (Step 2.2) should check this product.",
    )
    last_checked_at = models.DateTimeField(null=True, blank=True)

    # Store Sync (apps.sync): identity of this product inside the merchant's
    # own store (LiG). Set on first match/seed so future syncs don't need to
    # re-resolve by sku/slug. `store_synced_at` is the last time the sync
    # engine pushed values to the store.
    store_product_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Row id of the corresponding product in the merchant store "
        "(apps.sync / LiG store_product).",
    )
    store_synced_at = models.DateTimeField(
        null=True, blank=True, help_text="Last time values were synced to the merchant store."
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "sku"],
                condition=models.Q(deleted_at__isnull=True) & ~models.Q(sku=""),
                name="unique_active_sku_per_owner",
            )
        ]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["supplier"]),
        ]

    def __str__(self) -> str:
        return self.name
