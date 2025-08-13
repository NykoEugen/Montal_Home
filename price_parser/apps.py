from django.apps import AppConfig


class PriceParserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'price_parser'
    verbose_name = 'Парсер цін' 