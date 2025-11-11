from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("checkout", "0012_alter_order_payment_type_alter_order_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="LiqPayReceipt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("payment_id", models.CharField(blank=True, max_length=64)),
                ("status", models.CharField(blank=True, max_length=32)),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("currency", models.CharField(default="UAH", max_length=8)),
                ("receipt_url", models.URLField(blank=True)),
                ("items_snapshot", models.JSONField(blank=True, default=list)),
                ("raw_response", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="liqpay_receipt",
                        to="checkout.order",
                        verbose_name="Замовлення",
                    ),
                ),
            ],
            options={
                "verbose_name": "Чек LiqPay",
                "verbose_name_plural": "Чеки LiqPay",
            },
        ),
    ]
