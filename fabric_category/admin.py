from django.contrib import admin
from .models import FabricBrand, FabricCategory

class FabricCategoryInline(admin.TabularInline):
    model = FabricCategory
    extra = 1

@admin.register(FabricBrand)
class FabricBrandAdmin(admin.ModelAdmin):
    list_display = ("name",)
    inlines = [FabricCategoryInline]

@admin.register(FabricCategory)
class FabricCategoryAdmin(admin.ModelAdmin):
    list_display = ("brand", "name", "price")
    list_filter = ("brand",)
    search_fields = ("brand__name", "name") 