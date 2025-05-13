from django.urls import path

from . import views

app_name: str = 'shop'

urlpatterns = [
    path('', views.home, name='home'),
    path('catalog/', views.catalog, name='catalog'),
    path('category/<str:category_slug>/', views.category_detail, name='category_detail'),
    path('promotions/', views.promotions, name='promotions'),
    path('where-to-buy/', views.where_to_buy, name='where_to_buy'),
    path('contacts/', views.contacts, name='contacts'),
    path('furniture/<str:furniture_slug>/', views.furniture_detail, name='furniture_detail'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-history/', views.order_history, name='order_history'),
]
