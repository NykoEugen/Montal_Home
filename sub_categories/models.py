from django.db import models

from categories.models import Category
from params.models import Parameter


class SubCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="sub_categories"
    )
    allowed_params = models.ManyToManyField(
        Parameter, blank=True, related_name="sub_categories", verbose_name="Дозволені параметри"
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
