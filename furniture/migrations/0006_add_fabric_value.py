# Generated by Django 5.2 on 2025-07-27 07:36

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("furniture", "0005_add_selected_fabric_brand"),
    ]

    operations = [
        migrations.AddField(
            model_name="furniture",
            name="fabric_value",
            field=models.DecimalField(
                decimal_places=2,
                default=1.0,
                help_text="Множник для розрахунку вартості тканини",
                max_digits=5,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Коефіцієнт тканини",
            ),
        ),
    ]
