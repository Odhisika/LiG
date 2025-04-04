# Generated by Django 5.1.4 on 2025-03-18 09:42

import orders.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_alter_order_payment_method'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='orderproduct',
            name='payment',
        ),
        migrations.RemoveField(
            model_name='order',
            name='payment',
        ),
        migrations.RemoveField(
            model_name='order',
            name='payment_method',
        ),
        migrations.AddField(
            model_name='order',
            name='expires_at',
            field=models.DateTimeField(default=orders.models.Order.default_expiry),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('New', 'New'), ('Pending Payment', 'Pending Payment'), ('Expired', 'Expired'), ('Accepted', 'Accepted'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')], default='Pending Payment', max_length=20),
        ),
        migrations.DeleteModel(
            name='Payment',
        ),
    ]
