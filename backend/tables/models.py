import uuid

from django.db import models


class Table(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        OCCUPIED = "OCCUPIED", "Occupied"
        INACTIVE = "INACTIVE", "Inactive"

    number = models.PositiveIntegerField(unique=True)

    name = models.CharField(
        max_length=100,
        blank=True,
    )

    capacity = models.PositiveIntegerField(default=2)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.name:
            return f"Table {self.number} - {self.name}"

        return f"Table {self.number}"


class TableQRCode(models.Model):
    table = models.OneToOneField(
        Table,
        on_delete=models.CASCADE,
        related_name="qr_code",
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    qr_image = models.ImageField(
        upload_to="table_qr/",
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"QR - Table {self.table.number}"


class CustomerSession(models.Model):
    table = models.ForeignKey(
        Table,
        on_delete=models.PROTECT,
        related_name="customer_sessions",
    )

    session_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    is_active = models.BooleanField(default=True)

    started_at = models.DateTimeField(
        auto_now_add=True,
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return (
            f"Session {self.session_token} - "
            f"Table {self.table.number}"
        )