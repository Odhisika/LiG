import logging
from abc import ABC, abstractmethod

from apps.common.exceptions import ScraperError
from apps.scrapers.types import ScrapedProduct

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Every supplier scraper implements this. Never hardcode a scraper
    call site elsewhere in the codebase — always go through
    ScraperRegistry so new suppliers are a config change, not a
    code change everywhere else.
    """

    #: Key used in Supplier.default_scraper and ScraperRegistry.
    key: str

    @abstractmethod
    def fetch(self, url: str) -> ScrapedProduct:
        """Fetch and parse one product page. Must raise ScraperError
        (not return partial/garbage data) if required fields can't be
        determined — silent bad data is worse than a loud failure here,
        since it would otherwise get written straight into PriceHistory.
        """
        raise NotImplementedError

    def discover_product_urls(self, catalog_url: str) -> list[str]:
        """Optional capability: find product page URLs on a catalog/
        listing page. Deliberately returns bare URLs, not full
        ScrapedProduct data — accurate title/price/stock for a newly
        found product comes from calling fetch() on it individually
        (already proven correct), rather than trying to parse rich
        details out of a listing grid whose markup is far less
        predictable than a single product page's.

        Not every scraper needs to support this. The default raises,
        so DiscoveryService can treat "not implemented" as a normal,
        catchable outcome rather than assuming every scraper has it.
        """
        raise ScraperError(f"{type(self).__name__} does not support product discovery.")


class PlaywrightRenderMixin:
    """Shared browser-automation plumbing for scrapers whose target site
    renders product data client-side (common for React/Next.js/Vue
    storefronts). Concrete scrapers call `_render()` to get fully
    hydrated HTML + visible text, then do their own parsing — keeping
    the "drive a browser" concern separate from the "parse this site's
    markup" concern, so parsing logic stays unit-testable without ever
    launching a browser.
    """

    render_timeout_ms = 20_000

    def _render(self, url: str) -> tuple[str, str]:
        """Returns (full_rendered_html, visible_body_text)."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover
            raise ScraperError(
                "Playwright is not installed. Run `playwright install --with-deps chromium`."
            ) from exc

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
                try:
                    page = browser.new_page()
                    page.goto(url, wait_until="networkidle", timeout=self.render_timeout_ms)
                    html = page.content()
                    visible_text = page.inner_text("body")
                    return html, visible_text
                finally:
                    browser.close()
        except Exception as exc:
            logger.warning("Scraper render failed for %s: %s", url, exc)
            raise ScraperError(f"Failed to render {url}: {exc}") from exc
