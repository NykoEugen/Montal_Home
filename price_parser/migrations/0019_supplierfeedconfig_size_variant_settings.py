from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("price_parser", "0018_supplierfeedconfig_article_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="supplierfeedconfig",
            name="update_size_variants",
            field=models.BooleanField(
                default=False,
                verbose_name="Оновлювати розміри товару",
                help_text=(
                    "Якщо увімкнено, парсер оновлює ціни окремих розмірів (FurnitureSizeVariant), "
                    "а не базову ціну товару. Потрібно вказати 'Назва XML-параметру розміру'."
                ),
            ),
        ),
        migrations.AddField(
            model_name="supplierfeedconfig",
            name="size_param_name",
            field=models.CharField(
                blank=True,
                default="",
                max_length=100,
                verbose_name="Назва XML-параметру розміру",
                help_text=(
                    "Атрибут name тегу <param>, який містить розмір у форматі 'ШхД' (напр. '70x190'). "
                    "Для матраців Matro: 'Розмір матрацу (ШхД)'."
                ),
            ),
        ),
    ]
