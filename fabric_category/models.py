from django.db import models

class FabricBrand(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class FabricCategory(models.Model):
    brand = models.ForeignKey(FabricBrand, on_delete=models.CASCADE, related_name="quality_categories")
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('brand', 'name')
        verbose_name = "Fabric Category"
        verbose_name_plural = "Fabric Categories"

    def __str__(self):
        return f"{self.brand.name} - {self.name} ({self.price} грн)"
