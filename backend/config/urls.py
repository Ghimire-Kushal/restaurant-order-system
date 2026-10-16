from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from tables.views import table_qr_scan


urlpatterns = [
    path("", TemplateView.as_view(template_name="restaurant/home.html"), name="home"),
    path("table/<uuid:token>/", TemplateView.as_view(template_name="restaurant/app.html"), {"mode": "customer"}, name="customer-app"),
    path("staff/reception/", TemplateView.as_view(template_name="restaurant/app.html"), {"mode": "reception"}, name="reception-app"),
    path("staff/kitchen/", TemplateView.as_view(template_name="restaurant/app.html"), {"mode": "kitchen"}, name="kitchen-app"),
    # ============================================================
    # ADMIN
    # ============================================================

    path(
        "admin/",
        admin.site.urls,
    ),

    # ============================================================
    # TABLE QR SCAN
    # ============================================================

    path(
        "table/scan/<uuid:token>/",
        table_qr_scan,
        name="table-qr-scan",
    ),

    # ============================================================
    # MENU API
    # ============================================================

    path(
        "api/menu/",
        include("menu.urls"),
    ),

    # ============================================================
    # ORDERS / CART API
    # ============================================================

    path(
        "api/cart/",
        include("orders.urls"),
    ),
]


# ================================================================
# MEDIA FILES - DEVELOPMENT ONLY
# ================================================================

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
