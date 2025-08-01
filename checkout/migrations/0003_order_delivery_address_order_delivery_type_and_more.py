# Generated by Django 5.2 on 2025-07-10 07:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("checkout", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="delivery_address",
            field=models.TextField(blank=True, verbose_name="Адреса доставки"),
        ),
        migrations.AddField(
            model_name="order",
            name="delivery_type",
            field=models.CharField(
                choices=[("local", "Локальна доставка"), ("nova_poshta", "Нова Пошта")],
                default=1,
                max_length=20,
                verbose_name="Тип доставки",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="payment_type",
            field=models.CharField(
                choices=[("iban", "IBAN"), ("liqupay", "LiquPay")],
                default=1,
                max_length=20,
                verbose_name="Тип оплати",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="order",
            name="delivery_branch",
            field=models.CharField(
                blank=True, max_length=200, verbose_name="Відділення Нової Пошти"
            ),
        ),
    ]
