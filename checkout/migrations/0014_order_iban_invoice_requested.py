from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("checkout", "0013_liqpayreceipt"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="iban_invoice_requested",
            field=models.BooleanField(
                default=False,
                help_text="Увімкніть, якщо клієнту потрібно згенерувати рахунок на оплату через IBAN.",
                verbose_name="Потрібен рахунок IBAN",
            ),
        ),
    ]
