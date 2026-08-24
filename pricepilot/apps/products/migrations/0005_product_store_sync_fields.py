# Generated manually for the Store Sync feature (apps.sync).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0004_alter_product_supplier_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="store_product_id",
            field=models.BigIntegerField(
                blank=True,
                null=True,
                help_text="Row id of the corresponding product in the merchant store "
                "(apps.sync / LiG store_product).",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="store_synced_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="Last time values were synced to the merchant store.",
            ),
        ),
    ]
