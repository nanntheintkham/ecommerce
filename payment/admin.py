from django.contrib import admin
from .models import ShippingAddress, Order, OrderItem
from django.contrib.auth.models import User

admin.site.register(ShippingAddress)
admin.site.register(Order)
admin.site.register(OrderItem)

# Order Item inline
class OrderItemInline(admin.StackedInline):
    model = OrderItem
    extra = 0

# Order Admin
class OrderAdmin(admin.ModelAdmin):
    model = Order
    readonly_fields = ["date_ordered"]
    fields = ["user", "full_name", "email", "shipping_address", "amount_paid", "date_ordered", "shipped", "date_shipped", "invoice", "paid"]
    inlines = [OrderItemInline]

# unregister order
admin.site.unregister(Order)

# register order with inlines
admin.site.register(Order, OrderAdmin)