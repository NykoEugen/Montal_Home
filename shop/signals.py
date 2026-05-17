from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

from categories.models import Category
from furniture.models import Furniture
from shop.models import SeasonalSettings
from sub_categories.models import SubCategory


def _delete_pattern(pattern: str) -> None:
    """Delete cache keys matching pattern. Falls back silently for LocMem."""
    try:
        cache.delete_pattern(pattern)
    except AttributeError:
        pass


@receiver(post_save, sender=Category)
def invalidate_category_cache(sender, **kwargs):
    cache.delete("categories:with_furniture")
    _delete_pattern("breadcrumbs::*")


@receiver(post_save, sender=SubCategory)
def invalidate_subcategory_cache(sender, **kwargs):
    _delete_pattern("breadcrumbs::*")


@receiver(post_save, sender=Furniture)
def invalidate_furniture_cache(sender, **kwargs):
    cache.delete("promotional_furniture_ids")
    cache.delete("categories:with_furniture")
    _delete_pattern("breadcrumbs::*")
    _delete_pattern("search_suggestions::*")


@receiver(post_save, sender=SeasonalSettings)
def invalidate_seasonal_cache(sender, **kwargs):
    cache.delete("seasonal_pack_settings")
