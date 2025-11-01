from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    image = models.ImageField(
        upload_to="categories/", max_length=255, null=True, blank=True, verbose_name="Зображення"
    )

    class Meta:
        db_table = "categories"
        verbose_name = "Категорія"
        verbose_name_plural = "Категорії"

    def __str__(self) -> str:
        return self.name
