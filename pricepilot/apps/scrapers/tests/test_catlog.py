import json
from decimal import Decimal

import pytest

from apps.common.exceptions import ScraperError
from apps.scrapers.base import BaseScraper
from apps.scrapers.catlog import CatlogScraper, extract_page_item, extract_store_id, parse_item
from apps.scrapers.registry import ScraperRegistry


def make_html(
    title="APC EASY 1000VA SMV1000I-MSX UPS | Jred Technologies Ltd - Catlog",
    description="APC Easy UPS 1 Ph Line Interactive, 1000VA, Tower, 230V",
    image="https://catlog-s3.s3.eu-west-2.amazonaws.com/ITEMS/3dda7sm6r5.jpeg",
) -> str:
    """Builds HTML matching the real og:* meta tag shape confirmed by
    fetching a live jredtechnologiesltd.com (Catlog) product page.
    """
    return f"""
    <html>
      <head>
        <title>{title}</title>
        <meta property="og:title" content="{title}" />
        <meta property="og:description" content="{description}" />
        <meta property="og:image" content="{image}" />
      </head>
      <body></body>
    </html>
    """


@pytest.fixture
def scraper():
    return CatlogScraper()


class TestParseHappyPath:
    def test_parses_ngn_price_and_explicit_stock_count(self, scraper):
        html = make_html()
        visible_text = "APC EASY UPS\n₦150,000\n3 items left\nAdd to cart"

        result = scraper.parse(html, visible_text)

        assert result.title == "APC EASY 1000VA SMV1000I-MSX UPS"
        assert result.price == Decimal("150000")
        assert result.currency == "NGN"
        assert result.stock == 3
        assert result.images == [
            "https://catlog-s3.s3.eu-west-2.amazonaws.com/ITEMS/3dda7sm6r5.jpeg"
        ]
        assert "APC Easy UPS" in result.description

    def test_price_with_decimal_and_commas(self, scraper):
        html = make_html()
        visible_text = "₦1,250,000.50\nIn Stock"

        result = scraper.parse(html, visible_text)

        assert result.price == Decimal("1250000.50")

    def test_in_stock_with_no_count_is_none_not_zero(self, scraper):
        html = make_html()
        visible_text = "₦5,000\nIn Stock\nAdd to cart"

        result = scraper.parse(html, visible_text)

        assert result.stock is None

    def test_in_stock_with_count_captures_quantity(self, scraper):
        html = make_html()
        visible_text = "₦5,000\n30 IN STOCK\nAdd to cart"

        result = scraper.parse(html, visible_text)

        assert result.stock == 30

    def test_out_of_stock_maps_to_zero(self, scraper):
        html = make_html()
        visible_text = "₦5,000\nOut of Stock"

        result = scraper.parse(html, visible_text)

        assert result.stock == 0

    def test_sold_out_maps_to_zero(self, scraper):
        html = make_html()
        visible_text = "₦5,000\nSold Out"

        result = scraper.parse(html, visible_text)

        assert result.stock == 0

    def test_no_stock_signal_at_all_is_none(self, scraper):
        html = make_html()
        visible_text = "₦5,000\nAdd to cart"

        result = scraper.parse(html, visible_text)

        assert result.stock is None


class TestCurrencyVariants:
    def test_ghs_cedi_symbol(self, scraper):
        result = scraper.parse(make_html(), "₵450\nIn Stock")
        assert result.currency == "GHS"
        assert result.price == Decimal("450")

    def test_ghs_text_prefix(self, scraper):
        result = scraper.parse(make_html(), "GHS 13,300.00\nIn Stock")
        assert result.currency == "GHS"
        assert result.price == Decimal("13300.00")

    def test_ngn_text_prefix(self, scraper):
        result = scraper.parse(make_html(), "Price: NGN 20,000\nIn Stock")
        assert result.currency == "NGN"
        assert result.price == Decimal("20000")

    def test_usd_dollar_symbol(self, scraper):
        result = scraper.parse(make_html(), "$49.99\nIn Stock")
        assert result.currency == "USD"
        assert result.price == Decimal("49.99")

    def test_naira_preferred_over_dollar_when_both_present(self, scraper):
        # Some pages show a converted USD estimate alongside the real NGN
        # price — NGN pattern is checked first since it's Catlog's home market.
        result = scraper.parse(make_html(), "₦75,000 (~$49.99)\nIn Stock")
        assert result.currency == "NGN"
        assert result.price == Decimal("75000")


