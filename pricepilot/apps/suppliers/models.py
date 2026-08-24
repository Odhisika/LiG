from django.conf import settings
from django.db import models

from apps.common.models import SoftDeleteModel


class Supplier(SoftDeleteModel):
    """A source website a merchant scrapes products from.

    Scoped to the owning user (`owner`) — this is the ownership pattern
    Step 1.3's Product model reuses, and Phase 4 multi-tenancy will later
    generalize into tenant-level scoping.
    """

    class Currency(models.TextChoices):
        USD = "USD", "US Dollar"
        EUR = "EUR", "Euro"
        GBP = "GBP", "British Pound"
        CNY = "CNY", "Chinese Yuan"
        GHS = "GHS", "Ghanaian Cedi"
        NGN = "NGN", "Nigerian Naira"
        OTHER = "OTHER", "Other"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="suppliers",
    )
    name = models.CharField(max_length=255)
    website = models.URLField()
    catalog_url = models.URLField(
        blank=True,
        help_text="Page listing all products (for discovering new ones). "
        "Falls back to `website` if left blank — for a Catlog storefront, "
        "the homepage usually *is* the catalog.",
    )
    country = models.CharField(max_length=100, blank=True)
    currency = models.CharField(max_length=10, choices=Currency.choices, default=Currency.USD)

    # Matches a key in apps.scrapers.registry.ScraperRegistry (Step 1.4).
    # Left as a plain string now so Suppliers doesn't have to import
    # Scrapers — the registry validates the value instead.
    default_scraper = models.CharField(max_length=100, blank=True)

    rate_limit_per_minute = models.PositiveIntegerField(
        default=10,
        help_text="Max scrape requests per minute against this supplier's website.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_supplier_name_per_owner",
            )
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def effective_catalog_url(self) -> str:
        return self.catalog_url or self.website
