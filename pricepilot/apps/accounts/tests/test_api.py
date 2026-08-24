import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


class TestRegister:
    def test_register_creates_user(self, api_client):
        url = reverse("accounts:register")
        payload = {
            "email": "merchant@example.com",
            "password": "supersecret123",
            "full_name": "Merchant One",
        }

        response = api_client.post(url, payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email="merchant@example.com").exists()
        assert "password" not in response.data["data"]

    def test_register_rejects_duplicate_email(self, api_client):
        User.objects.create_user(email="dup@example.com", password="supersecret123")
        url = reverse("accounts:register")

        response = api_client.post(url, {"email": "dup@example.com", "password": "supersecret123"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] is not None

    def test_register_rejects_short_password(self, api_client):
        url = reverse("accounts:register")

        response = api_client.post(url, {"email": "short@example.com", "password": "123"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestLogin:
    def test_login_returns_tokens(self, api_client):
        User.objects.create_user(email="login@example.com", password="supersecret123")
        url = reverse("accounts:login")

        response = api_client.post(
            url, {"email": "login@example.com", "password": "supersecret123"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_rejects_bad_password(self, api_client):
        User.objects.create_user(email="login2@example.com", password="supersecret123")
        url = reverse("accounts:login")

        response = api_client.post(
            url, {"email": "login2@example.com", "password": "wrongpassword"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestMe:
    def test_me_requires_auth(self, api_client):
        url = reverse("accounts:me")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_returns_current_user(self, api_client):
        user = User.objects.create_user(email="me@example.com", password="supersecret123")
        api_client.force_authenticate(user=user)
        url = reverse("accounts:me")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["email"] == "me@example.com"
