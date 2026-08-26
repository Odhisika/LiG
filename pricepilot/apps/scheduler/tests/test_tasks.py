from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from celery.exceptions import Retry
from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import User
from apps.common.exceptions import ProductNotFoundOnSupplier, ScraperError
from apps.history.models import PriceHistory
from apps.products.models import Product
from apps.scheduler.tasks import (
    MAX_SCRAPE_RETRIES,
    _due_products,
    _lock_key,
    check_product_task,
    enqueue_due_product_checks,
)
from apps.scrapers.types import ScrapedProduct
from apps.suppliers.models import Supplier

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user():
    return User.objects.create_user(email="owner@example.com", password="supersecret123")


@pytest.fixture
def supplier(user):
    return Supplier.objects.create(owner=user, name="AliExpress", website="https://aliexpress.com")


def make_product(user, supplier, **overrides):
    defaults = {
        "owner": user,
        "supplier": supplier,
        "name": "Test Product",
        "supplier_url": "https://a.com",
        "supplier_price": 10,
        "status": Product.Status.ACTIVE,
        "check_frequency_minutes": 60,
    }
    defaults.update(overrides)
    return Product.objects.create(**defaults)


class TestDueProducts:
    def test_never_checked_is_due(self, user, supplier):
        product = make_product(user, supplier, last_checked_at=None)

        assert product in _due_products()

    def test_recently_checked_is_not_due(self, user, supplier):
        product = make_product(
            user, supplier, last_checked_at=timezone.now(), check_frequency_minutes=60
        )

        assert product not in _due_products()

    def test_checked_past_frequency_is_due(self, user, supplier):
        product = make_product(
            user,
            supplier,
            last_checked_at=timezone.now() - timedelta(minutes=61),
            check_frequency_minutes=60,
        )

        assert product in _due_products()

    def test_checked_just_under_frequency_is_not_due(self, user, supplier):
        product = make_product(
            user,
            supplier,
            last_checked_at=timezone.now() - timedelta(minutes=30),
            check_frequency_minutes=60,
        )

        assert product not in _due_products()

    def test_paused_product_is_never_due(self, user, supplier):
        product = make_product(user, supplier, status=Product.Status.PAUSED, last_checked_at=None)

        assert product not in _due_products()

    def test_respects_per_product_frequency(self, user, supplier):
        frequent = make_product(
            user,
            supplier,
            name="Frequent",
            last_checked_at=timezone.now() - timedelta(minutes=10),
            check_frequency_minutes=5,
        )
        infrequent = make_product(
            user,
            supplier,
            name="Infrequent",
            last_checked_at=timezone.now() - timedelta(minutes=10),
            check_frequency_minutes=120,
        )

        due = list(_due_products())

        assert frequent in due
        assert infrequent not in due


class TestEnqueueDueProductChecks:
    @patch("apps.scheduler.tasks.check_product_task.delay")
    def test_enqueues_due_products(self, mock_delay, user, supplier):
        product = make_product(user, supplier, last_checked_at=None)

        count = enqueue_due_product_checks()

        assert count == 1
        mock_delay.assert_called_once_with(str(product.id))

    @patch("apps.scheduler.tasks.check_product_task.delay")
    def test_skips_products_not_due(self, mock_delay, user, supplier):
        make_product(user, supplier, last_checked_at=timezone.now())

        count = enqueue_due_product_checks()

        assert count == 0
        mock_delay.assert_not_called()

    @patch("apps.scheduler.tasks.check_product_task.delay")
    def test_does_not_double_enqueue_within_lock_window(self, mock_delay, user, supplier):
        make_product(user, supplier, last_checked_at=None)

        first_count = enqueue_due_product_checks()
        second_count = enqueue_due_product_checks()

        assert first_count == 1
        assert second_count == 0  # still locked
        mock_delay.assert_called_once()

    @patch("apps.scheduler.tasks.check_product_task.delay")
    def test_multiple_due_products_all_enqueued(self, mock_delay, user, supplier):
        make_product(user, supplier, name="A", last_checked_at=None)
        make_product(user, supplier, name="B", last_checked_at=None)

        count = enqueue_due_product_checks()

        assert count == 2
        assert mock_delay.call_count == 2