class TestTitleCleanup:
    def test_strips_store_and_catlog_suffix(self, scraper):
        html = make_html(title="Wireless Mouse | Some Store - Catlog")
        result = scraper.parse(html, "₦5,000\nIn Stock")
        assert result.title == "Wireless Mouse"

    def test_falls_back_to_title_tag_when_og_title_missing(self, scraper):
        html = """
        <html><head><title>Fallback Title</title></head><body></body></html>
        """
        result = scraper.parse(html, "₦5,000\nIn Stock")
        assert result.title == "Fallback Title"


class TestFailureModes:
    def test_raises_scraper_error_when_price_missing(self, scraper):
        html = make_html()
        visible_text = "No price shown here at all."

        with pytest.raises(ScraperError):
            scraper.parse(html, visible_text)

    def test_raises_scraper_error_when_title_missing(self, scraper):
        html = "<html><head></head><body></body></html>"

        with pytest.raises(ScraperError):
            scraper.parse(html, "₦5,000\nIn Stock")


class TestRegistry:
    def test_catlog_is_registered(self):
        scraper = ScraperRegistry.get("catlog")
        assert isinstance(scraper, CatlogScraper)

    def test_unknown_key_raises_not_found(self):
        from apps.common.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            ScraperRegistry.get("does-not-exist")

    def test_available_keys_includes_catlog(self):
        assert "catlog" in ScraperRegistry.available_keys()


class TestParseCatalog:
    """Tests the /products/ URL-segment discovery strategy against a
    constructed listing-page fixture — a plausible product grid with
    real-looking product links mixed in with nav/footer noise. This is
    now the HTML fallback path; primary discovery for Catlog goes through
    the public API (see TestWholeStoreAPI).
    """

    def _catalog_html(self, product_links: list[str], noise_links: list[str] | None = None) -> str:
        noise_links = noise_links or []
        product_anchors = "".join(f'<a href="{link}">Product</a>' for link in product_links)
        noise_anchors = "".join(f'<a href="{link}">Nav</a>' for link in noise_links)
        return f"""
        <html><body>
          <nav>{noise_anchors}</nav>
          <div class="grid">{product_anchors}</div>
        </body></html>
        """

    def test_finds_product_links(self, scraper):
        html = self._catalog_html(
            [
                "/products/apc-easy-1000va-smv1000imsx-ups-1783075304676-2r5",
                "/products/hp-allinone-24cr1044nh-b40hwea-1786314841525-66w",
            ]
        )

        urls = scraper.parse_catalog(html, "https://www.jredtechnologiesltd.com/")

        assert len(urls) == 2
        assert all("/products/" in u for u in urls)

    def test_resolves_relative_urls_to_absolute(self, scraper):
        html = self._catalog_html(["/products/some-item-123"])

        urls = scraper.parse_catalog(html, "https://www.jredtechnologiesltd.com/")

        assert urls == ["https://www.jredtechnologiesltd.com/products/some-item-123"]

    def test_leaves_already_absolute_urls_unchanged(self, scraper):
        html = self._catalog_html(["https://www.jredtechnologiesltd.com/products/some-item-123"])

        urls = scraper.parse_catalog(html, "https://www.jredtechnologiesltd.com/")

        assert urls == ["https://www.jredtechnologiesltd.com/products/some-item-123"]

    def test_ignores_non_product_links(self, scraper):
        html = self._catalog_html(
            product_links=["/products/real-item-123"],
            noise_links=["/cart", "/about", "/products", "https://facebook.com/jredtech"],
        )

        urls = scraper.parse_catalog(html, "https://www.jredtechnologiesltd.com/")

        assert len(urls) == 1
        assert "real-item-123" in urls[0]

    def test_dedupes_repeated_links(self, scraper):
        html = self._catalog_html(
            ["/products/same-item-123", "/products/same-item-123", "/products/same-item-123"]
        )

        urls = scraper.parse_catalog(html, "https://www.jredtechnologiesltd.com/")

        assert len(urls) == 1

    def test_empty_grid_returns_empty_list(self, scraper):
        html = self._catalog_html([])

        urls = scraper.parse_catalog(html, "https://www.jredtechnologiesltd.com/")

        assert urls == []

    def test_results_sorted_for_determinism(self, scraper):
        html = self._catalog_html(["/products/zebra-item", "/products/apple-item"])

        urls = scraper.parse_catalog(html, "https://www.jredtechnologiesltd.com/")

        assert urls == sorted(urls)


class TestDiscoveryNotSupportedByDefault:
    def test_base_scraper_default_raises(self):
        from apps.common.exceptions import ScraperError

        class NoDiscoveryScraper(CatlogScraper):
            def discover_product_urls(self, catalog_url: str) -> list[str]:
                return BaseScraper.discover_product_urls(self, catalog_url)

        with pytest.raises(ScraperError):
            NoDiscoveryScraper().discover_product_urls("https://example.com")


