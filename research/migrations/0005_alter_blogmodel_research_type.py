# Generated by Django 5.1.4 on 2025-03-27 13:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('category', '0003_researchtypes'),
        ('research', '0004_remove_blogmodel_category_blogmodel_research_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blogmodel',
            name='research_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='category.researchtypes'),
        ),
    ]
