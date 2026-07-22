from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("furniture", "0032_furniture_fabric_step_raw_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="furniture",
            name="fabric_value",
            field=models.DecimalField(
                decimal_places=2,
                default=1.0,
                help_text="Множник для розрахунку вартості тканини",
                max_digits=10,
                validators=[MinValueValidator(0)],
                verbose_name="Коефіцієнт тканини",
            ),
        ),
    ]