def make_next_data_html(store_id: str) -> str:
    """A rendered Catlog page with a realistic __NEXT_DATA__ block."""
    payload = {
        "props": {
            "pageProps": {
                "data": {"data": {"store": {"id": store_id, "name": "Jred Technologies Ltd"}}}
            }
        },
        "page": "/products",
        "query": {},
        "buildId": "abc123",
        "isFallback": False,
        "gssp": True,
        "scriptLoader": [],
    }
    return (
        "<html><body>"
        '<script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(payload)}"
        "</script></body></html>"
    )


def make_item_html(item: dict) -> str:
    """A product page fixture with a server-rendered item in __NEXT_DATA__."""
    payload = {
        "props": {"pageProps": {"item": item, "error": None, "query": {}}},
        "page": "/products/[slug]",
        "query": {},
        "buildId": "abc123",
        "isFallback": False,
        "gssp": True,
        "scriptLoader": [],
    }
    return (
        "<html><body>"
        '<script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(payload)}"
        "</script></body></html>"
    )


def sample_item(**overrides) -> dict:
    item = {
        "id": "6a4483abd0f8c90007f11809",
        "name": "LIGHTWAVE 4K HD 11 IN 1 DOCKING STATION(LW-SIL-DOCK11/1)",
        "price": 260,
        "discount_price": 220,
        "quantity": 60,
        "available": True,
        "description": "The Lightwave LW-SIL-DOCK-11I1 USB-C Docking Hub.",
        "images": ["https://catlog-s3.s3.eu-west-2.amazonaws.com/k7lkfuiwdz.jpeg"],
        "sku": "LIG002",
    }
    item.update(overrides)
    return item


def items_page(slugs: list[str], page: int, total_pages: int) -> dict:
    return {
        "message": "Items fetched successfully",
        "total": len(slugs),
        "total_pages": total_pages,
        "per_page": 100,
        "data": {
            "items": {
                "featured_items": [],
                "other_items": [{"slug": slug, "name": slug} for slug in slugs],
            }
        },
    }


class TestStoreIDExtraction:
    def test_extracts_id_from_next_data(self):
        assert extract_store_id(make_next_data_html("6720e1e0d489a00007234138")) == (
            "6720e1e0d489a00007234138"
        )

    def test_returns_none_when_no_next_data(self):
        assert extract_store_id("<html><body>plain</body></html>") is None

    def test_returns_none_on_malformed_json(self):
        html = '<script id="__NEXT_DATA__" type="application/json">not json</script>'
        assert extract_store_id(html) is None


class TestFastPathItemParse:
    """fetch()'s primary path: server-rendered item in __NEXT_DATA__ via
    plain HTTP GET — no browser. parse_item() is the pure core.
    """

    def test_parse_item_uses_discount_price_when_present(self):
        result = parse_item(sample_item())

        assert result.title == "LIGHTWAVE 4K HD 11 IN 1 DOCKING STATION(LW-SIL-DOCK11/1)"
        assert result.price == Decimal("220.00")
        assert result.stock == 60
        assert result.images == ["https://catlog-s3.s3.eu-west-2.amazonaws.com/k7lkfuiwdz.jpeg"]
        assert "USB-C Docking Hub" in result.description

    def test_parse_item_falls_back_to_base_price_without_discount(self):
        result = parse_item(sample_item(discount_price=None))

        assert result.price == Decimal("260.00")
        assert result.stock == 60

    def test_parse_item_unavailable_maps_to_zero_stock(self):
        result = parse_item(sample_item(available=False, quantity=60))

        assert result.stock == 0

    def test_parse_item_raises_when_no_price(self):
        with pytest.raises(ScraperError):
            parse_item(sample_item(price=None, discount_price=None))

    def test_extract_page_item_from_html(self):
        html = make_item_html(sample_item())

        item = extract_page_item(html)

        assert item["name"].startswith("LIGHTWAVE")
        assert item["price"] == 260

    def test_extract_page_item_none_when_missing(self):
        assert extract_page_item("<html><body>no data</body></html>") is None

    def test_fetch_uses_fast_path_when_item_present(self, scraper, caplog):
        html = make_item_html(sample_item(discount_price=None, quantity=30))
        scraper._http_get = lambda url: html
        caplog.set_level("INFO")

        result = scraper.fetch("https://www.example.com/products/some-item")

        assert result.price == Decimal("260.00")
        assert result.stock == 30
        assert "Catlog scrape used embedded item JSON" in caplog.text

    def test_fetch_falls_back_to_render_when_no_item(self, scraper, caplog):
        render_html = (
            "<html><head><title>Fallback | Store - Catlog</title>"
            '<meta property="og:title" content="Fallback | Store - Catlog"/>'
            "</head><body></body></html>"
        )
        scraper._http_get = lambda url: "<html><body>no item embedded</body></html>"
        scraper._render = lambda url: (render_html, "₦5,000\nIn Stock")
        caplog.set_level("INFO")

        result = scraper.fetch("https://www.example.com/products/some-item")

        assert result.title == "Fallback"
        assert result.price == Decimal("5000")
        assert result.currency == "NGN"
        assert "Catlog scrape used Playwright render" in caplog.text

    def test_fetch_uses_raw_html_parse_before_render_when_possible(self, scraper, caplog):
        html = make_html(title="Fallback Title | Store - Catlog")
        html = html.replace("<body></body>", "<body>₦5,000\nIn Stock</body>")
        scraper._http_get = lambda url: html
        caplog.set_level("INFO")

        render_called = False

        def fake_render(url):
            nonlocal render_called
            render_called = True
            return make_html(title="Should Not Be Used | Store - Catlog"), "₦9,999\nIn Stock"

        scraper._render = fake_render

        result = scraper.fetch("https://www.example.com/products/some-item")

        assert result.title == "Fallback Title"
        assert result.price == Decimal("5000")
        assert result.currency == "NGN"
        assert render_called is False
        assert "Catlog scrape used raw HTML parse" in caplog.text

    def test_fetch_raises_when_both_paths_fail(self, scraper):
        scraper._http_get = lambda url: "<html><body>nothing</body></html>"
        scraper._render = lambda url: (make_html(), "No price shown here at all.")

        with pytest.raises(ScraperError):
            scraper.fetch("https://www.example.com/products/some-item")


