from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from categories.models import Category
from furniture.models import Furniture
from sub_categories.models import SubCategory


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return [
            "shop:home",
            "shop:promotions",
            "shop:where_to_buy",
            "shop:contacts",
            "shop:warranty",
            "shop:delivery_payment",
            "shop:offer",
            "shop:view_cart",
            "categories:categories_list",
            "sub_categories:sub_categories_list",
        ]

    def location(self, item):
        return reverse(item)


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Category.objects.all()

    def location(self, obj: Category):
        return reverse("categories:category_detail", kwargs={"category_slug": obj.slug})


class SubCategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return SubCategory.objects.filter(furniture__isnull=False).distinct()

    def location(self, obj: SubCategory):
        return reverse(
            "sub_categories:sub_categories_details",
            kwargs={"sub_categories_slug": obj.slug},
        )


class FurnitureSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Furniture.objects.all()

    def lastmod(self, obj: Furniture):
        return obj.updated_at

    def location(self, obj: Furniture):
        return reverse(
            "furniture:furniture_detail",
            kwargs={"furniture_slug": obj.slug},
        )


SITEMAPS = {
    "static": StaticViewSitemap,
    "categories": CategorySitemap,
    "sub_categories": SubCategorySitemap,
    "furniture": FurnitureSitemap,
}
