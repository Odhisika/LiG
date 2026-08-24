"""Bulk-import all pending discovered products from a supplier.

Usage:
    python manage.py bulk_import_supplier "JRED Technologies"
    python manage.py bulk_import_supplier "JRED Technologies" --dry-run
    python manage.py bulk_import_supplier "JRED Technologies" --limit 50
"""

import logging
import sys

from django.core.management.base import BaseCommand

from apps.discovery.models import DiscoveredProduct
from apps.discovery.services import DiscoveryService
from apps.products.categorizer import categorize_product
from apps.suppliers.models import Supplier

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Bulk-import all pending discovered products from a supplier into PricePilot and LiG."

    def add_arguments(self, parser):
        parser.add_argument("supplier_name", type=str, help="Name of the supplier to import from")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be imported without importing")
        parser.add_argument("--limit", type=int, default=0, help="Max number of products to import (0 = all)")
        parser.add_argument("--skip-errors", action="store_true", help="Continue on individual product errors")

    def handle(self, *args, **options):
        supplier_name = options["supplier_name"]
        dry_run = options["dry_run"]
        limit = options["limit"]
        skip_errors = options["skip_errors"]

        try:
            supplier = Supplier.objects.get(name=supplier_name)
        except Supplier.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Supplier '{supplier_name}' not found."))
            sys.exit(1)

        pending = DiscoveredProduct.objects.filter(
            supplier=supplier,
            status=DiscoveredProduct.Status.PENDING,
        ).exclude(price__isnull=True).order_by("title")

        if limit > 0:
            pending = pending[:limit]

        total = pending.count()
        self.stdout.write(f"\n{'DRY RUN - ' if dry_run else ''}Bulk importing {total} products from {supplier.name}\n")

        if dry_run:
            self._show_preview(pending)
            return

        imported = skipped = failed = 0
        for i, discovery in enumerate(pending.iterator(), 1):
            title = discovery.title or "Untitled"
            try:
                product = DiscoveryService.import_discovery(
                    supplier.owner, discovery.id
                )
                # Auto-categorize
                cat = categorize_product(product.name, product.description)
                if cat and product.category != cat:
                    product.category = cat
                    product.save(update_fields=["category"])
                imported += 1
                self.stdout.write(f"  [{i}/{total}] OK  {title[:60]}")
            except Exception as exc:
                if skip_errors:
                    failed += 1
                    self.stderr.write(f"  [{i}/{total}] FAIL  {title[:60]}: {exc}")
                else:
                    raise

        self.stdout.write(self.style.SUCCESS(
            f"\nDone: {imported} imported, {skipped} skipped, {failed} failed"
        ))

    def _show_preview(self, queryset):
        """Show a preview of what would be imported."""
        from apps.products.categorizer import categorize_product

        self.stdout.write(f"{'Category':<25} {'Price':>10}  Title")
        self.stdout.write("-" * 95)

        categories = {}
        for d in queryset.iterator():
            cat = categorize_product(d.title, "") if d.title else "(uncategorized)"
            categories[cat] = categories.get(cat, 0) + 1
            self.stdout.write(f"  {(cat or '(uncategorized)'):<23} {d.price or 0:>10.2f}  {(d.title or 'Untitled')[:45]}")

        self.stdout.write(f"\nCategory summary:")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            self.stdout.write(f"  {cat or '(uncategorized)':<25} {count:>4}")
