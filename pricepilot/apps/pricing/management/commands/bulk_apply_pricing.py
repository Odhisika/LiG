"""Bulk-apply pricing rules or default markup to products.

Examples:
    # Set 30% default markup for all products without a rule
    python manage.py bulk_apply_pricing --default-markup 30

    # Assign a specific rule to all products in a category
    python manage.py bulk_apply_pricing --rule "Hardware Markup" --category "Laptops"

    # Assign a rule to all products from a specific supplier
    python manage.py bulk_apply_pricing --rule "Hardware Markup" --supplier "JRED"

    # Preview changes without writing
    python manage.py bulk_apply_pricing --default-markup 30 --dry-run

    # Also recompute selling prices and sync to LiG
    python manage.py bulk_apply_pricing --default-markup 30 --recalc --sync
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.products.models import Product


class Command(BaseCommand):
    help = "Bulk-apply pricing rules or default markup to products."

    def add_arguments(self, parser):
        parser.add_argument(
            "--default-markup",
            type=float,
            help="Set the owner's default markup %% (applied to all products without a rule or manual price).",
        )
        parser.add_argument(
            "--rule",
            type=str,
            help="Name of a PricingRule to assign to matching products.",
        )
        parser.add_argument(
            "--category",
            type=str,
            help="Assign rule to products in this category (exact match).",
        )
        parser.add_argument(
            "--supplier",
            type=str,
            help="Assign rule to products from this supplier (name contains).",
        )
        parser.add_argument(
            "--all-products",
            action="store_true",
            help="Apply rule to ALL products (no category/supplier filter).",
        )
        parser.add_argument(
            "--recalc",
            action="store_true",
            help="Recompute selling_price for products that get a new rule.",
        )
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Push updated prices to the LiG store afterwards.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        recalc = options["recalc"]
        sync = options["sync"]

        # Determine the owner (use the first user — single-merchant system)
        from apps.accounts.models import User

        owner = User.objects.first()
        if owner is None:
            self.stderr.write("No users found.")
            return

        # Step 1: Set default markup if requested
        if options["default_markup"] is not None:
            self._set_default_markup(owner, options["default_markup"], dry_run)

        # Step 2: Assign a pricing rule if requested
        if options["rule"]:
            self._assign_rule(owner, options, dry_run, recalc)

        # Step 3: Sync to LiG if requested
        if sync and not dry_run:
            self._sync_to_lig(owner)

    def _set_default_markup(self, owner, markup_pct, dry_run):
        from apps.pricing.models import DefaultMarkup
        from apps.pricing.services import DefaultMarkupService

        percent = Decimal(str(markup_pct))
        affected = Product.objects.filter(
            owner=owner, pricing_rule__isnull=True, selling_price__isnull=True
        ).count()

        if dry_run:
            self.stdout.write(
                f"[DRY RUN] Would set default markup to {percent}% "
                f"({affected} products affected)"
            )
            return

        markup, _ = DefaultMarkup.objects.update_or_create(
            owner=owner,
            defaults={"markup_percent": percent, "is_active": True},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Default markup set to {markup.markup_percent}% "
                f"({affected} products will use it at sync time)"
            )
        )

    def _assign_rule(self, owner, options, dry_run, recalc):
        from apps.pricing.models import PricingRule
        from apps.pricing.services import PricingService

        rule_name = options["rule"]
        rule = PricingRule.objects.filter(owner=owner, name=rule_name).first()
        if rule is None:
            self.stderr.write(f"Pricing rule '{rule_name}' not found.")
            return

        qs = Product.objects.filter(owner=owner)

        if options["category"]:
            qs = qs.filter(category=options["category"])
        elif options["supplier"]:
            from apps.suppliers.models import Supplier

            supplier = Supplier.objects.filter(
                owner=owner, name__icontains=options["supplier"]
            ).first()
            if supplier is None:
                self.stderr.write(f"Supplier '{options['supplier']}' not found.")
                return
            qs = qs.filter(supplier=supplier)
        elif not options["all_products"]:
            self.stderr.write(
                "Specify --category, --supplier, or --all-products to choose products."
            )
            return

        products = list(qs)
        count = len(products)
        if count == 0:
            self.stdout.write("No matching products found.")
            return

        if dry_run:
            self.stdout.write(
                f"[DRY RUN] Would assign rule '{rule.name}' to {count} products"
            )
            return

        updated = 0
        for product in products:
            product.pricing_rule = rule
            if recalc:
                product.selling_price = PricingService.compute_selling_price(
                    product.supplier_price, rule
                )
            product.save(update_fields=["pricing_rule"] + (["selling_price"] if recalc else []))
            updated += 1

        msg = f"Assigned rule '{rule.name}' to {updated} products."
        if recalc:
            msg += " selling_price recomputed."
        self.stdout.write(self.style.SUCCESS(msg))

    def _sync_to_lig(self, owner):
        from apps.sync.services import StoreSyncService

        self.stdout.write("Syncing to LiG store...")
        products = Product.objects.filter(owner=owner)
        result = StoreSyncService.sync_all(products)
        self.stdout.write(
            self.style.SUCCESS(
                f"Sync complete: updated={result.get('updated', 0)}, "
                f"noop={result.get('noop', 0)}"
            )
        )
