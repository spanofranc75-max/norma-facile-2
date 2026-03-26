"""
Block Notes PDF — Foglio per schizzi a mano (rilievi / officina).
Landscape A4 con logo aziendale, dati cliente, QR code, griglia a quadretti.
"""
import io
import base64
import qrcode
from datetime import datetime, timezone
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


GRID_COLOR = HexColor("#D0D5DD")
HEADER_BG = HexColor("#1E3A5F")
ACCENT = HexColor("#0055FF")
LIGHT_TEXT = HexColor("#667085")
PAGE_W, PAGE_H = landscape(A4)
MARGIN = 12 * mm


def _make_qr(data: str, size: int = 140) -> ImageReader:
    """Generate a QR code as an ImageReader for ReportLab."""
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def _decode_logo(logo_url: str) -> ImageReader | None:
    """Decode a base64 data URL into an ImageReader."""
    if not logo_url or not logo_url.startswith("data:image"):
        return None
    try:
        header, b64data = logo_url.split(",", 1)
        raw = base64.b64decode(b64data)
        buf = io.BytesIO(raw)
        return ImageReader(buf)
    except Exception:
        return None


def generate_block_notes(
    commessa: dict | None,
    client: dict | None,
    company: dict,
    app_url: str,
) -> bytes:
    """Generate a branded Block Notes PDF (landscape A4) for hand sketches."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(A4))
    c.setTitle("Block Notes — Schizzi Rilievo")

    # ─── Header background bar ──────────────────────────
    header_h = 28 * mm
    c.setFillColor(HEADER_BG)
    c.rect(0, PAGE_H - header_h, PAGE_W, header_h, fill=1, stroke=0)

    # ─── Logo ────────────────────────────────────────────
    logo_img = _decode_logo(company.get("logo_url", ""))
    logo_x = MARGIN
    logo_y = PAGE_H - header_h + 3 * mm
    if logo_img:
        try:
            c.drawImage(logo_img, logo_x, logo_y, width=22 * mm, height=22 * mm, preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
        text_x = logo_x + 25 * mm
    else:
        text_x = logo_x

    # ─── Company name in header ──────────────────────────
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(text_x, PAGE_H - 12 * mm, company.get("business_name", ""))
    c.setFont("Helvetica", 7)
    cert = company.get("certificato_en1090_numero", "")
    ente = company.get("ente_certificatore", "")
    if cert:
        c.drawString(text_x, PAGE_H - 17 * mm, f"Certificazione EN 1090-1 EXC3 — {ente} {cert}")
    addr_parts = [company.get("address", ""), company.get("cap", ""), company.get("city", ""), company.get("province", "")]
    addr_line = " ".join(p for p in addr_parts if p)
    if addr_line:
        c.drawString(text_x, PAGE_H - 22 * mm, addr_line)

    # ─── QR Code (top right in header) ───────────────────
    qr_size = 22 * mm
    qr_x = PAGE_W - MARGIN - qr_size
    qr_y = PAGE_H - header_h + 3 * mm
    if commessa:
        commessa_id = commessa.get("commessa_id", "")
        qr_data = f"{app_url}/commesse/{commessa_id}"
        qr_img = _make_qr(qr_data)
        # White background for QR
        c.setFillColor(white)
        c.roundRect(qr_x - 1 * mm, qr_y - 1 * mm, qr_size + 2 * mm, qr_size + 2 * mm, 2, fill=1, stroke=0)
        c.drawImage(qr_img, qr_x, qr_y, width=qr_size, height=qr_size)

    # ─── Sub-header: Client + Commessa info ──────────────
    subheader_y = PAGE_H - header_h - 14 * mm
    c.setFillColor(HexColor("#F8FAFC"))
    c.rect(0, subheader_y - 2 * mm, PAGE_W, 16 * mm, fill=1, stroke=0)
    c.setStrokeColor(GRID_COLOR)
    c.line(0, subheader_y - 2 * mm, PAGE_W, subheader_y - 2 * mm)

    col1_x = MARGIN
    col2_x = PAGE_W / 2

    # Left column: Client data
    c.setFillColor(LIGHT_TEXT)
    c.setFont("Helvetica", 6)
    c.drawString(col1_x, subheader_y + 9 * mm, "CLIENTE")
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 9)
    client_name = ""
    if client:
        client_name = client.get("business_name") or client.get("ragione_sociale") or ""
    elif commessa:
        client_name = commessa.get("client_name", "")
    c.drawString(col1_x, subheader_y + 4 * mm, client_name or "—")
    c.setFont("Helvetica", 7)
    c.setFillColor(LIGHT_TEXT)
    if client:
        client_addr = " ".join(p for p in [client.get("address", ""), client.get("city", ""), client.get("province", "")] if p)
        c.drawString(col1_x, subheader_y, client_addr or "")
        piva = client.get("partita_iva", "")
        if piva:
            c.drawString(col1_x, subheader_y - 4 * mm, f"P.IVA: {piva}")

    # Right column: Commessa data
    c.setFillColor(LIGHT_TEXT)
    c.setFont("Helvetica", 6)
    c.drawString(col2_x, subheader_y + 9 * mm, "COMMESSA")
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 9)
    if commessa:
        c.drawString(col2_x, subheader_y + 4 * mm, commessa.get("numero", ""))
        c.setFont("Helvetica", 7)
        c.setFillColor(LIGHT_TEXT)
        c.drawString(col2_x, subheader_y, commessa.get("title", "")[:60])
    else:
        c.drawString(col2_x, subheader_y + 4 * mm, "Foglio generico")

    # Date on right
    c.setFillColor(LIGHT_TEXT)
    c.setFont("Helvetica", 7)
    date_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    c.drawRightString(PAGE_W - MARGIN, subheader_y + 4 * mm, f"Data: {date_str}")

    # ─── Grid area ───────────────────────────────────────
    grid_top = subheader_y - 5 * mm
    grid_bottom = MARGIN + 12 * mm
    grid_left = MARGIN
    grid_right = PAGE_W - MARGIN

    cell = 5 * mm  # 5mm grid squares

    c.setStrokeColor(GRID_COLOR)
    c.setLineWidth(0.25)

    # Vertical lines
    x = grid_left
    while x <= grid_right:
        c.line(x, grid_bottom, x, grid_top)
        x += cell

    # Horizontal lines
    y = grid_bottom
    while y <= grid_top:
        c.line(grid_left, y, grid_right, y)
        y += cell

    # Border around grid
    c.setStrokeColor(HexColor("#98A2B3"))
    c.setLineWidth(0.5)
    c.rect(grid_left, grid_bottom, grid_right - grid_left, grid_top - grid_bottom, fill=0, stroke=1)

    # ─── Footer ──────────────────────────────────────────
    footer_y = 4 * mm
    c.setFillColor(HEADER_BG)
    c.rect(0, 0, PAGE_W, MARGIN, fill=1, stroke=0)

    c.setFillColor(HexColor("#B0BEC5"))
    c.setFont("Helvetica", 5.5)

    footer_parts = []
    bn = company.get("business_name", "")
    if bn:
        footer_parts.append(bn)
    if addr_line:
        footer_parts.append(addr_line)
    tel = company.get("phone") or company.get("telefono", "")
    if tel:
        footer_parts.append(f"Tel. {tel}")
    piva = company.get("partita_iva", "")
    if piva:
        footer_parts.append(f"P.IVA: {piva}")
    email = company.get("email", "")
    if email:
        footer_parts.append(email)
    website = company.get("website", "")
    if website:
        footer_parts.append(website)

    footer_line = "  •  ".join(footer_parts)
    c.drawCentredString(PAGE_W / 2, footer_y, footer_line)

    c.showPage()
    c.save()
    return buf.getvalue()
