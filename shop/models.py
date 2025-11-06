
from django.db import models


class SeasonalSettings(models.Model):
    """Singleton-style configuration for seasonal decoration toggles."""

    name = models.CharField(
        max_length=120,
        default="Зимовий пак",
        verbose_name="Назва сезонного паку",
        help_text="Назва поточного набору святкових елементів.",
    )
    is_enabled = models.BooleanField(
        default=True,
        verbose_name="Увімкнути святкове оформлення",
        help_text="Якщо вимкнено, гірлянда та сніг на сайті не відображатимуться.",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Оновлено")

    class Meta:
        verbose_name = "Сезонне оформлення"
        verbose_name_plural = "Сезонне оформлення"

    def __str__(self) -> str:
        status = "увімкнено" if self.is_enabled else "вимкнено"
        return f"{self.name} ({status})"

    @classmethod
    def get_solo(cls) -> "SeasonalSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
