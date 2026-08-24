from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.accounts.models import User
from apps.common.exceptions import NotFoundError, ScraperError, ValidationError
from apps.discovery.models import DiscoveredProduct
from apps.discovery.services import DiscoveryService
from apps.notifications.models import NotificationEvent
from apps.products.models import Product
from apps.scrapers.types import ScrapedProduct
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
    return Supplier.objects.create(
        owner=user,
        name="Jred Technologies",
        website="https://www.jredtechnologiesltd.com/",
        default_scraper="catlog",
    )


def mock_scraper(urls, fetch_results=None):
    fake = MagicMock()
    fake.discover_product_urls.return_value = urls
    if fetch_results is not None:
        fake.fetch.side_effect = fetch_results
    else:
        fake.fetch.return_value = ScrapedProduct(
            title="Discovered Item", price=Decimal("50.00"), currency="NGN", stock=5
        )
    return fake


class TestScanSupplier:
    def test_creates_discovered_products_for_new_urls(self, user, supplier):
        fake = mock_scraper(["https://a.com/products/item-1", "https://a.com/products/item-2"])

        with patch("apps.discovery.services.ScraperRegistry.get", return_value=fake):
            created = DiscoveryService.scan_supplier(supplier)

        assert created == 2
        assert DiscoveredProduct.objects.filter(supplier=supplier).count() == 2

    def test_skips_supplier_with_no_scraper_configured(self, user):
        supplier = Supplier.objects.create(
            owner=user, name="NoScraper", website="https://x.com", default_scraper=""
        )

        created = DiscoveryService.scan_supplier(supplier)

        assert created == 0
        assert DiscoveredProduct.objects.count() == 0

    def test_does_not_rediscover_already_tracked_product(self, user, supplier):
        Product.objects.create(
            owner=user,
            supplier=supplier,
            name="Already tracked",
            supplier_url="https://a.com/products/item-1",
            supplier_price=10,
        )
        fake = mock_scraper(["https://a.com/products/item-1", "https://a.com/products/item-2"])

        with patch("apps.discovery.services.ScraperRegistry.get", return_value=fake):
            created = DiscoveryService.scan_supplier(supplier)

        assert created == 1
        assert DiscoveredProduct.objects.get().url == "https://a.com/products/item-2"

    def test_does_not_reduplicate_across_scans(self, user, supplier):
        fake = mock_scraper(["https://a.com/products/item-1"])

        with patch("apps.discovery.services.ScraperRegistry.get", return_value=fake):
            first_run = DiscoveryService.scan_supplier(supplier)
            second_run = DiscoveryService.scan_supplier(supplier)

        assert first_run == 1
        assert second_run == 0
        assert DiscoveredProduct.objects.count() == 1

    def test_preview_data_populated_from_fetch(self, user, supplier):
        fake = mock_scraper(
            ["https://a.com/products/item-1"],
            fetch_results=[
                ScrapedProduct(
                    title="Nice Widget",
                    price=Decimal("199.99"),
                    currency="NGN",
                    stock=3,
                    images=["https://img.example.com/1.jpg"],
                )
            ],
        )

        with patch("apps.discovery.services.ScraperRegistry.get", return_value=fake):
            DiscoveryService.scan_supplier(supplier)

        discovered = DiscoveredProduct.objects.get()
        assert discovered.title == "Nice Widget"
        assert discovered.price == Decimal("199.99")
        assert discovered.image == "https://img.example.com/1.jpg"

    def test_preview_fetch_failure_still_records_url(self, user, supplier):
        fake = MagicMock()
        fake.discover_product_urls.return_value = ["https://a.com/products/item-1"]
        fake.fetch.side_effect = ScraperError("preview render failed")

        with patch("apps.discovery.services.ScraperRegistry.get", return_value=fake):
            created = DiscoveryService.scan_supplier(supplier)

        assert created == 1
        discovered = DiscoveredProduct.objects.get()
        assert discovered.title == ""
        assert discovered.price is None

    def test_catalog_scan_failure_handled_gracefully(self, user, supplier):
        fake = MagicMock()
        fake.discover_product_urls.side_effect = ScraperError("catalog page unreachable")

        with patch("apps.discovery.services.ScraperRegistry.get", return_value=fake):
            created = DiscoveryService.scan_supplier(supplier)

        assert created == 0

    def test_records_new_products_found_notification(self, user, supplier):
        fake = mock_scraper(["https://a.com/products/item-1", "https://a.com/products/item-2"])

        with patch("apps.discovery.services.ScraperRegistry.get", return_value=fake):
            DiscoveryService.scan_supplier(supplier)

        event = NotificationEvent.objects.get(
            owner=user, event_type=NotificationEvent.EventType.NEW_PRODUCTS_FOUND
        )
        assert event.payload["count"] == 2

    def test_no_notification_when_nothing_new_found(self, user, supplier):
        fake = mock_scraper([])

        with patch("apps.discovery.services.ScraperRegistry.get", return_value=fake):
            DiscoveryService.scan_supplier(supplier)

        assert NotificationEvent.objects.count() == 0


