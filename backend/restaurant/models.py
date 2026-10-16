from django.db import models


class Restaurant(models.Model):
    name = models.CharField(max_length=200)

    logo = models.ImageField(
        upload_to="restaurant/logo/",
        blank=True,
        null=True,
    )

    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    opening_time = models.TimeField(
        blank=True,
        null=True,
    )

    closing_time = models.TimeField(
        blank=True,
        null=True,
    )

    is_open = models.BooleanField(default=True)

    currency = models.CharField(
        max_length=10,
        default="NPR",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class RestaurantSetting(models.Model):
    restaurant = models.OneToOneField(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="settings",
    )

    # Tax / VAT
    tax_enabled = models.BooleanField(default=False)

    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    # Service charge
    service_charge_enabled = models.BooleanField(
        default=False,
    )

    SERVICE_CHARGE_PERCENTAGE = "PERCENTAGE"
    SERVICE_CHARGE_FIXED = "FIXED"

    SERVICE_CHARGE_TYPE_CHOICES = [
        (
            SERVICE_CHARGE_PERCENTAGE,
            "Percentage",
        ),
        (
            SERVICE_CHARGE_FIXED,
            "Fixed Amount",
        ),
    ]

    service_charge_type = models.CharField(
        max_length=20,
        choices=SERVICE_CHARGE_TYPE_CHOICES,
        default=SERVICE_CHARGE_PERCENTAGE,
    )

    service_charge_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    # Reception discount limit
    max_reception_discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    # Reviews
    allow_private_reviews = models.BooleanField(
        default=True,
    )

    allow_public_reviews = models.BooleanField(
        default=False,
    )

    # Invoice
    invoice_footer = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Settings - {self.restaurant.name}"