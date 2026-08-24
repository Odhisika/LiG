from decimal import Decimal

import pytest

from apps.pricing.models import PricingRuleStep
from apps.pricing.services import PricingService


def step(step_type: str, value: str) -> PricingRuleStep:
    """Unsaved model instance — apply() is pure, no DB hit needed."""
    return PricingRuleStep(step_type=step_type, value=Decimal(value))


class TestMarkupPct:
    def test_simple_20_percent_markup(self):
        result = PricingService.compute_from_steps(
            Decimal("100.00"), [step(PricingRuleStep.StepType.MARKUP_PCT, "20")]
        )
        assert result == Decimal("120.00")

    def test_zero_percent_markup_is_noop(self):
        result = PricingService.compute_from_steps(
            Decimal("50.00"), [step(PricingRuleStep.StepType.MARKUP_PCT, "0")]
        )
        assert result == Decimal("50.00")


class TestFlatFeeAndShipping:
    def test_flat_fee_adds_directly(self):
        result = PricingService.compute_from_steps(
            Decimal("100.00"), [step(PricingRuleStep.StepType.FLAT_FEE, "15.00")]
        )
        assert result == Decimal("115.00")

    def test_shipping_adds_directly(self):
        result = PricingService.compute_from_steps(
            Decimal("100.00"), [step(PricingRuleStep.StepType.SHIPPING, "7.50")]
        )
        assert result == Decimal("107.50")


class TestTax:
    def test_tax_percent_applied_to_running_price(self):
        result = PricingService.compute_from_steps(
            Decimal("100.00"), [step(PricingRuleStep.StepType.TAX, "7.5")]
        )
        assert result == Decimal("107.50")


class TestFxConvert:
    def test_fx_conversion_multiplies(self):
        result = PricingService.compute_from_steps(
            Decimal("10.00"), [step(PricingRuleStep.StepType.FX_CONVERT, "1500")]
        )
        assert result == Decimal("15000.00")


class TestChainedSteps:
    def test_blueprint_example_cost_plus(self):
        # Supplier Price + Shipping + Tax + Profit, blueprint's own example
        steps = [
            step(PricingRuleStep.StepType.SHIPPING, "5.00"),
            step(PricingRuleStep.StepType.TAX, "10"),  # 10% tax on (price + shipping)
            step(PricingRuleStep.StepType.MARKUP_PCT, "20"),  # 20% profit margin on top
        ]
        # 100 -> +5 shipping = 105 -> +10% tax = 115.50 -> +20% markup = 138.60
        result = PricingService.compute_from_steps(Decimal("100.00"), steps)
        assert result == Decimal("138.60")

    def test_blueprint_example_fx_adjusted(self):
        # Supplier Price x Exchange Rate + Profit
        steps = [
            step(PricingRuleStep.StepType.FX_CONVERT, "1600"),  # USD -> NGN
            step(PricingRuleStep.StepType.MARKUP_PCT, "25"),
        ]
        # 10 -> x1600 = 16000 -> +25% = 20000.00
        result = PricingService.compute_from_steps(Decimal("10.00"), steps)
        assert result == Decimal("20000.00")

    def test_step_order_matters(self):
        # markup-then-fee vs fee-then-markup give different results —
        # proves steps are applied in the order given, not summed.
        markup_then_fee = [
            step(PricingRuleStep.StepType.MARKUP_PCT, "10"),
            step(PricingRuleStep.StepType.FLAT_FEE, "10.00"),
        ]
        fee_then_markup = [
            step(PricingRuleStep.StepType.FLAT_FEE, "10.00"),
            step(PricingRuleStep.StepType.MARKUP_PCT, "10"),
        ]

        result_a = PricingService.compute_from_steps(Decimal("100.00"), markup_then_fee)
        result_b = PricingService.compute_from_steps(Decimal("100.00"), fee_then_markup)

        assert result_a == Decimal("120.00")  # (100*1.1) + 10
        assert result_b == Decimal("121.00")  # (100+10) * 1.1
        assert result_a != result_b


class TestApplyMarkup:
    def test_simple_percentage(self):
        result = PricingService.apply_markup(Decimal("100.00"), Decimal("20"))
        assert result == Decimal("120.00")

    def test_zero_is_noop(self):
        result = PricingService.apply_markup(Decimal("50.00"), Decimal("0"))
        assert result == Decimal("50.00")

    def test_rounds_half_up(self):
        result = PricingService.apply_markup(Decimal("10.00"), Decimal("33.333"))
        assert result == Decimal("13.33")


class TestEffectiveSellingPrice:
    def test_none_supplier_price_returns_none(self):
        assert PricingService.effective_selling_price(None) is None

    def test_manual_selling_price_wins_over_markup(self):
        result = PricingService.effective_selling_price(
            Decimal("100.00"), selling_price=Decimal("999.99"), markup_percent=Decimal("20")
        )
        assert result == Decimal("999.99")

    def test_markup_applied_when_no_manual_price(self):
        result = PricingService.effective_selling_price(
            Decimal("100.00"), markup_percent=Decimal("25")
        )
        assert result == Decimal("125.00")

    def test_supplier_price_returned_when_no_markup(self):
        result = PricingService.effective_selling_price(Decimal("100.00"))
        assert result == Decimal("100.00")


class TestRoundingAndEdgeCases:
    def test_rounds_to_two_decimal_places(self):
        result = PricingService.compute_from_steps(
            Decimal("10.00"), [step(PricingRuleStep.StepType.MARKUP_PCT, "33.333")]
        )
        assert result == Decimal("13.33")

    def test_no_steps_returns_supplier_price_unchanged(self):
        result = PricingService.compute_from_steps(Decimal("42.00"), [])
        assert result == Decimal("42.00")

    def test_unknown_step_type_raises(self):
        bad_step = PricingRuleStep(step_type="not_a_real_type", value=Decimal("1"))
        with pytest.raises(ValueError):
            PricingService.compute_from_steps(Decimal("10.00"), [bad_step])
