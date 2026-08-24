import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.notifications.models import NotificationEvent
from apps.notifications.services import NotificationService
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
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def supplier(user):
    return Supplier.objects.create(owner=user, name="AliExpress", website="https://aliexpress.com")


@pytest.fixture
def product(user, supplier):
    return Product.objects.create(
        owner=user,
        supplier=supplier,
        name="Widget",
        supplier_url="https://a.com",
        supplier_price=10,
    )


class TestNotificationList:
    def test_requires_auth(self):
        client = APIClient()
        response = client.get(reverse("notifications:list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_lists_own_events(self, api_client, user, product):
        NotificationService.record_event(
            user, NotificationEvent.EventType.PRODUCT_UPDATED, product=product
        )

        response = api_client.get(reverse("notifications:list"))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) == 1

    def test_does_not_include_other_users_events(self, api_client, other_user):
        other_supplier = Supplier.objects.create(
            owner=other_user, name="Theirs", website="https://theirs.com"
        )
        other_product = Product.objects.create(
            owner=other_user,
            supplier=other_supplier,
            name="Not Mine",
            supplier_url="https://x.com",
            supplier_price=10,
        )
        NotificationService.record_event(
            other_user, NotificationEvent.EventType.PRODUCT_UPDATED, product=other_product
        )

        response = api_client.get(reverse("notifications:list"))

        assert response.data["data"] == []

    def test_filter_by_event_type(self, api_client, user, product):
        NotificationService.record_event(
            user, NotificationEvent.EventType.PRODUCT_UPDATED, product=product
        )
        NotificationService.record_event(
            user, NotificationEvent.EventType.OUT_OF_STOCK, product=product
        )

        response = api_client.get(reverse("notifications:list"), {"event_type": "out_of_stock"})

        assert len(response.data["data"]) == 1
        assert response.data["data"][0]["event_type"] == "out_of_stock"

    def test_filter_by_sent_status(self, api_client, user, product):
        NotificationService.record_event(
            user, NotificationEvent.EventType.PRODUCT_UPDATED, product=product
        )
        NotificationService.send_pending_digests()
        NotificationService.record_event(
            user, NotificationEvent.EventType.OUT_OF_STOCK, product=product
        )

        response = api_client.get(reverse("notifications:list"), {"sent": "false"})

        assert len(response.data["data"]) == 1
        assert response.data["data"][0]["event_type"] == "out_of_stock"

    def test_includes_product_name(self, api_client, user, product):
        NotificationService.record_event(
            user, NotificationEvent.EventType.PRODUCT_UPDATED, product=product
        )

        response = api_client.get(reverse("notifications:list"))

        assert response.data["data"][0]["product_name"] == "Widget"
