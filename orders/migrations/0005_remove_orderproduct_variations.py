# Generated by Django 5.1.4 on 2025-03-27 11:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_remove_orderproduct_payment_remove_order_payment_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='orderproduct',
            name='variations',
        ),
    ]
