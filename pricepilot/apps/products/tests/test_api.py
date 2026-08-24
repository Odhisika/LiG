import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.pricing.models import PricingRule
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
def supplier(user):
    return Supplier.objects.create(owner=user, name="AliExpress", website="https://aliexpress.com")


@pytest.fixture
def other_supplier(other_user):
    return Supplier.objects.create(owner=other_user, name="Temu", website="https://temu.com")


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def product_payload(supplier, **overrides):
    payload = {
        "supplier": str(supplier.id),
        "name": "Wireless Earbuds",
        "supplier_url": "https://aliexpress.com/item/123",
        "sku": "WE-001",
        "supplier_price": "12.50",
        "currency": "USD",
    }
    payload.update(overrides)
    return payload


class TestProductCreate:
    def test_create_product(self, api_client, user, supplier):
        url = reverse("products:list-create")

        response = api_client.post(url, product_payload(supplier))

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["data"]["name"] == "Wireless Earbuds"
        assert response.data["data"]["supplier_name"] == "AliExpress"
        product = Product.objects.get(sku="WE-001")
        assert product.owner == user
        assert product.status == Product.Status.ACTIVE

    def test_create_requires_auth(self, supplier):
        client = APIClient()
        url = reverse("products:list-create")

        response = client.post(url, product_payload(supplier))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cannot_create_against_another_owners_supplier(self, api_client, other_supplier):
        url = reverse("products:list-create")

        response = api_client.post(url, product_payload(other_supplier))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Product.objects.count() == 0

    def test_cannot_create_with_another_owners_pricing_rule(self, api_client, supplier, other_user):
        other_rule = PricingRule.objects.create(owner=other_user, name="Not Mine")
        url = reverse("products:list-create")

        response = api_client.post(url, product_payload(supplier, pricing_rule=str(other_rule.id)))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Product.objects.count() == 0

    def test_duplicate_sku_for_same_owner_rejected(self, api_client, supplier):
        url = reverse("products:list-create")
        api_client.post(url, product_payload(supplier))

        response = api_client.post(url, product_payload(supplier, name="Different Name"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_blank_sku_does_not_collide(self, api_client, supplier):
        url = reverse("products:list-create")
        api_client.post(url, product_payload(supplier, sku=""))

        response = api_client.post(url, product_payload(supplier, sku="", name="Second Product"))

        assert response.status_code == status.HTTP_201_CREATED

    def test_negative_price_rejected(self, api_client, supplier):
        url = reverse("products:list-create")

        response = api_client.post(url, product_payload(supplier, supplier_price="-5.00"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_check_frequency_rejected(self, api_client, supplier):
        url = reverse("products:list-create")

        response = api_client.post(url, product_payload(supplier, check_frequency_minutes=0))

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestProductList:
    def test_list_only_returns_own_products(
        self, api_client, user, other_user, supplier, other_supplier
    ):
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Mine",
            supplier_url="https://a.com",
            supplier_price=1,
        )
        Product.objects.create(
            owner=other_user,
            supplier=other_supplier,
            name="TheirsNotMine",
            supplier_url="https://b.com",
            supplier_price=1,
        )
        url = reverse("products:list-create")

        response = api_client.get(url)

        names = [p["name"] for p in response.data["data"]]
        assert names == ["Mine"]

    def test_filter_by_status(self, api_client, user, supplier):
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Active One",
            supplier_url="https://a.com",
            supplier_price=1,
            status=Product.Status.ACTIVE,
        )
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Paused One",
            supplier_url="https://b.com",
            supplier_price=1,
            status=Product.Status.PAUSED,
        )
        url = reverse("products:list-create")

        response = api_client.get(url, {"status": "paused"})

        names = [p["name"] for p in response.data["data"]]
        assert names == ["Paused One"]

    def test_filter_by_category(self, api_client, user, supplier):
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="UPS One",
            supplier_url="https://a.com",
            supplier_price=1,
            category="UPS",
        )
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Battery One",
            supplier_url="https://b.com",
            supplier_price=1,
            category="Batteries",
        )
        url = reverse("products:list-create")

        response = api_client.get(url, {"category": "UPS"})

        names = [p["name"] for p in response.data["data"]]
        assert names == ["UPS One"]

    def test_list_categories(self, api_client, user, supplier):
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="A",
            supplier_url="https://a.com",
            supplier_price=1,
            category="UPS",
        )
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="B",
            supplier_url="https://b.com",
            supplier_price=1,
            category="UPS",
        )
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="C",
            supplier_url="https://c.com",
            supplier_price=1,
            category="Batteries",
        )
        url = reverse("products:categories")

        response = api_client.get(url)

        assert response.data["data"] == ["Batteries", "UPS"]

    def test_list_categories_empty(self, api_client):
        url = reverse("products:categories")

        response = api_client.get(url)

        assert response.data["data"] == []


class TestProductDetail:
    def test_get_own_product(self, api_client, user, supplier):
        product = Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Mine",
            supplier_url="https://a.com",
            supplier_price=1,
        )
        url = reverse("products:detail", args=[product.id])

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_cannot_get_other_users_product(self, api_client, other_user, other_supplier):
        product = Product.objects.create(
            owner=other_user,
            supplier=other_supplier,
            name="Theirs",
            supplier_url="https://a.com",
            supplier_price=1,
        )
        url = reverse("products:detail", args=[product.id])

        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_updates_product(self, api_client, user, supplier):
        product = Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Mine",
            supplier_url="https://a.com",
            supplier_price=1,
        )
        url = reverse("products:detail", args=[product.id])

        response = api_client.patch(url, {"stock": 42, "status": "out_of_stock"})

        assert response.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.stock == 42
        assert product.status == "out_of_stock"

    def test_patch_cannot_reassign_to_another_owners_supplier(
        self, api_client, user, supplier, other_supplier
    ):
        product = Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Mine",
            supplier_url="https://a.com",
            supplier_price=1,
        )
        url = reverse("products:detail", args=[product.id])

        response = api_client.patch(url, {"supplier": str(other_supplier.id)})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_patch_cannot_assign_another_owners_pricing_rule(
        self, api_client, user, supplier, other_user
    ):
        other_rule = PricingRule.objects.create(owner=other_user, name="Not Mine")
        product = Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Mine",
            supplier_url="https://a.com",
            supplier_price=1,
        )
        url = reverse("products:detail", args=[product.id])

        response = api_client.patch(url, {"pricing_rule": str(other_rule.id)})

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_patch_can_assign_own_pricing_rule(self, api_client, user, supplier):
        rule = PricingRule.objects.create(owner=user, name="Mine")
        product = Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Mine",
            supplier_url="https://a.com",
            supplier_price=1,
        )
        url = reverse("products:detail", args=[product.id])

        response = api_client.patch(url, {"pricing_rule": str(rule.id)})

        assert response.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.pricing_rule_id == rule.id

    def test_delete_is_soft_delete(self, api_client, user, supplier):
        product = Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Mine",
            supplier_url="https://a.com",
            supplier_price=1,
        )
        url = reverse("products:detail", args=[product.id])

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Product.objects.filter(id=product.id).count() == 0
        assert Product.all_objects.filter(id=product.id).count() == 1
