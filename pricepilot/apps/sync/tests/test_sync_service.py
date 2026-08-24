from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.accounts.models import User
from apps.products.models import Product
from apps.products.services import PriceMonitorService
from apps.scrapers.types import ScrapedProduct
from apps.suppliers.models import Supplier
from apps.sync.models import LiGCategory, LiGProduct

pytestmark = pytest.mark.django_db(databases=["default", "lig"])


@pytest.fixture
def user():
    return User.objects.create_user(email="owner@example.com", password="supersecret123")


@pytest.fixture
def supplier(user):
    return Supplier.objects.create(
        owner=user, name="AliExpress", website="https://aliexpress.com", default_scraper="catlog"
    )


def make_product(user, supplier, **overrides):
    defaults = {
        "owner": user,
        "supplier": supplier,
        "name": "APC Easy 1000VA UPS",
        "supplier_url": "https://supplier.example/products/ups-1000",
        "supplier_price": Decimal("100.00"),
        "selling_price": None,
        "stock": 5,
        "status": Product.Status.ACTIVE,
        "description": "Line interactive UPS.",
        "category": "UPS",
    }
    defaults.update(overrides)
    return Product.objects.create(**defaults)


@pytest.fixture
def lig_store(lig_schema):
    with override_settings(
        LIG_SYNC_ENABLED=True,
        LIG_SYNC_STOCK=True,
        LIG_SYNC_IMAGES=False,
        LIG_DEFAULT_CATEGORY_SLUG="uncategorized",
    ):
        yield


def seed_category(name, slug, **extra):
    return LiGCategory.objects.create(category_name=name, slug=slug, **extra)


class TestDisabledSync:
    def test_skips_when_not_enabled(self, user, supplier):
        from apps.sync.services import StoreSyncService

        product = make_product(user, supplier)
        with override_settings(LIG_SYNC_ENABLED=False):
            res = StoreSyncService.sync_product(product)
        assert res["action"] == "skipped"


