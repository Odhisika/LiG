import logging
from decimal import Decimal

from django.db.models import Count
from django.utils import timezone

from apps.accounts.models import User
from apps.products.models import Product
from apps.suppliers.models import Supplier

logger = logging.getLogger(__name__)


class ActivityService:
    """Thin write helper for the ActivityEvent audit trail.

    Every instrumentation point (scraper check, store sync, discovery,
    etc.) calls ``ActivityService.record(...)`` so the event stays
    decoupled from the caller and the dashboard can query a single table
    for the full activity feed.
    """

    @staticmethod
    def record(owner, event_type, *, product=None, supplier=None, **payload):
        from apps.dashboard.models import ActivityEvent

        try:
            ActivityEvent.objects.create(
                owner=owner,
                event_type=event_type,
                product=product,
                supplier=supplier,
                payload=payload,
            )
        except Exception:  # pragma: no cover — never break the caller
            logger.exception("Failed to record activity event %s", event_type)


class DashboardService:
    """Read-only aggregation over Product/Supplier and ActivityEvent
    for the current user. No models of its own — this is intentionally
    a pure query layer.
    """

    @staticmethod
    def _products_by_status(owner: User) -> dict[str, int]:
        counts = {choice.value: 0 for choice in Product.Status}
        rows = Product.objects.filter(owner=owner).values("status").annotate(count=Count("id"))
        for row in rows:
            counts[row["status"]] = row["count"]
        return counts

    @staticmethod
    def _products_by_category(owner: User) -> list[dict]:
        rows = (
            Product.objects.filter(owner=owner)
            .exclude(category="")
            .values("category")
            .annotate(count=Count("id"))
            .order_by("-count", "category")
        )
        return [{"category": row["category"], "count": row["count"]} for row in rows]

    @staticmethod
    def _average_profit(owner: User) -> Decimal | None:
        """Average margin using the *effective* selling price (manual
        selling_price, else default markup, else supplier price) — so the
        dashboard number matches what the store actually charges.
        """
        from apps.pricing.services import DefaultMarkupService, PricingService

        products = list(
            Product.objects.filter(owner=owner, supplier_price__isnull=False).only(
                "supplier_price", "selling_price", "pricing_rule_id"
            )
        )
        markup = DefaultMarkupService.get_markup_percent(owner)
        margins = []
        for product in products:
            priced = (
                product.selling_price is not None
                or product.pricing_rule_id is not None
                or bool(markup)
            )
            if not priced:
                continue
            effective = PricingService.effective_selling_price(
                product.supplier_price,
                selling_price=product.selling_price,
                markup_percent=markup,
            )
            margins.append(effective - product.supplier_price)
        if not margins:
            return None
        return (sum(margins) / len(margins)).quantize(Decimal("0.01"))

    @staticmethod
    def get_summary(owner: User) -> dict:
        from apps.dashboard.models import ActivityEvent
        from apps.dashboard.serializers import ActivityEventSerializer
        from apps.pricing.services import DefaultMarkupService

        markup = DefaultMarkupService.get_markup_percent(owner)

        today = timezone.now().date()
        today_qs = ActivityEvent.objects.filter(owner=owner, created_at__date=today)

        return {
            "products_monitored": Product.objects.filter(
                owner=owner, status=Product.Status.ACTIVE
            ).count(),
            "suppliers_count": Supplier.objects.filter(owner=owner, is_active=True).count(),
            "products_by_status": DashboardService._products_by_status(owner),
            "products_by_category": DashboardService._products_by_category(owner),
            "average_profit": DashboardService._average_profit(owner),
            "default_markup": str(markup) if markup is not None else None,
            "todays_checks": today_qs.filter(
                event_type__in=[
                    ActivityEvent.EventType.CHECK_OK,
                    ActivityEvent.EventType.PRICE_CHANGE,
                    ActivityEvent.EventType.STOCK_CHANGE,
                    ActivityEvent.EventType.SCRAPE_FAILED,
                ]
            ).count(),
            "products_changed_today": today_qs.filter(
                event_type__in=[
                    ActivityEvent.EventType.PRICE_CHANGE,
                    ActivityEvent.EventType.STOCK_CHANGE,
                ]
            )
            .values("product")
            .distinct()
            .count(),
            "stock_changes_today": today_qs.filter(
                event_type=ActivityEvent.EventType.STOCK_CHANGE,
            ).count(),
            "failed_scrapes_today": today_qs.filter(
                event_type=ActivityEvent.EventType.SCRAPE_FAILED,
            ).count(),
            "recent_activity": ActivityEventSerializer(
                ActivityEvent.objects.filter(owner=owner)
                .select_related("product", "supplier")[:20],
                many=True,
            ).data,
        }
