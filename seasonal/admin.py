from django.contrib import admin

from .models import SeasonalCampaign


@admin.register(SeasonalCampaign)
class SeasonalCampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "enabled", "starts_at", "ends_at", "priority")
    search_fields = ("slug", "title")
    list_filter = ("enabled", "starts_at", "ends_at")
    ordering = ("-priority", "starts_at")
    readonly_fields = ("created_at", "updated_at")

