import pytest

from apps.accounts.models import User
from apps.products.models import Product
from apps.products.services import ProductService
from apps.suppliers.models import Supplier

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(email="owner@example.com", password="supersecret123")


@pytest.fixture
def supplier(user):
    return Supplier.objects.create(owner=user, name="AliExpress", website="https://aliexpress.com")


class TestAutoCategorization:
    def test_assigns_category_when_none_provided(self, user, supplier):
        product = ProductService.create(
            user,
            {
                "supplier": str(supplier.id),
                "name": "HP EliteBook 640 G11 16GB RAM 1TB SSD",
                "supplier_url": "https://supplier.example/item/1",
                "supplier_price": "100.00",
            },
        )
        assert product.category == "Laptops"

    def test_keeps_explicit_category(self, user, supplier):
        product = ProductService.create(
            user,
            {
                "supplier": str(supplier.id),
                "name": "HP EliteBook 640 G11 16GB RAM 1TB SSD",
                "supplier_url": "https://supplier.example/item/2",
                "supplier_price": "100.00",
                "category": "My Own Bucket",
            },
        )
        assert product.category == "My Own Bucket"

    def test_blank_when_unknown(self, user, supplier):
        product = ProductService.create(
            user,
            {
                "supplier": str(supplier.id),
                "name": "Samsung Galaxy S24 128GB",
                "supplier_url": "https://supplier.example/item/3",
                "supplier_price": "100.00",
            },
        )
        assert product.category == ""
        assert Product.objects.get(id=product.id).category == ""

    def test_does_not_overwrite_on_update(self, user, supplier):
        product = ProductService.create(
            user,
            {
                "supplier": str(supplier.id),
                "name": "HP P24v FHD Monitor",
                "supplier_url": "https://supplier.example/item/4",
                "supplier_price": "100.00",
            },
        )
        assert product.category == "Monitors"

        ProductService.update(
            user, product.id, {"name": "HP P24v FHD Display", "category": "Curated"}
        )
        product.refresh_from_db()
        assert product.category == "Curated"
