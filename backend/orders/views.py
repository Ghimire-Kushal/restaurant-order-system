import uuid
from decimal import Decimal
from html import escape

from django.db import transaction
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from menu.models import Addon, FoodItem, SpiceLevel
from tables.models import CustomerSession

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

from .serializers import (
    CartSerializer,
    OrderSerializer,
    PaymentSerializer,
)
from .permissions import KitchenPermission, ReceptionPermission


# ============================================================
# HELPERS
# ============================================================


def get_cart_for_session(session_token):
    """
    Get the active customer session and its cart.
    """

    session = get_object_or_404(
        CustomerSession,
        session_token=session_token,
        is_active=True,
    )

    cart, _ = Cart.objects.get_or_create(
        session=session,
    )

    return session, cart


def get_full_cart(cart):
    """
    Reload cart with all related objects required
    by the serializer.
    """

    return (
        Cart.objects
        .select_related(
            "session",
        )
        .prefetch_related(
            "items__food_item",
            "items__spice_level",
            "items__addons__addon",
        )
        .get(pk=cart.pk)
    )


def get_full_order(order):
    """
    Reload order with all related objects required
    by the order serializer.
    """

    return (
        Order.objects
        .select_related(
            "session",
            "table",
        )
        .prefetch_related(
            "items__addons__addon",
            "payments",
            "status_history__changed_by",
        )
        .get(pk=order.pk)
    )


# ============================================================
# CART DETAIL
# ============================================================


