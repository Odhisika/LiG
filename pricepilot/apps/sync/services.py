import logging
import uuid
from collections import Counter
from decimal import Decimal
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.text import slugify

from apps.dashboard.models import ActivityEvent
from apps.dashboard.services import ActivityService
from apps.products.categorizer import CANONICAL_CATEGORIES as CATEGORIZER_CANONICAL_CATEGORIES
from apps.sync.models import LiGCategory, LiGProduct, LiGProductGallery

logger = logging.getLogger(__name__)

TWO_PLACES = Decimal("0.01")
_IMAGE_TIMEOUT_SECONDS = 30
_IMAGE_USER_AGENT = "Mozilla/5.0 (compatible; PricePilot/1.0)"

# When LiG does not yet have a fine-grained category row, fall back to the
# closest broader department that already exists in the merchant store.
_CATEGORY_ALIASES: dict[str, tuple[str, ...]] = {
    "laptops": ("Computers",),
    "desktops": ("Computers",),
    "monitors": ("Computers",),
    "components": ("Computers",),
    "storage": ("Computers",),
    "routers & modems": ("Networking",),
    "switches": ("Networking",),
    "printers": ("Peripherals",),
    "security cameras": ("Security & CCTV",),
    "projectors & screens": ("Peripherals",),
    "cctv accessories": ("Security & CCTV", "Accessories"),
    "pos equipment": ("Peripherals",),
    "hdmi & av cables": ("Accessories",),
    "networking cables": ("Networking", "Accessories"),
    "toner & ink": ("Peripherals", "Accessories"),
}


class StoreSyncError(Exception):
    """Raised for sync problems that should be reported but not crash the
    caller (the Price Monitor Engine or a scheduled task).
    """


def is_configured() -> bool:
    """True only when the store sync is both switched on (LIG_SYNC_ENABLED)
    and a `lig` database alias exists (LIG_DATABASE_URL set). All other
    code paths treat an unconfigured sync as a silent no-op, so the feature
    can't break existing monitoring even if these settings are wrong.
    """
    return settings.LIG_SYNC_ENABLED and "lig" in settings.DATABASES


def resolve_lig_category(text: str) -> LiGCategory | None:
    """Match a category string against LiG's existing categories.

    Tries `category_name`, then `slug`, then a case-insensitive
    `category_name` contains-match. If the fine-grained category does not
    exist in LiG, tries a broader alias (e.g. `Laptops` -> `Computers`).
    Returns None when nothing matches, so callers decide whether to fall
    back to the default category. No category is ever created here.
    """
    qs = LiGCategory.objects.filter(is_active=True)
    text = (text or "").strip()
    if not text:
        return None
    candidates = (text,) + _CATEGORY_ALIASES.get(text.casefold(), ())
    seen: set[str] = set()
    for candidate in candidates:
        candidate = (candidate or "").strip()
        candidate_key = candidate.casefold()
        if not candidate or candidate_key in seen:
            continue
        seen.add(candidate_key)

        exact = qs.filter(category_name__iexact=candidate).first()
        if exact is not None:
            return exact
        slug_exact = qs.filter(slug__iexact=candidate).first()
        if slug_exact is not None:
            return slug_exact
        contains = qs.filter(category_name__icontains=candidate).first()
        if contains is not None:
            return contains
    return None


def _effective_selling(pp_product) -> Decimal | None:
    """The price to write into the store's `price` field.

    Precedence:
    1. Manual selling_price (stored on the product)
    2. Product's pricing_rule (applied to supplier_price)
    3. Owner's default markup (applied to supplier_price)
    4. Raw supplier_price
    None if nothing usable (e.g. a zero/absent price).
    """
    from apps.pricing.services import DefaultMarkupService, PricingService

    # 1. Manual selling_price wins
    if pp_product.selling_price is not None:
        return pp_product.selling_price.quantize(TWO_PLACES)

    # 2. Product-level pricing_rule
    if pp_product.pricing_rule_id:
        try:
            value = PricingService.compute_selling_price(
                pp_product.supplier_price, pp_product.pricing_rule
            )
            return value.quantize(TWO_PLACES) if value else None
        except Exception:
            pass  # fall through to default markup

    # 3. Owner's default markup
    markup = DefaultMarkupService.get_markup_percent(pp_product.owner)
    value = PricingService.effective_selling_price(
        pp_product.supplier_price,
        markup_percent=markup,
    )
    if value is None:
        return None
    value = value.quantize(TWO_PLACES)
    return value if value > 0 else None


