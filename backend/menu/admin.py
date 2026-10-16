from django.contrib import admin

from .models import (
    Addon,
    Category,
    FoodImage,
    FoodItem,
    MenuSection,
    SpiceLevel,
)


@admin.register(MenuSection)
class MenuSectionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "display_order",
        "is_active",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "display_order",
        "name",
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "section",
        "display_order",
        "is_active",
    )

    list_filter = (
        "section",
        "is_active",
    )

    search_fields = (
        "name",
        "description",
    )

    ordering = (
        "section__display_order",
        "display_order",
        "name",
    )


@admin.register(SpiceLevel)
class SpiceLevelAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "display_order",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "display_order",
        "name",
    )


@admin.register(Addon)
class AddonAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "name",
    )


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price",
        "is_available",
        "is_active",
        "display_order",
    )

    list_filter = (
        "category__section",
        "category",
        "is_available",
        "is_active",
    )

    search_fields = (
        "name",
        "description",
    )

    filter_horizontal = (
        "spice_levels",
        "addons",
    )

    ordering = (
        "category__section__display_order",
        "category__display_order",
        "display_order",
        "name",
    )


@admin.register(FoodImage)
class FoodImageAdmin(admin.ModelAdmin):
    list_display = (
        "food_item",
        "is_primary",
        "created_at",
    )

    list_filter = (
        "is_primary",
    )

    search_fields = (
        "food_item__name",
        "alt_text",
    )