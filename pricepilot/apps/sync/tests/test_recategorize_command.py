import io
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.test import override_settings

from apps.accounts.models import User
from apps.sync.models import LiGCategory, LiGProduct

pytestmark = pytest.mark.django_db(databases=["default", "lig"])


@pytest.fixture
def user():
    return User.objects.create_user(email="owner@example.com", password="supersecret123")


@pytest.fixture
def lig_store(lig_schema):
    with override_settings(
        LIG_SYNC_ENABLED=True,
        LIG_SYNC_STOCK=True,
        LIG_SYNC_IMAGES=False,
        LIG_DEFAULT_CATEGORY_SLUG="uncategorized",
    ):
        yield


def seed_category(name, slug):
    return LiGCategory.objects.create(category_name=name, slug=slug)


def seed_product(name, slug, category):
    return LiGProduct.objects.create(
        product_name=name,
        slug=slug,
        sku=f"SKU-{slug.upper()}",
        price=Decimal("100.00"),
        cost_price=Decimal("80.00"),
        stock=5,
        description="",
        is_available=True,
        category=category,
    )


def run_command(*args, **kwargs):
    out = io.StringIO()
    err = io.StringIO()
    call_command("recategorize_store", *args, stdout=out, stderr=err, **kwargs)
    return out.getvalue(), err.getvalue()


class TestRecategorizeStore:
    def test_dry_run_lists_changes_without_writing(self, lig_store):
        seed_category("Desktops", "desktops")
        seed_category("Switches", "switches")
        switch = seed_product(
            "TP-LINK LS1005 5-Port 10/100Mbps Desktop Network Switch",
            "tp-link-ls1005-switch",
            LiGCategory.objects.get(slug="desktops"),
        )

        out, _ = run_command()
        switch.refresh_from_db()

        assert "-> Switches" in out
        assert "Re-run with --apply" in out
        assert switch.category.slug == "desktops"

    def test_apply_moves_products_to_fine_grained_categories(self, lig_store):
        seed_category("Desktops", "desktops")
        seed_category("Networking", "networking")
        seed_category("Security & CCTV", "security-cctv")
        seed_category("Switches", "switches")
        seed_category("Routers & Modems", "routers-and-modems")
        seed_category("Security Cameras", "security-cameras")

        switch = seed_product(
            "TP-LINK LS1005 5-Port 10/100Mbps Desktop Network Switch",
            "tp-link-ls1005-switch",
            LiGCategory.objects.get(slug="desktops"),
        )
        router = seed_product(
            "TP-Link Archer C60 AC1350 Wireless Dual Band Router",
            "tp-link-archer-c60",
            LiGCategory.objects.get(slug="networking"),
        )
        camera = seed_product(
            "Dahua 2MP HD Dome CCTV Camera",
            "dahua-2mp-camera",
            LiGCategory.objects.get(slug="security-cctv"),
        )

        out, _ = run_command("--apply")

        switch.refresh_from_db()
        router.refresh_from_db()
        camera.refresh_from_db()
        assert switch.category.slug == "switches"
        assert router.category.slug == "routers-and-modems"
        assert camera.category.slug == "security-cameras"
        assert "3 products scanned; 3 applied" in out

    def test_apply_is_idempotent(self, lig_store):
        seed_category("Switches", "switches")
        switch = seed_product(
            "Cisco Catalyst 2960 24-Port Switch",
            "cisco-2960",
            LiGCategory.objects.get(slug="switches"),
        )

        out, _ = run_command("--apply")
        switch.refresh_from_db()

        assert switch.category.slug == "switches"
        assert "1 products scanned; 0 applied" in out

    def test_unmatched_product_left_alone_by_default(self, lig_store):
        seed_category("Uncategorized", "uncategorized")
        seed_category("Peripherals", "peripherals")
        product = seed_product(
            "Mystery Gadget 2000",
            "mystery-2000",
            LiGCategory.objects.get(slug="peripherals"),
        )

        out, _ = run_command("--apply")

        product.refresh_from_db()
        assert product.category.slug == "peripherals"
        assert "were left unchanged" in out

    def test_unmatched_product_moves_with_to_uncategorized(self, lig_store):
        seed_category("Uncategorized", "uncategorized")
        seed_category("Peripherals", "peripherals")
        product = seed_product(
            "Mystery Gadget 2000",
            "mystery-2000",
            LiGCategory.objects.get(slug="peripherals"),
        )

        out, _ = run_command("--apply", "--to-uncategorized")

        product.refresh_from_db()
        assert product.category.slug == "uncategorized"
        assert "were moved to the default" in out

    def test_warns_when_sync_not_configured(self, user):
        with override_settings(LIG_SYNC_ENABLED=False):
            out, _ = run_command()
        assert "not configured" in out
