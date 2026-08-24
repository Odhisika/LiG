import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
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


class TestDashboardSummary:
    def test_requires_auth(self):
        client = APIClient()
        url = reverse("dashboard:summary")

        response = client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_state(self, api_client):
        url = reverse("dashboard:summary")

        response = api_client.get(url)

        data = response.data["data"]
        assert data["products_monitored"] == 0
        assert data["suppliers_count"] == 0
        assert data["average_profit"] is None
        assert data["products_by_status"] == {
            "active": 0,
            "paused": 0,
            "out_of_stock": 0,
            "scrape_failed": 0,
            "archived": 0,
        }

    def test_phase_2_fields_are_honest_placeholders(self, api_client):
        url = reverse("dashboard:summary")

        response = api_client.get(url)

        data = response.data["data"]
        assert data["products_changed_today"] == 0
        assert data["stock_changes_today"] == 0
        assert data["failed_scrapes_today"] == 0
        assert data["todays_checks"] == 0
        assert data["recent_activity"] == []

    def test_products_monitored_counts_only_active(self, api_client, user, supplier):
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Active",
            supplier_url="https://a.com",
            supplier_price=10,
            status=Product.Status.ACTIVE,
        )
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Paused",
            supplier_url="https://b.com",
            supplier_price=10,
            status=Product.Status.PAUSED,
        )
        url = reverse("dashboard:summary")

        response = api_client.get(url)

        assert response.data["data"]["products_monitored"] == 1

    def test_products_by_status_breakdown(self, api_client, user, supplier):
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="A",
            supplier_url="https://a.com",
            supplier_price=10,
            status=Product.Status.ACTIVE,
        )
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="B",
            supplier_url="https://b.com",
            supplier_price=10,
            status=Product.Status.ACTIVE,
        )
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="C",
            supplier_url="https://c.com",
            supplier_price=10,
            status=Product.Status.OUT_OF_STOCK,
        )
        url = reverse("dashboard:summary")

        response = api_client.get(url)

        breakdown = response.data["data"]["products_by_status"]
        assert breakdown["active"] == 2
        assert breakdown["out_of_stock"] == 1
        assert breakdown["paused"] == 0

    def test_average_profit_computed_correctly(self, api_client, user, supplier):
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="A",
            supplier_url="https://a.com",
            supplier_price=10,
            selling_price=15,
        )
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="B",
            supplier_url="https://b.com",
            supplier_price=20,
            selling_price=25,
        )
        url = reverse("dashboard:summary")

        response = api_client.get(url)

        # profits are 5 and 5 -> average 5.00
        assert str(response.data["data"]["average_profit"]) == "5.00"

    def test_average_profit_ignores_products_without_selling_price(
        self, api_client, user, supplier
    ):
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="A",
            supplier_url="https://a.com",
            supplier_price=10,
            selling_price=20,
        )
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="No selling price",
            supplier_url="https://b.com",
            supplier_price=10,
            selling_price=None,
        )
        url = reverse("dashboard:summary")

        response = api_client.get(url)

        # only the one product with a selling_price counts -> profit 10.00
        assert str(response.data["data"]["average_profit"]) == "10.00"

    def test_only_counts_current_users_data(self, api_client, other_user):
        other_supplier = Supplier.objects.create(
            owner=other_user, name="Theirs", website="https://theirs.com"
        )
        Product.objects.create(
            owner=other_user,
            supplier=other_supplier,
            name="Not Mine",
            supplier_url="https://x.com",
            supplier_price=10,
        )
        url = reverse("dashboard:summary")

        response = api_client.get(url)

        data = response.data["data"]
        assert data["products_monitored"] == 0
        assert data["suppliers_count"] == 0

    def test_default_markup_reported(self, api_client, user):
        url = reverse("dashboard:summary")

        response = api_client.get(url)

        assert response.data["data"]["default_markup"] is None

        from apps.pricing.services import DefaultMarkupService

        DefaultMarkupService.set_markup(user, "25")
        response = api_client.get(url)
        assert response.data["data"]["default_markup"] == "25.00"

    def test_products_by_category_breakdown(self, api_client, user, supplier):
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="A",
            supplier_url="https://a.com",
            supplier_price=10,
            category="UPS",
        )
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="B",
            supplier_url="https://b.com",
            supplier_price=10,
            category="UPS",
        )
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="C",
            supplier_url="https://c.com",
            supplier_price=10,
            category="Batteries",
        )
        url = reverse("dashboard:summary")

        response = api_client.get(url)

        breakdown = {
            item["category"]: item["count"] for item in response.data["data"]["products_by_category"]
        }
        assert breakdown == {"UPS": 2, "Batteries": 1}

    def test_products_by_category_excludes_empty_category(self, api_client, user, supplier):
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="No category",
            supplier_url="https://a.com",
            supplier_price=10,
            category="",
        )
        url = reverse("dashboard:summary")

        response = api_client.get(url)

        assert response.data["data"]["products_by_category"] == []

    def test_average_profit_uses_default_markup(self, api_client, user, supplier):
        from apps.pricing.services import DefaultMarkupService

        DefaultMarkupService.set_markup(user, "10")
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="A",
            supplier_url="https://a.com",
            supplier_price=100,
        )
        url = reverse("dashboard:summary")

        response = api_client.get(url)

        # 100 -> 110 with 10% markup, profit 10.00
        assert str(response.data["data"]["average_profit"]) == "10.00"
