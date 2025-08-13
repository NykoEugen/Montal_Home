from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import GoogleSheetConfig, PriceUpdateLog
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
    
    return render(request, 'price_parser/config_detail.html', {
        'config': config,
        'recent_logs': recent_logs
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