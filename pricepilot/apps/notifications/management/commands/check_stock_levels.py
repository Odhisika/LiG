"""Check stock levels across all products and record low-stock alerts.

This command scans all active products and records LOW_STOCK notification
events for any that are at or below the threshold (default: 5 units).
Useful for initial seeding of alerts or periodic manual checks.

Examples:
    # Check all products, record alerts for low stock
    python manage.py check_stock_levels

    # Set custom threshold
    python manage.py check_stock_levels --threshold 10

    # Only check products from a specific supplier
    python manage.py check_stock_levels --supplier "JRED"

    # Preview what would be recorded
    python manage.py check_stock_levels --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.notifications.models import NotificationEvent
from apps.notifications.services import NotificationService
from apps.products.models import Product


class Command(BaseCommand):
    help = "Check stock levels and record low-stock alerts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--threshold",
            type=int,
            default=5,
            help="Stock level threshold for alerts (default: 5).",
        )
        parser.add_argument(
            "--supplier",
            type=str,
            help="Only check products from this supplier (name contains).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be recorded without writing.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        threshold = options["threshold"]

        owner = User.objects.first()
        if not owner:
            self.stderr.write("No users found.")
            return

        qs = Product.objects.filter(
            owner=owner,
            stock__isnull=False,
            stock__gt=0,
            stock__lte=threshold,
            status=Product.Status.ACTIVE,
        )

        if options["supplier"]:
            from apps.suppliers.models import Supplier

            supplier = Supplier.objects.filter(
                owner=owner, name__icontains=options["supplier"]
            ).first()
            if supplier is None:
                self.stderr.write(f"Supplier '{options['supplier']}' not found.")
                return
            qs = qs.filter(supplier=supplier)

        products = list(qs)
        count = len(products)

        if count == 0:
            self.stdout.write(f"No products with stock <= {threshold} found.")
            return

        self.stdout.write(f"Found {count} products with stock <= {threshold}:")

        recorded = 0
        for product in products:
            # Check if we already have a recent LOW_STOCK event for this product
            recent_alert = NotificationEvent.objects.filter(
                owner=owner,
                event_type=NotificationEvent.EventType.LOW_STOCK,
                product=product,
                sent=False,
            ).exists()

            status = "already has pending alert" if recent_alert else "NEW"
            self.stdout.write(
                f"  [{status}] {product.name[:40]}: stock={product.stock}"
            )

            if not recent_alert and not dry_run:
                NotificationService.record_event(
                    owner,
                    NotificationEvent.EventType.LOW_STOCK,
                    product=product,
                    payload={
                        "stock": product.stock,
                        "threshold": threshold,
                        "source": "stock_check",
                    },
                )
                recorded += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"[DRY RUN] Would record {count} low-stock alerts")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Recorded {recorded} new low-stock alerts")
            )
