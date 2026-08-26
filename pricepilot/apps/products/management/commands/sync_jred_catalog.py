"""Fetch every product from the Jred Technologies Catlog store and
upsert them into PricePilot with proper categorization.

Usage:
    python manage.py sync_jred_catalog
    python manage.py sync_jred_catalog --dry-run
    python manage.py sync_jred_catalog --limit 50
"""

from django.core.management.base import BaseCommand

from apps.products.catalog_sync import sync_catalog


class Command(BaseCommand):
    help = "Fetch all Jred products from Catlog API and upsert into PricePilot + LiG."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
        parser.add_argument("--limit", type=int, default=0, help="Max products to process (0=all)")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]
        label = "Previewing" if dry_run else "Syncing"
        self.stdout.write(f"{label} Jred catalog from Catlog API...")
        summary = sync_catalog(dry_run=dry_run, limit=limit)
        self.stdout.write(self.style.SUCCESS(
            f"Done: {summary['created']} created, {summary['updated']} updated, "
            f"{summary['unchanged']} unchanged, {summary['failed']} failed "
            f"{summary['removed']} removed/out-of-stock "
            f"(total: {summary['total']})"
        ))
