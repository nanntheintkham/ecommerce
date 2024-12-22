# payment/urls.py

from django.urls import path, include
from . import views

urlpatterns = [
    path('payment_success/', views.payment_success, name='payment_success'),
    path('payment_failed/', views.payment_failed, name='payment_failed'),
    path('checkout/', views.checkout, name='checkout'),
    path('products/<int:pk>/purchase/', views.purchase_digital_product, name='purchase_digital_product'),
    path('billing_info/', views.billing_info, name='billing_info'),
    path('order_dashboard/', views.order_dashboard, name='order_dashboard'),
    path('processing_dash/', views.processing_dash, name='processing_dash'),
    path('orders/<int:pk>', views.orders, name='orders'),
    path('order/update_order_status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('paypal/', include("paypal.standard.ipn.urls")),
    # Stripe endpoints
    path('create-checkout-session/', views.create_stripe_session, name='create_checkout_session'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('order/<int:order_id>/', views.order_details, name='order_details'),


]