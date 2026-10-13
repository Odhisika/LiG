# Generated for the storefront publishing toggles (apps.sync).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0005_product_store_sync_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="publish_to_store",
            field=models.BooleanField(
                default=True,
                help_text="When off, the product is hidden from the storefront on the "
                "next sync and is never seeded there. The single authoritative "
                "'show on our site' switch.",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="use_supplier_images",
            field=models.BooleanField(
                default=True,
                help_text="When off, the supplier's product images are not copied to "
                "the storefront. Use when the supplier's logo/branding is baked into "
                "their photos — the store then falls back to its own/placeholder image.",
            ),
        ),
    ]
