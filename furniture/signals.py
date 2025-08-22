from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.core.management import call_command
from django.conf import settings


@receiver(post_migrate)
def cleanup_expired_promotions_on_startup(sender, **kwargs):
    """
    Clean up expired promotions when the server starts.
    This ensures that promotional status is removed from expired items.
    """
    # Only run in production or when explicitly enabled
    if not settings.DEBUG or getattr(settings, 'CLEANUP_PROMOTIONS_ON_STARTUP', False):
        try:
            call_command('cleanup_all_expired_promotions', verbosity=0)
        except Exception as e:
            # Log the error but don't prevent server startup
            print(f"Warning: Failed to cleanup expired promotions on startup: {e}")
