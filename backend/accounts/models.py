from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        RECEPTION = "RECEPTION", "Reception"
        KITCHEN_MANAGER = "KITCHEN_MANAGER", "Kitchen Manager"

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.RECEPTION,
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"