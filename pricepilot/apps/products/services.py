import logging

from django.db import IntegrityError, transaction
from django.http import QueryDict
from django.utils import timezone

from apps.accounts.models import User
from apps.common.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from apps.history.models import PriceHistory
from apps.notifications.models import NotificationEvent
from apps.notifications.services import NotificationService
from apps.pricing.models import PricingRule
from apps.pricing.services import PricingService
from apps.products.categorizer import categorize_product
from apps.products.models import Product
from apps.products.serializers import ProductSerializer
from apps.scrapers.registry import ScraperRegistry
from apps.suppliers.models import Supplier
from apps.sync.services import StoreSyncService

logger = logging.getLogger(__name__)


class ProductService:
    """Business logic for product CRUD, kept out of the view layer.

    Every method is scoped by `owner`, mirroring SupplierService — and
    additionally checks that a product's `supplier` actually belongs to
    that same owner, since the supplier FK is otherwise just a UUID a
    client could point at anyone's supplier.
    """

    @staticmethod
    def list_for_owner(owner: User, *, status: str | None = None, supplier_id=None, category=None):
        qs = Product.objects.filter(owner=owner)
        if status:
            qs = qs.filter(status=status)
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        if category:
            qs = qs.filter(category=category)
        return qs

    @staticmethod
    def categories_for_owner(owner: User) -> list[str]:
        return list(
            Product.objects.filter(owner=owner)
            .exclude(category="")
            .values_list("category", flat=True)
            .distinct()
            .order_by("category")
        )

    @staticmethod
    def get_for_owner(owner: User, product_id) -> Product:
        product = Product.objects.filter(owner=owner, id=product_id).first()
        if product is None:
            raise NotFoundError("Product not found.")
        return product

    @staticmethod
    def _assert_supplier_owned(owner: User, supplier_id) -> None:
        if not Supplier.objects.filter(owner=owner, id=supplier_id).exists():
            raise PermissionDeniedError("Supplier does not belong to the current user.")

    @staticmethod
    def _assert_pricing_rule_owned(owner: User, rule_id) -> None:
        if not PricingRule.objects.filter(owner=owner, id=rule_id).exists():
            raise PermissionDeniedError("Pricing rule does not belong to the current user.")

    @staticmethod
    def create(owner: User, data: dict) -> Product:
        if isinstance(data, QueryDict):
            data = data.dict()
        else:
            data = dict(data)
        if not (data.get("category") or "").strip():
            data["category"] = categorize_product(
                data.get("name") or "", data.get("description") or ""
            )
        serializer = ProductSerializer(data=data)
        if not serializer.is_valid():
            raise ValidationError(str(serializer.errors))

        supplier = serializer.validated_data["supplier"]
        ProductService._assert_supplier_owned(owner, supplier.id)

        pricing_rule = serializer.validated_data.get("pricing_rule")
        if pricing_rule is not None:
            ProductService._assert_pricing_rule_owned(owner, pricing_rule.id)

        try:
            return Product.objects.create(owner=owner, **serializer.validated_data)
        except IntegrityError as exc:
            raise ValidationError(
                f"A product with SKU '{data.get('sku')}' already exists."
            ) from exc

    @staticmethod
    def update(owner: User, product_id, data: dict, partial: bool = True) -> Product:
        product = ProductService.get_for_owner(owner, product_id)
        serializer = ProductSerializer(product, data=data, partial=partial)
        if not serializer.is_valid():
            raise ValidationError(str(serializer.errors))

        if "supplier" in serializer.validated_data:
            ProductService._assert_supplier_owned(owner, serializer.validated_data["supplier"].id)

        if "pricing_rule" in serializer.validated_data:
            rule = serializer.validated_data["pricing_rule"]
            if rule is not None:
                ProductService._assert_pricing_rule_owned(owner, rule.id)

        try:
            return serializer.save()
        except IntegrityError as exc:
            raise ValidationError(
                f"A product with SKU '{data.get('sku')}' already exists."
            ) from exc

    @staticmethod
    def delete(owner: User, product_id) -> None:
        product = ProductService.get_for_owner(owner, product_id)
        product.soft_delete()


