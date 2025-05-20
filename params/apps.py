from django.apps import AppConfig


class ParamConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "params"

    def ready(self):
        from params.models import Parameter
        from store.settings import FURNITURE_PARAM_LABELS

        params = FURNITURE_PARAM_LABELS
        for key, label in params.items():
            Parameter.objects.get_or_create(key=key, defaults={'label': label})