def _is_available(pp_product) -> bool:
    """Whether the product should stay on sale in the store.

    Only a confirmed stock-out (or an archived product) takes it off the
    store. A failed scrape means the price couldn't be refreshed this round —
    it must NOT hide the product or its last known price, otherwise one
    transient supplier hiccup would pull a whole catalog offline.
    """
    from apps.products.models import Product

    return pp_product.status not in (
        Product.Status.OUT_OF_STOCK,
        Product.Status.ARCHIVED,
    )


class StoreSyncService:
    """Pushes PricePilot's monitored values into the merchant's own store
    (LiG) across the `lig` database alias.

    Two jobs:
      - **update** a LiG product that already exists, matched by
        Product.store_product_id (remembered from a previous run) and
        falling back to `sku` — only fields that actually changed are
        written, so a synced row is never touched when nothing differs.
      - **seed** a LiG product when none matches: full product row with
        name, price, cost, stock, description, category and downloaded
        images, created as a base store.Product row (every LiG product
        type shares that base table, so one INSERT covers all of them).

    Idempotent and safe to call from anywhere — the Price Monitor Engine
    after a change, a scheduled reconcile, or a management command.
    """

    @staticmethod
    def sync_product(pp_product) -> dict:
        """Sync one PricePilot product to the store.

        Returns a result dict {'action': ..., 'lig_product_id': ...|None}
        where action is one of: 'updated', 'created', 'noop', 'skipped',
        'failed'.
        """
        if not is_configured():
            return {"action": "skipped", "reason": "disabled", "lig_product_id": None}
        try:
            lig = StoreSyncService._resolve(pp_product)
            if lig is not None:
                action = StoreSyncService._update_existing(pp_product, lig)
            else:
                lig, action = StoreSyncService._seed_new(pp_product)

            if lig is not None:
                fields = ["store_product_id", "store_synced_at"]
                if not pp_product.sku and lig.sku:
                    pp_product.sku = lig.sku
                    fields.append("sku")
                pp_product.store_product_id = lig.id
                pp_product.store_synced_at = timezone.now()
                pp_product.save(update_fields=fields)

            if action in ("created", "updated"):
                ActivityService.record(
                    pp_product.owner,
                    ActivityEvent.EventType.STORE_SYNCED,
                    product=pp_product,
                    action=action,
                    lig_product_id=lig.id if lig is not None else None,
                )

            return {"action": action, "lig_product_id": lig.id if lig is not None else None}
        except Exception as exc:
            logger.exception("Store sync failed for product %s", pp_product.id)
            return {"action": "failed", "error": str(exc), "lig_product_id": None}

    @staticmethod
    def delete_product(pp_product) -> dict:
        """Hard-deletes the merchant-store row for a product the supplier
        has removed, and clears this side's sync pointers so a future
        reactivation re-seeds cleanly instead of resurrecting a stale row.

        Returns a result dict {'action': ..., 'deleted': bool} where action
        is one of: 'deleted', 'noop', 'skipped', 'failed'. Never raises.
        """
        if not is_configured():
            return {"action": "skipped", "reason": "disabled", "deleted": False}
        try:
            lig = StoreSyncService._resolve(pp_product)
            deleted = False
            if lig is not None:
                deleted_count, _ = lig.delete()
                deleted = deleted_count > 0
                logger.info(
                    "Store sync: deleted LiG product %s for removed PricePilot product %s",
                    lig.id,
                    pp_product.id,
                )

            if pp_product.store_product_id is not None or pp_product.store_synced_at is not None:
                pp_product.store_product_id = None
                pp_product.store_synced_at = None
                pp_product.save(update_fields=["store_product_id", "store_synced_at"])

            if deleted:
                ActivityService.record(
                    pp_product.owner,
                    ActivityEvent.EventType.STORE_DELETED,
                    product=pp_product,
                    lig_product_id=lig.id if lig is not None else None,
                )

            return {"action": "deleted" if deleted else "noop", "deleted": deleted}
        except Exception as exc:
            logger.exception("Store delete failed for product %s", pp_product.id)
            return {"action": "failed", "error": str(exc), "deleted": False}

    @staticmethod
    def _resolve(pp_product) -> LiGProduct | None:
        """Find the matching LiG row. Prefer the remembered id, then sku."""
        if pp_product.store_product_id:
            return LiGProduct.objects.filter(id=pp_product.store_product_id).first()
        if pp_product.sku:
            return LiGProduct.objects.filter(sku=pp_product.sku).first()
        return None

    @staticmethod
    def _update_existing(pp_product, lig: LiGProduct) -> str:
        updates: dict = {}

        if lig.product_name != pp_product.name:
            updates["product_name"] = pp_product.name

        selling = _effective_selling(pp_product)
        if selling is not None and lig.price != selling:
            updates["price"] = selling

        cost = pp_product.supplier_price.quantize(TWO_PLACES)
        if lig.cost_price != cost:
            updates["cost_price"] = cost

        if lig.description != pp_product.description:
            updates["description"] = pp_product.description

        available = _is_available(pp_product)
        if lig.is_available != available:
            updates["is_available"] = available

        if (
            settings.LIG_SYNC_STOCK
            and pp_product.stock is not None
            and lig.stock != pp_product.stock
        ):
            updates["stock"] = pp_product.stock

        category = StoreSyncService._resolve_category(pp_product)
        if category is not None and lig.category_id != category.id:
            updates["category"] = category

        if not updates:
            return (
                "noop"
                if not StoreSyncService._attach_missing_images(lig, pp_product)
                else "updated"
            )

        LiGProduct.objects.filter(id=lig.id).update(**updates)
        StoreSyncService._attach_missing_images(lig, pp_product)
        logger.info("Store sync: updated LiG product %s (%s)", lig.id, updates)
        return "updated"

    @staticmethod
    def _attach_missing_images(lig: LiGProduct, pp_product) -> bool:
        """Downloads the supplier's images into our own media directory when
        the LiG row still has none, so the store never hot-links to the
        supplier's host. Returns True if any image was attached.

        Runs from the update path too (not just seeding), so rows seeded
        before images existed get backfilled on the next sync.
        """
        if not settings.LIG_SYNC_IMAGES or lig.images or not pp_product.images:
            return False
        StoreSyncService._attach_images(lig, pp_product.images)
        return True

    @staticmethod
    def _seed_new(pp_product) -> tuple[LiGProduct, str]:
        category = StoreSyncService._resolve_category(pp_product)
        if category is None:
            raise StoreSyncError(
                f"Could not resolve a LiG category for product '{pp_product.name}' "
                f"(category text: '{pp_product.category or ''}'). Set a matching "
                "category_name/slug in LiG, or configure LIG_DEFAULT_CATEGORY_SLUG."
            )

        selling = _effective_selling(pp_product)
        if selling is None:
            raise StoreSyncError(f"Product '{pp_product.name}' has no usable selling price.")

        lig = LiGProduct.objects.create(
            product_name=pp_product.name[:500],
            slug=StoreSyncService._unique_slug(pp_product.name),
            sku=pp_product.sku or LiGProduct._meta.get_field("sku").get_default(),
            description=pp_product.description or "",
            short_description=(pp_product.description or "")[:500],
            price=selling,
            cost_price=pp_product.supplier_price.quantize(TWO_PLACES),
            stock=pp_product.stock if pp_product.stock is not None else 0,
            is_available=_is_available(pp_product),
            category=category,
        )

        if settings.LIG_SYNC_IMAGES and pp_product.images:
            StoreSyncService._attach_images(lig, pp_product.images)

        logger.info("Store sync: seeded LiG product %s (%s)", lig.id, lig.product_name)
        return lig, "created"

    @staticmethod
    def _resolve_category(pp_product) -> LiGCategory | None:
        """Find the LiG category for a seed.

        Tries the product's free-text `category` against category_name/slug
        (exact, then contains), then the configured LIG_DEFAULT_CATEGORY_SLUG
        fallback. Categories are only matched against ones the store already
        has — a canonical auto-categorizer name that's missing is logged and
        falls through to the default instead of inventing a new department.
        """
        qs = LiGCategory.objects.filter(is_active=True)
        text = (pp_product.category or "").strip()
        if text:
            resolved = resolve_lig_category(text)
            if resolved is not None:
                return resolved
            if text in CATEGORIZER_CANONICAL_CATEGORIES:
                logger.warning(
                    "Store sync: canonical category %r is not in the store — "
                    "falling back to the default category instead of creating it.",
                    text,
                )
        fallback_slug = settings.LIG_DEFAULT_CATEGORY_SLUG
        if fallback_slug:
            return qs.filter(slug__iexact=fallback_slug).first()
        return None

    @staticmethod
    def _unique_slug(name: str) -> str:
        """Deterministic, unique-enough slug for LiG's unique slug column."""
        base = slugify(name) or "product"
        candidate = base[:450]
        if not LiGProduct.objects.filter(slug=candidate).exists():
            return candidate
        for _ in range(5):
            candidate = f"{base[:440]}-{uuid.uuid4().hex[:6]}"
            if not LiGProduct.objects.filter(slug=candidate).exists():
                return candidate
        return f"product-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _attach_images(lig: LiGProduct, image_urls: list[str]) -> None:
        """Download supplier images and attach them: the first becomes the
        product's primary image, the rest become gallery rows. Each download
        is isolated so one bad URL never fails the whole seed.

        The files land in this process's MEDIA_ROOT — point LIG_MEDIA_ROOT at
        the merchant site's media directory when the two don't share it.
        """
        for index, url in enumerate(image_urls):
            if not url:
                continue
            try:
                request = Request(url, headers={"User-Agent": _IMAGE_USER_AGENT})
                with urlopen(request, timeout=_IMAGE_TIMEOUT_SECONDS) as response:
                    if response.status != 200:
                        logger.warning(
                            "Store sync: image %s returned HTTP %s", url, response.status
                        )
                        continue
                    content = response.read()
                name = f"{uuid.uuid4().hex[:10]}{StoreSyncService._extension(url)}"
                if index == 0 and not lig.images:
                    lig.images.save(name, ContentFile(content), save=True)
                else:
                    gallery = LiGProductGallery.objects.create(
                        product=lig, image_type="gallery", order=index
                    )
                    gallery.image.save(name, ContentFile(content), save=True)
            except Exception as exc:
                logger.warning("Store sync: could not download image %s: %s", url, exc)

    @staticmethod
    def _extension(url: str) -> str:
        path = url.split("?", 1)[0].split("#", 1)[0]
        for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            if path.lower().endswith(ext):
                return ext
        return ".jpg"

    @staticmethod
    def sync_all(queryset=None) -> dict:
        """Reconcile every store-bound product: matched rows get updated,
        unmatched rows with a sku get seeded. Returns an action tally.

        The whole pass is resilient — one product failing to sync never
        stops the rest.
        """
        from apps.products.models import Product

        # Every live product is fair game: already-synced rows get updated,
        # and brand-new products (imported via discovery with no sku yet)
        # get seeded. `Product.objects` excludes soft-deleted rows.
        qs = queryset or Product.objects.all()
        tally: Counter = Counter()
        for product in qs.iterator():
            result = StoreSyncService.sync_product(product)
            tally[result.get("action", "unknown")] += 1
            if result.get("action") == "failed":
                logger.error("Store sync: product %s failed: %s", product.id, result.get("error"))
        return dict(tally)
