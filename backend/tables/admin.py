from django.contrib import admin

from .models import Table, TableQRCode
from .qr_service import generate_table_qr


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "name",
        "capacity",
        "status",
        "is_active",
    )

    list_filter = (
        "status",
        "is_active",
    )

    search_fields = (
        "number",
        "name",
    )


@admin.register(TableQRCode)
class TableQRCodeAdmin(admin.ModelAdmin):
    list_display = (
        "table",
        "token",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "table__number",
        "token",
    )

    readonly_fields = (
        "token",
        "qr_image",
        "created_at",
        "updated_at",
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if not obj.qr_image:
            generate_table_qr(obj)