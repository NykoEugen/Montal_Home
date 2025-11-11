from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("checkout", "0014_order_iban_invoice_requested"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="iban_invoice_generated",
            field=models.BooleanField(default=False, verbose_name="Рахунок IBAN згенеровано"),
        ),
    ]