class CartDetailView(APIView):
    """
    Get the current cart for a customer session.
    """

    def get(self, request, session_token):

        session, cart = get_cart_for_session(
            session_token
        )

        cart = get_full_cart(cart)

        return Response(
            {
                "success": True,
                "cart": CartSerializer(cart).data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# ADD TO CART
# ============================================================


class AddToCartView(APIView):
    """
    Add a food item to the customer's cart.
    """

    @transaction.atomic
    def post(self, request, session_token):

        session, cart = get_cart_for_session(
            session_token
        )

        food_item_id = request.data.get(
            "food_item_id",
            request.data.get("food_item"),
        )

        quantity = request.data.get(
            "quantity",
            1,
        )

        spice_level_id = request.data.get(
            "spice_level_id",
            request.data.get("spice_level"),
        )

        addon_ids = request.data.get(
            "addon_ids",
            request.data.get("addons", []),
        )

        special_instruction = request.data.get(
            "special_instruction",
            "",
        )

        # ----------------------------------------------------
        # Food item ID validation
        # ----------------------------------------------------

        if food_item_id is None:
            return Response(
                {
                    "success": False,
                    "message": "food_item_id is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # Food validation
        # ----------------------------------------------------

        food_item = get_object_or_404(
            FoodItem,
            id=food_item_id,
            is_active=True,
        )

        if not food_item.is_available:
            return Response(
                {
                    "success": False,
                    "message": (
                        f"{food_item.name} is currently "
                        "out of stock."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # Quantity validation
        # ----------------------------------------------------

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Quantity must be a valid integer."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quantity < 1:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Quantity must be at least 1."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quantity > 50:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Maximum quantity is 50."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # Special instruction validation
        # ----------------------------------------------------

        if (
            special_instruction
            and not food_item.allow_special_instruction
        ):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Special instructions are not "
                        "allowed for this food item."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # Spice level validation
        # ----------------------------------------------------

        spice_level = None

        if spice_level_id is not None:

            spice_level = get_object_or_404(
                SpiceLevel,
                id=spice_level_id,
                is_active=True,
            )

            if not food_item.spice_levels.filter(
                id=spice_level.id
            ).exists():
                return Response(
                    {
                        "success": False,
                        "message": (
                            f"{spice_level.name} is not "
                            f"available for "
                            f"{food_item.name}."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # ----------------------------------------------------
        # Add-on validation
        # ----------------------------------------------------

        if addon_ids is None:
            addon_ids = []

        if not isinstance(addon_ids, list):
            return Response(
                {
                    "success": False,
                    "message": (
                        "addon_ids must be a list of IDs."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            unique_addon_ids = list(
                dict.fromkeys(
                    int(addon_id)
                    for addon_id in addon_ids
                )
            )
        except (TypeError, ValueError):
            return Response(
                {
                    "success": False,
                    "message": (
                        "addon_ids must contain valid "
                        "integer IDs."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        addons = list(
            Addon.objects.filter(
                id__in=unique_addon_ids,
                is_active=True,
            )
        )

        if len(addons) != len(unique_addon_ids):
            return Response(
                {
                    "success": False,
                    "message": (
                        "One or more selected add-ons "
                        "are invalid or inactive."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_addon_ids = set(
            food_item.addons.filter(
                is_active=True,
            ).values_list(
                "id",
                flat=True,
            )
        )

        invalid_addons = [
            addon.id
            for addon in addons
            if addon.id not in allowed_addon_ids
        ]

        if invalid_addons:
            return Response(
                {
                    "success": False,
                    "message": (
                        "One or more selected add-ons "
                        "are not available for this "
                        "food item."
                    ),
                    "invalid_addons": invalid_addons,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # Create cart item
        # ----------------------------------------------------

        cart_item = CartItem.objects.create(
            cart=cart,
            food_item=food_item,
            quantity=quantity,
            spice_level=spice_level,
            special_instruction=special_instruction,
            unit_price=food_item.price,
        )

        # ----------------------------------------------------
        # Create cart add-ons
        # ----------------------------------------------------

        CartItemAddon.objects.bulk_create(
            [
                CartItemAddon(
                    cart_item=cart_item,
                    addon=addon,
                    price=addon.price,
                )
                for addon in addons
            ]
        )

        # ----------------------------------------------------
        # Return updated cart
        # ----------------------------------------------------

        cart = get_full_cart(cart)

        return Response(
            {
                "success": True,
                "message": (
                    "Item added to cart successfully."
                ),
                "cart": CartSerializer(cart).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# UPDATE CART ITEM
# ============================================================


class UpdateCartItemView(APIView):
    """
    Update the quantity of a cart item.
    """

    @transaction.atomic
    def patch(
        self,
        request,
        session_token,
        item_id,
    ):

        session, cart = get_cart_for_session(
            session_token
        )

        cart_item = get_object_or_404(
            CartItem,
            id=item_id,
            cart=cart,
        )

        quantity = request.data.get(
            "quantity"
        )

        if quantity is None:
            return Response(
                {
                    "success": False,
                    "message": (
                        "quantity is required."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(
                {
                    "success": False,
                    "message": (
                        "Quantity must be a valid integer."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quantity < 1:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Quantity must be at least 1."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quantity > 50:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Maximum quantity is 50."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        food_item = cart_item.food_item

        if not food_item.is_active:
            return Response(
                {
                    "success": False,
                    "message": (
                        f"{food_item.name} is no longer "
                        "available."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not food_item.is_available:
            return Response(
                {
                    "success": False,
                    "message": (
                        f"{food_item.name} is currently "
                        "out of stock."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart_item.quantity = quantity

        cart_item.save(
            update_fields=[
                "quantity",
                "updated_at",
            ]
        )

        cart = get_full_cart(cart)

        return Response(
            {
                "success": True,
                "message": (
                    "Cart item quantity updated "
                    "successfully."
                ),
                "cart": CartSerializer(cart).data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# REMOVE CART ITEM
# ============================================================


class RemoveCartItemView(APIView):
    """
    Remove one item from the customer's cart.
    """

    @transaction.atomic
    def delete(
        self,
        request,
        session_token,
        item_id,
    ):

        session, cart = get_cart_for_session(
            session_token
        )

        cart_item = get_object_or_404(
            CartItem,
            id=item_id,
            cart=cart,
        )

        food_name = cart_item.food_item.name

        cart_item.delete()

        cart = get_full_cart(cart)

        return Response(
            {
                "success": True,
                "message": (
                    f"{food_name} removed "
                    "from cart successfully."
                ),
                "cart": CartSerializer(cart).data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# CLEAR CART
# ============================================================


class ClearCartView(APIView):
    """
    Remove all items from the customer's cart.
    """

    @transaction.atomic
    def delete(
        self,
        request,
        session_token,
    ):

        session, cart = get_cart_for_session(
            session_token
        )

        cart.items.all().delete()

        cart = get_full_cart(cart)

        return Response(
            {
                "success": True,
                "message": (
                    "Cart cleared successfully."
                ),
                "cart": CartSerializer(cart).data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# CREATE ORDER FROM CART
# ============================================================


class CreateOrderView(APIView):
    """
    Convert the customer's cart into an order.

    The cart is copied into permanent Order / OrderItem
    records and then emptied.
    """

    @transaction.atomic
    def post(
        self,
        request,
        session_token,
    ):

        # ----------------------------------------------------
        # Get and lock customer session
        # ----------------------------------------------------

        session = get_object_or_404(
            CustomerSession.objects.select_for_update(),
            session_token=session_token,
            is_active=True,
        )

        # ----------------------------------------------------
        # Get and lock cart
        # ----------------------------------------------------

        cart = get_object_or_404(
            Cart.objects.select_for_update(),
            session=session,
        )

        # ----------------------------------------------------
        # Get cart items
        # ----------------------------------------------------

        cart_items = list(
            cart.items
            .select_related(
                "food_item",
                "spice_level",
            )
            .prefetch_related(
                "addons__addon",
            )
        )

        # ----------------------------------------------------
        # Empty cart check
        # ----------------------------------------------------

        if not cart_items:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Your cart is empty."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # Validate table
        # ----------------------------------------------------

        table = session.table

        if table is None:
            return Response(
                {
                    "success": False,
                    "message": (
                        "No table is associated "
                        "with this customer session."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not table.is_active:
            return Response(
                {
                    "success": False,
                    "message": (
                        "This table is currently inactive."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # Validate cart items
        # ----------------------------------------------------

        for cart_item in cart_items:

            food_item = cart_item.food_item

            if not food_item.is_active:
                return Response(
                    {
                        "success": False,
                        "message": (
                            f"{food_item.name} is no longer "
                            "available."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not food_item.is_available:
                return Response(
                    {
                        "success": False,
                        "message": (
                            f"{food_item.name} is currently "
                            "out of stock."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ------------------------------------------------
            # Validate spice
            # ------------------------------------------------

            if cart_item.spice_level:

                if not food_item.spice_levels.filter(
                    id=cart_item.spice_level.id,
                    is_active=True,
                ).exists():

                    return Response(
                        {
                            "success": False,
                            "message": (
                                f"{cart_item.spice_level.name} "
                                f"is no longer available for "
                                f"{food_item.name}."
                            ),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # ------------------------------------------------
            # Validate add-ons
            # ------------------------------------------------

            allowed_addon_ids = set(
                food_item.addons.filter(
                    is_active=True,
                ).values_list(
                    "id",
                    flat=True,
                )
            )

            for cart_addon in cart_item.addons.all():

                if cart_addon.addon.id not in allowed_addon_ids:

                    return Response(
                        {
                            "success": False,
                            "message": (
                                f"{cart_addon.addon.name} "
                                f"is no longer available for "
                                f"{food_item.name}."
                            ),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # ----------------------------------------------------
        # Calculate subtotal
        # ----------------------------------------------------

        subtotal = Decimal("0.00")

        for cart_item in cart_items:

            addon_total = sum(
                (
                    cart_addon.price
                    for cart_addon in cart_item.addons.all()
                ),
                Decimal("0.00"),
            )

            unit_total = (
                cart_item.unit_price
                + addon_total
            )

            item_subtotal = (
                unit_total
                * cart_item.quantity
            )

            subtotal += item_subtotal

        # ----------------------------------------------------
        # Generate unique order number
        # ----------------------------------------------------

        order_number = (
            "ORD-"
            f"{timezone.now().strftime('%Y%m%d%H%M%S')}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        # ----------------------------------------------------
        # Create order
        # ----------------------------------------------------

        order = Order.objects.create(
            order_number=order_number,
            session=session,
            table=table,
            status=Order.Status.PENDING,
            subtotal=subtotal,
            discount_amount=Decimal("0.00"),
            service_charge=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            total_amount=subtotal,
            submitted_at=timezone.now(),
        )

        # ----------------------------------------------------
        # Create order items
        # ----------------------------------------------------

        for cart_item in cart_items:

            addon_total = sum(
                (
                    cart_addon.price
                    for cart_addon in cart_item.addons.all()
                ),
                Decimal("0.00"),
            )

            unit_total = (
                cart_item.unit_price
                + addon_total
            )

            item_subtotal = (
                unit_total
                * cart_item.quantity
            )

            spice_name = ""

            if cart_item.spice_level:
                spice_name = (
                    cart_item.spice_level.name
                )

            order_item = OrderItem.objects.create(
                order=order,
                food_item=cart_item.food_item,
                food_name=cart_item.food_item.name,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                spice_level=cart_item.spice_level,
                spice_name=spice_name,
                special_instruction=(
                    cart_item.special_instruction
                ),
                addon_total=addon_total,
                unit_total=unit_total,
                subtotal=item_subtotal,
            )

            # ------------------------------------------------
            # Copy add-ons
            # ------------------------------------------------

            OrderItemAddon.objects.bulk_create(
                [
                    OrderItemAddon(
                        order_item=order_item,
                        addon=cart_addon.addon,
                        addon_name=cart_addon.addon.name,
                        price=cart_addon.price,
                    )
                    for cart_addon in cart_item.addons.all()
                ]
            )

        # ----------------------------------------------------
        # Initial order status history
        # ----------------------------------------------------

        OrderStatusHistory.objects.create(
            order=order,
            status=Order.Status.PENDING,
            note="Order submitted by customer.",
        )

        # ----------------------------------------------------
        # Clear cart
        # ----------------------------------------------------

        cart.items.all().delete()

        # ----------------------------------------------------
        # Reload complete order
        # ----------------------------------------------------

        order = get_full_order(order)

        return Response(
            {
                "success": True,
                "message": (
                    "Order placed successfully."
                ),
                "order": OrderSerializer(order).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# CUSTOMER ORDER DETAIL
# ============================================================


class CustomerOrderDetailView(APIView):
    """
    Get a single order belonging to the customer's session.
    """

    def get(
        self,
        request,
        session_token,
        order_number,
    ):

        session = get_object_or_404(
            CustomerSession,
            session_token=session_token,
            is_active=True,
        )

        order = get_object_or_404(
            Order.objects
            .select_related(
                "session",
                "table",
            )
            .prefetch_related(
                "items__addons__addon",
                "status_history__changed_by",
            ),
            order_number=order_number,
            session=session,
        )

        return Response(
            {
                "success": True,
                "order": OrderSerializer(order).data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# RECEPTION ORDER LIST
# ============================================================


class ReceptionOrderListView(APIView):
    """
    Return pending orders for Reception.

    These are orders waiting for Reception to accept
    or reject.
    """

    permission_classes = [ReceptionPermission]

    def get(self, request):

        requested_status = request.query_params.get("status")
        allowed_statuses = {value for value, _ in Order.Status.choices}
        if requested_status and requested_status not in allowed_statuses:
            return Response(
                {"success": False, "message": "Invalid order status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        orders = (
            Order.objects
            .select_related(
                "session",
                "table",
            )
            .prefetch_related(
                "items__addons__addon",
                "status_history__changed_by",
            )
            .filter(status=requested_status or Order.Status.PENDING)
            .order_by(
                "-created_at",
            )
        )

        return Response(
            {
                "success": True,
                "count": orders.count(),
                "orders": OrderSerializer(
                    orders,
                    many=True,
                ).data,
            },
            status=status.HTTP_200_OK,
        )


def transition_order(order, new_status, actor, note="", **updates):
    transitions = {
        Order.Status.PENDING: {
            Order.Status.RECEPTION_ACCEPTED,
            Order.Status.REJECTED,
        },
        Order.Status.RECEPTION_ACCEPTED: {Order.Status.PREPARING},
        Order.Status.PREPARING: {Order.Status.READY},
        Order.Status.READY: {Order.Status.SERVED, Order.Status.COMPLETED},
        Order.Status.SERVED: {Order.Status.COMPLETED},
    }
    if new_status not in transitions.get(order.status, set()):
        return False
    previous = order.status
    order.status = new_status
    for field, value in updates.items():
        setattr(order, field, value)
    order.save(update_fields=["status", *updates.keys(), "updated_at"])
    OrderStatusHistory.objects.create(
        order=order,
        status=new_status,
        note=note or f"Status changed from {previous} to {new_status}.",
        changed_by=actor,
    )
    return True


class ReceptionOrderActionView(APIView):
    permission_classes = [ReceptionPermission]

    @transaction.atomic
    def post(self, request, order_number, action):
        order = get_object_or_404(
            Order.objects.select_for_update(), order_number=order_number
        )
        if action == "accept":
            new_status = Order.Status.RECEPTION_ACCEPTED
        elif action == "reject":
            new_status = Order.Status.REJECTED
        else:
            return Response({"success": False, "message": "Unknown action."}, status=400)
        reason = str(request.data.get("reason", "")).strip()
        if new_status == Order.Status.REJECTED and not reason:
            return Response({"success": False, "message": "A rejection reason is required."}, status=400)
        if not transition_order(
            order, new_status, request.user, reason,
            rejection_reason=reason if new_status == Order.Status.REJECTED else order.rejection_reason,
        ):
            return Response({"success": False, "message": "Invalid order status transition."}, status=409)
        return Response({"success": True, "order": OrderSerializer(get_full_order(order)).data})


class KitchenOrderListView(APIView):
    permission_classes = [KitchenPermission]

    def get(self, request):
        orders = Order.objects.filter(
            status__in=[Order.Status.RECEPTION_ACCEPTED, Order.Status.PREPARING]
        ).select_related("table").prefetch_related("items__addons__addon")
        return Response({"success": True, "count": orders.count(), "orders": OrderSerializer(orders, many=True).data})


class KitchenOrderActionView(APIView):
    permission_classes = [KitchenPermission]

    @transaction.atomic
    def post(self, request, order_number, action):
        order = get_object_or_404(Order.objects.select_for_update(), order_number=order_number)
        if action == "start":
            try:
                minutes = int(request.data.get("preparation_minutes", 0))
            except (TypeError, ValueError):
                minutes = 0
            if minutes not in {15, 20, 25, 30, 35} and minutes < 1:
                return Response({"success": False, "message": "Preparation time must be a positive custom value or one of 15, 20, 25, 30, 35."}, status=400)
            if not transition_order(order, Order.Status.PREPARING, request.user, "Kitchen preparation started.", preparation_minutes=minutes, preparation_started_at=timezone.now()):
                message = "Invalid order status transition."
                return Response({"success": False, "message": message}, status=409)
        elif action == "ready":
            if not transition_order(order, Order.Status.READY, request.user, "Order marked ready.", ready_at=timezone.now()):
                return Response({"success": False, "message": "Invalid order status transition."}, status=409)
        else:
            return Response({"success": False, "message": "Unknown action."}, status=400)
        return Response({"success": True, "order": OrderSerializer(get_full_order(order)).data})


class RecordPaymentView(APIView):
    permission_classes = [ReceptionPermission]

    @transaction.atomic
    def post(self, request, order_number):
        order = get_object_or_404(Order.objects.select_for_update(), order_number=order_number)
        if order.status in {Order.Status.REJECTED, Order.Status.CANCELLED}:
            return Response({"success": False, "message": "Rejected or cancelled orders cannot be paid."}, status=409)
        if Payment.objects.filter(order=order, status=Payment.Status.SUCCESSFUL).exists():
            return Response({"success": False, "message": "This order already has a successful payment."}, status=409)
        try:
            amount = Decimal(str(request.data.get("amount", order.total_amount)))
        except Exception:
            return Response({"success": False, "message": "Amount must be a valid number."}, status=400)
        if amount != order.total_amount or amount <= 0:
            return Response({"success": False, "message": "Payment amount must match the order total."}, status=400)
        method = request.data.get("method", Payment.Method.CASH)
        if method not in Payment.Method.values:
            return Response({"success": False, "message": "Invalid payment method."}, status=400)
        if method == Payment.Method.ONLINE:
            return Response(
                {
                    "success": False,
                    "message": "Online payments are unavailable until a provider is configured and server-side verification is enabled.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        payment, _ = Payment.objects.get_or_create(
            order=order,
            transaction_reference=request.data.get("transaction_reference") or None,
            defaults={"amount": amount, "method": method, "status": Payment.Status.SUCCESSFUL, "recorded_by": request.user},
        )
        if payment.status != Payment.Status.SUCCESSFUL:
            return Response({"success": False, "message": "Payment reference already exists with another status."}, status=409)
        return Response({"success": True, "payment": PaymentSerializer(payment).data}, status=status.HTTP_201_CREATED)


class ApplyDiscountView(APIView):
    permission_classes = [ReceptionPermission]

    @transaction.atomic
    def post(self, request, order_number):
        order = get_object_or_404(Order.objects.select_for_update(), order_number=order_number)
        try:
            percentage = Decimal(str(request.data.get("percentage", "0")))
        except Exception:
            return Response({"success": False, "message": "Discount percentage must be numeric."}, status=400)
        if percentage < 0 or percentage > 100:
            return Response({"success": False, "message": "Discount percentage must be between 0 and 100."}, status=400)
        if order.status not in {Order.Status.PENDING, Order.Status.RECEPTION_ACCEPTED}:
            return Response({"success": False, "message": "Discounts can only be applied before preparation."}, status=409)
        discount = (order.subtotal * percentage / Decimal("100")).quantize(Decimal("0.01"))
        total = (order.subtotal - discount + order.service_charge + order.tax_amount).quantize(Decimal("0.01"))
        order.discount_amount = discount
        order.total_amount = max(total, Decimal("0.00"))
        order.save(update_fields=["discount_amount", "total_amount", "updated_at"])
        OrderStatusHistory.objects.create(
            order=order,
            status=order.status,
            note=f"Discount of {percentage}% applied by reception.",
            changed_by=request.user,
        )
        return Response({"success": True, "order": OrderSerializer(get_full_order(order)).data})


class ReceiptView(APIView):
    permission_classes = [ReceptionPermission]

    def get(self, request, order_number):
        order = get_object_or_404(
            Order.objects.select_related("table").prefetch_related("items__addons", "payments"),
            order_number=order_number,
        )
        rows = "".join(
            f"<tr><td>{escape(item.food_name)}</td><td>{item.quantity}</td><td>{item.subtotal:.2f}</td></tr>"
            for item in order.items.all()
        )
        payments = "".join(
            f"<p>{escape(payment.method)}: {payment.amount:.2f} ({escape(payment.status)})</p>"
            for payment in order.payments.all()
        ) or "<p>Unpaid</p>"
        html = f"""<!doctype html><html><head><meta charset='utf-8'><title>Receipt {escape(order.order_number)}</title>
        <style>body{{font:16px system-ui;max-width:720px;margin:32px auto;padding:0 16px}}table{{width:100%;border-collapse:collapse}}td,th{{padding:8px;border-bottom:1px solid #ddd;text-align:left}}.total{{text-align:right;font-weight:700}}</style></head>
        <body onload='window.print()'><h1>Restaurant Receipt</h1><p>Order {escape(order.order_number)} · Table {order.table.number}</p>
        <table><thead><tr><th>Item</th><th>Qty</th><th>Amount</th></tr></thead><tbody>{rows}</tbody></table>
        <p class='total'>Subtotal: {order.subtotal:.2f}<br>Discount: -{order.discount_amount:.2f}<br>Total: {order.total_amount:.2f}</p>
        <h3>Payments</h3>{payments}</body></html>"""
        return HttpResponse(html)


class ReportsView(APIView):
    permission_classes = [ReceptionPermission]

    def get(self, request):
        orders = Order.objects.all()
        status_counts = list(orders.values("status").annotate(count=Count("id")).order_by("status"))
        payments = Payment.objects.filter(status=Payment.Status.SUCCESSFUL)
        popular = list(
            OrderItem.objects.values("food_name")
            .annotate(quantity=Sum("quantity"), sales=Sum("subtotal"))
            .order_by("-quantity")[:10]
        )
        return Response({
            "success": True,
            "orders": {"count": orders.count(), "by_status": status_counts},
            "sales": {"ordered_total": orders.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00"), "collected_total": payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")},
            "payments_by_method": list(payments.values("method").annotate(total=Sum("amount"), count=Count("id"))),
            "popular_items": popular,
        })


class ReleaseTableView(APIView):
    permission_classes = [ReceptionPermission]

    @transaction.atomic
    def post(self, request, table_id):
        from tables.models import Table
        table = get_object_or_404(Table.objects.select_for_update(), id=table_id)
        override = request.data.get("override", False)
        if not isinstance(override, bool):
            return Response(
                {"success": False, "message": "override must be a boolean."},
                status=400,
            )
        unresolved = table.orders.filter(status__in=[Order.Status.PENDING, Order.Status.RECEPTION_ACCEPTED, Order.Status.PREPARING, Order.Status.READY, Order.Status.SERVED]).exists()
        unpaid = table.orders.exclude(
            status__in=[Order.Status.REJECTED, Order.Status.CANCELLED]
        ).exclude(
            payments__status=Payment.Status.SUCCESSFUL
        ).exists()
        if (unresolved or unpaid) and not override:
            return Response({"success": False, "message": "Table has unresolved orders or unpaid balance."}, status=409)
        CustomerSession.objects.filter(table=table, is_active=True).update(is_active=False, ended_at=timezone.now())
        table.status = Table.Status.AVAILABLE
        table.save(update_fields=["status", "updated_at"])
        return Response({"success": True, "message": "Table released."})
