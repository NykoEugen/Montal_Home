from django.apps import AppConfig


class FurnitureConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "furniture"
    
    def ready(self):
        """Import signals when the app is ready."""
        import furniture.signals