class PriceMonitorService:
    """The Price Monitor Engine (blueprint Module 5): scrape a product,
    compare the result to what's stored, and record + apply any change.

    Also acts as the current, minimal Synchronization Engine (Module 8).
    The "store" being synced today is PricePilot's own Product row —
    pushing changes out to an actual external merchant store (Shopify,
    WooCommerce, etc.) is Phase 4 scope, not built yet. Notifying the
    merchant (Module 10) is Phase 3.

    Deliberately framework-agnostic about *how* it's invoked: the
    Scheduler (Step 2.1) calls this from a Celery task, but nothing
    here depends on Celery, which keeps it directly unit-testable and
    reusable from a management command or the API later.
    """

    @staticmethod
    def check_product(product_id) -> PriceHistory | None:
        """Runs one check. Returns the PriceHistory row if something
        changed, or None if the scrape matched what was already stored.

        Raises ScraperError (propagated, not swallowed) if the scrape
        itself fails — the caller (scheduler task) decides how to
        handle retries/failure status, since that's a scheduling
        concern, not a monitoring concern.
        """
        product = Product.objects.select_related("supplier").filter(id=product_id).first()
        if product is None:
            raise NotFoundError(f"Product {product_id} not found.")

        scraper_key = product.supplier.default_scraper
        if not scraper_key:
            raise ValidationError(
                f"Supplier '{product.supplier.name}' has no default_scraper configured."
            )

        scraper = ScraperRegistry.get(scraper_key)
        scraped = scraper.fetch(product.supplier_url)

        price_changed = scraped.price != product.supplier_price
        stock_changed = scraped.stock != product.stock
        now = timezone.now()

        if not price_changed and not stock_changed:
            product.last_checked_at = now
            update_fields = ["last_checked_at"]
            if product.status == Product.Status.SCRAPE_FAILED:
                # A successful scrape means the product is monitored fine
                # again — clear the failure flag so the scheduler's
                # "due products" query picks it back up.
                product.status = Product.Status.ACTIVE
                update_fields.append("status")
            product.save(update_fields=update_fields)
            return None

        with transaction.atomic():
            history = PriceHistory.objects.create(
                product=product,
                owner=product.owner,
                old_price=product.supplier_price,
                new_price=scraped.price,
                old_stock=product.stock,
                new_stock=scraped.stock,
                price_changed=price_changed,
                stock_changed=stock_changed,
                source=scraper_key,
                reason=PriceHistory.Reason.SCRAPE,
            )

            was_out_of_stock = product.status == Product.Status.OUT_OF_STOCK

            product.supplier_price = scraped.price
            product.stock = scraped.stock
            product.last_checked_at = now
            if price_changed and product.pricing_rule_id:
                product.selling_price = PricingService.compute_selling_price(
                    scraped.price, product.pricing_rule
                )
            newly_out_of_stock = False
            newly_low_stock = False
            if scraped.stock == 0:
                newly_out_of_stock = not was_out_of_stock
                product.status = Product.Status.OUT_OF_STOCK
            elif scraped.stock is not None and scraped.stock <= 5:
                # Low stock: stock is above 0 but at or below threshold
                was_low_before = product.stock is not None and 0 < product.stock <= 5
                newly_low_stock = not was_low_before and not was_out_of_stock
                if product.status in (Product.Status.OUT_OF_STOCK, Product.Status.SCRAPE_FAILED):
                    product.status = Product.Status.ACTIVE
            elif product.status in (Product.Status.OUT_OF_STOCK, Product.Status.SCRAPE_FAILED):
                # Auto-recover: it was out of stock (or previously flagged
                # scrape_failed) and now it's being scraped successfully.
                product.status = Product.Status.ACTIVE
            product.save()

            NotificationService.record_event(
                product.owner,
                NotificationEvent.EventType.PRODUCT_UPDATED,
                product=product,
                payload={"old_price": str(history.old_price), "new_price": str(history.new_price)},
            )
            # Only on the transition into out-of-stock, not every
            # subsequent check while it stays out of stock — otherwise
            # a product stuck at zero stock would generate a fresh event
            # (and digest line) on every single scheduler tick.
            if newly_out_of_stock:
                NotificationService.record_event(
                    product.owner, NotificationEvent.EventType.OUT_OF_STOCK, product=product
                )
            # Low-stock alert: stock just dropped to threshold or below
            if newly_low_stock:
                NotificationService.record_event(
                    product.owner,
                    NotificationEvent.EventType.LOW_STOCK,
                    product=product,
                    payload={"stock": scraped.stock, "threshold": 5},
                )

        # Store Sync (Module 8's external store): push the new values out to
        # the merchant's own store (LiG). Deliberately outside the atomic
        # block — the store is a separate database, so its write is an
        # independent, idempotent operation that the scheduled reconcile
        # task can redo if it ever fails here.
        try:
            StoreSyncService.sync_product(product)
        except Exception as exc:  # pragma: no cover - defensive; sync catches its own
            logger.error("Store sync failed for product %s: %s", product.id, exc)

        return history
