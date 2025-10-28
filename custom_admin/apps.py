from django.apps import AppConfig


class CustomAdminConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "custom_admin"
    verbose_name = "Custom Admin"

    def ready(self) -> None:
        # Import default registry configuration.
        from . import config  # noqa: F401
