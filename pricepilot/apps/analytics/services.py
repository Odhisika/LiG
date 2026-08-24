from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F
from django.utils import timezone

from apps.accounts.models import User
from apps.common.exceptions import ValidationError
from apps.history.models import PriceHistory
from apps.products.models import Product


class AnalyticsService:
    """Read-only aggregate queries over PriceHistory and Product — the
    blueprint's Module 11 ("which supplier changes prices most", "most
    volatile products", "largest price swings", "profit impact"). Pure
    query layer, no models of its own, like DashboardService.
    """

    @staticmethod
    def _validate_params(days: int, limit: int) -> None:
        if days <= 0:
            raise ValidationError("days must be a positive integer.")
        if limit <= 0 or limit > 100:
            raise ValidationError("limit must be between 1 and 100.")

    @staticmethod
    def _history_in_period(owner: User, days: int):
        since = timezone.now() - timedelta(days=days)
        return PriceHistory.objects.filter(owner=owner, created_at__gte=since)

    @staticmethod
    def most_active_suppliers(owner: User, days: int, limit: int) -> list[dict]:
        rows = (
            AnalyticsService._history_in_period(owner, days)
            .values("product__supplier_id", "product__supplier__name")
            .annotate(change_count=Count("id"))
            .order_by("-change_count")[:limit]
        )
        return [
            {
                "supplier_id": row["product__supplier_id"],
                "supplier_name": row["product__supplier__name"],
                "change_count": row["change_count"],
            }
            for row in rows
        ]

    @staticmethod
    def most_volatile_products(owner: User, days: int, limit: int) -> list[dict]:
        rows = (
            AnalyticsService._history_in_period(owner, days)
            .values("product_id", "product__name")
            .annotate(change_count=Count("id"))
            .order_by("-change_count")[:limit]
        )
        return [
            {
                "product_id": row["product_id"],
                "product_name": row["product__name"],
                "change_count": row["change_count"],
            }
            for row in rows
        ]

    @staticmethod
    def _price_diff_queryset(owner: User, days: int):
        return (
            AnalyticsService._history_in_period(owner, days)
            .filter(price_changed=True)
            .select_related("product")
            .annotate(
                diff=ExpressionWrapper(
                    F("new_price") - F("old_price"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            )
        )

    @staticmethod
    def _serialize_diff_row(row: PriceHistory) -> dict:
        return {
            "product_id": row.product_id,
            "product_name": row.product.name,
            "old_price": row.old_price,
            "new_price": row.new_price,
            "diff": row.diff,
            "created_at": row.created_at,
        }

    @staticmethod
    def largest_price_increases(owner: User, days: int, limit: int) -> list[dict]:
        rows = AnalyticsService._price_diff_queryset(owner, days).order_by("-diff")[:limit]
        return [AnalyticsService._serialize_diff_row(r) for r in rows]

    @staticmethod
    def largest_price_decreases(owner: User, days: int, limit: int) -> list[dict]:
        rows = AnalyticsService._price_diff_queryset(owner, days).order_by("diff")[:limit]
        return [AnalyticsService._serialize_diff_row(r) for r in rows]

    @staticmethod
    def average_daily_changes(owner: User, days: int) -> Decimal:
        total = AnalyticsService._history_in_period(owner, days).count()
        return (Decimal(total) / Decimal(days)).quantize(Decimal("0.01"))

    @staticmethod
    def profit_impact(owner: User) -> dict:
        """Current potential profit across products that actually carry a
        margin — manual selling price, their own pricing rule, or the
        owner's default markup. Margins use the same *effective* selling
        price the store sync writes, so the analytics match the storefront.
        A snapshot, not a time series (there's no separate selling_price
        history table; only the supplier-side price is tracked over time).
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
            return {
                "total_potential_profit": Decimal("0"),
                "average_margin": None,
                "products_with_pricing": 0,
            }
        total = sum(margins)
        return {
            "total_potential_profit": total,
            "average_margin": (total / len(margins)).quantize(Decimal("0.01")),
            "products_with_pricing": len(margins),
        }

    @staticmethod
    def get_summary(owner: User, days: int = 30, limit: int = 10) -> dict:
        AnalyticsService._validate_params(days, limit)
        return {
            "period_days": days,
            "total_changes_in_period": AnalyticsService._history_in_period(owner, days).count(),
            "average_daily_changes": AnalyticsService.average_daily_changes(owner, days),
            "most_active_suppliers": AnalyticsService.most_active_suppliers(owner, days, limit),
            "most_volatile_products": AnalyticsService.most_volatile_products(owner, days, limit),
            "largest_price_increases": AnalyticsService.largest_price_increases(owner, days, limit),
            "largest_price_decreases": AnalyticsService.largest_price_decreases(owner, days, limit),
            "profit_impact": AnalyticsService.profit_impact(owner),
        }
