from django.contrib import admin

from .models import Restaurant, RestaurantSetting


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "phone",
        "email",
        "is_open",
        "currency",
    )

    search_fields = (
        "name",
        "phone",
        "email",
    )


@admin.register(RestaurantSetting)
class RestaurantSettingAdmin(admin.ModelAdmin):
    list_display = (
        "restaurant",
        "tax_enabled",
        "service_charge_enabled",
        "service_charge_type",
        "service_charge_value",
        "max_reception_discount_percentage",
    )