def run_task(product_id: str, retries: int = 0):
    """Calls check_product_task directly (synchronous, in-process) with a
    controlled `self.request.retries` value, using Celery's own
    push_request/pop_request test helpers — avoids needing a real broker.
    """
    check_product_task.push_request(retries=retries)
    try:
        return check_product_task(product_id)
    finally:
        check_product_task.pop_request()


class TestCheckProductTaskNoScraperConfigured:
    """Products in these tests have no default_scraper set (the fixture's
    Supplier leaves it blank) — PriceMonitorService raises ValidationError
    before ever touching a scraper, which is itself worth covering.
    """

    def test_updates_last_checked_at_even_on_config_failure(self, user, supplier):
        product = make_product(user, supplier, last_checked_at=None)

        run_task(str(product.id))

        product.refresh_from_db()
        assert product.last_checked_at is not None

    def test_marks_scrape_failed_immediately_no_retry(self, user, supplier):
        product = make_product(user, supplier)

        run_task(str(product.id))

        product.refresh_from_db()
        assert product.status == Product.Status.SCRAPE_FAILED

    def test_config_failure_records_notification_event(self, user, supplier):
        from apps.notifications.models import NotificationEvent

        product = make_product(user, supplier)

        run_task(str(product.id))

        assert NotificationEvent.objects.filter(
            owner=user, event_type=NotificationEvent.EventType.SCRAPE_FAILED, product=product
        ).exists()

    def test_releases_lock_after_running(self, user, supplier):
        product = make_product(user, supplier, last_checked_at=None)
        cache.add(_lock_key(product.id), "1", timeout=300)

        run_task(str(product.id))

        assert cache.get(_lock_key(product.id)) is None

    def test_handles_missing_product_without_raising(self):
        # Should log and return, not raise — a product could be deleted
        # between being enqueued and the task actually running.
        run_task("00000000-0000-0000-0000-000000000000")


class TestCheckProductTaskSupplierRemoval:
    def test_404_marks_out_of_stock_and_deletes_store_row(self, user, supplier):
        product = make_product(user, supplier)

        with (
            patch("apps.products.services.PriceMonitorService.check_product", side_effect=ProductNotFoundOnSupplier("gone")),
            patch("apps.scheduler.tasks.StoreSyncService.delete_product") as mock_delete,
        ):
            run_task(str(product.id))

        product.refresh_from_db()
        assert product.status == Product.Status.OUT_OF_STOCK
        assert product.stock == 0
        mock_delete.assert_called_once()


