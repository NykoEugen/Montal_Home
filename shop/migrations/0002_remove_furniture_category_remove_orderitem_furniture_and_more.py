# Generated by Django 5.2 on 2025-07-10 06:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="furniture",
            name="category",
        ),
        migrations.RemoveField(
            model_name="orderitem",
            name="furniture",
        ),
        migrations.RemoveField(
            model_name="order",
            name="items",
        ),
        migrations.RemoveField(
            model_name="orderitem",
            name="order",
        ),
        migrations.DeleteModel(
            name="Category",
        ),
        migrations.DeleteModel(
            name="Furniture",
        ),
        migrations.DeleteModel(
            name="Order",
        ),
        migrations.DeleteModel(
            name="OrderItem",
        ),
    ]
