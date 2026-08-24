from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.analytics.services import AnalyticsService
from apps.common.exceptions import ValidationError
from apps.history.models import PriceHistory
from apps.products.models import Product
from apps.suppliers.models import Supplier

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(email="owner@example.com", password="supersecret123")


@pytest.fixture
def other_user():
    return User.objects.create_user(email="other@example.com", password="supersecret123")


@pytest.fixture
def supplier_a(user):
    return Supplier.objects.create(owner=user, name="AliExpress", website="https://aliexpress.com")


@pytest.fixture
def supplier_b(user):
    return Supplier.objects.create(owner=user, name="Temu", website="https://temu.com")


def make_product(user, supplier, **overrides):
    defaults = {
        "owner": user,
        "supplier": supplier,
        "name": "Product",
        "supplier_url": "https://a.com",
        "supplier_price": Decimal("10.00"),
    }
    defaults.update(overrides)
    return Product.objects.create(**defaults)


def make_history(product, owner, *, days_ago=0, **overrides):
    defaults = {
        "product": product,
        "owner": owner,
        "old_price": Decimal("10.00"),
        "new_price": Decimal("12.00"),
        "price_changed": True,
        "stock_changed": False,
        "source": "catlog",
    }
    defaults.update(overrides)
    entry = PriceHistory.objects.create(**defaults)
    if days_ago:
        entry.created_at = timezone.now() - timedelta(days=days_ago)
        entry.save(update_fields=["created_at"])
    return entry


class TestValidation:
    def test_rejects_zero_days(self, user):
        with pytest.raises(ValidationError):
            AnalyticsService.get_summary(user, days=0, limit=10)

    def test_rejects_negative_days(self, user):
        with pytest.raises(ValidationError):
            AnalyticsService.get_summary(user, days=-5, limit=10)

    def test_rejects_limit_over_100(self, user):
        with pytest.raises(ValidationError):
            AnalyticsService.get_summary(user, days=30, limit=101)

    def test_rejects_zero_limit(self, user):
        with pytest.raises(ValidationError):
            AnalyticsService.get_summary(user, days=30, limit=0)


class TestMostActiveSuppliers:
    def test_ranks_suppliers_by_change_count(self, user, supplier_a, supplier_b):
        product_a = make_product(user, supplier_a, name="A")
        product_b = make_product(user, supplier_b, name="B")
        make_history(product_a, user)
        make_history(product_a, user)
        make_history(product_a, user)
        make_history(product_b, user)

        result = AnalyticsService.most_active_suppliers(user, days=30, limit=10)

        assert result[0]["supplier_name"] == "AliExpress"
        assert result[0]["change_count"] == 3
        assert result[1]["supplier_name"] == "Temu"
        assert result[1]["change_count"] == 1

    def test_respects_limit(self, user, supplier_a, supplier_b):
        product_a = make_product(user, supplier_a, name="A")
        product_b = make_product(user, supplier_b, name="B")
        make_history(product_a, user)
        make_history(product_b, user)

        result = AnalyticsService.most_active_suppliers(user, days=30, limit=1)

        assert len(result) == 1

    def test_excludes_other_owners(self, user, other_user, supplier_a):
        other_supplier = Supplier.objects.create(
            owner=other_user, name="Theirs", website="https://theirs.com"
        )
        other_product = make_product(other_user, other_supplier, name="Not Mine")
        make_history(other_product, other_user)

        result = AnalyticsService.most_active_suppliers(user, days=30, limit=10)

        assert result == []


class TestMostVolatileProducts:
    def test_ranks_products_by_change_count(self, user, supplier_a):
        volatile = make_product(user, supplier_a, name="Volatile")
        stable = make_product(user, supplier_a, name="Stable")
        make_history(volatile, user)
        make_history(volatile, user)
        make_history(stable, user)

        result = AnalyticsService.most_volatile_products(user, days=30, limit=10)

        assert result[0]["product_name"] == "Volatile"
        assert result[0]["change_count"] == 2


