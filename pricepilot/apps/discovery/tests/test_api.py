from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.discovery.models import DiscoveredProduct
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
    return Supplier.objects.create(
        owner=user, name="Jred Technologies", website="https://a.com", default_scraper="catlog"
    )


class TestDiscoveryList:
    def test_requires_auth(self):
        client = APIClient()
        response = client.get(reverse("discovery:list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_lists_own_discoveries(self, api_client, user, supplier):
        DiscoveredProduct.objects.create(
            owner=user, supplier=supplier, url="https://a.com/products/1", price=Decimal("10.00")
        )

        response = api_client.get(reverse("discovery:list"))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) == 1

    def test_excludes_other_users_discoveries(self, api_client, other_user):
        other_supplier = Supplier.objects.create(
            owner=other_user, name="Theirs", website="https://theirs.com"
        )
        DiscoveredProduct.objects.create(
            owner=other_user,
            supplier=other_supplier,
            url="https://theirs.com/products/1",
            price=Decimal("10.00"),
        )

        response = api_client.get(reverse("discovery:list"))

        assert response.data["data"] == []

    def test_filter_by_status(self, api_client, user, supplier):
        DiscoveredProduct.objects.create(
            owner=user,
            supplier=supplier,
            url="https://a.com/products/1",
            price=Decimal("10.00"),
            status=DiscoveredProduct.Status.PENDING,
        )
        DiscoveredProduct.objects.create(
            owner=user,
            supplier=supplier,
            url="https://a.com/products/2",
            price=Decimal("10.00"),
            status=DiscoveredProduct.Status.DISMISSED,
        )

        response = api_client.get(reverse("discovery:list"), {"status": "dismissed"})

        assert len(response.data["data"]) == 1
        assert response.data["data"][0]["status"] == "dismissed"


class TestDiscoveryImport:
    def test_import_creates_product(self, api_client, user, supplier):
        discovery = DiscoveredProduct.objects.create(
            owner=user,
            supplier=supplier,
            url="https://a.com/products/1",
            title="Nice Widget",
            price=Decimal("99.00"),
            currency="NGN",
        )
        url = reverse("discovery:import", args=[discovery.id])

        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["data"]["name"] == "Nice Widget"

    def test_import_with_overrides(self, api_client, user, supplier):
        discovery = DiscoveredProduct.objects.create(
            owner=user, supplier=supplier, url="https://a.com/products/1", price=None
        )
        url = reverse("discovery:import", args=[discovery.id])

        response = api_client.post(url, {"supplier_price": "55.00"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["data"]["supplier_price"] == "55.00"

    def test_import_without_price_or_override_fails(self, api_client, user, supplier):
        discovery = DiscoveredProduct.objects.create(
            owner=user, supplier=supplier, url="https://a.com/products/1", price=None
        )
        url = reverse("discovery:import", args=[discovery.id])

        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_import_other_users_discovery(self, api_client, other_user):
        other_supplier = Supplier.objects.create(
            owner=other_user, name="Theirs", website="https://theirs.com"
        )
        discovery = DiscoveredProduct.objects.create(
            owner=other_user,
            supplier=other_supplier,
            url="https://theirs.com/products/1",
            price=Decimal("10.00"),
        )
        url = reverse("discovery:import", args=[discovery.id])

        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDiscoveryDismiss:
    def test_dismiss_marks_status(self, api_client, user, supplier):
        discovery = DiscoveredProduct.objects.create(
            owner=user, supplier=supplier, url="https://a.com/products/1", price=Decimal("10.00")
        )
        url = reverse("discovery:dismiss", args=[discovery.id])

        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["status"] == "dismissed"

    def test_cannot_dismiss_other_users_discovery(self, api_client, other_user):
        other_supplier = Supplier.objects.create(
            owner=other_user, name="Theirs", website="https://theirs.com"
        )
        discovery = DiscoveredProduct.objects.create(
            owner=other_user,
            supplier=other_supplier,
            url="https://theirs.com/products/1",
            price=Decimal("10.00"),
        )
        url = reverse("discovery:dismiss", args=[discovery.id])

        response = api_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
