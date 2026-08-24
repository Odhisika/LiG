from django.core.management.base import BaseCommand

from apps.products.categorizer import categorize_product
from apps.products.models import Product


class Command(BaseCommand):
    help = (
        "Auto-categorize products that have no category yet (laptops -> "
        "Laptops, network devices -> Networking, desktops -> Desktops, "
        "monitors -> Monitors, ...). Existing manual categories are left alone."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report how many products would change without saving.",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Re-push changed products to the merchant store afterwards.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        missing = list(Product.objects.filter(category__in=["", None]))
        updates = []
        for product in missing:
            category = categorize_product(product.name, product.description)
            if category:
                updates.append((product, category))

        if dry_run:
            self.stdout.write(
                f"{len(missing)} products without a category; "
                f"{len(updates)} would be categorized."
            )
            return

        if not updates:
            self.stdout.write("No products need categorizing.")
            return

        for product, category in updates:
            product.category = category
            product.save(update_fields=["category"])

        self.stdout.write(
            self.style.SUCCESS(f"Categorized {len(updates)} products.")
        )

        if options["sync"]:
            from apps.sync.services import StoreSyncService

            for product, _ in updates:
                StoreSyncService.sync_product(product)
            self.stdout.write(
                self.style.SUCCESS(f"Re-synced {len(updates)} products to the store.")
            )
