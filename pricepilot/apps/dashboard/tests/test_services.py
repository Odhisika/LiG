import pytest

from apps.accounts.models import User
from apps.dashboard.models import ActivityEvent
from apps.dashboard.services import ActivityService, DashboardService

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(email="owner@example.com", password="supersecret123")


class TestActivityService:
    def test_record_creates_event(self, user):
        ActivityService.record(
            user,
            ActivityEvent.EventType.CHECK_OK,
            stock=5,
        )
        assert ActivityEvent.objects.count() == 1
        event = ActivityEvent.objects.first()
        assert event.owner == user
        assert event.event_type == "check_ok"
        assert event.payload == {"stock": 5}

    def test_record_with_product_and_supplier(self, user):
        from apps.products.models import Product
        from apps.suppliers.models import Supplier

        supplier = Supplier.objects.create(owner=user, name="Ali", website="https://a.com")
        product = Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Widget",
            supplier_url="https://a.com/1",
            supplier_price=10,
        )
        ActivityService.record(
            user,
            ActivityEvent.EventType.PRICE_CHANGE,
            product=product,
            supplier=supplier,
            old_price="10.00",
            new_price="12.00",
        )
        event = ActivityEvent.objects.first()
        assert event.product == product
        assert event.supplier == supplier
        assert event.payload["old_price"] == "10.00"
        assert event.payload["new_price"] == "12.00"

    def test_record_does_not_raise_on_error(self, user):
        # The service swallows exceptions — never breaks the caller.
        ActivityService.record(
            user,
            "invalid_event_type",
        )
        # Should not raise; the event may or may not be created
        # depending on DB validation, but the caller is safe.


class TestDashboardServiceActivityFields:
    def test_todays_checks_populated(self, user):
        ActivityService.record(user, ActivityEvent.EventType.CHECK_OK)
        ActivityService.record(user, ActivityEvent.EventType.CHECK_OK)
        ActivityService.record(user, ActivityEvent.EventType.PRICE_CHANGE)

        summary = DashboardService.get_summary(user)
        assert summary["todays_checks"] == 3

    def test_products_changed_today_populated(self, user):
        from apps.products.models import Product
        from apps.suppliers.models import Supplier

        supplier = Supplier.objects.create(owner=user, name="Ali", website="https://a.com")
        p1 = Product.objects.create(
            owner=user, supplier=supplier, name="A",
            supplier_url="https://a.com/1", supplier_price=10,
        )
        p2 = Product.objects.create(
            owner=user, supplier=supplier, name="B",
            supplier_url="https://a.com/2", supplier_price=10,
        )
        ActivityService.record(user, ActivityEvent.EventType.PRICE_CHANGE, product=p1)
        ActivityService.record(user, ActivityEvent.EventType.PRICE_CHANGE, product=p1)
        ActivityService.record(user, ActivityEvent.EventType.STOCK_CHANGE, product=p2)

        summary = DashboardService.get_summary(user)
        assert summary["products_changed_today"] == 2

    def test_failed_scrapes_today_populated(self, user):
        ActivityService.record(user, ActivityEvent.EventType.SCRAPE_FAILED)
        ActivityService.record(user, ActivityEvent.EventType.SCRAPE_FAILED)

        summary = DashboardService.get_summary(user)
        assert summary["failed_scrapes_today"] == 2

    def test_stock_changes_today_populated(self, user):
        ActivityService.record(user, ActivityEvent.EventType.STOCK_CHANGE)
        ActivityService.record(user, ActivityEvent.EventType.PRICE_CHANGE)

        summary = DashboardService.get_summary(user)
        assert summary["stock_changes_today"] == 1

    def test_recent_activity_included(self, user):
        ActivityService.record(user, ActivityEvent.EventType.CHECK_OK)
        ActivityService.record(user, ActivityEvent.EventType.PRICE_CHANGE)

        summary = DashboardService.get_summary(user)
        assert len(summary["recent_activity"]) == 2

    def test_only_own_activity_counted(self, user):
        from apps.accounts.models import User as UserModel

        other = UserModel.objects.create_user(email="other@example.com", password="pw")
        ActivityService.record(user, ActivityEvent.EventType.CHECK_OK)
        ActivityService.record(other, ActivityEvent.EventType.SCRAPE_FAILED)

        summary = DashboardService.get_summary(user)
        assert summary["todays_checks"] == 1
        assert summary["failed_scrapes_today"] == 0
