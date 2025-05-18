from django.db import models

from categories.models import Category


class SubCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="sub_categories"
    )
    image = models.ImageField(
        upload_to="categories/", null=True, blank=True, verbose_name="Зображення"
    )

    class Meta:
        db_table = "sub_categories"
        verbose_name = "Підкатегорії"
        verbose_name_plural = "Підкатегорії"

    def __str__(self) -> str:
        return self.name
