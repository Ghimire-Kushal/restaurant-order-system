from rest_framework import serializers

from .models import (
    Addon,
    Category,
    FoodImage,
    FoodItem,
    MenuSection,
    SpiceLevel,
)


class FoodImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodImage
        fields = [
            "id",
            "image",
            "alt_text",
            "is_primary",
        ]


class SpiceLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpiceLevel
        fields = [
            "id",
            "name",
            "description",
            "display_order",
        ]


class AddonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Addon
        fields = [
            "id",
            "name",
            "price",
        ]


class FoodItemSerializer(serializers.ModelSerializer):
    spice_levels = SpiceLevelSerializer(many=True, read_only=True)
    addons = AddonSerializer(many=True, read_only=True)
    images = FoodImageSerializer(many=True, read_only=True)

    class Meta:
        model = FoodItem
        fields = [
            "id",
            "name",
            "description",
            "price",
            "is_available",
            "spice_levels",
            "addons",
            "allow_special_instruction",
            "display_order",
            "images",
        ]


class CategorySerializer(serializers.ModelSerializer):
    food_items = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "description",
            "display_order",
            "food_items",
        ]

    def get_food_items(self, obj):
        food_items = (
            obj.food_items
            .filter(
                is_active=True,
                is_available=True,
            )
            .prefetch_related(
                "spice_levels",
                "addons",
                "images",
            )
            .order_by("display_order", "name")
        )

        return FoodItemSerializer(
            food_items,
            many=True,
            context=self.context,
        ).data


class MenuSectionSerializer(serializers.ModelSerializer):
    categories = serializers.SerializerMethodField()

    class Meta:
        model = MenuSection
        fields = [
            "id",
            "name",
            "display_order",
            "categories",
        ]

    def get_categories(self, obj):
        categories = (
            obj.categories
            .filter(is_active=True)
            .order_by("display_order", "name")
        )

        return CategorySerializer(
            categories,
            many=True,
            context=self.context,
        ).data