class TestCheckProductTaskPriceMonitoring:
    """Products here have a mocked scraper wired in via
    ScraperRegistry.get, so PriceMonitorService runs its full compare
    + record + apply logic.
    """

    def _mock_scraper(self, price=None, stock=None):
        fake = MagicMock()
        fake.fetch.return_value = ScrapedProduct(
            title="Mock Product", price=price, currency="NGN", stock=stock
        )
        return fake

    def test_writes_history_and_updates_product_on_change(self, user, supplier):
        supplier.default_scraper = "catlog"
        supplier.save()
        product = make_product(
            user, supplier, supplier_price=Decimal("100.00"), stock=5, last_checked_at=None
        )
        fake_scraper = self._mock_scraper(price=Decimal("120.00"), stock=3)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake_scraper):
            run_task(str(product.id))

        product.refresh_from_db()
        assert product.supplier_price == Decimal("120.00")
        assert product.stock == 3
        assert product.status != Product.Status.SCRAPE_FAILED
        assert PriceHistory.objects.filter(product=product).count() == 1

    def test_no_history_written_when_nothing_changed(self, user, supplier):
        supplier.default_scraper = "catlog"
        supplier.save()
        product = make_product(user, supplier, supplier_price=Decimal("100.00"), stock=5)
        fake_scraper = self._mock_scraper(price=Decimal("100.00"), stock=5)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake_scraper):
            run_task(str(product.id))

        assert PriceHistory.objects.filter(product=product).count() == 0
        product.refresh_from_db()
        assert product.last_checked_at is not None

    def test_stock_zero_marks_out_of_stock(self, user, supplier):
        supplier.default_scraper = "catlog"
        supplier.save()
        product = make_product(user, supplier, supplier_price=Decimal("50.00"), stock=5)
        fake_scraper = self._mock_scraper(price=Decimal("50.00"), stock=0)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake_scraper):
            run_task(str(product.id))

        product.refresh_from_db()
        assert product.status == Product.Status.OUT_OF_STOCK

    def test_restock_auto_recovers_status(self, user, supplier):
        supplier.default_scraper = "catlog"
        supplier.save()
        product = make_product(
            user,
            supplier,
            supplier_price=Decimal("50.00"),
            stock=0,
            status=Product.Status.OUT_OF_STOCK,
        )
        fake_scraper = self._mock_scraper(price=Decimal("50.00"), stock=10)

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake_scraper):
            run_task(str(product.id))

        product.refresh_from_db()
        assert product.status == Product.Status.ACTIVE


class TestCheckProductTaskRetryBehavior:
    def test_retries_transient_scraper_error_before_max(self, user, supplier):
        supplier.default_scraper = "catlog"
        supplier.save()
        product = make_product(user, supplier)
        fake_scraper = MagicMock()
        fake_scraper.fetch.side_effect = ScraperError("temporary network blip")

        with (
            patch("apps.products.services.ScraperRegistry.get", return_value=fake_scraper),
            patch.object(check_product_task, "retry", side_effect=Retry()) as mock_retry,
            pytest.raises(Retry),
        ):
            run_task(str(product.id), retries=0)

        mock_retry.assert_called_once()
        product.refresh_from_db()
        assert product.status != Product.Status.SCRAPE_FAILED

    def test_marks_scrape_failed_once_retries_exhausted(self, user, supplier):
        supplier.default_scraper = "catlog"
        supplier.save()
        product = make_product(user, supplier)
        fake_scraper = MagicMock()
        fake_scraper.fetch.side_effect = ScraperError("still failing")

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake_scraper):
            run_task(str(product.id), retries=MAX_SCRAPE_RETRIES)

        product.refresh_from_db()
        assert product.status == Product.Status.SCRAPE_FAILED

    def test_exhausted_retries_records_notification_event(self, user, supplier):
        from apps.notifications.models import NotificationEvent

        supplier.default_scraper = "catlog"
        supplier.save()
        product = make_product(user, supplier)
        fake_scraper = MagicMock()
        fake_scraper.fetch.side_effect = ScraperError("still failing")

        with patch("apps.products.services.ScraperRegistry.get", return_value=fake_scraper):
            run_task(str(product.id), retries=MAX_SCRAPE_RETRIES)

        assert NotificationEvent.objects.filter(
            owner=user, event_type=NotificationEvent.EventType.SCRAPE_FAILED, product=product
        ).exists()

    def test_lock_released_even_when_retry_raised(self, user, supplier):
        supplier.default_scraper = "catlog"
        supplier.save()
        product = make_product(user, supplier)
        cache.add(_lock_key(product.id), "1", timeout=300)
        fake_scraper = MagicMock()
        fake_scraper.fetch.side_effect = ScraperError("temporary network blip")

        with (
            patch("apps.products.services.ScraperRegistry.get", return_value=fake_scraper),
            patch.object(check_product_task, "retry", side_effect=Retry()),
            pytest.raises(Retry),
        ):
            run_task(str(product.id), retries=0)

        assert cache.get(_lock_key(product.id)) is None
