"""Automated Catlog catalog sync service.

Fetches all products from a Catlog store's public API and upserts them
into PricePilot with categorization. Designed to be called from both
management commands and Celery tasks.
"""

import json
import logging
import urllib.request
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import ScraperError
from apps.products.categorizer import categorize_product
from apps.products.models import Product
from apps.suppliers.models import Supplier

logger = logging.getLogger(__name__)

CATLOG_API_BASE = "https://api.catlog.shop"
CATLOG_ITEMS_PATH = "/items/public"
CATLOG_PER_PAGE = 100
STORE_DOMAIN = "jredtechnologiesltd.com"

STORE_IDS = {
    "Jred Technologies": "6720e1e0d489a00007234138",
    "JRED Technologies": "6720e1e0d489a00007234138",
}

TAG_TO_CATEGORY = {
    "laptops & Notebooks": "Laptops",
    "Desktop Computers": "Desktops",
    "Monitors & Displays": "Monitors",
    "Routers & modems ": "Routers & Modems",
    "Switches": "Switches",
    "Printers & Scanners": "Printers",
    "Printer Accessories": "Printers",
    "Security Cameras & Systems": "Security Cameras",
    "UPS/ACCESSORIES ": "UPS",
    "cables & connectors": "Networking Cables",
    "keyboards & Mice": "Accessories",
    "Memory & Storages": "Storage",
    "Computer Accessories": "Accessories",
    "Softwares": "Software",
    "Projector & accessories ": "Projectors & Screens",
    "projectors": "Projectors & Screens",
    "Tripod & Stabilizers": "Accessories",
    "Samsung Phones": "Peripherals",
    "Tablets": "Laptops",
    "money counting machine": "POS Equipment",
}

User = get_user_model()


def _summary(
    *,
    created: int = 0,
    updated: int = 0,
    unchanged: int = 0,
    failed: int = 0,
    removed: int = 0,
    total: int = 0,
    dry_run: bool = False,
) -> dict:
    return {
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "failed": failed,
        "removed": removed,
        "total": total,
        "dry_run": dry_run,
    }


def _normalize_url(url: str) -> str:
    return url.replace("https://www.", "https://").replace("http://www.", "http://")


