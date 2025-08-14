from django.urls import path, include
from .views import home, add_to_cart, remove_from_cart, checkout, place_order, order_success, products

urlpatterns = [
    path('', home , name='home'),
    path('products/', products, name='products'),
    path('add/', add_to_cart, name='add_to_cart'),
    path('remove/', remove_from_cart, name='remove_from_cart'),
    path('products/checkout/', checkout, name='checkout'),
    path('place-order/', place_order, name='place_order'),
    path('order-success/<int:order_number>/', order_success, name='order_success'),
]
