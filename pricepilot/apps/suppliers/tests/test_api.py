import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
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


class TestSupplierCreate:
    def test_create_supplier(self, api_client, user):
        url = reverse("suppliers:list-create")
        payload = {
            "name": "AliExpress",
            "website": "https://aliexpress.com",
            "country": "China",
            "currency": "CNY",
            "rate_limit_per_minute": 5,
        }

        response = api_client.post(url, payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["data"]["name"] == "AliExpress"
        supplier = Supplier.objects.get(name="AliExpress")
        assert supplier.owner == user

    def test_create_requires_auth(self):
        client = APIClient()
        url = reverse("suppliers:list-create")

        response = client.post(url, {"name": "X", "website": "https://x.com"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_duplicate_name_for_same_owner_rejected(self, api_client):
        url = reverse("suppliers:list-create")
        payload = {"name": "Temu", "website": "https://temu.com"}

        api_client.post(url, payload)
        response = api_client.post(url, payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_same_name_allowed_for_different_owners(self, api_client, other_user):
        url = reverse("suppliers:list-create")
        payload = {"name": "Temu", "website": "https://temu.com"}
        api_client.post(url, payload)

        other_client = APIClient()
        other_client.force_authenticate(user=other_user)
        response = other_client.post(url, payload)

        assert response.status_code == status.HTTP_201_CREATED

    def test_invalid_rate_limit_rejected(self, api_client):
        url = reverse("suppliers:list-create")
        payload = {"name": "BadRate", "website": "https://bad.com", "rate_limit_per_minute": 0}

        response = api_client.post(url, payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestSupplierList:
    def test_list_only_returns_own_suppliers(self, api_client, user, other_user):
        Supplier.objects.create(owner=user, name="Mine", website="https://mine.com")
        Supplier.objects.create(
            owner=other_user, name="TheirsNotMine", website="https://theirs.com"
        )
        url = reverse("suppliers:list-create")

        response = api_client.get(url)

        names = [s["name"] for s in response.data["data"]]
        assert names == ["Mine"]


class TestSupplierDetail:
    def test_get_own_supplier(self, api_client, user):
        supplier = Supplier.objects.create(owner=user, name="Mine", website="https://mine.com")
        url = reverse("suppliers:detail", args=[supplier.id])

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["id"] == str(supplier.id)

    def test_cannot_get_other_users_supplier(self, api_client, other_user):
        supplier = Supplier.objects.create(
            owner=other_user, name="Theirs", website="https://theirs.com"
        )
        url = reverse("suppliers:detail", args=[supplier.id])

        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_updates_supplier(self, api_client, user):
        supplier = Supplier.objects.create(owner=user, name="Mine", website="https://mine.com")
        url = reverse("suppliers:detail", args=[supplier.id])

        response = api_client.patch(url, {"is_active": False})

        assert response.status_code == status.HTTP_200_OK
        supplier.refresh_from_db()
        assert supplier.is_active is False

    def test_delete_is_soft_delete(self, api_client, user):
        supplier = Supplier.objects.create(owner=user, name="Mine", website="https://mine.com")
        url = reverse("suppliers:detail", args=[supplier.id])

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Supplier.objects.filter(id=supplier.id).count() == 0  # hidden from default manager
        assert Supplier.all_objects.filter(id=supplier.id).count() == 1  # still in the DB

    def test_deleted_supplier_name_can_be_reused(self, api_client, user):
        supplier = Supplier.objects.create(owner=user, name="Reusable", website="https://a.com")
        supplier.soft_delete()
        url = reverse("suppliers:list-create")

        response = api_client.post(url, {"name": "Reusable", "website": "https://b.com"})

        assert response.status_code == status.HTTP_201_CREATED
