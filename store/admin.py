# store/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from .models import Products, Order, OrderItem
from django.utils.text import Truncator
from django.utils.html import format_html
from django.db.models import F



# ---------- Products ----------
@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    list_display = ("name", "classification", "price", "compare_price", "best_seller")
    list_filter = ("classification", "best_seller")
    search_fields = ("name",)
    list_editable = ("price", "best_seller")
    ordering = ("-best_seller", "classification", "name")


# ---------- Inline: Order items ----------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ("product",)
    fields = ("product", "quantity", "price", "line_total_display")
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
    list_display = ("order", "product", "quantity", "price", "line_total_display")
    list_filter = ("order__status", "product__classification")
    search_fields = ("order__order_number", "product__name")
    autocomplete_fields = ("product", "order")

    def line_total_display(self, obj):
        qty = obj.quantity or 0
        price = obj.price or 0
        return f"EGP {qty * int(price)}"
    line_total_display.short_description = "Line total"


# ---------- Admin site labels ----------
admin.site.site_header = "Hunters Admin"
admin.site.site_title = "Hunters Admin"
admin.site.index_title = "Management"
