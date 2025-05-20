from django.db import models


class Parameter(models.Model):
    key = models.CharField(max_length=100, unique=True)  # Наприклад, "width", "height"
    label = models.CharField(max_length=200)  # Наприклад, "Ширина (см)", "Висота (см)"

    class Meta:
        db_table = "parameters"
        verbose_name = "Параметр"
        verbose_name_plural = "Параметри"

    def __str__(self):
        return self.label


class FurnitureParameter(models.Model):
    furniture = models.ForeignKey(
        'furniture.Furniture', on_delete=models.CASCADE, related_name="parameters"
    )
    parameter = models.ForeignKey(
        Parameter, on_delete=models.CASCADE, related_name="furniture_parameters"
    )
    value = models.CharField(max_length=200)  # Значення параметра, наприклад "120" або "blue"

    class Meta:
        db_table = "furniture_parameters"
        verbose_name = "Параметр меблів"
        verbose_name_plural = "Параметри меблів"
        unique_together = ('furniture', 'parameter')  # Один параметр на меблі

    def __str__(self):
        return f"{self.furniture.name}: {self.parameter.label} = {self.value}"