def _fetch_all_items(store_id: str) -> list[dict]:
    all_items = []
    page = 1
    while True:
        url = (
            f"{CATLOG_API_BASE}{CATLOG_ITEMS_PATH}"
            f"?filter[store]={store_id}&page={page}"
            f"&per_page={CATLOG_PER_PAGE}&separateFeaturedItems=false"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        items_data = data.get("data", {}).get("items", {})
        page_items = items_data.get("featured_items", []) + items_data.get("other_items", [])
        all_items.extend(page_items)
        if page >= data.get("total_pages", 1):
            break
        page += 1
    return all_items


def _category_from_tags(item: dict) -> str:
    tags = item.get("tags") or []
    for tag in tags:
        tag_name = tag.get("name", "") if tag else ""
        mapped = TAG_TO_CATEGORY.get(tag_name)
        if mapped:
            return mapped
    return categorize_product(item.get("name", ""), item.get("description", ""))


def _get_or_create_supplier(owner) -> Supplier:
    jred_suppliers = Supplier.objects.filter(
        name__in=["Jred Technologies", "JRED Technologies"]
    )
    if jred_suppliers.exists():
        supplier = jred_suppliers.first()
        if jred_suppliers.count() > 1:
            old = jred_suppliers.exclude(id=supplier.id).first()
            if old:
                Product.objects.filter(supplier=old).update(supplier=supplier)
                old.delete()
                logger.info("Merged supplier '%s' into '%s'", old.name, supplier.name)
        return supplier
    return Supplier.objects.create(
        name="Jred Technologies",
        owner=owner,
        default_scraper="catlog",
    )


def _is_store_product_url(url: str) -> bool:
    normalized = _normalize_url(url or "")
    return normalized.startswith(f"https://{STORE_DOMAIN}/products/")


def _get_owner():
    owner_email = settings.JRED_CATALOG_OWNER_EMAIL.strip()
    if owner_email:
        owner = User.objects.filter(email__iexact=owner_email).first()
        if owner is None:
            logger.error("sync_catalog: owner email %s was not found, aborting.", owner_email)
        return owner
    return User.objects.first()


def sync_catalog(
    store_id: str | None = None,
    *,
    dry_run: bool = False,
    limit: int = 0,
    mark_missing_out_of_stock: bool = True,
) -> dict:
    """Fetch the full Catlog catalog and upsert into PricePilot.

    Returns: {created, updated, unchanged, failed, removed, total}
    """
    owner = _get_owner()
    if owner is None:
        logger.error("sync_catalog: no users found, aborting.")
        return _summary(dry_run=dry_run)

    supplier = _get_or_create_supplier(owner)

    if store_id is None:
        store_id = STORE_IDS.get(supplier.name, "6720e1e0d489a00007234138")

    logger.info("sync_catalog: fetching from Catlog API (store=%s)...", store_id)
    api_items = _fetch_all_items(store_id)
    if limit > 0:
        api_items = api_items[:limit]
    logger.info("sync_catalog: fetched %d products", len(api_items))

    existing = {}
    for p in Product.objects.filter(supplier=supplier).select_related("supplier"):
        existing[_normalize_url(p.supplier_url)] = p

    created = updated = unchanged = failed = removed = 0
    seen_urls: set[str] = set()

    with transaction.atomic():
        for item in api_items:
            slug = item.get("slug", "")
            api_url = f"https://{STORE_DOMAIN}/products/{slug}"
            norm_url = _normalize_url(api_url)
            seen_urls.add(norm_url)
            name = (item.get("name") or "Untitled")[:255]

            try:
                price = item.get("discount_price") or item.get("price")
                if price is None:
                    raise ScraperError(f"No price for {name}")
                supplier_price = Decimal(str(price))
            except (InvalidOperation, TypeError, ScraperError):
                failed += 1
                continue

            stock = None
            if item.get("available") is False:
                stock = 0
            elif item.get("quantity") is not None:
                stock = int(item["quantity"])

            description = item.get("description") or ""
            images = item.get("images") or []
            category = _category_from_tags(item)

            product = existing.get(norm_url)

            if product is not None:
                changed = False
                if product.supplier_price != supplier_price:
                    product.supplier_price = supplier_price
                    changed = True
                if product.stock != stock:
                    product.stock = stock
                    changed = True
                if product.name != name:
                    product.name = name
                    changed = True
                if product.description != description:
                    product.description = description
                    changed = True
                if product.images != images:
                    product.images = images
                    changed = True
                if category and product.category != category:
                    product.category = category
                    changed = True
                if product.status != Product.Status.ACTIVE:
                    product.status = Product.Status.ACTIVE
                    changed = True

                if changed:
                    product.last_checked_at = timezone.now()
                    if not dry_run:
                        product.save()
                    updated += 1
                else:
                    unchanged += 1
            else:
                if not dry_run:
                    Product.objects.create(
                        owner=owner,
                        supplier=supplier,
                        name=name,
                        supplier_url=api_url,
                        sku=slug[:100],
                        supplier_price=supplier_price,
                        currency="GHS",
                        status=Product.Status.ACTIVE,
                        stock=stock,
                        images=images,
                        description=description,
                        category=category or "",
                        last_checked_at=timezone.now(),
                    )
                created += 1

        should_mark_missing = mark_missing_out_of_stock and limit <= 0
        if should_mark_missing:
            for norm_url, product in existing.items():
                if (
                    norm_url not in seen_urls
                    and _is_store_product_url(product.supplier_url)
                    and product.status != Product.Status.OUT_OF_STOCK
                ):
                    product.status = Product.Status.OUT_OF_STOCK
                    product.stock = 0
                    product.last_checked_at = timezone.now()
                    if not dry_run:
                        product.save(update_fields=["status", "stock", "last_checked_at"])
                    removed += 1

        if dry_run:
            transaction.set_rollback(True)

    summary = _summary(
        created=created,
        updated=updated,
        unchanged=unchanged,
        failed=failed,
        removed=removed,
        total=len(api_items),
        dry_run=dry_run,
    )
    logger.info("sync_catalog: %s", summary)
    return summary
