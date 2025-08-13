from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path
from django.contrib import messages
from django.utils.html import format_html
from django.utils import timezone

from .models import GoogleSheetConfig, PriceUpdateLog, FurniturePriceCellMapping
from .services import GoogleSheetsPriceUpdater


@admin.register(GoogleSheetConfig)
class GoogleSheetConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'sheet_id', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'sheet_id']
    readonly_fields = ['sheet_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('name', 'is_active')
        }),
        ('Google Таблиці', {
            'fields': ('sheet_url', 'sheet_id', 'sheet_name', 'sheet_gid'),
            'description': 'Налаштування для Google таблиць'
        }),
        ('XLSX Файли', {
            'fields': ('xlsx_file',),
            'description': 'Альтернатива Google таблицям - завантажте XLSX файл'
        }),
        ('Налаштування цін', {
            'fields': ('price_multiplier',),
            'description': 'Налаштування конвертації валют'
        }),
        ('Системна інформація', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:config_id>/update-prices/',
                self.admin_site.admin_view(self.update_prices_view),
                name='price_parser_googlesheetconfig_update_prices',
            ),
            path(
                '<int:config_id>/test-parse/',
                self.admin_site.admin_view(self.test_parse_view),
                name='price_parser_googlesheetconfig_test_parse',
            ),
        ]
        return custom_urls + urls
    
    def update_prices_view(self, request, config_id):
        """View to trigger price update from admin."""
        try:
            config = GoogleSheetConfig.objects.get(id=config_id)
            updater = GoogleSheetsPriceUpdater(config)
            result = updater.update_prices()
            
            if result['success']:
                messages.success(
                    request, 
                    f"Оновлено {result['updated_count']} товарів з {result['processed_count']} оброблених"
                )
            else:
                messages.error(
                    request, 
                    f"Помилка оновлення: {result['error']}"
                )
                
        except GoogleSheetConfig.DoesNotExist:
            messages.error(request, "Конфігурація не знайдена")
        except Exception as e:
            messages.error(request, f"Помилка: {str(e)}")
        
        return HttpResponseRedirect("../")
    
    def test_parse_view(self, request, config_id):
        """View to test parsing without updating prices."""
        try:
            config = GoogleSheetConfig.objects.get(id=config_id)
            updater = GoogleSheetsPriceUpdater(config)
            result = updater.test_parse()
            
            if result['success']:
                messages.success(
                    request, 
                    f"Тестовий парсинг успішний. Знайдено {len(result['data'])} рядків"
                )
            else:
                messages.error(
                    request, 
                    f"Помилка тестового парсингу: {result['error']}"
                )
                
        except GoogleSheetConfig.DoesNotExist:
            messages.error(request, "Конфігурація не знайдена")
        except Exception as e:
            messages.error(request, f"Помилка: {str(e)}")
        
        return HttpResponseRedirect("../")
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        actions['update_prices'] = (update_prices_action, 'update_prices', "Оновити ціни для вибраних конфігурацій")
        actions['test_parse'] = (test_parse_action, 'test_parse', "Тестувати парсинг для вибраних конфігурацій")
        return actions


def update_prices_action(modeladmin, request, queryset):
    """Admin action to update prices for selected configs."""
    updated_count = 0
    for config in queryset:
        try:
            updater = GoogleSheetsPriceUpdater(config)
            result = updater.update_prices()
            if result['success']:
                updated_count += 1
        except Exception as e:
            modeladmin.message_user(
                request, 
                f"Помилка оновлення {config.name}: {str(e)}", 
                messages.ERROR
            )
    
    modeladmin.message_user(
        request, 
        f"Успішно оновлено {updated_count} конфігурацій"
    )


def test_parse_action(modeladmin, request, queryset):
    """Admin action to test parse for selected configs."""
    tested_count = 0
    for config in queryset:
        try:
            updater = GoogleSheetsPriceUpdater(config)
            result = updater.test_parse()
            if result['success']:
                tested_count += 1
        except Exception as e:
            modeladmin.message_user(
                request, 
                f"Помилка тестування {config.name}: {str(e)}", 
                messages.ERROR
            )
    
    modeladmin.message_user(
        request, 
        f"Успішно протестовано {tested_count} конфігурацій"
    )


@admin.register(PriceUpdateLog)
class PriceUpdateLogAdmin(admin.ModelAdmin):
    list_display = [
        'config', 'status', 'started_at', 'completed_at', 
        'items_processed', 'items_updated', 'duration'
    ]
    list_filter = ['status', 'started_at', 'config']
    readonly_fields = [
        'config', 'status', 'started_at', 'completed_at',
        'items_processed', 'items_updated', 'errors', 'log_details'
    ]
    search_fields = ['config__name']
    
    def duration(self, obj):
        """Calculate duration of the update process."""
        if obj.completed_at:
            duration = obj.completed_at - obj.started_at
            return f"{duration.total_seconds():.1f} сек"
        return "В процесі"
    duration.short_description = "Тривалість"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False





@admin.register(FurniturePriceCellMapping)
class FurniturePriceCellMappingAdmin(admin.ModelAdmin):
    list_display = ['furniture', 'config', 'cell_reference', 'price_type', 'is_active']
    list_filter = ['is_active', 'config', 'price_type', 'created_at']
    search_fields = ['furniture__name', 'price_type']
    autocomplete_fields = ['furniture', 'size_variant']
    readonly_fields = ['cell_reference', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Основна інформація', {
            'fields': ('furniture', 'config', 'price_type', 'is_active')
        }),
        ('Позиція в таблиці', {
            'fields': ('sheet_row', 'sheet_column', 'cell_reference'),
            'description': 'Вкажіть точну позицію комірки з ціною в Google таблиці'
        }),
        ('Розмірний варіант', {
            'fields': ('size_variant',),
            'description': 'Виберіть розмірний варіант, якщо ціна залежить від розміру'
        }),
        ('Системна інформація', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('furniture', 'config', 'size_variant') 