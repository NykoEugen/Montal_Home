from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("price_parser", "0017_supplierwebconfig_price_block_selector"),
    ]

    operations = [
        migrations.AddField(
            model_name="supplierfeedconfig",
            name="article_tag_name",
            field=models.CharField(
                default="model",
                max_length=50,
                verbose_name="XML тег артикулу",
                help_text=(
                    "Назва XML-тегу, з якого читати артикул товару. "
                    "Для більшості фідів: 'model'. Для Vetro: 'article'."
                ),
            ),
        ),
        migrations.AddField(
            model_name="supplierfeedconfig",
            name="article_prefix_parts",
            field=models.PositiveIntegerField(
                default=0,
                verbose_name="Кількість частин артикулу (prefix)",
                help_text=(
                    "Кількість частин артикулу через '-' для зіставлення з базовим кодом товару. "
                    "0 = використовувати повний артикул. "
                    "Наприклад: для 'S-120-cappuccino-velvet' з значенням 2 отримаємо 'S-120'."
                ),
            ),
        ),
    ]
