from django.conf import settings
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import Parameter


@receiver(post_migrate)
def create_default_parameters(sender, **kwargs):
    """Create default parameters after migrations are applied."""
    if sender.name == "params":
        from store.settings import FURNITURE_PARAM_LABELS

        for key, label in FURNITURE_PARAM_LABELS.items():
            Parameter.objects.get_or_create(key=key, defaults={"label": label})
