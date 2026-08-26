import pytest

from apps.accounts.models import User
from apps.dashboard.models import ActivityEvent

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(email="owner@example.com", password="supersecret123")


class TestActivityEvent:
    def test_create_event(self, user):
        event = ActivityEvent.objects.create(
            owner=user,
            event_type=ActivityEvent.EventType.CHECK_OK,
            payload={"stock": 5},
        )
        assert event.event_type == "check_ok"
        assert event.payload == {"stock": 5}
        assert event.product is None
        assert event.supplier is None
        assert event.created_at is not None

    def test_str_with_product(self, user):
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
        event = ActivityEvent.objects.create(
            owner=user,
            event_type=ActivityEvent.EventType.PRICE_CHANGE,
            product=product,
        )
        assert "price_change" in str(event)
        assert str(product.id) in str(event)

    def test_ordering_is_newest_first(self, user):
        from django.utils import timezone

        e1 = ActivityEvent.objects.create(
            owner=user,
            event_type=ActivityEvent.EventType.CHECK_OK,
        )
        e2 = ActivityEvent.objects.create(
            owner=user,
            event_type=ActivityEvent.EventType.PRICE_CHANGE,
        )
        qs = list(ActivityEvent.objects.filter(owner=user))
        assert qs[0].id == e2.id
        assert qs[1].id == e1.id

    def test_event_type_choices(self):
        expected = {
            "check_ok", "price_change", "stock_change", "scrape_failed",
            "removed", "store_synced", "store_deleted", "discovered",
            "imported", "status_change",
        }
        actual = {choice.value for choice in ActivityEvent.EventType}
        assert expected == actual