class TestSeeding:
    def test_creates_store_row_with_full_info(self, user, supplier, lig_store):
        seed_category("UPS", "ups")
        product = make_product(user, supplier)

        from apps.sync.services import StoreSyncService

        result = StoreSyncService.sync_product(product)
        product.refresh_from_db()

        assert result["action"] == "created"
        assert result["lig_product_id"] is not None
        lig = LiGProduct.objects.get(id=result["lig_product_id"])
        assert lig.product_name == product.name
        assert lig.price == Decimal("100.00")
        assert lig.cost_price == Decimal("100.00")
        assert lig.stock == 5
        assert lig.description == "Line interactive UPS."
        assert lig.is_available is True
        assert lig.category.category_name == "UPS"
        assert product.store_product_id == lig.id
        assert product.sku == lig.sku  # backfilled so future matches work

    def test_uses_selling_price_when_pricing_rule_set(self, user, supplier, lig_store):
        from apps.pricing.models import PricingRule, PricingRuleStep

        seed_category("UPS", "ups")
        rule = PricingRule.objects.create(owner=user, name="Markup")
        PricingRuleStep.objects.create(rule=rule, order=0, step_type="markup_percent", value="10")
        product = make_product(user, supplier, pricing_rule=rule, selling_price=Decimal("110.00"))

        from apps.sync.services import StoreSyncService

        result = StoreSyncService.sync_product(product)
        lig = LiGProduct.objects.get(id=result["lig_product_id"])
        assert lig.price == Decimal("110.00")
        assert lig.cost_price == Decimal("100.00")

    def test_uses_default_markup_when_no_rule_or_manual_price(self, user, supplier, lig_store):
        from apps.pricing.services import DefaultMarkupService

        seed_category("UPS", "ups")
        DefaultMarkupService.set_markup(user, "25")
        product = make_product(user, supplier)

        from apps.sync.services import StoreSyncService

        result = StoreSyncService.sync_product(product)
        lig = LiGProduct.objects.get(id=result["lig_product_id"])
        assert lig.price == Decimal("125.00")
        assert lig.cost_price == Decimal("100.00")

    def test_uses_default_category_slug_fallback(self, user, supplier, lig_store):
        seed_category("Misc", "uncategorized")
        product = make_product(user, supplier, category="Totally Unknown Category")

        from apps.sync.services import StoreSyncService

        result = StoreSyncService.sync_product(product)
        lig = LiGProduct.objects.get(id=result["lig_product_id"])
        assert lig.category.slug == "uncategorized"

    def test_uses_alias_category_when_fine_grained_row_is_missing(
        self, user, supplier, lig_store
    ):
        seed_category("Computers", "computers")
        product = make_product(user, supplier, category="Laptops")

        from apps.sync.services import StoreSyncService

        result = StoreSyncService.sync_product(product)
        lig = LiGProduct.objects.get(id=result["lig_product_id"])
        assert lig.category.slug == "computers"

    def test_uses_broader_security_category_when_camera_row_is_missing(
        self, user, supplier, lig_store
    ):
        seed_category("Security & CCTV", "security-cctv")
        product = make_product(user, supplier, category="Security Cameras")

        from apps.sync.services import StoreSyncService

        result = StoreSyncService.sync_product(product)
        lig = LiGProduct.objects.get(id=result["lig_product_id"])
        assert lig.category.slug == "security-cctv"

    def test_fails_cleanly_without_category(self, user, supplier, lig_store):
        product = make_product(user, supplier, category="Totally Unknown Category")

        from apps.sync.services import StoreSyncService

        with override_settings(LIG_DEFAULT_CATEGORY_SLUG=""):
            result = StoreSyncService.sync_product(product)
        assert result["action"] == "failed"
        assert LiGProduct.objects.count() == 0

    def test_seed_does_not_duplicate_on_resync(self, user, supplier, lig_store):
        seed_category("UPS", "ups")
        product = make_product(user, supplier)

        from apps.sync.services import StoreSyncService

        first = StoreSyncService.sync_product(product)
        product.refresh_from_db()
        second = StoreSyncService.sync_product(product)

        assert first["action"] == "created"
        assert second["action"] == "noop"
        assert second["lig_product_id"] == first["lig_product_id"]
        assert LiGProduct.objects.count() == 1

    def test_sync_all_seeds_product_with_no_sku_or_store_id(self, user, supplier, lig_store):
        seed_category("UPS", "ups")
        product = make_product(user, supplier, sku="")

        from apps.sync.services import StoreSyncService

        tally = StoreSyncService.sync_all(Product.objects.filter(id=product.id))
        product.refresh_from_db()

        assert tally.get("created") == 1
        assert product.store_product_id is not None
        assert product.sku != ""


