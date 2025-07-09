from django.apps import AppConfig
from django.db.models.signals import post_migrate


class ParamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "params"

    def ready(self):
        # Import signals to register them
        from . import signals
