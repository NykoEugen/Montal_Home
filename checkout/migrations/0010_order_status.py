from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("checkout", "0009_alter_order_invoice_pdf_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "Нове"),
                    ("processing", "В обробці"),
                    ("shipped", "Відправлено"),
                    ("completed", "Завершено"),
                    ("canceled", "Скасовано"),
                ],
                default="new",
                max_length=20,
                verbose_name="Статус замовлення",
            ),
        ),
    ]
