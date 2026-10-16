from django.contrib import admin

from .models import (
    Cart,
    CartItem,
    Order,
    OrderItem,
    OrderStatusHistory,
    Payment,
)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "table", "status", "total_amount", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order_number", "table__number")
    readonly_fields = ("order_number", "created_at", "updated_at", "submitted_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "amount", "method", "status", "recorded_by", "created_at")
    list_filter = ("method", "status")
    search_fields = ("order__order_number", "transaction_reference")


admin.site.register((Cart, CartItem, OrderItem, OrderStatusHistory))