class TestPriceSwings:
    def test_largest_increase(self, user, supplier_a):
        product = make_product(user, supplier_a)
        make_history(product, user, old_price=Decimal("10.00"), new_price=Decimal("15.00"))
        make_history(product, user, old_price=Decimal("15.00"), new_price=Decimal("16.00"))

        result = AnalyticsService.largest_price_increases(user, days=30, limit=10)

        assert result[0]["diff"] == Decimal("5.00")

    def test_largest_decrease(self, user, supplier_a):
        product = make_product(user, supplier_a)
        make_history(product, user, old_price=Decimal("20.00"), new_price=Decimal("18.00"))
        make_history(product, user, old_price=Decimal("18.00"), new_price=Decimal("5.00"))

        result = AnalyticsService.largest_price_decreases(user, days=30, limit=10)

        assert result[0]["diff"] == Decimal("-13.00")

    def test_stock_only_changes_excluded(self, user, supplier_a):
        product = make_product(user, supplier_a)
        make_history(
            product,
            user,
            old_price=Decimal("10.00"),
            new_price=Decimal("10.00"),
            price_changed=False,
            stock_changed=True,
            old_stock=5,
            new_stock=2,
        )

        increases = AnalyticsService.largest_price_increases(user, days=30, limit=10)
        decreases = AnalyticsService.largest_price_decreases(user, days=30, limit=10)

        assert increases == []
        assert decreases == []


class TestDateWindow:
    def test_excludes_changes_outside_window(self, user, supplier_a):
        product = make_product(user, supplier_a)
        make_history(product, user, days_ago=45)  # outside a 30-day window

        result = AnalyticsService.most_volatile_products(user, days=30, limit=10)

        assert result == []

    def test_includes_changes_inside_window(self, user, supplier_a):
        product = make_product(user, supplier_a)
        make_history(product, user, days_ago=5)

        result = AnalyticsService.most_volatile_products(user, days=30, limit=10)

        assert len(result) == 1


class TestAverageDailyChanges:
    def test_computes_average_correctly(self, user, supplier_a):
        product = make_product(user, supplier_a)
        for _ in range(10):
            make_history(product, user)

        result = AnalyticsService.average_daily_changes(user, days=10)

        assert result == Decimal("1.00")


class TestProfitImpact:
    def test_computes_total_and_average_margin(self, user, supplier_a):
        make_product(
            user,
            supplier_a,
            name="A",
            supplier_price=Decimal("10.00"),
            selling_price=Decimal("15.00"),
        )
        make_product(
            user,
            supplier_a,
            name="B",
            supplier_price=Decimal("20.00"),
            selling_price=Decimal("30.00"),
        )

        result = AnalyticsService.profit_impact(user)

        assert result["total_potential_profit"] == Decimal("15.00")  # 5 + 10
        assert result["average_margin"] == Decimal("7.50")
        assert result["products_with_pricing"] == 2

    def test_ignores_products_without_selling_price(self, user, supplier_a):
        make_product(
            user,
            supplier_a,
            name="A",
            supplier_price=Decimal("10.00"),
            selling_price=Decimal("15.00"),
        )
        make_product(user, supplier_a, name="No price set", selling_price=None)

        result = AnalyticsService.profit_impact(user)

        assert result["products_with_pricing"] == 1
        assert result["total_potential_profit"] == Decimal("5.00")

    def test_empty_state_returns_zero_not_none(self, user):
        result = AnalyticsService.profit_impact(user)

        assert result["total_potential_profit"] == Decimal("0")
        assert result["average_margin"] is None
        assert result["products_with_pricing"] == 0


class TestGetSummary:
    def test_full_summary_shape(self, user, supplier_a):
        product = make_product(
            user, supplier_a, supplier_price=Decimal("10.00"), selling_price=Decimal("15.00")
        )
        make_history(product, user)

        summary = AnalyticsService.get_summary(user, days=30, limit=10)

        assert summary["period_days"] == 30
        assert summary["total_changes_in_period"] == 1
        assert len(summary["most_active_suppliers"]) == 1
        assert len(summary["most_volatile_products"]) == 1
        assert "profit_impact" in summary

    def test_uses_defaults_when_not_specified(self, user):
        summary = AnalyticsService.get_summary(user)

        assert summary["period_days"] == 30
