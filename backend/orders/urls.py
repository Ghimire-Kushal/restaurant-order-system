from django.urls import path

from .views import (
    CartDetailView,
    AddToCartView,
    UpdateCartItemView,
    RemoveCartItemView,
    ClearCartView,
    CreateOrderView,
    CustomerOrderDetailView,
    ReceptionOrderListView,
    ReceptionOrderActionView,
    KitchenOrderListView,
    KitchenOrderActionView,
    RecordPaymentView,
    ReleaseTableView,
    ApplyDiscountView,
    ReceiptView,
    ReportsView,
)


urlpatterns = [

    # ============================================================
    # RECEPTION
    # ============================================================

    path(
        "reception/",
        ReceptionOrderListView.as_view(),
        name="reception-order-list",
    ),
    path("reception/<str:order_number>/payment/", RecordPaymentView.as_view(), name="record-payment"),
    path("reception/<str:order_number>/discount/", ApplyDiscountView.as_view(), name="apply-discount"),
    path("reception/<str:order_number>/receipt/", ReceiptView.as_view(), name="receipt"),
    path("reports/", ReportsView.as_view(), name="reports"),
    path("reception/<str:order_number>/<str:action>/", ReceptionOrderActionView.as_view(), name="reception-order-action"),
    path("kitchen/", KitchenOrderListView.as_view(), name="kitchen-order-list"),
    path("kitchen/<str:order_number>/<str:action>/", KitchenOrderActionView.as_view(), name="kitchen-order-action"),
    path("reception/table/<int:table_id>/release/", ReleaseTableView.as_view(), name="release-table"),

    # ============================================================
    # CART
    # ============================================================

    # Get current cart
    path(
        "<uuid:session_token>/",
        CartDetailView.as_view(),
        name="cart-detail",
    ),

    # Add item to cart
    path(
        "<uuid:session_token>/add/",
        AddToCartView.as_view(),
        name="cart-add",
    ),

    # Update cart item quantity
    path(
        "<uuid:session_token>/item/<int:item_id>/",
        UpdateCartItemView.as_view(),
        name="cart-item-update",
    ),

    # Remove cart item
    path(
        "<uuid:session_token>/item/<int:item_id>/remove/",
        RemoveCartItemView.as_view(),
        name="cart-item-remove",
    ),

    # Clear cart
    path(
        "<uuid:session_token>/clear/",
        ClearCartView.as_view(),
        name="cart-clear",
    ),

    # ============================================================
    # ORDER
    # ============================================================

    # Submit cart → create order
    path(
        "<uuid:session_token>/submit/",
        CreateOrderView.as_view(),
        name="create-order",
    ),

    # Customer order detail
    path(
        "<uuid:session_token>/order/<str:order_number>/",
        CustomerOrderDetailView.as_view(),
        name="customer-order-detail",
    ),
]
