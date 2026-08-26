from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.accounts.models import User
from apps.products.catalog_sync import sync_catalog
from apps.products.models import Product
from apps.suppliers.models import Supplier

pytestmark = pytest.mark.django_db


def api_item(slug="laptop-1", **overrides):
    data = {
        "slug": slug,
        "name": "Laptop 1",
        "price": "100.00",
        "discount_price": None,
        "available": True,
        "quantity": 5,
        "description": "Fast laptop",
        "images": ["https://cdn.example.com/laptop.jpg"],
        "tags": [{"name": "laptops & Notebooks"}],
    }
    data.update(overrides)
    return data


@pytest.fixture
def owner():
    return User.objects.create_user(email="owner@example.com", password="secret123")


@pytest.fixture
def supplier(owner):
    return Supplier.objects.create(owner=owner, name="Jred Technologies", default_scraper="catlog")


@pytest.fixture(autouse=True)
def default_jred_owner_setting(settings):
    settings.JRED_CATALOG_OWNER_EMAIL = ""


@patch("apps.products.catalog_sync._fetch_all_items")
def test_sync_catalog_creates_product(mock_fetch, owner, supplier):
    mock_fetch.return_value = [api_item()]

    summary = sync_catalog()

    product = Product.objects.get(sku="laptop-1")
    assert summary["created"] == 1
    assert summary["removed"] == 0
    assert product.supplier_price == Decimal("100.00")
    assert product.stock == 5
    assert product.category == "Laptops"


def test_sync_catalog_without_owner_returns_full_zero_summary():
    summary = sync_catalog()

    assert summary == {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "failed": 0,
        "removed": 0,
        "total": 0,
        "dry_run": False,
    }


@patch("apps.products.catalog_sync._fetch_all_items")
def test_sync_catalog_uses_configured_owner_email(mock_fetch, settings):
    owner = User.objects.create_user(email="catalog@example.com", password="secret123")
    User.objects.create_user(email="other@example.com", password="secret123")
    settings.JRED_CATALOG_OWNER_EMAIL = "catalog@example.com"
    mock_fetch.return_value = [api_item()]

    sync_catalog()

    assert Product.objects.get(sku="laptop-1").owner == owner


def test_sync_catalog_missing_configured_owner_email_returns_zero_summary(settings):
    User.objects.create_user(email="other@example.com", password="secret123")
    settings.JRED_CATALOG_OWNER_EMAIL = "missing@example.com"

    summary = sync_catalog()

    assert summary["total"] == 0
    assert Product.objects.count() == 0


@patch("apps.products.catalog_sync._fetch_all_items")
def test_sync_catalog_dry_run_does_not_write(mock_fetch, owner, supplier):
    mock_fetch.return_value = [api_item()]

    summary = sync_catalog(dry_run=True)

    assert summary["created"] == 1
    assert summary["dry_run"] is True
    assert Product.objects.count() == 0


@patch("apps.products.catalog_sync._fetch_all_items")
def test_sync_catalog_limit_does_not_mark_missing_products_removed(mock_fetch, owner, supplier):
    existing = Product.objects.create(
        owner=owner,
        supplier=supplier,
        name="Old",
        supplier_url="https://jredtechnologiesltd.com/products/old",
        sku="old",
        supplier_price=50,
        status=Product.Status.ACTIVE,
    )
    mock_fetch.return_value = [api_item(), api_item("second")]

    summary = sync_catalog(limit=1)

    existing.refresh_from_db()
    assert summary["total"] == 1
    assert summary["removed"] == 0
    assert existing.status == Product.Status.ACTIVE


@patch("apps.products.catalog_sync._fetch_all_items")
def test_sync_catalog_marks_missing_jred_product_out_of_stock(mock_fetch, owner, supplier):
    existing = Product.objects.create(
        owner=owner,
        supplier=supplier,
        name="Old",
        supplier_url="https://jredtechnologiesltd.com/products/old",
        sku="old",
        supplier_price=50,
        status=Product.Status.ACTIVE,
        stock=3,
    )
    mock_fetch.return_value = [api_item()]

    summary = sync_catalog()

    existing.refresh_from_db()
    assert summary["removed"] == 1
    assert existing.status == Product.Status.OUT_OF_STOCK
    assert existing.stock == 0
