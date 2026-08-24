"""Fetch product descriptions from supplier pages for products that lack one."""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import URLError
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

from apps.products.models import Product

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PricePilot/1.0)"}
_TIMEOUT = 15
_WORKERS = 5
_DELAY = 0.2  # seconds between batches


def _fetch_description(url: str) -> str | None:
    """Return the product description scraped from *url*, or None on failure."""
    try:
        req = Request(url, headers=_HEADERS)
        resp = urlopen(req, timeout=_TIMEOUT)
        html = resp.read().decode("utf-8", errors="replace")
    except (URLError, OSError, ValueError):
        return None

    soup = BeautifulSoup(html, "html.parser")

    # 1. og:description meta tag (most Catlog / Shopify stores)
    meta = soup.find("meta", property="og:description")
    if meta and meta.get("content"):
        return meta["content"].strip()

    # 2. JSON-LD product description
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get("@type") == "Product":
                desc = data.get("description", "")
                if desc:
                    return desc.strip()
        except (json.JSONDecodeError, TypeError):
            continue

    # 3. Common product-description divs
    for selector in [
        {"class": "product-description"},
        {"data-hook": "product-description"},
        {"class": "ProductDetails-description"},
    ]:
        div = soup.find("div", selector)
        if div:
            text = div.get_text(separator="\n", strip=True)
            if text:
                return text[:2000]

    return None


class Command(BaseCommand):
    help = (
        "Scrape supplier pages to fill in empty product descriptions. "
        "Uses threading for speed; safe to re-run (skips products that "
        "already have a description)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max products to process (0 = all).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be fetched without writing.",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Re-push updated products to the merchant store afterwards.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]

        qs = Product.objects.filter(
            (models_Q(description="") | models_Q(description__isnull=True))
        ).exclude(supplier_url="").exclude(supplier_url__isnull=True)

        if limit:
            qs = qs[:limit]

        products = list(qs)
        total = len(products)
        if total == 0:
            self.stdout.write("All products already have descriptions.")
            return

        self.stdout.write(f"Fetching descriptions for {total} products …")

        updated = 0
        failed = 0

        def _process(product):
            nonlocal updated, failed
            desc = _fetch_description(product.supplier_url)
            if desc:
                if not dry_run:
                    Product.objects.filter(pk=product.pk).update(description=desc)
                updated += 1
            else:
                failed += 1

        with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
            futures = {pool.submit(_process, p): p for p in products}
            for i, future in enumerate(as_completed(futures), 1):
                future.result()  # propagate exceptions
                if i % 20 == 0 or i == total:
                    self.stdout.write(f"  {i}/{total} processed …")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Updated: {updated}, Failed: {failed}, Total: {total}"
            )
        )

        if options["sync"] and updated and not dry_run:
            from apps.sync.services import StoreSyncService

            service = StoreSyncService()
            pks = [p.pk for p in products if p.description]
            result = service.sync_all(Product.objects.filter(pk__in=pks))
            self.stdout.write(
                self.style.SUCCESS(
                    f"Re-synced to store: synced={result.get('synced', 0)}, "
                    f"skipped={result.get('skipped', 0)}"
                )
            )


# django Q objects imported at module level to keep the class clean
from django.db import models as _models  # noqa: E402

models_Q = _models.Q
