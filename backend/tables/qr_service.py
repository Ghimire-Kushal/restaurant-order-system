from io import BytesIO

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile


def generate_table_qr(qr_code):
    qr_url = f"{settings.SITE_URL}/table/{qr_code.token}/"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )

    qr.add_data(qr_url)
    qr.make(fit=True)

    image = qr.make_image()

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    filename = f"table-{qr_code.table.number}-qr.png"

    qr_code.qr_image.save(
        filename,
        ContentFile(buffer.getvalue()),
        save=False,
    )

    qr_code.save(
        update_fields=["qr_image", "updated_at"]
    )