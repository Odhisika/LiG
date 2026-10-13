"""Strip supplier images from storefront products in excluded categories.

The store sync deliberately skips copying supplier images for categories in
``LIG_SYNC_IMAGES_EXCLUDED_CATEGORIES`` (default: ``software``), because the
supplier's logo/branding is often baked into their product photos and must not
appear on our own site. That gate only stops *future* downloads — this command
cleans up the images attached before the gate was turned on.

Dry-run by default; pass ``--apply`` to actually clear the images. It only
removes the storefront's *reference* to the image (the file stays in MEDIA_ROOT
so nothing is irreversibly deleted).
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.sync.models import LiGCategory, LiGProduct, LiGProductGallery
from apps.sync.services import is_configured


class Command(BaseCommand):
    help = (
        "Clear supplier-sourced storefront images for excluded categories "
        "(default: software) so supplier logos stop showing on our site. "
        "Dry-run by default; pass --apply to write."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--category",
            action="append",
            dest="categories",
            default=None,
            help="Category name/slug to strip (repeatable). Defaults to "
            "LIG_SYNC_IMAGES_EXCLUDED_CATEGORIES.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually clear the images (default is a dry run).",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        if not is_configured():
            self.stdout.write(
                self.style.WARNING(
                    "Store sync not configured — set LIG_DATABASE_URL and "
                    "LIG_SYNC_ENABLED=True, then run migrations on both databases."
                )
            )
            return

        wanted = {
            str(entry).strip().casefold()
            for entry in (options["categories"] or settings.LIG_SYNC_IMAGES_EXCLUDED_CATEGORIES)
            if str(entry).strip()
        }
        if not wanted:
            self.stdout.write(
                self.style.WARNING(
                    "No categories to strip — pass --category or set "
                    "LIG_SYNC_IMAGES_EXCLUDED_CATEGORIES."
                )
            )
            return

        category_ids = [
            cat.id
            for cat in LiGCategory.objects.all()
            if (cat.category_name or "").strip().casefold() in wanted
            or (cat.slug or "").strip().casefold() in wanted
        ]
        if not category_ids:
            self.stdout.write(
                self.style.WARNING(
                    f"No store categories matched {sorted(wanted)} — nothing to do."
                )
            )
            return

        scanned = cleared = galleries_hidden = 0
        for product in LiGProduct.objects.filter(category_id__in=category_ids).iterator():
            scanned += 1
            has_primary = bool(product.images)
            gallery = LiGProductGallery.objects.filter(product_id=product.id, is_active=True)
            gallery_count = gallery.count()
            if not has_primary and not gallery_count:
                continue

            cleared += 1
            galleries_hidden += gallery_count
            self.stdout.write(
                f"  {product.id} {product.product_name[:55]:<55} "
                f"primary={'yes' if has_primary else 'no'} gallery={gallery_count}"
            )
            if apply:
                with transaction.atomic(using="lig"):
                    if has_primary:
                        LiGProduct.objects.filter(id=product.id).update(images=None)
                    if gallery_count:
                        gallery.update(is_active=False)

        verb = "cleared" if apply else "would clear"
        self.stdout.write(
            f"\n{scanned} products scanned; {cleared} {verb} "
            f"({galleries_hidden} gallery image(s) {'hidden' if apply else 'to hide'})."
        )
        if not apply and cleared:
            self.stdout.write("Re-run with --apply to clear the images.")
