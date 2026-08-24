"""Seed PriceHistory records for products that have supplier_price changes.

Creates realistic historical price data for the last 30 days
to populate the Price History Dashboard.
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.history.models import PriceHistory
from apps.products.models import Product


class Command(BaseCommand):
    help = "Seed PriceHistory records for dashboard visualization."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days of history to seed (default: 30).",
        )
        parser.add_argument(
            "--products",
            type=int,
            default=50,
            help="Number of products to create history for (default: 50).",
        )
        parser.add_argument(
            "--events-per-product",
            type=int,
            default=5,
            help="Average price change events per product (default: 5).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        days = options["days"]
        num_products = options["products"]
        events_per_product = options["events_per_product"]

        owner = User.objects.first()
        if not owner:
            self.stderr.write("No users found.")
            return

        # Get products with supplier prices
        products = list(
            Product.objects.filter(
                owner=owner,
                supplier_price__isnull=False,
                supplier_price__gt=0,
            ).order_by("?")[:num_products]
        )

        if not products:
            self.stderr.write("No products with supplier prices found.")
            return

        self.stdout.write(f"Seeding history for {len(products)} products...")

        created_count = 0
        now = timezone.now()

        for product in products:
            # Generate 2-8 price change events per product
            num_events = random.randint(2, events_per_product)
            base_price = product.supplier_price

            for i in range(num_events):
                # Random time in the past N days
                days_ago = random.uniform(0, days)
                timestamp = now - timedelta(days=days_ago)

                # Price fluctuation: -15% to +15%
                change_pct = random.uniform(-0.15, 0.15)
                old_price = base_price * Decimal(str(1 - change_pct))
                new_price = base_price

                # Stock fluctuation
                old_stock = random.randint(0, 100)
                new_stock = random.randint(0, 100)

                if dry_run:
                    self.stdout.write(
                        f"  {product.name[:40]}: {old_price:.2f} -> {new_price:.2f} "
                        f"(stock: {old_stock} -> {new_stock})"
                    )
                else:
                    PriceHistory.objects.create(
                        product=product,
                        owner=owner,
                        old_price=old_price.quantize(Decimal("0.01")),
                        new_price=new_price.quantize(Decimal("0.01")),
                        old_stock=old_stock,
                        new_stock=new_stock,
                        price_changed=True,
                        stock_changed=(old_stock != new_stock),
                        source="seed",
                        reason="scrape",
                        created_at=timestamp,
                    )
                    created_count += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f"[DRY RUN] Would create {len(products) * events_per_product} records"))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Created {created_count} PriceHistory records")
            )
