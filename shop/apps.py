from django.apps import AppConfig


class ShopConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shop"

    def ready(self):
        from .init_furniture import init_furniture_taxonomy
        try:
            init_furniture_taxonomy()
        except Exception as e:
            # Avoid crashing server on migration or missing tables
            print(f"[ShopConfig] Could not initialize furniture taxonomy: {e}")
