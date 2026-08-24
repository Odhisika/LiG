import logging

from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.models import User
from apps.common.exceptions import NotFoundError, ScraperError, ValidationError
from apps.discovery.models import DiscoveredProduct
from apps.notifications.models import NotificationEvent
from apps.notifications.services import NotificationService
from apps.products.models import Product
from apps.products.services import ProductService
from apps.scrapers.registry import ScraperRegistry
from apps.suppliers.models import Supplier
from apps.sync.services import StoreSyncService

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Scans a supplier's catalog page for product URLs not already
    tracked (as a Product or a prior DiscoveredProduct), records them
    for review, and turns a reviewed one into a real Product on import.
    """

    @staticmethod
    def list_for_owner(owner: User, *, status: str | None = None):
        qs = DiscoveredProduct.objects.filter(owner=owner)
        if status:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def get_for_owner(owner: User, discovery_id) -> DiscoveredProduct:
        discovery = DiscoveredProduct.objects.filter(owner=owner, id=discovery_id).first()
        if discovery is None:
            raise NotFoundError("Discovered product not found.")
        return discovery

    @staticmethod
    def scan_supplier(supplier: Supplier) -> dict:
        """Finds product URLs on the supplier's catalog page that
        aren't already a tracked Product or a previously-seen
        DiscoveredProduct, fetches a preview for each genuinely new one,
        and records it. Also detects products removed from the supplier
        and marks them out-of-stock.

        Returns a dict with counts: {"created": int, "removed": int}.
        """
        if not supplier.default_scraper:
            return {"created": 0, "removed": 0}

        try:
            scraper = ScraperRegistry.get(supplier.default_scraper)
            found_urls = set(scraper.discover_product_urls(supplier.effective_catalog_url))
        except ScraperError as exc:
            logger.warning("Discovery scan failed for supplier %s: %s", supplier.id, exc.message)
            return {"created": 0, "removed": 0}

        already_tracked = set(supplier.products.values_list("supplier_url", flat=True)) | set(
            supplier.discovered_products.values_list("url", flat=True)
        )
        new_urls = [url for url in found_urls if url not in already_tracked]

        created_count = 0
        for url in new_urls:
            discovery = DiscoveryService._create_with_preview(supplier, url)
            if discovery is not None:
                created_count += 1

        # Detect products removed from the supplier's catalog.
        tracked_urls = set(
            supplier.products.values_list("supplier_url", flat=True)
        )
        removed_urls = tracked_urls - found_urls
        removed_count = 0
        for url in removed_urls:
            product = supplier.products.filter(supplier_url=url).first()
            if product and product.status not in (
                Product.Status.OUT_OF_STOCK,
                Product.Status.ARCHIVED,
            ):
                product.status = Product.Status.OUT_OF_STOCK
                product.stock = 0
                product.last_checked_at = timezone.now()
                product.save(update_fields=["status", "stock", "last_checked_at"])
                NotificationService.record_event(
                    supplier.owner,
                    NotificationEvent.EventType.SUPPLIER_UNAVAILABLE,
                    product=product,
                    supplier=supplier,
                    payload={
                        "reason": "Product no longer found on supplier catalog during scan",
                        "supplier_url": url,
                    },
                )
                removed_count += 1
                logger.warning(
                    "Product %s (%s) removed from supplier %s catalog — marked out-of-stock.",
                    product.id,
                    url,
                    supplier.id,
                )

        if created_count:
            NotificationService.record_event(
                supplier.owner,
                NotificationEvent.EventType.NEW_PRODUCTS_FOUND,
                supplier=supplier,
                payload={"count": created_count, "supplier_name": supplier.name},
            )

        return {"created": created_count, "removed": removed_count}

    @staticmethod
    def _create_with_preview(supplier: Supplier, url: str) -> DiscoveredProduct | None:
        preview = {}
        try:
            scraper = ScraperRegistry.get(supplier.default_scraper)
            scraped = scraper.fetch(url)
            preview = {
                "title": scraped.title,
                "price": scraped.price,
                "currency": scraped.currency,
                "image": scraped.images[0] if scraped.images else "",
            }
        except ScraperError as exc:
            # Recorded anyway, just with less information — the URL
            # itself is still useful for the merchant to review, and a
            # full fetch happens again at import time via ProductService.
            logger.info("Preview fetch failed for discovered URL %s: %s", url, exc.message)

        try:
            return DiscoveredProduct.objects.create(
                owner=supplier.owner, supplier=supplier, url=url, **preview
            )
        except IntegrityError:
            # Another scan (or a race) already recorded this URL.
            return None

    @staticmethod
    def import_discovery(owner: User, discovery_id, overrides: dict | None = None):
        """Turns a pending DiscoveredProduct into a real, tracked
        Product — the "one click" the merchant actually presses.
        Reuses ProductService.create so the new Product gets the same
        validation and cross-owner supplier protection as any other.
        """
        discovery = DiscoveryService.get_for_owner(owner, discovery_id)
        if discovery.status != DiscoveredProduct.Status.PENDING:
            raise ValidationError(f"This discovery has already been {discovery.status}.")

        overrides = overrides or {}
        supplier_price = overrides.get("supplier_price", discovery.price)
        if supplier_price is None:
            raise ValidationError(
                "No price was found automatically for this product — "
                "provide supplier_price to import it."
            )

        data = {
            "supplier": str(discovery.supplier_id),
            "name": overrides.get("name") or discovery.title or "Untitled product",
            "supplier_url": discovery.url,
            "supplier_price": str(supplier_price),
            "currency": (
                overrides.get("currency")
                or discovery.currency
                or discovery.supplier.currency
                or "USD"
            ),
        }
        if discovery.image:
            # Carry the preview image over so the store seed can download
            # and host its own copy instead of hot-linking the supplier.
            data["images"] = [discovery.image]
        for optional_field in ("sku", "category", "check_frequency_minutes", "pricing_rule"):
            if optional_field in overrides:
                data[optional_field] = overrides[optional_field]

        product = ProductService.create(owner, data)

        # Seed the new product into the merchant store right away (best
        # effort — sync_product never raises; the daily reconcile task is the
        # safety net if the store is unavailable right now).
        StoreSyncService.sync_product(product)

        discovery.status = DiscoveredProduct.Status.IMPORTED
        discovery.imported_product = product
        discovery.save(update_fields=["status", "imported_product"])

        return product

    @staticmethod
    def dismiss_discovery(owner: User, discovery_id) -> DiscoveredProduct:
        discovery = DiscoveryService.get_for_owner(owner, discovery_id)
        if discovery.status != DiscoveredProduct.Status.PENDING:
            raise ValidationError(f"This discovery has already been {discovery.status}.")
        discovery.status = DiscoveredProduct.Status.DISMISSED
        discovery.save(update_fields=["status"])
        return discovery
