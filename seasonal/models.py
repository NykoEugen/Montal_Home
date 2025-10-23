from __future__ import annotations

from datetime import datetime
from typing import Optional

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from .ab import bucket_user
from .matchers import match_country, match_device, match_path

class SeasonalCampaign(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    enabled = models.BooleanField(default=False)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    priority = models.IntegerField(default=0)
    pack_path = models.CharField(max_length=255)
    path_glob = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=2, blank=True, null=True)
    device = models.CharField(max_length=10, blank=True, null=True)
    percentage_rollout = models.IntegerField(
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-priority", "-starts_at", "slug")

    def __str__(self) -> str:
        return f"{self.title} ({self.slug})"

    def clean(self) -> None:
        if self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "End date must be after start date."})

    def is_active(self, *, at: Optional[datetime] = None) -> bool:
        moment = at or timezone.now()
        return self.enabled and self.starts_at <= moment <= self.ends_at

    def matches_request(self, request) -> bool:  # pragma: no cover - exercised via context processor
        if request is None:
            return False

        if self.path_glob and not match_path(request, self.path_glob):
            return False

        if self.country and not match_country(request, self.country):
            return False

        if self.device and not match_device(request, self.device):
            return False

        if self.percentage_rollout >= 100:
            return True

        bucket = bucket_user(request, salt=self.slug)
        return bucket < self.percentage_rollout
