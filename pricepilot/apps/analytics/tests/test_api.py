from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.history.models import PriceHistory
from apps.products.models import Product
from apps.suppliers.models import Supplier

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(email="owner@example.com", password="supersecret123")


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


class TestAnalyticsSummaryAPI:
    def test_requires_auth(self):
        client = APIClient()
        response = client.get(reverse("analytics:summary"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_summary_with_defaults(self, api_client):
        response = api_client.get(reverse("analytics:summary"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["period_days"] == 30

    def test_respects_days_query_param(self, api_client):
        response = api_client.get(reverse("analytics:summary"), {"days": 7})

        assert response.data["data"]["period_days"] == 7

    def test_invalid_days_returns_400(self, api_client):
        response = api_client.get(reverse("analytics:summary"), {"days": 0})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_limit_returns_400(self, api_client):
        response = api_client.get(reverse("analytics:summary"), {"limit": 500})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_includes_real_history_data(self, api_client, user, product):
        PriceHistory.objects.create(
            product=product,
            owner=user,
            old_price=Decimal("10.00"),
            new_price=Decimal("15.00"),
            price_changed=True,
            stock_changed=False,
            source="catlog",
        )

        response = api_client.get(reverse("analytics:summary"))

        data = response.data["data"]
        assert data["total_changes_in_period"] == 1
        assert data["most_volatile_products"][0]["product_name"] == "Widget"
        assert data["largest_price_increases"][0]["diff"] == "5.00"
