from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from .models import GoogleSheetConfig, PriceUpdateLog, FurniturePriceCellMapping
from .services import GoogleSheetsPriceUpdater


@login_required
def config_list(request):
    """List all Google Sheet configurations."""
    configs = GoogleSheetConfig.objects.all().order_by('-created_at')
    return render(request, 'price_parser/config_list.html', {
        'configs': configs
    })


@login_required
def config_detail(request, config_id):
    """Show details of a specific configuration."""
    config = get_object_or_404(GoogleSheetConfig, id=config_id)
    recent_logs = PriceUpdateLog.objects.filter(config=config).order_by('-started_at')[:10]
    mapping_qs = FurniturePriceCellMapping.objects.filter(config=config)
    mapping_stats = {
        "total": mapping_qs.count(),
        "active": mapping_qs.filter(is_active=True).count(),
        "with_variants": mapping_qs.filter(size_variant__isnull=False).count(),
    }
    last_log = recent_logs[0] if recent_logs else None
    source_label = "XLSX файл" if config.xlsx_file else "Google Sheets"
    
    return render(request, 'price_parser/config_detail.html', {
        'config': config,
        'recent_logs': recent_logs,
        'mapping_stats': mapping_stats,
        'last_log': last_log,
        'source_label': source_label,
    })


@login_required
@require_POST
def update_prices(request, config_id):
    """Trigger price update for a specific configuration."""
    config = get_object_or_404(GoogleSheetConfig, id=config_id)
    
    try:
        updater = GoogleSheetsPriceUpdater(config)
        result = updater.update_prices()
        
        if result['success']:
            messages.success(
                request,
                f"Оновлено {result['updated_count']} товарів з {result['processed_count']} оброблених"
            )
        else:
            messages.error(request, f"Помилка оновлення: {result['error']}")
            
    except Exception as e:
        messages.error(request, f"Помилка: {str(e)}")
    
    return redirect('price_parser:config_detail', config_id=config_id)


@login_required
@require_POST
def test_parse(request, config_id):
    """Test parsing without updating prices."""
    config = get_object_or_404(GoogleSheetConfig, id=config_id)
    
    try:
        updater = GoogleSheetsPriceUpdater(config)
        result = updater.test_parse()
        
        if result['success']:
            messages.success(
                request,
                f"Тестовий парсинг успішний. Знайдено {result['count']} рядків"
            )
        else:
            messages.error(request, f"Помилка тестового парсингу: {result['error']}")
            
    except Exception as e:
        messages.error(request, f"Помилка: {str(e)}")
    
    return redirect('price_parser:config_detail', config_id=config_id)


@login_required
def log_list(request):
    """List all price update logs."""
    logs = PriceUpdateLog.objects.select_related('config').order_by('-started_at')
    return render(request, 'price_parser/log_list.html', {
        'logs': logs
    }) 
