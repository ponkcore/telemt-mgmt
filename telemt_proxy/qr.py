"""QR code generation for proxy links.

Generates PNG QR code images for ``tg://proxy`` links using the
``qrcode`` library with PIL backend. The QR code is sent to users
alongside the text link so they can scan it on one device and apply
the proxy on another.

No module-level side effects (INV-EMBED).
"""

from __future__ import annotations

import io

import qrcode
from qrcode.image.pil import PilImage


def generate_qr(link: str) -> bytes:
    """Generate a PNG QR code image for the given proxy link.

    Uses the ``qrcode`` library to create a QR code encoding the link
    string, then renders it to PNG bytes via PIL.

    Args:
        link: The proxy link string (e.g.
            ``tg://proxy?server=...&port=...&secret=...``).

    Returns:
        PNG image data as bytes. The first bytes are the PNG magic
        number ``\\x89PNG\\r\\n\\x1a\\n``.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(link)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    # make_image() returns PilImage when PIL is installed (our only path).
    # The isinstance check narrows the type so mypy sees format= on save().
    assert isinstance(img, PilImage)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
