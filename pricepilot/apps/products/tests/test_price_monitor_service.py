from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.accounts.models import User
from apps.common.exceptions import NotFoundError, ValidationError
from apps.history.models import PriceHistory
from apps.pricing.models import PricingRule, PricingRuleStep
from apps.products.models import Product
from apps.products.services import PriceMonitorService
from apps.scrapers.types import ScrapedProduct
from apps.suppliers.models import Supplier

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(email="owner@example.com", password="supersecret123")


@pytest.fixture
def supplier(user):
    return Supplier.objects.create(
        owner=user, name="AliExpress", website="https://aliexpress.com", default_scraper="catlog"
    )


def make_product(user, supplier, **overrides):
    defaults = {
        "owner": user,
        "supplier": supplier,
        "name": "Test Product",
        "supplier_url": "https://a.com",
        "supplier_price": Decimal("100.00"),
        "stock": 5,
        "status": Product.Status.ACTIVE,
    }
    defaults.update(overrides)
    return Product.objects.create(**defaults)


def mock_scraper(price, stock):
    fake = MagicMock()
    fake.fetch.return_value = ScrapedProduct(title="X", price=price, currency="NGN", stock=stock)
    return fake


class TestCheckProductHappyPath:
    def test_returns_none_and_no_history_when_unchanged(self, user, supplier):
        product = make_product(user, supplier, supplier_price=Decimal("100.00"), stock=5)
        fake = mock_scraper(Decimal("100.00"), 5)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            result = PriceMonitorService.check_product(product.id)

        assert result is None
        assert PriceHistory.objects.count() == 0

    def test_returns_history_row_on_price_change(self, user, supplier):
        product = make_product(user, supplier, supplier_price=Decimal("100.00"), stock=5)
        fake = mock_scraper(Decimal("150.00"), 5)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            result = PriceMonitorService.check_product(product.id)

        assert result is not None
        assert result.old_price == Decimal("100.00")
        assert result.new_price == Decimal("150.00")
        assert result.price_changed is True
        assert result.stock_changed is False

    def test_returns_history_row_on_stock_only_change(self, user, supplier):
        product = make_product(user, supplier, supplier_price=Decimal("100.00"), stock=5)
        fake = mock_scraper(Decimal("100.00"), 2)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            result = PriceMonitorService.check_product(product.id)

        assert result.price_changed is False
        assert result.stock_changed is True
        assert result.old_stock == 5
        assert result.new_stock == 2

    def test_product_fields_actually_updated(self, user, supplier):
        product = make_product(user, supplier, supplier_price=Decimal("100.00"), stock=5)
        fake = mock_scraper(Decimal("200.00"), 1)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            PriceMonitorService.check_product(product.id)

        product.refresh_from_db()
        assert product.supplier_price == Decimal("200.00")
        assert product.stock == 1
        assert product.last_checked_at is not None

    def test_history_source_records_scraper_key(self, user, supplier):
        product = make_product(user, supplier)
        fake = mock_scraper(Decimal("999.00"), 5)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            result = PriceMonitorService.check_product(product.id)

        assert result.source == "catlog"
        assert result.reason == PriceHistory.Reason.SCRAPE

    def test_history_owner_matches_product_owner(self, user, supplier):
        product = make_product(user, supplier)
        fake = mock_scraper(Decimal("999.00"), 5)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            result = PriceMonitorService.check_product(product.id)

        assert result.owner == user


class TestStatusTransitions:
    def test_stock_zero_sets_out_of_stock(self, user, supplier):
        product = make_product(user, supplier, status=Product.Status.ACTIVE, stock=5)
        fake = mock_scraper(Decimal("100.00"), 0)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            PriceMonitorService.check_product(product.id)

        product.refresh_from_db()
        assert product.status == Product.Status.OUT_OF_STOCK

    def test_restock_recovers_from_out_of_stock(self, user, supplier):
        product = make_product(
            user,
            supplier,
            status=Product.Status.OUT_OF_STOCK,
            stock=0,
            supplier_price=Decimal("100.00"),
        )
        fake = mock_scraper(Decimal("100.00"), 7)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            PriceMonitorService.check_product(product.id)

        product.refresh_from_db()
        assert product.status == Product.Status.ACTIVE

    def test_unchanged_scrape_recovers_from_scrape_failed(self, user, supplier):
        product = make_product(
            user,
            supplier,
            status=Product.Status.SCRAPE_FAILED,
            supplier_price=Decimal("100.00"),
            stock=5,
        )
        fake = mock_scraper(Decimal("100.00"), 5)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            result = PriceMonitorService.check_product(product.id)

        assert result is None
        product.refresh_from_db()
        assert product.status == Product.Status.ACTIVE

    def test_changed_scrape_recovers_from_scrape_failed(self, user, supplier):
        product = make_product(
            user,
            supplier,
            status=Product.Status.SCRAPE_FAILED,
            supplier_price=Decimal("100.00"),
            stock=5,
        )
        fake = mock_scraper(Decimal("150.00"), 5)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            PriceMonitorService.check_product(product.id)

        product.refresh_from_db()
        assert product.status == Product.Status.ACTIVE
        assert product.supplier_price == Decimal("150.00")

    def test_paused_status_not_disturbed_by_price_change(self, user, supplier):
        product = make_product(user, supplier, status=Product.Status.PAUSED, stock=5)
        fake = mock_scraper(Decimal("150.00"), 5)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            PriceMonitorService.check_product(product.id)

        product.refresh_from_db()
        assert product.status == Product.Status.PAUSED


