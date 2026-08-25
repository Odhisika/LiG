import json
import logging
import re
import urllib.request
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from apps.common.exceptions import ProductNotFoundOnSupplier, ScraperError
from apps.scrapers.base import BaseScraper, PlaywrightRenderMixin
from apps.scrapers.registry import ScraperRegistry
from apps.scrapers.types import ScrapedProduct

logger = logging.getLogger(__name__)

# Ordered (symbol/prefix, currency code, capture-group regex). Checked in
# order so a more specific prefix (e.g. "GH₵") is tried before a generic
# one. Catlog operates across Nigeria, Ghana, South Africa, and Kenya.
_PRICE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("NGN", re.compile(r"₦\s?([\d,]+(?:\.\d{1,2})?)")),
    ("NGN", re.compile(r"\bNGN\s?([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)),
    ("GHS", re.compile(r"GH₵\s?([\d,]+(?:\.\d{1,2})?)")),
    ("GHS", re.compile(r"₵\s?([\d,]+(?:\.\d{1,2})?)")),
    ("GHS", re.compile(r"\bGHS\s?([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)),
    ("KES", re.compile(r"\bKES\s?([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)),
    ("ZAR", re.compile(r"\bZAR\s?([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)),
    ("USD", re.compile(r"\$\s?([\d,]+(?:\.\d{1,2})?)")),
]

_OUT_OF_STOCK_RE = re.compile(r"\b(out of stock|sold out|unavailable)\b", re.IGNORECASE)
# (?<![\d,]) guards against matching thousands-group digits of a formatted
# price like "₦5,000\nIn Stock" (which would otherwise match "000 in stock").
_STOCK_COUNT_RE = re.compile(
    r"(?<![\d,])(\d+)\s*(?:items?\s*)?(?:left|remaining|available|in stock)\b", re.IGNORECASE
)
_IN_STOCK_RE = re.compile(r"\bin stock\b", re.IGNORECASE)

# Catlog product URLs consistently contain a /products/<slug> segment —
# confirmed against two real product pages. Matching on this structural
# marker is far more durable than guessing at a listing grid's CSS
# classes, which we haven't been able to inspect directly.
_PRODUCT_URL_SEGMENT = "/products/"

# Catlog storefronts are a Next.js app whose catalog grids render cards
# with no <a> links at all — every product URL lives in the public API
# the storefront itself calls, keyed on the store id embedded in each
# page's __NEXT_DATA__. Whole-store discovery enumerates slugs via this
# API instead of parsing anchors, and falls back to the HTML parser
# below for stores that still render links.
_API_BASE = "https://api.catlog.shop"
_API_ITEMS_PATH = "/items/public"
_API_ITEMS_PER_PAGE = 100


def _quote_url(url: str) -> str:
    """Percent-encodes characters urllib can't send (real Catlog slugs
    contain e.g. U+202F NARROW NO-BREAK SPACE). Keeps reserved
    characters (%/:=&?[] etc.) untouched.
    """
    return quote(url, safe="%/:=&?[]~+!$,;'@()*")


def _extract_next_data(html: str) -> dict | None:
    """Returns the parsed __NEXT_DATA__ JSON from a rendered Catlog page,
    or None if it isn't present/parseable. Catlog embeds its serialized
    Next.js state in a <script id="__NEXT_DATA__"> block on every page.
    """
    marker = "__NEXT_DATA__"
    script_open = html.find(marker)
    if script_open == -1:
        return None
    script_body_start = html.find(">", script_open)
    if script_body_start == -1:
        return None
    script_close = html.find("</script>", script_body_start)
    if script_close == -1:
        return None
    try:
        data = json.loads(html[script_body_start + 1 : script_close])
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def extract_store_id(html: str) -> str | None:
    """Pulls the Catlog store id out of a rendered storefront page.

    The store object inside __NEXT_DATA__ carries the `id` used to key
    all store-scoped API requests.
    """
    data = _extract_next_data(html)
    if data is None:
        return None
    try:
        store = data["props"]["pageProps"]["data"]["data"]["store"]
    except (KeyError, TypeError):
        return None
    return store.get("id") if isinstance(store, dict) else None


def extract_page_item(html: str) -> dict | None:
    """Pulls the product's item object out of a product page's
    __NEXT_DATA__. It's server-rendered on every product page, so a plain
    HTTP GET (no browser) is enough to get price/stock/images/description.
    """
    data = _extract_next_data(html)
    if data is None:
        return None
    try:
        item = data["props"]["pageProps"]["item"]
    except (KeyError, TypeError):
        return None
    if not isinstance(item, dict) or not item.get("name"):
        return None
    return item


def _extract_item_slugs(payload: dict) -> list[str]:
    """Slugs from one items/public page. Items come back as
    {'featured_items': [...], 'other_items': [...]} inside data.items.
    """
    data = payload.get("data") or {}
    items = data.get("items") or {}
    return [
        item["slug"]
        for item in (items.get("featured_items") or []) + (items.get("other_items") or [])
        if item.get("slug")
    ]


def _clean_title(raw_title: str) -> str:
    """Catlog's og:title is "PRODUCT NAME | StoreName - Catlog" — keep
    just the product name.
    """
    return raw_title.split("|")[0].strip()


def _extract_meta(soup: BeautifulSoup, name: str) -> str | None:
    tag = soup.find("meta", property=name) or soup.find("meta", attrs={"name": name})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def _extract_price(visible_text: str) -> tuple[Decimal, str]:
    for currency, pattern in _PRICE_PATTERNS:
        match = pattern.search(visible_text)
        if match:
            raw = match.group(1).replace(",", "")
            try:
                return Decimal(raw), currency
            except InvalidOperation:
                continue
    raise ScraperError(
        "Could not find a price on the page. The page may not have finished "
        "rendering, or its price display format isn't recognized yet — see "
        "apps/scrapers/catlog.py:_PRICE_PATTERNS."
    )


def _extract_stock(visible_text: str) -> int | None:
    if _OUT_OF_STOCK_RE.search(visible_text):
        return 0
    count_match = _STOCK_COUNT_RE.search(visible_text)
    if count_match:
        return int(count_match.group(1))
    if _IN_STOCK_RE.search(visible_text):
        return None  # known to be in stock, exact quantity not shown
    logger.info("No stock signal found in rendered page text.")
    return None


def parse_item(item: dict) -> ScrapedProduct:
    """Builds a ScrapedProduct from a Catlog item object (the shape used
    both by the items/public API and each product page's __NEXT_DATA__).

    Price follows what the storefront displays: the discount price when
    one is set, otherwise the base price (both are in display units —
    confirmed against rendered price text). Stock mirrors parse()'s
    semantics: 0 = unavailable, an int = quantity, None = unknown.
    """
    price = item.get("discount_price")
    if price is None:
        price = item.get("price")
    if price is None:
        raise ScraperError("Catlog item has no price.")

    if item.get("available") is False:
        stock = 0
    elif item.get("quantity") is not None:
        stock = int(item.get("quantity"))
    else:
        stock = None

    description = item.get("description") or ""
    if not description:
        parts = []
        if item.get("name"):
            parts.append(item["name"])
        for key in ("brand", "category", "sku"):
            val = item.get(key)
            if val:
                parts.append(f"{key.title()}: {val}")
        description = " - ".join(parts) if parts else ""

    return ScrapedProduct(
        title=(item.get("name") or "")[:255],
        price=Decimal(str(price)),
        currency=item.get("currency") or "",
        stock=stock,
        description=description,
        images=item.get("images") or [],
    )


@ScraperRegistry.register
class CatlogScraper(PlaywrightRenderMixin, BaseScraper):
    """Scraper for storefronts built on Catlog (catlog.shop and mapped
    custom domains like jredtechnologiesltd.com) — a social-commerce
    storefront builder used by many small suppliers in Nigeria, Ghana,
    South Africa, and Kenya.

    Product pages are a Next.js app, but the full product object (name,
    price, discount price, quantity, images, description) is
    server-rendered into each page's __NEXT_DATA__ JSON — so `fetch()`
    takes a fast path: a plain HTTP GET + parse_item(). Playwright
    rendering is only used as a fallback for the edge case where a store
    doesn't embed the item (the original client-rendered path).

    The prices in __NEXT_DATA__/items-public are in display units — we
    verified discount_price/price match the rendered price text exactly
    (e.g. GHS 220.00 shown <-> discount_price 220). Catlog's Paystack
    integration represents money in kobo internally, but this public
    storefront API does not; the render-based parse() exists as a
    cross-check for any store that deviates.
    """

    key = "catlog"

    def fetch(self, url: str) -> ScrapedProduct:
        try:
            html = self._http_get(url)
            item = extract_page_item(html)
        except ProductNotFoundOnSupplier:
            # 404/410 — product is gone from the supplier. Don't waste
            # time rendering with Playwright; propagate immediately.
            raise
        except Exception as exc:
            logger.warning(
                "Catlog fast-path fetch failed for %s (%s) — falling back to render.", url, exc
            )
            item = None
        if item is not None:
            return parse_item(item)

        html, visible_text = self._render(url)
        return self.parse(html, visible_text)

    def _http_get(self, url: str) -> str:
        """Plain GET for Catlog's server-rendered pages — kept as a
        method so tests can substitute fixtures without the network.
        Raises ProductNotFoundOnSupplier for 404/410 responses.
        """
        request = urllib.request.Request(_quote_url(url), headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            if exc.code in (404, 410):
                raise ProductNotFoundOnSupplier(
                    f"Product not found on supplier (HTTP {exc.code}): {url}"
                ) from exc
            raise

    def parse(self, html: str, visible_text: str) -> ScrapedProduct:
        """Pure parsing logic, deliberately separate from `fetch()` so
        it's testable against saved HTML fixtures without a browser.
        """
        soup = BeautifulSoup(html, "html.parser")

        raw_title = _extract_meta(soup, "og:title") or (soup.title.string if soup.title else None)
        if not raw_title:
            raise ScraperError("Could not find a product title on the page.")
        title = _clean_title(raw_title)

        description = _extract_meta(soup, "og:description") or ""
        if not description:
            description = _extract_meta(soup, "description") or ""
        if not description and visible_text:
            lines = [ln.strip() for ln in visible_text.splitlines() if ln.strip()]
            desc_lines = []
            for ln in lines:
                if ln == title or _PRICE_PATTERNS[0][1].search(ln) or _IN_STOCK_RE.search(ln):
                    continue
                desc_lines.append(ln)
                if len(desc_lines) >= 3:
                    break
            description = " ".join(desc_lines)

        images = []
        image_url = _extract_meta(soup, "og:image")
        if image_url:
            images.append(image_url)

        price, currency = _extract_price(visible_text)
        stock = _extract_stock(visible_text)

        return ScrapedProduct(
            title=title,
            price=price,
            currency=currency,
            stock=stock,
            description=description,
            images=images,
        )

    def discover_product_urls(self, catalog_url: str) -> list[str]:
        """Whole-store discovery: renders the catalog page to learn the
        store id, then enumerates every product slug via Catlog's public
        API (the storefront's own grids render cards with no links, so
        HTML parsing finds nothing). Falls back to parse_catalog() for
        the edge case where the API route isn't available.
        """
        html, _ = self._render(catalog_url)

        store_id = extract_store_id(html)
        if store_id:
            try:
                return self._discover_via_api(store_id, catalog_url)
            except ScraperError as exc:
                logger.warning(
                    "Catlog API discovery failed for %s (%s) — falling back to HTML parsing.",
                    catalog_url,
                    exc.message,
                )
        return self.parse_catalog(html, catalog_url)

    def _discover_via_api(self, store_id: str, catalog_url: str) -> list[str]:
        base = urljoin(catalog_url, "/products/")
        return sorted({urljoin(base, slug) for slug in self._fetch_store_slugs(store_id)})

    def _fetch_store_slugs(self, store_id: str) -> list[str]:
        """Paginates items/public store-wide (no category filter) and
        collects every slug.
        """
        slugs: list[str] = []
        page = 1
        while True:
            url = (
                f"{_API_BASE}{_API_ITEMS_PATH}"
                f"?filter[store]={store_id}&page={page}"
                f"&per_page={_API_ITEMS_PER_PAGE}&separateFeaturedItems=false"
            )
            payload = self._api_json(url)
            slugs.extend(_extract_item_slugs(payload))

            total_pages = payload.get("total_pages") or 1
            if page >= total_pages:
                return slugs
            page += 1

    def _api_json(self, url: str) -> dict:
        """Minimal JSON GET against the Catlog public API — kept as a
        method so tests can substitute fixtures without the network.
        """
        try:
            request = urllib.request.Request(_quote_url(url), headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except Exception as exc:
            raise ScraperError(f"Catlog API request failed for {url}: {exc}") from exc

    def parse_catalog(self, html: str, base_url: str) -> list[str]:
        """Pure parsing logic, deliberately separate from
        discover_product_urls() so it's testable against saved HTML
        fixtures without a browser — same pattern as parse().

        Finds every link containing a /products/ segment and resolves
        it to an absolute URL. Doesn't attempt to extract title/price
        from the listing markup — see BaseScraper.discover_product_urls
        for why that's deliberate.
        """
        soup = BeautifulSoup(html, "html.parser")
        urls: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if _PRODUCT_URL_SEGMENT in href:
                urls.add(urljoin(base_url, href))

        return sorted(urls)
