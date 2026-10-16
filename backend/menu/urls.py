from django.urls import path

from .views import customer_menu


urlpatterns = [
    path(
        "<uuid:session_token>/",
        customer_menu,
        name="customer_menu",
    ),
]