from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("furniture", "0018_furnituresizevariant_parameter_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="furniturevariantimage",
            name="name",
            field=models.CharField(
                help_text="Назва варіанту (наприклад: 'Білий', 'Дуб світлий')",
                max_length=255,
                verbose_name="Назва варіанту",
            ),
        ),
    ]
