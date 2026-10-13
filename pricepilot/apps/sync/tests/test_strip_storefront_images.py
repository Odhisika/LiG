from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.test import override_settings

from apps.sync.models import LiGCategory, LiGProduct, LiGProductGallery

pytestmark = pytest.mark.django_db(databases=["default", "lig"])


@pytest.fixture
def lig_store(lig_schema):
    with override_settings(LIG_SYNC_ENABLED=True, LIG_DEFAULT_CATEGORY_SLUG="uncategorized"):
        yield


def make_lig_product(name, category, images=None):
    return LiGProduct.objects.create(
        product_name=name,
        slug=name.lower().replace(" ", "-"),
        sku=f"SKU-{name[:6].upper()}",
        price=Decimal("10.00"),
        cost_price=Decimal("5.00"),
        stock=1,
        category=category,
        images=images,
    )


class TestStripStorefrontImages:
    def test_dry_run_leaves_images_in_place(self, lig_store):
        software = LiGCategory.objects.create(category_name="Software", slug="software")
        product = make_lig_product("Windows 11", software, images="photos/products/a.jpg")
        LiGProductGallery.objects.create(product=product, image="store/products/g.jpg")

        out = StringIO()
        call_command("strip_storefront_images", stdout=out)

        product.refresh_from_db()
        assert product.images == "photos/products/a.jpg"
        assert LiGProductGallery.objects.get(product=product).is_active is True
        assert "Re-run with --apply" in out.getvalue()

    def test_apply_clears_primary_and_deactivates_gallery(self, lig_store):
        software = LiGCategory.objects.create(category_name="Software", slug="software")
        product = make_lig_product("Windows 11", software, images="photos/products/a.jpg")
        LiGProductGallery.objects.create(product=product, image="store/products/a.jpg")

        call_command("strip_storefront_images", "--apply")

        product.refresh_from_db()
        assert not product.images
        assert LiGProductGallery.objects.get(product=product).is_active is False

    def test_leaves_other_categories_untouched(self, lig_store):
        LiGCategory.objects.create(category_name="Software", slug="software")
        ups = LiGCategory.objects.create(category_name="UPS", slug="ups")
        product = make_lig_product("APC UPS", ups, images="photos/products/ups.jpg")

        call_command("strip_storefront_images", "--apply")

        product.refresh_from_db()
        assert product.images == "photos/products/ups.jpg"