class TestWholeStoreAPI:
    """Primary Catlog discovery: render page -> store id -> paginate
    items/public -> build /products/<slug> URLs. No network in tests —
    _render and _api_json are stubbed.
    """

    def test_discover_paginates_and_builds_product_urls(self, scraper):
        scraper._render = lambda url: (make_next_data_html("store-123"), "")
        pages = {
            "1": items_page(["item-a-1", "item-b-2"], page=1, total_pages=2),
            "2": items_page(["item-c-3"], page=2, total_pages=2),
        }

        def fake_api(url):
            page = url.split("page=")[1].split("&")[0]
            return pages[page]

        scraper._api_json = fake_api

        urls = scraper.discover_product_urls("https://www.jredtechnologiesltd.com/products")

        assert urls == [
            "https://www.jredtechnologiesltd.com/products/item-a-1",
            "https://www.jredtechnologiesltd.com/products/item-b-2",
            "https://www.jredtechnologiesltd.com/products/item-c-3",
        ]

    def test_deduplicates_and_sorts(self, scraper):
        scraper._render = lambda url: (make_next_data_html("store-123"), "")
        scraper._api_json = lambda url: items_page(
            ["z-item-9", "a-item-1", "a-item-1"], page=1, total_pages=1
        )

        urls = scraper.discover_product_urls("https://www.jredtechnologiesltd.com/products")

        assert urls == [
            "https://www.jredtechnologiesltd.com/products/a-item-1",
            "https://www.jredtechnologiesltd.com/products/z-item-9",
        ]

    def test_handles_empty_store(self, scraper):
        scraper._render = lambda url: (make_next_data_html("store-123"), "")
        scraper._api_json = lambda url: items_page([], page=1, total_pages=1)

        assert scraper.discover_product_urls("https://www.jredtechnologiesltd.com/products") == []

    def test_uses_products_segment_under_catalog_homepage(self, scraper):
        scraper._render = lambda url: (make_next_data_html("store-123"), "")
        scraper._api_json = lambda url: items_page(["item-a-1"], page=1, total_pages=1)

        urls = scraper.discover_product_urls("https://www.jredtechnologiesltd.com/")

        assert urls == ["https://www.jredtechnologiesltd.com/products/item-a-1"]

    def test_falls_back_to_html_when_no_store_id(self, scraper):
        html = "<html><body><a href='/products/legacy-item-1'>X</a></body></html>"
        scraper._render = lambda url: (html, "")

        urls = scraper.discover_product_urls("https://www.jredtechnologiesltd.com/")

        assert urls == ["https://www.jredtechnologiesltd.com/products/legacy-item-1"]

    def test_falls_back_to_html_when_api_fails(self, scraper):
        html = make_next_data_html("store-123").replace(
            "</body></html>", "<a href='/products/legacy-item-1'>X</a></body></html>"
        )
        scraper._render = lambda url: (html, "")

        def bad_api(url):
            raise ScraperError("boom")

        scraper._api_json = bad_api

        urls = scraper.discover_product_urls("https://www.jredtechnologiesltd.com/")

        assert urls == ["https://www.jredtechnologiesltd.com/products/legacy-item-1"]
