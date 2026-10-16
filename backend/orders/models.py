from decimal import Decimal
import uuid

from django.db import models

from menu.models import FoodItem, SpiceLevel, Addon
from tables.models import CustomerSession


# ============================================================
# CART
# ============================================================

class Cart(models.Model):
    """
    Shopping cart belonging to one customer device/session.
    """

    session = models.OneToOneField(
        CustomerSession,
        on_delete=models.CASCADE,
        related_name="cart",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Cart - Session {self.session.id}"

    @property
    def subtotal(self):
        return sum(
            (
                item.subtotal
                for item in self.items.all()
            ),
            Decimal("0.00"),
        )


class CartItem(models.Model):
    """
    Individual food item inside a customer's cart.
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )

    food_item = models.ForeignKey(
        FoodItem,
        on_delete=models.PROTECT,
        related_name="cart_items",
    )

    quantity = models.PositiveIntegerField(
        default=1,
    )

    spice_level = models.ForeignKey(
        SpiceLevel,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cart_items",
    )

    special_instruction = models.TextField(
        blank=True,
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.food_item.name} x {self.quantity}"

    @property
    def addon_total(self):
        return sum(
            (
                addon.price
                for addon in self.addons.all()
            ),
            Decimal("0.00"),
        )

    @property
    def unit_total(self):
        return self.unit_price + self.addon_total

    @property
    def subtotal(self):
        return self.unit_total * self.quantity


class CartItemAddon(models.Model):
    """
    Add-on selected for a cart item.
    """

    cart_item = models.ForeignKey(
        CartItem,
        on_delete=models.CASCADE,
        related_name="addons",
    )

    addon = models.ForeignKey(
        Addon,
        on_delete=models.PROTECT,
        related_name="cart_item_addons",
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart_item", "addon"],
                name="unique_addon_per_cart_item",
            ),
        ]

    def __str__(self):
        return f"{self.addon.name} - {self.price}"


# ============================================================
# ORDER
# ============================================================

class Order(models.Model):
    """
    Final order created from a customer's cart.
    One customer session can create multiple orders.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RECEPTION_ACCEPTED = (
            "RECEPTION_ACCEPTED",
            "Reception Accepted",
        )
        KITCHEN_CONFIRMED = (
            "KITCHEN_CONFIRMED",
            "Kitchen Confirmed",
        )
        PREPARING = "PREPARING", "Preparing"
        READY = "READY", "Ready"
        SERVED = "SERVED", "Served"
        COMPLETED = "COMPLETED", "Completed"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    order_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )

    session = models.ForeignKey(
        CustomerSession,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    table = models.ForeignKey(
        "tables.Table",
        on_delete=models.PROTECT,
        related_name="orders",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    service_charge = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    rejection_reason = models.TextField(
        blank=True,
    )

    cancellation_reason = models.TextField(
        blank=True,
    )

    preparation_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    preparation_started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    ready_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number


# ============================================================
# ORDER ITEM
# ============================================================

class OrderItem(models.Model):
    """
    Snapshot of a cart item at the time the order is submitted.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    food_item = models.ForeignKey(
        FoodItem,
        on_delete=models.PROTECT,
        related_name="order_items",
    )

    food_name = models.CharField(
        max_length=255,
    )

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    spice_level = models.ForeignKey(
        SpiceLevel,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="order_items",
    )

    spice_name = models.CharField(
        max_length=100,
        blank=True,
    )

    special_instruction = models.TextField(
        blank=True,
    )

    addon_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    unit_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.food_name} x {self.quantity}"


# ============================================================
# ORDER ITEM ADDON
# ============================================================

class OrderItemAddon(models.Model):
    """
    Snapshot of an add-on selected for an order item.
    """

    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name="addons",
    )

    addon = models.ForeignKey(
        Addon,
        on_delete=models.PROTECT,
        related_name="order_item_addons",
    )

    addon_name = models.CharField(
        max_length=255,
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.addon_name} - {self.price}"


# ============================================================
# ORDER STATUS HISTORY
# ============================================================

class OrderStatusHistory(models.Model):
    """
    Keeps a history of every important order status change.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history",
    )

    status = models.CharField(
        max_length=30,
        choices=Order.Status.choices,
    )

    note = models.TextField(
        blank=True,
    )

    changed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_status_changes",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.order.order_number} - {self.status}"


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESSFUL = "SUCCESSFUL", "Successful"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        ONLINE = "ONLINE", "Online"

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    transaction_reference = models.CharField(
        max_length=120,
        blank=True,
        unique=True,
        null=True,
    )
    recorded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_payments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.order_number} - {self.amount} ({self.status})"
