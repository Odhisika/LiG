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


def make_history(product, owner, **overrides):
    defaults = {
        "product": product,
        "owner": owner,
        "old_price": Decimal("10.00"),
        "new_price": Decimal("12.00"),
        "old_stock": 5,
        "new_stock": 3,
        "price_changed": True,
        "stock_changed": True,
        "source": "catlog",
    }
    defaults.update(overrides)
    return PriceHistory.objects.create(**defaults)


class TestHistoryList:
    def test_requires_auth(self):
        client = APIClient()
        response = client.get(reverse("history:list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_lists_own_history(self, api_client, user, product):
        make_history(product, user)
        response = api_client.get(reverse("history:list"))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) == 1

    def test_does_not_include_other_users_history(self, api_client, other_user):
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
        make_history(other_product, other_user)

        response = api_client.get(reverse("history:list"))

        assert response.data["data"] == []

    def test_filter_by_product(self, api_client, user, supplier, product):
        other_product = Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Other",
            supplier_url="https://b.com",
            supplier_price=5,
        )
        make_history(product, user)
        make_history(other_product, user)

        response = api_client.get(reverse("history:list"), {"product": str(product.id)})

        assert len(response.data["data"]) == 1
        assert response.data["data"][0]["product"] == product.id

    def test_price_diff_computed(self, api_client, user, product):
        make_history(product, user, old_price=Decimal("10.00"), new_price=Decimal("15.00"))

        response = api_client.get(reverse("history:list"))

        assert response.data["data"][0]["price_diff"] == Decimal("5.00")

    def test_stock_diff_computed(self, api_client, user, product):
        make_history(product, user, old_stock=10, new_stock=4)

        response = api_client.get(reverse("history:list"))

        assert response.data["data"][0]["stock_diff"] == -6

    def test_ordered_newest_first(self, api_client, user, product):
        first = make_history(product, user, new_price=Decimal("11.00"))
        second = make_history(product, user, new_price=Decimal("12.00"))

        response = api_client.get(reverse("history:list"))

        ids = [row["id"] for row in response.data["data"]]
        assert ids == [str(second.id), str(first.id)]


class TestHistoryDetail:
    def test_get_own_entry(self, api_client, user, product):
        entry = make_history(product, user)
        response = api_client.get(reverse("history:detail", args=[entry.id]))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["id"] == str(entry.id)

    def test_cannot_get_other_users_entry(self, api_client, other_user):
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
        entry = make_history(other_product, other_user)

        response = api_client.get(reverse("history:detail", args=[entry.id]))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_history_is_read_only(self, api_client, user, product):
        entry = make_history(product, user)
        url = reverse("history:detail", args=[entry.id])

        # No PATCH/PUT/DELETE routes exist for history — verify the
        # method isn't even allowed at the URL level.
        response = api_client.patch(url, {"new_price": "999.00"})

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
