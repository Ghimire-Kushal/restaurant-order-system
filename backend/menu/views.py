from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from tables.models import CustomerSession

from .models import MenuSection
from .serializers import MenuSectionSerializer


@api_view(["GET"])
def customer_menu(request, session_token):
    """
    Return the active customer menu for a valid customer session.
    """

    try:
        session = (
            CustomerSession.objects
            .select_related("table")
            .get(
                session_token=session_token,
                is_active=True,
            )
        )
    except CustomerSession.DoesNotExist:
        return Response(
            {
                "success": False,
                "message": "Invalid or expired customer session.",
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if not session.table.is_active:
        return Response(
            {
                "success": False,
                "message": "This table is currently inactive.",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    sections = (
        MenuSection.objects
        .filter(is_active=True)
        .prefetch_related("categories")
        .order_by("display_order", "name")
    )

    serializer = MenuSectionSerializer(
        sections,
        many=True,
        context={"request": request},
    )

    return Response(
        {
            "success": True,
            "session": {
                "id": session.id,
                "session_token": str(session.session_token),
                "table": {
                    "id": session.table.id,
                    "number": session.table.number,
                    "name": session.table.name,
                    "capacity": session.table.capacity,
                    "status": session.table.status,
                },
            },
            "menu": serializer.data,
        }
    )