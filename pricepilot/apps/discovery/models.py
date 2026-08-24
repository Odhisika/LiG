from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.products.models import Product
from apps.suppliers.models import Supplier


class DiscoveredProduct(TimeStampedModel):
    """A product URL found on a supplier's catalog page that isn't
    already tracked as a Product. Created by DiscoveryService.scan_supplier,
    reviewed by the merchant, then either imported (becomes a real
    Product) or dismissed.

    Deliberately not soft-deleting — once imported or dismissed it just
    changes status, it's a small append-only review queue, not data
    worth preserving deletion history for the way Product/Supplier are.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        IMPORTED = "imported", "Imported"
        DISMISSED = "dismissed", "Dismissed"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="discovered_products"
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="discovered_products"
    )
    # Same rationale as Product.supplier_url — Catlog slugs embed the
    # full product name; the longest seen is 622 chars.
    url = models.URLField(max_length=2000)

    # Preview fields, populated at discovery time via the same fetch()
    # used for regular monitoring — see DiscoveryService.scan_supplier.
    # Best-effort: a preview fetch failing doesn't stop the URL from
    # being recorded, it's just recorded with less information.
    title = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, blank=True)
    image = models.URLField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    imported_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discovered_from",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "url"], name="unique_discovered_url_per_supplier"
            )
        ]
        indexes = [models.Index(fields=["owner", "status"])]

    def __str__(self) -> str:
        return f"{self.title or self.url} ({self.status})"
