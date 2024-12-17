from django.contrib import admin
from .models import Category, Customer, Product, Order, Profile, UserDigitalPurchase
from django.contrib.auth.models import User

admin.site.register(Category)
admin.site.register(Customer)
admin.site.register(UserDigitalPurchase)
admin.site.register(Order)
admin.site.register(Profile)


# Mix profile info and user info
class ProfileInline(admin.StackedInline):
	model = Profile

# Extend User Model
class UserAdmin(admin.ModelAdmin):
	model = User
	field = ["username", "first_name", "last_name", "email"]
	inlines = [ProfileInline]

# Unregister the old way
admin.site.unregister(User)

# Re-Register the new way
admin.site.register(User, UserAdmin)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Admin interface for managing both physical and digital products.
    """
    list_display = ('name', 'price', 'product_type', 'category', 'created_at', 'updated_at')
    list_filter = ('product_type', 'category', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'price', 'product_type', 'category', 'is_sale', 'sale_price', 'image')
        }),
        ('Digital Product Fields', {
            'fields': ('s3_object_key',),
            'classes': ('collapse',),  # Makes it collapsible
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_fieldsets(self, request, obj=None):
        """
        Dynamically show/hide fields based on product_type.
        """
        fieldsets = super().get_fieldsets(request, obj)
        if obj and obj.product_type == 'physical':
            # Remove Digital Product fields if it's a physical product
            fieldsets = [fs for fs in fieldsets if 'Digital Product Fields' not in fs[0]]
        elif obj and obj.product_type == 'digital':
            # Remove Physical Product fields if it's a digital product
            fieldsets = [fs for fs in fieldsets if 'Physical Product Fields' not in fs[0]]
        return fieldsets

    def save_model(self, request, obj, form, change):
        """
        Custom save logic to ensure correct data for each product type.
        """
        if obj.product_type == 'digital':
            obj.stock = None
            obj.weight = None
            obj.dimensions = None
        elif obj.product_type == 'physical':
            obj.s3_object_key = None
            obj.thumbnail = None
        super().save_model(request, obj, form, change)