class TestPricingRuleIntegration:
    def test_selling_price_recomputed_when_price_changes_and_rule_assigned(self, user, supplier):
        rule = PricingRule.objects.create(owner=user, name="20pct")
        PricingRuleStep.objects.create(
            rule=rule, order=0, step_type=PricingRuleStep.StepType.MARKUP_PCT, value=Decimal("20")
        )
        product = make_product(
            user,
            supplier,
            supplier_price=Decimal("100.00"),
            selling_price=Decimal("120.00"),
            pricing_rule=rule,
        )
        fake = mock_scraper(Decimal("200.00"), 5)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            PriceMonitorService.check_product(product.id)

        product.refresh_from_db()
        assert product.selling_price == Decimal("240.00")

    def test_selling_price_untouched_when_no_rule_assigned(self, user, supplier):
        product = make_product(
            user,
            supplier,
            supplier_price=Decimal("100.00"),
            selling_price=Decimal("150.00"),
            pricing_rule=None,
        )
        fake = mock_scraper(Decimal("200.00"), 5)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            PriceMonitorService.check_product(product.id)

        product.refresh_from_db()
        assert product.selling_price == Decimal("150.00")  # unchanged — manual pricing

    def test_selling_price_not_recomputed_when_only_stock_changed(self, user, supplier):
        rule = PricingRule.objects.create(owner=user, name="20pct")
        PricingRuleStep.objects.create(
            rule=rule, order=0, step_type=PricingRuleStep.StepType.MARKUP_PCT, value=Decimal("20")
        )
        product = make_product(
            user,
            supplier,
            supplier_price=Decimal("100.00"),
            selling_price=Decimal("999.00"),  # deliberately "wrong" to prove it's untouched
            stock=5,
            pricing_rule=rule,
        )
        fake = mock_scraper(Decimal("100.00"), 1)  # price unchanged, only stock differs

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            PriceMonitorService.check_product(product.id)

        product.refresh_from_db()
        assert product.selling_price == Decimal("999.00")

    def test_description_only_change_updates_product_and_triggers_store_sync(
        self, user, supplier
    ):
        product = make_product(user, supplier, description="Old description")
        fake = MagicMock()
        fake.fetch.return_value = ScrapedProduct(
            title="X",
            price=Decimal("100.00"),
            currency="NGN",
            stock=5,
            description="Fresh supplier description",
        )

        with (
            patch("apps.products.services.ScraperRegistry.get", return_value=fake),
            patch("apps.products.services.StoreSyncService.sync_product") as mock_sync,
        ):
            result = PriceMonitorService.check_product(product.id)

        product.refresh_from_db()
        assert result is None
        assert PriceHistory.objects.filter(product=product).count() == 0
        assert product.description == "Fresh supplier description"
        mock_sync.assert_called_once()


class TestNotificationIntegration:
    def test_product_updated_event_recorded_on_price_change(self, user, supplier):
        from apps.notifications.models import NotificationEvent

        product = make_product(user, supplier, supplier_price=Decimal("100.00"))
        fake = mock_scraper(Decimal("150.00"), 5)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            PriceMonitorService.check_product(product.id)

        events = NotificationEvent.objects.filter(
            owner=user, event_type=NotificationEvent.EventType.PRODUCT_UPDATED
        )
        assert events.count() == 1
        assert events.first().product == product

    def test_no_event_recorded_when_nothing_changed(self, user, supplier):
        from apps.notifications.models import NotificationEvent

        product = make_product(user, supplier, supplier_price=Decimal("100.00"), stock=5)
        fake = mock_scraper(Decimal("100.00"), 5)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            PriceMonitorService.check_product(product.id)

        assert NotificationEvent.objects.filter(owner=user).count() == 0

    def test_out_of_stock_event_only_on_transition(self, user, supplier):
        from apps.notifications.models import NotificationEvent

        product = make_product(
            user, supplier, supplier_price=Decimal("100.00"), stock=5, status=Product.Status.ACTIVE
        )
        fake = mock_scraper(Decimal("100.00"), 0)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            PriceMonitorService.check_product(product.id)

        events = NotificationEvent.objects.filter(
            owner=user, event_type=NotificationEvent.EventType.OUT_OF_STOCK
        )
        assert events.count() == 1

    def test_no_repeat_out_of_stock_event_while_still_out_of_stock(self, user, supplier):
        from apps.notifications.models import NotificationEvent

        product = make_product(
            user,
            supplier,
            supplier_price=Decimal("100.00"),
            stock=0,
            status=Product.Status.OUT_OF_STOCK,
        )
        # Price changes while still out of stock (stock stays 0 -> 0, no stock_changed,
        # but price_changed triggers the update branch regardless).
        fake = mock_scraper(Decimal("90.00"), 0)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            PriceMonitorService.check_product(product.id)

        events = NotificationEvent.objects.filter(
            owner=user, event_type=NotificationEvent.EventType.OUT_OF_STOCK
        )
        assert events.count() == 0  # already was out of stock — no repeat event


class TestFailureModes:
    def test_raises_not_found_for_missing_product(self):
        with pytest.raises(NotFoundError):
            PriceMonitorService.check_product("00000000-0000-0000-0000-000000000000")

    def test_raises_validation_error_when_no_scraper_configured(self, user):
        supplier_no_scraper = Supplier.objects.create(
            owner=user, name="NoScraper", website="https://x.com", default_scraper=""
        )
        product = make_product(user, supplier_no_scraper)

        with pytest.raises(ValidationError):
            PriceMonitorService.check_product(product.id)

    def test_scraper_error_propagates_uncaught(self, user, supplier):
        from apps.common.exceptions import ScraperError

        product = make_product(user, supplier)
        fake = MagicMock()
        fake.fetch.side_effect = ScraperError("boom")

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake):
            with pytest.raises(ScraperError):
                PriceMonitorService.check_product(product.id)
