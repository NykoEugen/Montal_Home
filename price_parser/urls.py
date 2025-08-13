from django.urls import path
from . import views

app_name = 'price_parser'

urlpatterns = [
    path('', views.config_list, name='config_list'),
    path('<int:config_id>/', views.config_detail, name='config_detail'),
    path('<int:config_id>/update/', views.update_prices, name='update_prices'),
    path('<int:config_id>/test/', views.test_parse, name='test_parse'),
    path('logs/', views.log_list, name='log_list'),
] 