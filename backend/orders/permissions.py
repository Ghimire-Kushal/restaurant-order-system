from rest_framework.permissions import BasePermission


class HasRestaurantRole(BasePermission):
    allowed_roles = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.role in self.allowed_roles)
        )


class ReceptionPermission(HasRestaurantRole):
    allowed_roles = ("RECEPTION", "ADMIN")


class KitchenPermission(HasRestaurantRole):
    allowed_roles = ("KITCHEN_MANAGER", "ADMIN")
