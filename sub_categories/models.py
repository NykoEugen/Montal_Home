from django.db import models

from categories.models import Category
from utils.image_variants import schedule_variant_generation_for_field


class SubCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="sub_categories"
    )
    image = models.ImageField(
        upload_to="categories/", max_length=255, null=True, blank=True, verbose_name="Зображення"
    )

    class Meta:
        db_table = "sub_categories"
        verbose_name = "Підкатегорії"
        verbose_name_plural = "Підкатегорії"

    def __str__(self) -> str:
        return self.name
    
    def has_furniture(self) -> bool:
        """Check if this subcategory has any furniture items."""
        return self.furniture.exists()
    
    def save(self, *args, **kwargs):
        old_image_name = None
        if self.pk:
            try:
                old_image_name = SubCategory.objects.filter(pk=self.pk).values_list("image", flat=True).first()
            except Exception:
                pass

        super().save(*args, **kwargs)

        new_image_name = self.image.name if self.image else None
        if new_image_name and new_image_name != old_image_name:
            schedule_variant_generation_for_field(
                self.image,
                force=True,
                assume_exists=False,
            )