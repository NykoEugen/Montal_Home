from django.contrib import admin

from .models import FabricBrand, FabricCategory, FabricColor, FabricColorPalette


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


class FabricColorInline(admin.TabularInline):
    model = FabricColor
    extra = 1
    fields = ("name", "hex_code", "position", "is_active", "image")


@admin.register(FabricColorPalette)
class FabricColorPaletteAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "is_active", "updated_at")
    list_filter = ("brand", "is_active")
    search_fields = ("name", "brand__name")
    inlines = [FabricColorInline]


@admin.register(FabricColor)
class FabricColorAdmin(admin.ModelAdmin):
    list_display = ("name", "palette", "hex_code", "position", "is_active", "image")
    list_filter = ("palette", "is_active")
    search_fields = ("name", "palette__name")
