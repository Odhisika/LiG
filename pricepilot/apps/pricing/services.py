import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.common.exceptions import NotFoundError, ValidationError
from apps.pricing.models import DefaultMarkup, PricingRule, PricingRuleStep
from apps.pricing.serializers import PricingRuleSerializer

logger = logging.getLogger(__name__)

TWO_PLACES = Decimal("0.01")


class PricingService:
    """Pure computation — no DB writes, no ownership concerns. Kept
    separate from PricingRuleService (CRUD) so the actual pricing math
    is trivially unit-testable against plain Decimal values.
    """

    @staticmethod
    def compute_from_steps(supplier_price: Decimal, steps: Iterable[PricingRuleStep]) -> Decimal:
        price = supplier_price
        for step in steps:
            price = step.apply(price)
        return price.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    @staticmethod
    def compute_selling_price(supplier_price: Decimal, rule: PricingRule) -> Decimal:
        return PricingService.compute_from_steps(supplier_price, rule.steps.all())

    @staticmethod
    def apply_markup(supplier_price: Decimal, markup_percent: Decimal) -> Decimal:
        """supplier_price + markup% of it, rounded to 2dp (half up)."""
        return (supplier_price + (supplier_price * markup_percent / Decimal(100))).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )

    @staticmethod
    def effective_selling_price(
        supplier_price: Decimal | None,
        *,
        selling_price: Decimal | None = None,
        markup_percent: Decimal | None = None,
    ) -> Decimal | None:
        """The price the store should show for a product.

        Precedence: an explicit manual selling price wins, then a default
        markup percentage, then the raw supplier price. None if there's
        nothing to price.
        """
        if supplier_price is None:
            return None
        if selling_price is not None:
            return selling_price.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        if markup_percent:
            return PricingService.apply_markup(supplier_price, markup_percent)
        return supplier_price.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


class DefaultMarkupService:
    """Owner-scoped access to the merchant's single default markup %.

    The markup is applied *dynamically* (see
    PricingService.effective_selling_price) rather than being written
    into each product's stored selling_price — that way it stays correct
    when supplier prices change and is trivially reversible, and a manual
    selling_price always wins over it.
    """

    @staticmethod
    def get_for_owner(owner: User) -> DefaultMarkup | None:
        return DefaultMarkup.objects.filter(owner=owner).first()

    @staticmethod
    def get_markup_percent(owner: User) -> Decimal | None:
        markup = DefaultMarkupService.get_for_owner(owner)
        if markup is None or not markup.is_active:
            return None
        return markup.markup_percent

    @staticmethod
    def eligible_products(owner: User):
        """Products that should use the owner's default markup.

        Scraped/imported products are included even before they have a
        remembered LiG store_product_id; StoreSyncService can seed or match
        them during sync. Manual selling prices and product-specific rules
        are intentionally excluded.
        """
        from apps.products.models import Product

        return Product.objects.filter(
            owner=owner,
            pricing_rule__isnull=True,
            selling_price__isnull=True,
        )

    @staticmethod
    def set_markup(owner: User, markup_percent) -> tuple[DefaultMarkup, int]:
        """Upsert the owner's default markup.

        Returns (markup, number of products that will use it — i.e. those
        without their own PricingRule). Products with a rule or a manual
        selling price are never touched by the default.
        """
        percent = Decimal(markup_percent)
        if percent < 0:
            raise ValidationError("Markup percentage cannot be negative.")

        markup, _ = DefaultMarkup.objects.update_or_create(
            owner=owner,
            defaults={"markup_percent": percent, "is_active": True},
        )

        affected = DefaultMarkupService.eligible_products(owner).count()
        return markup, affected


class PricingRuleService:
    """Owner-scoped CRUD for PricingRule + its steps, mirroring
    SupplierService/ProductService's pattern.
    """

    @staticmethod
    def list_for_owner(owner: User):
        return PricingRule.objects.filter(owner=owner)

    @staticmethod
    def get_for_owner(owner: User, rule_id) -> PricingRule:
        rule = PricingRule.objects.filter(owner=owner, id=rule_id).first()
        if rule is None:
            raise NotFoundError("Pricing rule not found.")
        return rule

    @staticmethod
    def _replace_steps(rule: PricingRule, steps_data: list[dict]) -> None:
        rule.steps.all().delete()
        PricingRuleStep.objects.bulk_create(
            [
                PricingRuleStep(
                    rule=rule,
                    order=i,
                    step_type=step["step_type"],
                    value=step["value"],
                )
                for i, step in enumerate(steps_data)
            ]
        )

    @staticmethod
    def _reprice_and_sync_products(rule: PricingRule) -> int:
        """Recompute stored selling_price for products using this rule and
        push affected products to LiG immediately.

        We sync every product attached to the rule because the sync service
        can update by remembered store id, resolve by sku, or seed a new row.
        """
        from apps.products.models import Product
        from apps.sync.services import StoreSyncService

        all_products = Product.objects.filter(owner=rule.owner, pricing_rule=rule)
        updated = 0
        for product in all_products.iterator():
            product.selling_price = PricingService.compute_selling_price(
                product.supplier_price, rule
            )
            product.save(update_fields=["selling_price"])
            updated += 1

        if updated:
            StoreSyncService.sync_all(all_products)
            logger.info(
                "Repriced and synced %d product(s) for pricing rule %s.", updated, rule.id
            )

        return updated

    @staticmethod
    def create(owner: User, data: dict) -> PricingRule:
        serializer = PricingRuleSerializer(data=data)
        if not serializer.is_valid():
            raise ValidationError(str(serializer.errors))

        steps_data = serializer.validated_data.pop("steps")
        try:
            with transaction.atomic():
                rule = PricingRule.objects.create(owner=owner, **serializer.validated_data)
                PricingRuleService._replace_steps(rule, steps_data)
        except IntegrityError as exc:
            raise ValidationError(
                f"A pricing rule named '{data.get('name')}' already exists."
            ) from exc
        return rule

    @staticmethod
    def update(
        owner: User, rule_id, data: dict, partial: bool = True, *, sync_lig: bool = False
    ) -> PricingRule:
        rule = PricingRuleService.get_for_owner(owner, rule_id)
        serializer = PricingRuleSerializer(rule, data=data, partial=partial)
        if not serializer.is_valid():
            raise ValidationError(str(serializer.errors))

        steps_data = serializer.validated_data.pop("steps", None)
        try:
            with transaction.atomic():
                rule = serializer.save()
                if steps_data is not None:
                    PricingRuleService._replace_steps(rule, steps_data)
        except IntegrityError as exc:
            raise ValidationError(
                f"A pricing rule named '{data.get('name')}' already exists."
            ) from exc
        if sync_lig:
            PricingRuleService._reprice_and_sync_products(rule)
        return rule

    @staticmethod
    def delete(owner: User, rule_id) -> None:
        rule = PricingRuleService.get_for_owner(owner, rule_id)
        rule.soft_delete()