class TestUpdates:
    def test_updates_existing_row_by_sku(self, user, supplier, lig_store):
        seed_category("UPS", "ups")
        lig = LiGProduct.objects.create(
            product_name="Old Name",
            slug="apc-easy-1000va-ups",
            sku="SKU-EXISTING",
            price=Decimal("50.00"),
            cost_price=Decimal("40.00"),
            stock=9,
            description="Old description",
            category=LiGCategory.objects.first(),
        )
        product = make_product(user, supplier, sku="SKU-EXISTING")

        from apps.sync.services import StoreSyncService

        result = StoreSyncService.sync_product(product)
        product.refresh_from_db()
        lig.refresh_from_db()

        assert result["action"] == "updated"
        assert result["lig_product_id"] == lig.id
        assert lig.price == Decimal("100.00")
        assert lig.cost_price == Decimal("100.00")
        assert lig.stock == 5
        assert lig.product_name == product.name
        assert lig.description == "Line interactive UPS."
        assert product.store_product_id == lig.id

    def test_noop_when_nothing_changed(self, user, supplier, lig_store):
        seed_category("UPS", "ups")
        LiGProduct.objects.create(
            product_name="APC Easy 1000VA UPS",
            slug="apc-easy-1000va-ups",
            sku="SKU-EXISTING",
            price=Decimal("100.00"),
            cost_price=Decimal("100.00"),
            stock=5,
            description="Line interactive UPS.",
            is_available=True,
            category=LiGCategory.objects.first(),
        )
        product = make_product(user, supplier, sku="SKU-EXISTING")

        from apps.sync.services import StoreSyncService

        result = StoreSyncService.sync_product(product)
        assert result["action"] == "noop"

    def test_stock_left_alone_when_toggle_off(self, user, supplier, lig_store):
        seed_category("UPS", "ups")
        lig = LiGProduct.objects.create(
            product_name="APC Easy 1000VA UPS",
            slug="apc-easy-1000va-ups",
            sku="SKU-EXISTING",
            price=Decimal("50.00"),
            cost_price=Decimal("40.00"),
            stock=2,  # order-driven, must survive
            category=LiGCategory.objects.first(),
        )
        product = make_product(user, supplier, sku="SKU-EXISTING")

        from apps.sync.services import StoreSyncService

        with override_settings(LIG_SYNC_STOCK=False):
            result = StoreSyncService.sync_product(product)
        lig.refresh_from_db()
        assert result["action"] == "updated"
        assert lig.stock == 2

    def test_out_of_stock_marks_unavailable(self, user, supplier, lig_store):
        seed_category("UPS", "ups")
        product = make_product(user, supplier, stock=0, status=Product.Status.OUT_OF_STOCK)

        from apps.sync.services import StoreSyncService

        result = StoreSyncService.sync_product(product)
        lig = LiGProduct.objects.get(id=result["lig_product_id"])
        assert lig.is_available is False
        assert lig.stock == 0

    def test_scrape_failure_keeps_product_on_sale(self, user, supplier, lig_store):
        seed_category("UPS", "ups")
        product = make_product(user, supplier, status=Product.Status.SCRAPE_FAILED)

        from apps.sync.services import StoreSyncService

        result = StoreSyncService.sync_product(product)
        lig = LiGProduct.objects.get(id=result["lig_product_id"])
        assert lig.is_available is True
        assert lig.price == Decimal("100.00")

    def test_category_change_moves_store_row(self, user, supplier, lig_store):
        seed_category("UPS", "ups")
        seed_category("Networking", "networking")
        product = make_product(user, supplier, category="UPS")

        from apps.sync.services import StoreSyncService

        first = StoreSyncService.sync_product(product)
        product.category = "Networking"
        product.save(update_fields=["category"])

        second = StoreSyncService.sync_product(product)
        lig = LiGProduct.objects.get(id=first["lig_product_id"])
        assert second["action"] == "updated"
        assert lig.category.category_name == "Networking"

    def test_missing_canonical_category_falls_back_not_created(self, user, supplier, lig_store):
        seed_category("Misc", "uncategorized")
        product = make_product(user, supplier, category="Monitors")

        from apps.sync.services import StoreSyncService

        result = StoreSyncService.sync_product(product)
        lig = LiGProduct.objects.get(id=result["lig_product_id"])
        assert lig.category.slug == "uncategorized"
        assert not LiGCategory.objects.filter(category_name="Monitors").exists()


class TestMonitorHook:
    def test_check_product_triggers_store_sync_on_change(self, user, supplier):
        product = make_product(user, supplier)
        fake_scraper = type(
            "Fake",
            (),
            {
                "fetch": lambda self, url: ScrapedProduct(
                    title="X", price=Decimal("150.00"), currency="NGN", stock=5
                )
            },
        )()

        with (
            patch("apps.products.services.ScraperRegistry.get", return_value=fake_scraper),
            patch("apps.products.services.StoreSyncService.sync_product") as mock_sync,
        ):
            PriceMonitorService.check_product(product.id)

        mock_sync.assert_called_once()
        assert mock_sync.call_args.args[0].id == product.id

    def test_check_product_does_not_sync_when_unchanged(self, user, supplier):
        product = make_product(user, supplier)
        fake_scraper = type(
            "Fake",
            (),
            {
                "fetch": lambda self, url: ScrapedProduct(
                    title="X", price=Decimal("100.00"), currency="NGN", stock=5
                )
            },
        )()

        with (
            patch("apps.products.services.ScraperRegistry.get", return_value=fake_scraper),
            patch("apps.products.services.StoreSyncService.sync_product") as mock_sync,
        ):
            PriceMonitorService.check_product(product.id)

        mock_sync.assert_not_called()
