"""QR Code generation for commesse/work orders."""
import io
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from core.database import db
from core.security import get_current_user, tenant_match
from core.config import settings
import qrcode

router = APIRouter(prefix="/qrcode", tags=["qrcode"])
logger = logging.getLogger(__name__)


@router.get("/commessa/{commessa_id}")
async def generate_commessa_qr(commessa_id: str, user: dict = Depends(get_current_user)):
    """Generate a QR code PNG that links to the commessa page."""
    # Verify commessa exists (scoped to user)
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "numero": 1, "cliente_nome": 1},
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    # Build the URL the QR should point to
    url = f"{settings.domain_url}/commesse/{commessa_id}"

    # Generate QR
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=qr_commessa_{commessa_id}.png"},
    )


@router.get("/commessa/{commessa_id}/data")
async def get_commessa_qr_data(commessa_id: str, user: dict = Depends(get_current_user)):
    """Return the URL and metadata for a commessa QR code (for frontend embedding)."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "numero": 1, "cliente_nome": 1, "oggetto": 1},
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    url = f"{settings.domain_url}/commesse/{commessa_id}"

    return {
        "commessa_id": commessa_id,
        "numero": commessa.get("numero", ""),
        "cliente_nome": commessa.get("cliente_nome", ""),
        "oggetto": commessa.get("oggetto", ""),
        "qr_url": url,
        "qr_image_endpoint": f"/api/qrcode/commessa/{commessa_id}",
    }
