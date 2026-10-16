from django.db import models


class MenuSection(models.Model):
    """
    Top-level menu section.

    Examples:
    - Veg
    - Non-Veg
    """

    name = models.CharField(
        max_length=50,
        unique=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "name",
        ]

    def __str__(self):
        return self.name


class Category(models.Model):
    """
    Category inside a menu section.

    Examples:
    Veg:
        - Momo
        - Chowmein
        - Pizza

    Non-Veg:
        - Chicken Momo
        - Chicken Chowmein
        - Chicken Pizza
    """

    section = models.ForeignKey(
        MenuSection,
        on_delete=models.PROTECT,
        related_name="categories",
    )

    name = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "section__display_order",
            "display_order",
            "name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["section", "name"],
                name="unique_category_per_section",
            ),
        ]

        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.section.name} - {self.name}"


class SpiceLevel(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
    )

    description = models.CharField(
        max_length=255,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "display_order",
            "name",
        ]

    def __str__(self):
        return self.name


class Addon(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "name",
        ]

    def __str__(self):
        return f"{self.name} - {self.price}"


class FoodItem(models.Model):
    name = models.CharField(
        max_length=150,
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="food_items",
    )

    description = models.TextField(
        blank=True,
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    # Controlled by Kitchen Manager
    is_available = models.BooleanField(
        default=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    spice_levels = models.ManyToManyField(
        SpiceLevel,
        blank=True,
        related_name="food_items",
    )

    addons = models.ManyToManyField(
        Addon,
        blank=True,
        related_name="food_items",
    )

    allow_special_instruction = models.BooleanField(
        default=True,
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "category__section__display_order",
            "category__display_order",
            "display_order",
            "name",
        ]

    def __str__(self):
        return self.name


class FoodImage(models.Model):
    food_item = models.ForeignKey(
        FoodItem,
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = models.ImageField(
        upload_to="food/",
    )

    alt_text = models.CharField(
        max_length=255,
        blank=True,
    )

    is_primary = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.food_item.name} image"