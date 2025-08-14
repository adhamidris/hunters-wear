# store/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Q
from .models import Products, Order, OrderItem, ProductSize
from django.utils.text import Truncator
from django.utils.html import format_html
from django.db.models import F



# ---------- Product Size Inline ----------
class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 3  # Shows 3 empty forms by default
    max_num = 6  # Maximum 6 sizes (XS, S, M, L, XL, XXL)
    fields = ['size', 'stock_count']
    verbose_name = "Size & Stock"
    verbose_name_plural = "Available Sizes & Stock"


# ---------- Products ----------
@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    list_display = ("name", "classification", "price", "compare_price", "best_seller", "get_total_stock", "get_available_sizes")
    list_filter = ("classification", "best_seller")
    search_fields = ("name",)
    list_editable = ("price", "best_seller")
    ordering = ("-best_seller", "classification", "name")
    inlines = [ProductSizeInline]  # ADD: This shows sizes when editing products
    
    # ADD: Helper methods for displaying size info
    def get_total_stock(self, obj):
        total = sum([ps.stock_count for ps in obj.productsizes.all()])
        return total if total > 0 else "No stock"
    get_total_stock.short_description = 'Total Stock'
    
    def get_available_sizes(self, obj):
        sizes = [ps.size for ps in obj.productsizes.filter(stock_count__gt=0)]
        return ', '.join(sizes) if sizes else 'No sizes'
    get_available_sizes.short_description = 'Available Sizes'

# ---------- Inline: Order items ----------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ("product",)
    fields = ("product", "size", "quantity", "price", "line_total_display")  # ADD: size field
    readonly_fields = ("line_total_display",)

    def line_total_display(self, obj):
        # robust even if price is None
        qty = (getattr(obj, "quantity", 0) or 0)
        price = (getattr(obj, "price", 0) or 0)
        return f"EGP {qty * int(price)}"
    line_total_display.short_description = "Line total"




# ---------- Orders ----------
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # what you see in the changelist
    list_display = (
        "order_number",
        "first_name",
        "phone",
        "area",
        "address_short",
        "status",
        "status_badge",
        "items_count",
        "items_product",
        "total_amount_display",
        "created_at",
    )
    list_filter = ("status", "area", "created_at")
    search_fields = ("order_number", "first_name", "phone", "address")
    readonly_fields = ("order_number", "created_at", "updated_at")
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"
    list_per_page = 25
    ordering = ("-created_at",)
    list_display_links = ("order_number", "first_name")
    list_editable = ("status",)  # if you want inline status editing, set to ("status",)

    # bulk actions to move status
    actions = ["mark_pending", "mark_processing", "mark_shipped", "mark_delivered", "mark_cancelled"]

    def address_short(self, obj):
        addr = obj.address or ""
        return format_html('<span title="{}">{}</span>',
                        addr,
                        Truncator(addr).chars(60))  # show first ~60 chars
    address_short.short_description = "Address"
    address_short.admin_order_field = "address"  # enables sorting by the real field


    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        total = obj.items.aggregate(
            t=Sum(F("quantity") * F("price"))
        )["t"]
        # handle None + cast to int
        obj.total_amount = int(total or 0)
        obj.save(update_fields=["total_amount"])

    # nice status badge in list
    def status_badge(self, obj):
        colors = {
            "pending": "#f59e0b",      # gray-500
            "processing": "#0ea5e9",   # sky-500
            "shipped": "#6b7280",      # amber-500
            "delivered": "#10b981",    # emerald-500
            "cancelled": "#ef4444",    # red-500
        }
        color = colors.get(obj.status, "#111827")
        return format_html('<b style="color:{};">{}</b>', color, obj.get_status_display())
    status_badge.short_description = "Status"

    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = "Items"

    def items_product(self, obj):
        items = obj.items.all()
        if not items:
            return "No Products"
        
        item_list = []
        for item in items:
            size_text = f"({item.get_size_display()})" if item.size else ""
            item_list.append(f"{item.quantity}x {item.product.name[:10]}{size_text}")

        return format_html("<br>-------------<br>".join(item_list))
    
    items_product.short_description = "Products"
    items_product.allow_tags = True

    def total_amount_display(self, obj):
        return f"EGP {int(obj.total_amount or 0)}"
    total_amount_display.short_description = "Order total"

    # --- bulk actions ---
    @admin.action(description="Mark selected as Pending")
    def mark_pending(self, request, queryset):
        queryset.update(status="pending")

    @admin.action(description="Mark selected as Processing")
    def mark_processing(self, request, queryset):
        queryset.update(status="processing")

    @admin.action(description="Mark selected as Shipped")
    def mark_shipped(self, request, queryset):
        queryset.update(status="shipped")

    @admin.action(description="Mark selected as Delivered")
    def mark_delivered(self, request, queryset):
        queryset.update(status="delivered")

    @admin.action(description="Mark selected as Cancelled")
    def mark_cancelled(self, request, queryset):
        queryset.update(status="cancelled")


