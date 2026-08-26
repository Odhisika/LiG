from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.pricing.models import PricingRule
from apps.products.models import Product

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
    from apps.suppliers.models import Supplier

    return Supplier.objects.create(owner=user, name="AliExpress", website="https://aliexpress.com")


def rule_payload(**overrides):
    payload = {
        "name": "Standard Markup",
        "steps": [{"step_type": "markup_pct", "value": "20"}],
    }
    payload.update(overrides)
    return payload


class TestPricingRuleCreate:
    def test_create_with_single_step(self, api_client, user):
        url = reverse("pricing:list-create")

        response = api_client.post(url, rule_payload(), format="json")

        assert response.status_code == status.HTTP_201_CREATED
        rule = PricingRule.objects.get(name="Standard Markup")
        assert rule.owner == user
        assert rule.steps.count() == 1

    def test_create_with_multiple_ordered_steps(self, api_client):
        url = reverse("pricing:list-create")
        payload = rule_payload(
            steps=[
                {"step_type": "shipping", "value": "5.00"},
                {"step_type": "tax", "value": "10"},
                {"step_type": "markup_pct", "value": "20"},
            ]
        )

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        rule = PricingRule.objects.get(name="Standard Markup")
        step_types = list(rule.steps.order_by("order").values_list("step_type", flat=True))
        assert step_types == ["shipping", "tax", "markup_pct"]

    def test_requires_auth(self):
        client = APIClient()
        response = client.post(reverse("pricing:list-create"), rule_payload(), format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_rejects_empty_steps(self, api_client):
        url = reverse("pricing:list-create")

        response = api_client.post(url, rule_payload(steps=[]), format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_rejects_invalid_step_type(self, api_client):
        url = reverse("pricing:list-create")
        payload = rule_payload(steps=[{"step_type": "not_real", "value": "5"}])

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_duplicate_name_for_same_owner_rejected(self, api_client):
        url = reverse("pricing:list-create")
        api_client.post(url, rule_payload(), format="json")

        response = api_client.post(url, rule_payload(), format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_same_name_allowed_for_different_owners(self, api_client, other_user):
        url = reverse("pricing:list-create")
        api_client.post(url, rule_payload(), format="json")

        other_client = APIClient()
        other_client.force_authenticate(user=other_user)
        response = other_client.post(url, rule_payload(), format="json")

        assert response.status_code == status.HTTP_201_CREATED


class TestPricingRuleList:
    def test_only_returns_own_rules(self, api_client, user, other_user):
        PricingRule.objects.create(owner=user, name="Mine")
        PricingRule.objects.create(owner=other_user, name="TheirsNotMine")

        response = api_client.get(reverse("pricing:list-create"))

        names = [r["name"] for r in response.data["data"]]
        assert names == ["Mine"]


class TestPricingRuleDetail:
    def test_get_includes_steps_display(self, api_client):
        create_response = api_client.post(
            reverse("pricing:list-create"), rule_payload(), format="json"
        )
        rule_id = create_response.data["data"]["id"]

        response = api_client.get(reverse("pricing:detail", args=[rule_id]))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]["steps_display"]) == 1
        assert response.data["data"]["steps_display"][0]["step_type"] == "markup_pct"

    def test_cannot_get_other_users_rule(self, api_client, other_user):
        rule = PricingRule.objects.create(owner=other_user, name="Theirs")

        response = api_client.get(reverse("pricing:detail", args=[rule.id]))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_replaces_steps_entirely(self, api_client):
        create_response = api_client.post(
            reverse("pricing:list-create"), rule_payload(), format="json"
        )
        rule_id = create_response.data["data"]["id"]
        url = reverse("pricing:detail", args=[rule_id])

        response = api_client.patch(
            url,
            {"steps": [{"step_type": "flat_fee", "value": "3.00"}]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        rule = PricingRule.objects.get(id=rule_id)
        assert rule.steps.count() == 1
        assert rule.steps.first().step_type == "flat_fee"

    def test_patch_without_steps_key_leaves_steps_untouched(self, api_client):
        create_response = api_client.post(
            reverse("pricing:list-create"), rule_payload(), format="json"
        )
        rule_id = create_response.data["data"]["id"]
        url = reverse("pricing:detail", args=[rule_id])

        response = api_client.patch(url, {"is_active": False}, format="json")

        assert response.status_code == status.HTTP_200_OK
        rule = PricingRule.objects.get(id=rule_id)
        assert rule.is_active is False
        assert rule.steps.count() == 1  # unchanged

    def test_delete_is_soft_delete(self, api_client):
        create_response = api_client.post(
            reverse("pricing:list-create"), rule_payload(), format="json"
        )
        rule_id = create_response.data["data"]["id"]
        url = reverse("pricing:detail", args=[rule_id])

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert PricingRule.objects.filter(id=rule_id).count() == 0
        assert PricingRule.all_objects.filter(id=rule_id).count() == 1


class TestDefaultMarkup:
    def test_returns_null_when_unset(self, api_client):
        url = reverse("pricing:default-markup")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["markup_percent"] is None

    def test_set_and_get(self, api_client, user, supplier):
        url = reverse("pricing:default-markup")
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="No rule",
            supplier_url="https://a.com",
            supplier_price=10,
            selling_price=None,
        )
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Has manual price",
            supplier_url="https://b.com",
            supplier_price=10,
            selling_price=20,
        )

        with patch("apps.pricing.views.StoreSyncService.sync_all") as mock_sync:
            response = api_client.put(url, {"markup_percent": "25"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["markup_percent"] == "25.00"
        # only the product without a manual price is affected
        assert response.data["data"]["affected_products"] == 1
        mock_sync.assert_called_once()

        fetched = api_client.get(url)
        assert fetched.data["data"]["markup_percent"] == "25.00"

    def test_default_markup_sync_includes_products_without_store_id(
        self, api_client, user, supplier
    ):
        url = reverse("pricing:default-markup")
        product = Product.objects.create(
            owner=user,
            supplier=supplier,
            name="No store identity yet",
            supplier_url="https://a.com",
            sku="sku-1",
            supplier_price=10,
            selling_price=None,
            store_product_id=None,
        )

        with patch("apps.pricing.views.StoreSyncService.sync_all") as mock_sync:
            response = api_client.put(url, {"markup_percent": "25"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        synced_products = list(mock_sync.call_args.args[0])
        assert product in synced_products

    def test_default_markup_includes_jred_scraped_products_without_store_pointer(
        self, api_client, user
    ):
        from apps.suppliers.models import Supplier

        jred = Supplier.objects.create(
            owner=user,
            name="JRED Technologies",
            website="https://www.jredtechnologiesltd.com/",
            default_scraper="catlog",
        )
        product = Product.objects.create(
            owner=user,
            supplier=jred,
            name="JRED imported laptop",
            supplier_url="https://jredtechnologiesltd.com/products/imported-laptop",
            sku="imported-laptop",
            supplier_price=100,
            selling_price=None,
            store_product_id=None,
        )

        with patch("apps.pricing.views.StoreSyncService.sync_all") as mock_sync:
            response = api_client.put(
                reverse("pricing:default-markup"),
                {"markup_percent": "15"},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["affected_products"] == 1
        synced_products = list(mock_sync.call_args.args[0])
        assert product in synced_products

    def test_negative_markup_rejected(self, api_client):
        url = reverse("pricing:default-markup")

        response = api_client.put(url, {"markup_percent": "-5"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_requires_auth(self):
        client = APIClient()

        response = client.get(reverse("pricing:default-markup"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
