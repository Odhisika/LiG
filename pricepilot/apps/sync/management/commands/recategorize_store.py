from collections import Counter

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.products.categorizer import categorize_product
from apps.sync.models import LiGProduct
from apps.sync.services import is_configured, resolve_lig_category


class Command(BaseCommand):
    help = (
        "Re-categorize LiG's existing store products using PricePilot's "
        "categorizer (fixes jred-imported rows like switches stuck in "
        "Desktops, routers in Networking, cameras in Security & CCTV). "
        "Dry-run by default; pass --apply to write changes. Products the "
        "categorizer can't confidently classify are left unchanged unless "
        "--to-uncategorized is also given."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write the category changes (default is a dry run).",
        )
        parser.add_argument(
            "--to-uncategorized",
            action="store_true",
            help="Also move products with no confident match to the default "
            "(Uncategorized) category.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        to_uncategorized = options["to_uncategorized"]

        if not is_configured():
            self.stdout.write(
                self.style.WARNING(
                    "Store sync not configured — set LIG_DATABASE_URL and "
                    "LIG_SYNC_ENABLED=True, then run migrations on both databases."
                )
            )
            return

        default_category = None
        if settings.LIG_DEFAULT_CATEGORY_SLUG:
            default_category = resolve_lig_category(settings.LIG_DEFAULT_CATEGORY_SLUG)

        total = changed = unmatched = 0
        moves: Counter = Counter()
        for product in LiGProduct.objects.all().iterator():
            total += 1
            canonical = categorize_product(product.product_name, product.description)
            target = resolve_lig_category(canonical) if canonical else None
            if target is None:
                unmatched += 1
                if not to_uncategorized or default_category is None:
                    continue
                target = default_category
            if target.id == product.category_id:
                continue
            changed += 1
            old_name = product.category.category_name if product.category_id else "(none)"
            moves[(old_name, target.category_name)] += 1
            if apply:
                LiGProduct.objects.filter(id=product.id).update(category_id=target.id)
            else:
                self.stdout.write(
                    f"  {product.id} {product.product_name[:55]:<55} "
                    f"{old_name} -> {target.category_name}"
                )

        verb = "applied" if apply else "would change"
        self.stdout.write(f"\n{total} products scanned; {changed} {verb}.")
        if unmatched:
            self.stdout.write(
                f"{unmatched} products had no confident category "
                + (
                    "and were moved to the default (Uncategorized) category."
                    if to_uncategorized and default_category is not None
                    else "and were left unchanged."
                )
            )
        if moves:
            self.stdout.write("Moves by category:")
            for (old_name, new_name), count in moves.most_common():
                self.stdout.write(f"  {count:>4}  {old_name} -> {new_name}")
        if not apply and changed:
            self.stdout.write("Re-run with --apply to write the changes.")
