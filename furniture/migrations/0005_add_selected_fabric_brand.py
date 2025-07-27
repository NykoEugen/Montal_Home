# Generated manually to add selected_fabric_brand field

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("furniture", "0004_alter_furniture_created_at"),
        ("fabric_category", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="furniture",
            name="selected_fabric_brand",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="furnitures",
                to="fabric_category.fabricbrand",
                verbose_name="Обраний бренд тканини",
            ),
        ),
    ]