class TestImportDiscovery:
    def test_creates_real_product(self, user, supplier):
        discovery = DiscoveredProduct.objects.create(
            owner=user,
            supplier=supplier,
            url="https://a.com/products/item-1",
            title="Nice Widget",
            price=Decimal("199.99"),
            currency="NGN",
        )

        product = DiscoveryService.import_discovery(user, discovery.id)

        assert product.name == "Nice Widget"
        assert product.supplier_price == Decimal("199.99")
        assert product.supplier_url == "https://a.com/products/item-1"

    def test_carries_preview_image_onto_product(self, user, supplier):
        discovery = DiscoveredProduct.objects.create(
            owner=user,
            supplier=supplier,
            url="https://a.com/products/item-1",
            title="Nice Widget",
            price=Decimal("199.99"),
            image="https://img.example.com/1.jpg",
        )

        product = DiscoveryService.import_discovery(user, discovery.id)

        assert product.images == ["https://img.example.com/1.jpg"]

    def test_marks_discovery_imported_and_links_product(self, user, supplier):
        discovery = DiscoveredProduct.objects.create(
            owner=user,
            supplier=supplier,
            url="https://a.com/products/item-1",
            price=Decimal("10.00"),
        )

        product = DiscoveryService.import_discovery(user, discovery.id)

        discovery.refresh_from_db()
        assert discovery.status == DiscoveredProduct.Status.IMPORTED
        assert discovery.imported_product == product

    def test_cannot_import_twice(self, user, supplier):
        discovery = DiscoveredProduct.objects.create(
            owner=user,
            supplier=supplier,
            url="https://a.com/products/item-1",
            price=Decimal("10.00"),
        )
        DiscoveryService.import_discovery(user, discovery.id)

        with pytest.raises(ValidationError):
            DiscoveryService.import_discovery(user, discovery.id)

    def test_missing_price_requires_override(self, user, supplier):
        discovery = DiscoveredProduct.objects.create(
            owner=user, supplier=supplier, url="https://a.com/products/item-1", price=None
        )

        with pytest.raises(ValidationError):
            DiscoveryService.import_discovery(user, discovery.id)

    def test_missing_price_succeeds_with_override(self, user, supplier):
        discovery = DiscoveredProduct.objects.create(
            owner=user, supplier=supplier, url="https://a.com/products/item-1", price=None
        )

        product = DiscoveryService.import_discovery(
            user, discovery.id, overrides={"supplier_price": Decimal("42.00")}
        )

        assert product.supplier_price == Decimal("42.00")

    def test_override_name_takes_precedence(self, user, supplier):
        discovery = DiscoveredProduct.objects.create(
            owner=user,
            supplier=supplier,
            url="https://a.com/products/item-1",
            title="Auto Title",
            price=Decimal("10.00"),
        )

        product = DiscoveryService.import_discovery(
            user, discovery.id, overrides={"name": "My Custom Name"}
        )

        assert product.name == "My Custom Name"

    def test_cannot_import_other_users_discovery(self, other_user, user, supplier):
        discovery = DiscoveredProduct.objects.create(
            owner=user,
            supplier=supplier,
            url="https://a.com/products/item-1",
            price=Decimal("10.00"),
        )

        with pytest.raises(NotFoundError):
            DiscoveryService.import_discovery(other_user, discovery.id)


class TestDismissDiscovery:
    def test_marks_dismissed(self, user, supplier):
        discovery = DiscoveredProduct.objects.create(
            owner=user,
            supplier=supplier,
            url="https://a.com/products/item-1",
            price=Decimal("10.00"),
        )

        result = DiscoveryService.dismiss_discovery(user, discovery.id)

        assert result.status == DiscoveredProduct.Status.DISMISSED

    def test_cannot_dismiss_twice(self, user, supplier):
        discovery = DiscoveredProduct.objects.create(
            owner=user,
            supplier=supplier,
            url="https://a.com/products/item-1",
            price=Decimal("10.00"),
        )
        DiscoveryService.dismiss_discovery(user, discovery.id)

        with pytest.raises(ValidationError):
            DiscoveryService.dismiss_discovery(user, discovery.id)

    def test_dismissed_url_not_rediscovered(self, user, supplier):
        DiscoveredProduct.objects.create(
            owner=user,
            supplier=supplier,
            url="https://a.com/products/item-1",
            price=Decimal("10.00"),
            status=DiscoveredProduct.Status.DISMISSED,
        )
        fake = mock_scraper(["https://a.com/products/item-1"])

        with patch("apps.discovery.services.ScraperRegistry.get", return_value=fake):
            created = DiscoveryService.scan_supplier(supplier)

        assert created == 0  # already known, even though dismissed not imported
