# Generated by Django 5.1.4 on 2025-03-27 13:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('category', '0003_researchtypes'),
        ('research', '0006_alter_blogmodel_research_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blogmodel',
            name='research_type',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='category.researchtypes'),
            preserve_default=False,
        ),
    ]
