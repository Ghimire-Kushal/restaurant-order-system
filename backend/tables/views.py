from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from .models import CustomerSession, TableQRCode


CUSTOMER_SESSION_COOKIE = "customer_session_token"


def table_qr_scan(request, token):
    """
    Validate a table QR code and create/reuse
    a customer session for this device.
    """

    qr_code = get_object_or_404(
        TableQRCode.objects.select_related("table"),
        token=token,
        is_active=True,
    )

    table = qr_code.table

    # Check whether the table itself is active
    if not table.is_active or table.status == table.Status.INACTIVE:
        return JsonResponse(
            {
                "success": False,
                "message": "This table is currently inactive.",
            },
            status=403,
        )

    # Try to get an existing session from this device/browser
    existing_token = request.COOKIES.get(
        CUSTOMER_SESSION_COOKIE
    )

    customer_session = None

    if existing_token:
        try:
            customer_session = (
                CustomerSession.objects
                .select_related("table")
                .get(
                    session_token=existing_token,
                    is_active=True,
                )
            )

            # Session must belong to the same table
            if customer_session.table_id != table.id:
                customer_session = None

        except CustomerSession.DoesNotExist:
            customer_session = None

        except ValueError:
            customer_session = None

    # No valid existing session → create a new one
    if customer_session is None:
        customer_session = CustomerSession.objects.create(
            table=table
        )

    response = JsonResponse(
        {
            "success": True,
            "message": "Table QR is valid.",
            "session": {
                "id": customer_session.id,
                "session_token": str(
                    customer_session.session_token
                ),
                "is_active": customer_session.is_active,
            },
            "table": {
                "id": table.id,
                "number": table.number,
                "name": table.name,
                "capacity": table.capacity,
                "status": table.status,
            },
        }
    )

    # Store session token in this device's browser
    response.set_cookie(
        key=CUSTOMER_SESSION_COOKIE,
        value=str(customer_session.session_token),
        max_age=60 * 60 * 6,
        httponly=True,
        secure=False,
        samesite="Lax",
    )

    return response
