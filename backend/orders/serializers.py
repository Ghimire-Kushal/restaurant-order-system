from rest_framework import serializers

from .models import (
    Cart,
    CartItem,
    CartItemAddon,
    Order,
    OrderItem,
    OrderItemAddon,
    OrderStatusHistory,
    Payment,
)


# ============================================================
# CART ITEM ADDON
# ============================================================

class CartItemAddonSerializer(
    serializers.ModelSerializer
):
    addon_name = serializers.CharField(
        source="addon.name",
        read_only=True,
    )

    class Meta:
        model = CartItemAddon

        fields = [
            "id",
            "addon",
            "addon_name",
            "price",
        ]


# ============================================================
# CART ITEM
# ============================================================

class CartItemSerializer(
    serializers.ModelSerializer
):
    food_name = serializers.CharField(
        source="food_item.name",
        read_only=True,
    )

    spice_name = serializers.CharField(
        source="spice_level.name",
        read_only=True,
    )

    addons = CartItemAddonSerializer(
        many=True,
        read_only=True,
    )

    addon_total = serializers.SerializerMethodField()
    unit_total = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem

        fields = [
            "id",
            "food_item",
            "food_name",
            "quantity",
            "unit_price",
            "spice_level",
            "spice_name",
            "addons",
            "special_instruction",
            "addon_total",
            "unit_total",
            "subtotal",
        ]

    def get_addon_total(self, obj):
        return obj.addon_total

    def get_unit_total(self, obj):
        return obj.unit_total

    def get_subtotal(self, obj):
        return obj.subtotal


# ============================================================
# CART
# ============================================================

class CartSerializer(
    serializers.ModelSerializer
):
    items = CartItemSerializer(
        many=True,
        read_only=True,
    )

    subtotal = serializers.SerializerMethodField()

    session_token = serializers.CharField(
        source="session.session_token",
        read_only=True,
    )

    class Meta:
        model = Cart

        fields = [
            "id",
            "session_token",
            "items",
            "subtotal",
            "created_at",
            "updated_at",
        ]

    def get_subtotal(self, obj):
        return obj.subtotal


# ============================================================
# ORDER ITEM ADDON
# ============================================================

class OrderItemAddonSerializer(
    serializers.ModelSerializer
):
    addon_name = serializers.CharField(
        source="addon.name",
        read_only=True,
    )

    class Meta:
        model = OrderItemAddon

        fields = [
            "id",
            "addon",
            "addon_name",
            "price",
        ]


# ============================================================
# ORDER ITEM
# ============================================================

class OrderItemSerializer(
    serializers.ModelSerializer
):
    addons = OrderItemAddonSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = OrderItem

        fields = [
            "id",
            "food_item",
            "food_name",
            "quantity",
            "unit_price",
            "spice_level",
            "spice_name",
            "addons",
            "special_instruction",
            "addon_total",
            "unit_total",
            "subtotal",
        ]


# ============================================================
# ORDER STATUS HISTORY
# ============================================================

class OrderStatusHistorySerializer(
    serializers.ModelSerializer
):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OrderStatusHistory

        fields = [
            "id",
            "status",
            "note",
            "changed_by",
            "changed_by_name",
            "created_at",
        ]

    def get_changed_by_name(self, obj):

        if obj.changed_by:
            return obj.changed_by.get_username()

        return None


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "amount",
            "method",
            "status",
            "transaction_reference",
            "recorded_by",
            "created_at",
            "updated_at",
        ]


# ============================================================
# ORDER
# ============================================================

class OrderSerializer(
    serializers.ModelSerializer
):
    items = OrderItemSerializer(
        many=True,
        read_only=True,
    )

    status_history = OrderStatusHistorySerializer(
        many=True,
        read_only=True,
    )

    payments = PaymentSerializer(many=True, read_only=True)

    session_token = serializers.CharField(
        source="session.session_token",
        read_only=True,
    )

    table_number = serializers.IntegerField(
        source="table.number",
        read_only=True,
    )

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = Order

        fields = [
            "id",
            "order_number",
            "session_token",
            "table",
            "table_number",
            "status",
            "status_display",
            "items",
            "subtotal",
            "discount_amount",
            "service_charge",
            "tax_amount",
            "total_amount",
            "rejection_reason",
            "cancellation_reason",
            "preparation_minutes",
            "preparation_started_at",
            "ready_at",
            "payments",
            "status_history",
            "created_at",
            "updated_at",
            "submitted_at",
        ]
