from django.core.cache import cache

from categories.models import Category

CATEGORIES_WITH_FURNITURE_CACHE_KEY = "categories:with_furniture"
CATEGORIES_CACHE_TIMEOUT = 300


def get_cached_categories_with_furniture():
    """
    Return categories that have at least one furniture item via subcategories.
    Cached for a short period to avoid repeated expensive joins.
    """
    categories = cache.get(CATEGORIES_WITH_FURNITURE_CACHE_KEY)
    if categories is not None:
        return categories

    categories = list(
        Category.objects.filter(sub_categories__furniture__isnull=False)
        .distinct()
        .order_by("name")
    )
    cache.set(CATEGORIES_WITH_FURNITURE_CACHE_KEY, categories, CATEGORIES_CACHE_TIMEOUT)
    return categories