# ---------- Order Items (direct admin) ----------
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "size", "quantity", "price", "line_total_display")  # ADD: size
    list_filter = ("order__status", "product__classification", "size")  # ADD: size filter
    search_fields = ("order__order_number", "product__name")
    autocomplete_fields = ("product", "order")

    def line_total_display(self, obj):
        qty = obj.quantity or 0
        price = obj.price or 0
        return f"EGP {qty * int(price)}"
    line_total_display.short_description = "Line total"


# ---------- Product Sizes (direct admin) ----------
@admin.register(ProductSize)
class ProductSizeAdmin(admin.ModelAdmin):
    list_display = ('product', 'size', 'stock_count', 'is_in_stock')
    list_filter = ('size', 'product__classification')
    list_editable = ('stock_count',)
    search_fields = ('product__name',)
    ordering = ('product__name', 'size')
    
    def is_in_stock(self, obj):
        return obj.stock_count > 0
    is_in_stock.boolean = True
    is_in_stock.short_description = 'In Stock'

# ---------- Admin site labels ----------
admin.site.site_header = "Hunters Admin"
admin.site.site_title = "Hunters Admin"
admin.site.index_title = "Management"


# Add this at the end of your admin.py file

from django.contrib import messages
from django.contrib.admin import AdminSite
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

# Hook into admin requests to show stock alerts
original_admin_view = AdminSite.admin_view

def custom_admin_view(self, view, cacheable=False):
    def wrapper(request, *args, **kwargs):
        # Only show on main admin pages, not every single page
        if request.path in ['/admin/', '/admin/store/', '/admin/store/products/']:
            # Get detailed stock info
            out_of_stock_products = Products.objects.filter(
                Q(productsizes__isnull=True) | 
                ~Q(productsizes__stock_count__gt=0)
            ).distinct()
            
            low_stock_sizes = ProductSize.objects.filter(
                stock_count__lte=5, stock_count__gt=0
            ).select_related('product')
            
            zero_stock_sizes = ProductSize.objects.filter(
                stock_count=0
            ).select_related('product')
            
            # Create detailed messages with proper link colors
            if out_of_stock_products.exists():
                product_links = []
                for product in out_of_stock_products[:5]:  # Show first 5
                    change_url = reverse('admin:store_products_change', args=[product.pk])
                    product_links.append(f'<a href="{change_url}" style=" text-decoration: underline; font-weight: bold;">{product.name}</a>')
                
                products_text = ', '.join(product_links)
                if out_of_stock_products.count() > 5:
                    products_text += f' <em>and {out_of_stock_products.count() - 5} more</em>'
                
                products_list_url = reverse('admin:store_products_changelist')
                message = mark_safe(
                    f'🚨 Out of stock products: {products_text} '
                    f'| <a href="{products_list_url}" style="font-weight: bold; text-decoration: underline;">View all products →</a>'
                )
                messages.error(request, message)
            
            if zero_stock_sizes.exists():
                size_links = []
                for size in zero_stock_sizes[:5]:  # Show first 5
                    change_url = reverse('admin:store_products_change', args=[size.product.pk])
                    size_links.append(f'<a href="{change_url}" style="text-decoration: underline; font-weight: bold;">{size.product.name} ({size.get_size_display()})</a>')
                
                sizes_text = ', '.join(size_links)
                if zero_stock_sizes.count() > 5:
                    sizes_text += f' <em>and {zero_stock_sizes.count() - 5} more</em>'
                
                sizes_list_url = reverse('admin:store_productsize_changelist')
                message = mark_safe(
                    f'❌ Zero stock sizes: {sizes_text} '
                    f'| <a href="{sizes_list_url}" style="font-weight: bold; text-decoration: underline;">Manage stock →</a>'
                )
                messages.warning(request, message)
                
            if low_stock_sizes.exists():
                size_links = []
                for size in low_stock_sizes[:5]:  # Show first 5
                    change_url = reverse('admin:store_products_change', args=[size.product.pk])
                    size_links.append(f'<a href="{change_url}" style="text-decoration: underline; font-weight: bold;">{size.product.name} ({size.get_size_display()}: {size.stock_count} left)</a>')
                
                sizes_text = ', '.join(size_links)
                if low_stock_sizes.count() > 5:
                    sizes_text += f' <em>and {low_stock_sizes.count() - 5} more</em>'
                
                sizes_list_url = reverse('admin:store_productsize_changelist')
                message = mark_safe(
                    f'⚠️ Low stock sizes: {sizes_text} '
                    f'| <a href="{sizes_list_url}" style="font-weight: bold; text-decoration: underline;">Manage stock →</a>'
                )
                messages.info(request, message)
        
        return view(request, *args, **kwargs)
    return wrapper

# Apply the custom wrapper
AdminSite.admin_view = lambda self, view, cacheable=False: original_admin_view(self, custom_admin_view(self, view, cacheable), cacheable)