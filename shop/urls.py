from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('furniture/<str:furniture_slug>/', views.furniture_detail, name='furniture_detail'),
    path('add-to-cart/<int:furniture_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:furniture_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-history/', views.order_history, name='order_history'),
]
