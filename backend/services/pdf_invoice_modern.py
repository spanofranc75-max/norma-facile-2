"""Professional Invoice PDF generator — ReportLab, layout NormaFacile 2.0.

Layout:
  - Logo a sinistra + dati azienda a destra
  - Linea separatrice blu sottile
  - Titolo documento centrato grande
  - Box DATA / TIPO sfondo grigio chiaro affiancati
  - Box cliente con bordo sinistro blu ("Spett.le")
  - Tabella articoli: header navy scuro, 5 colonne
  - Totali a destra con box navy per TOTALE
  - Coordinate bancarie con bordo sinistro blu
  - Scadenza pagamenti con bordo sinistro blu
  - Footer: generato da / data / pagina
  - Footer certificazioni EN 1090-1 EXC3

Encoding: UTF-8 diretto (€, \u2022, \u00e0, \u00e8, ecc.)
"""
from io import BytesIO
import base64
import logging
from datetime import datetime, timezone

from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
    KeepTogether,
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════
# Registrazione font TTF (Liberation Sans — supporto Unicode completo)
# ══════════════════════════════════════════════════════════════════
_FONT_DIR = "/usr/share/fonts/truetype/liberation"
_FONT_NAME = "LiberationSans"
_FONT_BOLD = "LiberationSans-Bold"

_fonts_registered = False

def _register_fonts():
    global _fonts_registered
    if _fonts_registered:
        return
    try:
        regular = os.path.join(_FONT_DIR, "LiberationSans-Regular.ttf")
        bold = os.path.join(_FONT_DIR, "LiberationSans-Bold.ttf")
        italic = os.path.join(_FONT_DIR, "LiberationSans-Italic.ttf")
        bold_italic = os.path.join(_FONT_DIR, "LiberationSans-BoldItalic.ttf")
        if os.path.exists(regular):
            pdfmetrics.registerFont(TTFont(_FONT_NAME, regular))
            pdfmetrics.registerFont(TTFont(_FONT_BOLD, bold))
            pdfmetrics.registerFont(TTFont("LiberationSans-Italic", italic))
            pdfmetrics.registerFont(TTFont("LiberationSans-BoldItalic", bold_italic))
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            registerFontFamily(
                _FONT_NAME,
                normal=_FONT_NAME,
                bold=_FONT_BOLD,
                italic="LiberationSans-Italic",
                boldItalic="LiberationSans-BoldItalic",
            )
            _fonts_registered = True
            logger.info("Font LiberationSans registrato con successo")
        else:
            logger.warning("LiberationSans non trovato, uso Helvetica")
    except Exception as e:
        logger.warning(f"Impossibile registrare font TTF: {e}")

_register_fonts()

def _fn():
    """Font name normale."""
    return _FONT_NAME if _fonts_registered else "Helvetica"

def _fb():
    """Font name bold."""
    return _FONT_BOLD if _fonts_registered else "Helvetica-Bold"

# ══════════════════════════════════════════════════════════════════
# Colori
# ══════════════════════════════════════════════════════════════════
NAVY = HexColor("#0F172A")
BLUE = HexColor("#2563EB")
GREY_BG = HexColor("#F1F5F9")
GREY_TEXT = HexColor("#64748B")
GREY_BORDER = HexColor("#CBD5E1")
DARK_TEXT = HexColor("#1a1a2e")
WHITE = white

# ══════════════════════════════════════════════════════════════════
# Margini (in mm)
# ══════════════════════════════════════════════════════════════════
LEFT_MARGIN = 16 * mm
RIGHT_MARGIN = 16 * mm
TOP_MARGIN = 14 * mm
BOTTOM_MARGIN = 22 * mm

# ══════════════════════════════════════════════════════════════════
# Stili paragrafo
# ══════════════════════════════════════════════════════════════════
STYLE_COMPANY_NAME = ParagraphStyle(
    "CompanyName", fontName=_fb(), fontSize=13, leading=16,
    textColor=DARK_TEXT, alignment=TA_RIGHT,
)
STYLE_COMPANY_DETAIL = ParagraphStyle(
    "CompanyDetail", fontName=_fn(), fontSize=7.5, leading=11,
    textColor=GREY_TEXT, alignment=TA_RIGHT,
)
STYLE_DOC_TITLE = ParagraphStyle(
    "DocTitle", fontName=_fb(), fontSize=20, leading=24,
    textColor=NAVY, alignment=TA_CENTER,
)
STYLE_META_LABEL = ParagraphStyle(
    "MetaLabel", fontName=_fb(), fontSize=7, leading=10,
    textColor=GREY_TEXT, alignment=TA_CENTER,
)
STYLE_META_VALUE = ParagraphStyle(
    "MetaValue", fontName=_fb(), fontSize=9, leading=12,
    textColor=DARK_TEXT, alignment=TA_CENTER,
)
STYLE_CLIENT_LABEL = ParagraphStyle(
    "ClientLabel", fontName=_fn(), fontSize=7.5, leading=10,
    textColor=GREY_TEXT,
)
STYLE_CLIENT_NAME = ParagraphStyle(
    "ClientName", fontName=_fb(), fontSize=11, leading=14,
    textColor=DARK_TEXT,
)
STYLE_CLIENT_DETAIL = ParagraphStyle(
    "ClientDetail", fontName=_fn(), fontSize=8, leading=11.5,
    textColor=HexColor("#475569"),
)
STYLE_TH = ParagraphStyle(
    "TableHeader", fontName=_fb(), fontSize=7, leading=9,
    textColor=WHITE,
)
STYLE_TH_R = ParagraphStyle(
    "TableHeaderR", fontName=_fb(), fontSize=7, leading=9,
    textColor=WHITE, alignment=TA_RIGHT,
)
STYLE_TH_C = ParagraphStyle(
    "TableHeaderC", fontName=_fb(), fontSize=7, leading=9,
    textColor=WHITE, alignment=TA_CENTER,
)
STYLE_TD = ParagraphStyle(
    "TableCell", fontName=_fn(), fontSize=8, leading=11,
    textColor=DARK_TEXT,
)
STYLE_TD_R = ParagraphStyle(
    "TableCellR", fontName=_fn(), fontSize=8, leading=11,
    textColor=DARK_TEXT, alignment=TA_RIGHT,
)
STYLE_TD_C = ParagraphStyle(
    "TableCellC", fontName=_fn(), fontSize=8, leading=11,
    textColor=DARK_TEXT, alignment=TA_CENTER,
)
STYLE_TD_BOLD_R = ParagraphStyle(
    "TableCellBoldR", fontName=_fb(), fontSize=8, leading=11,
    textColor=DARK_TEXT, alignment=TA_RIGHT,
)
STYLE_TOTALS_LABEL = ParagraphStyle(
    "TotalsLabel", fontName=_fn(), fontSize=8.5, leading=12,
    textColor=GREY_TEXT, alignment=TA_RIGHT,
)
STYLE_TOTALS_VALUE = ParagraphStyle(
    "TotalsValue", fontName=_fb(), fontSize=8.5, leading=12,
    textColor=DARK_TEXT, alignment=TA_RIGHT,
)
STYLE_GRAND_LABEL = ParagraphStyle(
    "GrandLabel", fontName=_fb(), fontSize=11, leading=14,
    textColor=WHITE, alignment=TA_RIGHT,
)
STYLE_GRAND_VALUE = ParagraphStyle(
    "GrandValue", fontName=_fb(), fontSize=14, leading=17,
    textColor=WHITE, alignment=TA_RIGHT,
)
STYLE_SECTION_TITLE = ParagraphStyle(
    "SectionTitle", fontName=_fb(), fontSize=7.5, leading=10,
    textColor=GREY_TEXT, spaceAfter=2 * mm,
)
STYLE_BANK_LINE = ParagraphStyle(
    "BankLine", fontName=_fn(), fontSize=8, leading=11.5,
    textColor=HexColor("#475569"),
)
STYLE_FOOTER = ParagraphStyle(
    "Footer", fontName=_fn(), fontSize=7, leading=9,
    textColor=GREY_TEXT, alignment=TA_CENTER,
)
STYLE_CERT_FOOTER = ParagraphStyle(
    "CertFooter", fontName=_fb(), fontSize=7, leading=9,
    textColor=GREY_TEXT, alignment=TA_CENTER,
)
STYLE_NOTES = ParagraphStyle(
    "Notes", fontName=_fn(), fontSize=7.5, leading=10.5,
    textColor=HexColor("#475569"),
)
STYLE_NOTES_TITLE = ParagraphStyle(
    "NotesTitle", fontName=_fb(), fontSize=7.5, leading=10,
    textColor=GREY_TEXT,
)
# Stili per pagina condizioni
STYLE_COND_TITLE = ParagraphStyle(
    "CondTitle", fontName=_fb(), fontSize=11, leading=14,
    textColor=DARK_TEXT, alignment=TA_CENTER, spaceAfter=4 * mm,
)
STYLE_COND_TEXT = ParagraphStyle(
    "CondText", fontName=_fn(), fontSize=7.5, leading=10.5,
    textColor=DARK_TEXT, alignment=TA_LEFT,
)
STYLE_COND_LEGAL = ParagraphStyle(
    "CondLegal", fontName=_fn(), fontSize=7, leading=9.5,
    textColor=HexColor("#475569"),
)

# ══════════════════════════════════════════════════════════════════
# Tipo documento
# ══════════════════════════════════════════════════════════════════
DOC_TYPE_NAMES = {
    "FT": "FATTURA",
    "PRV": "PREVENTIVO",
    "DDT": "DOCUMENTO DI TRASPORTO",
    "NC": "NOTA DI CREDITO",
}

PAYMENT_METHOD_NAMES = {
    "bonifico": "Bonifico Bancario",
    "contanti": "Contanti",
    "carta": "Carta di Credito",
    "assegno": "Assegno",
    "riba": "RiBa",
    "altro": "Altro",
}


# ══════════════════════════════════════════════════════════════════
# Utility
# ══════════════════════════════════════════════════════════════════
def _fmt(n) -> str:
    """Formatta numero stile italiano: 1.234,56"""
    try:
        val = float(n or 0)
    except (ValueError, TypeError):
        return "0,00"
    s = f"{val:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _s(val) -> str:
    """Safe string."""
    return str(val or "").strip()


def _date(d) -> str:
    """Formatta data in dd/mm/yyyy."""
    if isinstance(d, datetime):
        return d.strftime("%d/%m/%Y")
    if isinstance(d, str):
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",
                     "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
            try:
                return datetime.strptime(d.replace("Z", "+00:00").split("+")[0].split("Z")[0], fmt.split("%z")[0]).strftime("%d/%m/%Y")
            except (ValueError, IndexError):
                continue
        # fallback: try fromisoformat
        try:
            return datetime.fromisoformat(d.replace("Z", "+00:00")).strftime("%d/%m/%Y")
        except Exception:
            return d
    return ""


def _decode_logo(logo_url: str):
    """Decode base64 data URI to BytesIO for ReportLab Image."""
    if not logo_url:
        return None
    try:
        if logo_url.startswith("data:image"):
            header, b64data = logo_url.split(",", 1)
            img_bytes = base64.b64decode(b64data)
            buf = BytesIO(img_bytes)
            buf.seek(0)
            return buf
        # Se \u00e8 un URL HTTP, ReportLab pu\u00f2 gestirlo direttamente
        if logo_url.startswith("http"):
            return logo_url
    except Exception as e:
        logger.warning(f"Impossibile decodificare logo: {e}")
    return None


class _BlueBorderBox:
    """Flowable: box con bordo sinistro blu e padding interno."""

    def __init__(self, content_flowables, border_color=BLUE, border_width=2.5,
                 padding=8, bg_color=None, available_width=None):
        self.content = content_flowables
        self.border_color = border_color
        self.border_width = border_width
        self.padding = padding
        self.bg_color = bg_color
        self._available_width = available_width

    def wrap(self, available_width, available_height):
        self._available_width = self._available_width or available_width
        inner_w = self._available_width - self.padding * 2 - self.border_width
        self._content_heights = []
        total_h = 0
        for f in self.content:
            w, h = f.wrap(inner_w, available_height - total_h)
            self._content_heights.append(h)
            total_h += h
        self._total_h = total_h + self.padding * 2
        return self._available_width, self._total_h

    def draw(self, canvas, doc_unused=None):
        # Non usato direttamente; usiamo Table per simulare
        pass


# ══════════════════════════════════════════════════════════════════
# Generatore principale
# ══════════════════════════════════════════════════════════════════
def generate_modern_invoice_pdf(invoice: dict, client: dict, company: dict) -> bytes:
    """Genera PDF fattura/preventivo professionale con ReportLab."""
    buf = BytesIO()
    co = company or {}
    cl = client or {}

    # ── Dati azienda ──
    company_name = _s(co.get("business_name"))
    addr = _s(co.get("address"))
    cap = _s(co.get("cap"))
    city = _s(co.get("city"))
    prov = _s(co.get("province"))
    addr_parts = [addr]
    loc_parts = [p for p in [cap, city, f"({prov})" if prov else ""] if p]
    if loc_parts:
        addr_parts.append(" ".join(loc_parts))
    addr_line = " - ".join([p for p in addr_parts if p])

    piva = _s(co.get("partita_iva"))
    cf = _s(co.get("codice_fiscale"))
    phone = _s(co.get("phone") or co.get("tel"))
    email = _s(co.get("email") or co.get("contact_email"))

    # ── Dati documento ──
    doc_type = invoice.get("document_type", "FT")
    doc_title = DOC_TYPE_NAMES.get(doc_type, "DOCUMENTO")
    doc_number = _s(invoice.get("document_number", ""))
    display_num = doc_number
    for prefix in ("FT-", "NC-", "PRV-"):
        display_num = display_num.replace(prefix, "")
    issue_date = _date(invoice.get("issue_date", ""))
    payment_label = invoice.get("payment_type_label") or invoice.get("payment_terms") or PAYMENT_METHOD_NAMES.get(
        invoice.get("payment_method", ""), invoice.get("payment_method", "")
    )

    # ── Dati cliente ──
    cl_name = _s(cl.get("business_name"))
    cl_addr = _s(cl.get("address"))
    cl_cap = _s(cl.get("cap"))
    cl_city = _s(cl.get("city"))
    cl_prov = _s(cl.get("province"))
    cl_loc_parts = [p for p in [cl_cap, cl_city, f"({cl_prov})" if cl_prov else ""] if p]
    cl_full = cl_addr
    if cl_loc_parts:
        cl_full += (" - " if cl_addr else "") + " ".join(cl_loc_parts)
    cl_piva = _s(cl.get("partita_iva"))
    cl_cf = _s(cl.get("codice_fiscale"))
    cl_sdi = _s(cl.get("codice_sdi"))
    cl_pec = _s(cl.get("pec"))

    # ── Page size ──
    page_w, page_h = A4
    usable_w = page_w - LEFT_MARGIN - RIGHT_MARGIN

    # Contatore pagine per footer
    page_info = {"total": 0}

    def _footer(canvas, doc):
        """Footer su ogni pagina."""
        canvas.saveState()
        page_info["total"] = max(page_info["total"], doc.page)
        # Linea sottile sopra footer
        y_line = BOTTOM_MARGIN - 4 * mm
        canvas.setStrokeColor(GREY_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(LEFT_MARGIN, y_line, page_w - RIGHT_MARGIN, y_line)

        # Riga 1: Generato da
        canvas.setFont(_fn(), 6.5)
        canvas.setFillColor(GREY_TEXT)
        y_text = y_line - 3.5 * mm
        canvas.drawCentredString(page_w / 2, y_text,
                                 f"Generato da {company_name} - NormaFacile")

        # Riga 2: Data generazione
        now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y alle %H:%M")
        y_text2 = y_text - 3 * mm
        canvas.drawCentredString(page_w / 2, y_text2,
                                 f"Documento generato il {now_str}")

        # Riga 3: Pagina
        y_text3 = y_text2 - 3 * mm
        canvas.drawCentredString(page_w / 2, y_text3,
                                 f"Pagina {doc.page}")

        # Riga 4: Certificazioni
        y_cert = y_text3 - 3.5 * mm
        canvas.setFont(_fb(), 6.5)
        canvas.drawCentredString(page_w / 2, y_cert,
                                 "Azienda Certificata EN 1090-1 EXC3 \u2022 ISO 3834-2 \u2022 Centro di Trasformazione Acciaio")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=LEFT_MARGIN, rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN, bottomMargin=BOTTOM_MARGIN,
    )

    elements = []

    # ══════════════════════════════════════════════════════════════
    # 1. HEADER: Logo a sinistra + Azienda a destra
    # ══════════════════════════════════════════════════════════════
    logo_src = _decode_logo(co.get("logo_url", ""))
    if logo_src:
        try:
            logo_img = Image(logo_src, width=150, height=50)
            logo_img.hAlign = "LEFT"
        except Exception:
            logo_img = Paragraph("", STYLE_TD)
    else:
        logo_img = Paragraph("", STYLE_TD)

    company_detail_lines = [addr_line]
    if piva:
        company_detail_lines.append(f"P.IVA {piva}")
    if cf:
        company_detail_lines.append(f"C.F. {cf}")
    if phone:
        company_detail_lines.append(f"Tel. {phone}")
    if email:
        company_detail_lines.append(email)

    header_data = [[
        logo_img,
        [
            Paragraph(company_name, STYLE_COMPANY_NAME),
            Paragraph("<br/>".join(company_detail_lines), STYLE_COMPANY_DETAIL),
        ]
    ]]
    header_table = Table(header_data, colWidths=[usable_w * 0.40, usable_w * 0.60])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 3 * mm))

    # ══════════════════════════════════════════════════════════════
    # 2. Linea separatrice blu sottile
    # ══════════════════════════════════════════════════════════════
    elements.append(HRFlowable(
        width="100%", thickness=1.5, color=BLUE,
        spaceBefore=1 * mm, spaceAfter=4 * mm,
    ))

    # ══════════════════════════════════════════════════════════════
    # 3. Titolo documento centrato grande
    # ══════════════════════════════════════════════════════════════
    elements.append(Paragraph(f"{doc_title} N. {display_num}", STYLE_DOC_TITLE))
    elements.append(Spacer(1, 4 * mm))

    # ══════════════════════════════════════════════════════════════
    # 4. Box DATA / TIPO affiancati con sfondo grigio chiaro
    # ══════════════════════════════════════════════════════════════
    tipo_label = doc_title.title()
    meta_data = [[
        [Paragraph("DATA DOCUMENTO", STYLE_META_LABEL),
         Paragraph(issue_date, STYLE_META_VALUE)],
        [Paragraph("TIPO", STYLE_META_LABEL),
         Paragraph(tipo_label, STYLE_META_VALUE)],
    ]]
    meta_table = Table(meta_data, colWidths=[usable_w * 0.50, usable_w * 0.50])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GREY_BG),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEAFTER", (0, 0), (0, -1), 0.5, GREY_BORDER),
        ("BOX", (0, 0), (-1, -1), 0.5, GREY_BORDER),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 4 * mm))

    # ══════════════════════════════════════════════════════════════
    # 5. Box cliente con bordo sinistro blu
    # ══════════════════════════════════════════════════════════════
    client_lines = []
    if cl_full:
        client_lines.append(cl_full)
    if cl_piva:
        client_lines.append(f"P.IVA {cl_piva}")
    if cl_cf:
        client_lines.append(f"C.F. {cl_cf}")
    if cl_sdi:
        client_lines.append(f"Cod. SDI: {cl_sdi}")
    if cl_pec:
        client_lines.append(f"PEC: {cl_pec}")

    client_content = [
        [Paragraph("Spett.le", STYLE_CLIENT_LABEL)],
        [Paragraph(cl_name, STYLE_CLIENT_NAME)],
        [Paragraph("<br/>".join(client_lines), STYLE_CLIENT_DETAIL)],
    ]
    client_table = Table(client_content, colWidths=[usable_w - 4 * mm])
    client_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (0, 0), 6),
        ("BOTTOMPADDING", (-1, -1), (-1, -1), 6),
        ("TOPPADDING", (0, 1), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -2), 1),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, BLUE),
    ]))
    elements.append(client_table)
    elements.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════════
    # 6. Tabella articoli
    # ══════════════════════════════════════════════════════════════
    lines = invoice.get("lines", [])

    # Header
    th_row = [
        Paragraph("DESCRIZIONE", STYLE_TH),
        Paragraph("Q.T\u00c0", STYLE_TH_C),
        Paragraph("PREZZO UNIT.", STYLE_TH_R),
        Paragraph("IVA", STYLE_TH_C),
        Paragraph("TOTALE", STYLE_TH_R),
    ]

    # Colonne: Descrizione 44%, Qty 10%, Prezzo 18%, IVA 10%, Totale 18%
    col_widths = [
        usable_w * 0.44,
        usable_w * 0.10,
        usable_w * 0.18,
        usable_w * 0.10,
        usable_w * 0.18,
    ]

    table_data = [th_row]
    for ln in lines:
        desc = _s(ln.get("description") or "").replace("\n", "<br/>")
        qty = _fmt(ln.get("quantity", 0))
        price = _fmt(ln.get("unit_price", 0))
        vat = _s(str(ln.get("vat_rate", "22")))
        total = _fmt(ln.get("line_total", 0))

        table_data.append([
            Paragraph(desc, STYLE_TD),
            Paragraph(qty, STYLE_TD_C),
            Paragraph(f"\u20ac {price}", STYLE_TD_R),
            Paragraph(f"{vat}%", STYLE_TD_C),
            Paragraph(f"\u20ac {total}", STYLE_TD_BOLD_R),
        ])

    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        # Header navy
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), _fb()),
        # Padding
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        # Bordi righe
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, NAVY),
        ("LINEBELOW", (0, -1), (-1, -1), 1.5, GREY_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    # Bordi sottili tra righe body
    for i in range(1, len(table_data) - 1):
        style_cmds.append(("LINEBELOW", (0, i), (-1, i), 0.5, GREY_BORDER))

    # Zebra striping
    for i in range(2, len(table_data), 2):
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), HexColor("#F8FAFC")))

    items_table.setStyle(TableStyle(style_cmds))
    elements.append(items_table)
    elements.append(Spacer(1, 4 * mm))

    # ══════════════════════════════════════════════════════════════
    # 7. Note (se presenti)
    # ══════════════════════════════════════════════════════════════
    if invoice.get("notes"):
        notes_content = _s(invoice["notes"]).replace("\n", "<br/>")
        notes_data = [
            [Paragraph("NOTE", STYLE_NOTES_TITLE)],
            [Paragraph(notes_content, STYLE_NOTES)],
        ]
        notes_table = Table(notes_data, colWidths=[usable_w])
        notes_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#FAFAFA")),
            ("BOX", (0, 0), (-1, -1), 0.5, GREY_BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(notes_table)
        elements.append(Spacer(1, 4 * mm))

    # ══════════════════════════════════════════════════════════════
    # 8. Totali a destra + Banca a sinistra (side by side)
    # ══════════════════════════════════════════════════════════════
    from services.pdf_template import compute_iva_groups
    iva_data = compute_iva_groups(lines)

    # --- Blocco totali ---
    totals_rows = []
    totals_rows.append([
        Paragraph("Imponibile:", STYLE_TOTALS_LABEL),
        Paragraph(f"\u20ac {_fmt(iva_data['imponibile'])}", STYLE_TOTALS_VALUE),
    ])
    for rate_str, grp in sorted(iva_data["groups"].items()):
        totals_rows.append([
            Paragraph(f"IVA {rate_str}% su \u20ac {_fmt(grp['base'])}:", STYLE_TOTALS_LABEL),
            Paragraph(f"\u20ac {_fmt(grp['tax'])}", STYLE_TOTALS_VALUE),
        ])
    totals_rows.append([
        Paragraph("Totale IVA:", STYLE_TOTALS_LABEL),
        Paragraph(f"\u20ac {_fmt(iva_data['total_vat'])}", STYLE_TOTALS_VALUE),
    ])

    totals_col_w = usable_w * 0.52
    totals_inner = [totals_col_w * 0.55, totals_col_w * 0.45]

    totals_table = Table(totals_rows, colWidths=totals_inner)
    totals_table.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, GREY_BORDER),
    ]))

    # Riga TOTALE con sfondo navy
    grand_row = [[
        Paragraph("TOTALE", STYLE_GRAND_LABEL),
        Paragraph(f"\u20ac {_fmt(iva_data['total'])}", STYLE_GRAND_VALUE),
    ]]
    grand_table = Table(grand_row, colWidths=totals_inner)
    grand_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0, NAVY),
    ]))

    # Ritenuta d'acconto (se presente)
    totals_obj = invoice.get("totals", {})
    ritenuta = float(totals_obj.get("ritenuta", 0) or 0)
    ritenuta_elements = []
    if ritenuta > 0:
        netto = iva_data["total"] - ritenuta
        rit_rows = [
            [Paragraph("Ritenuta d'acconto:", STYLE_TOTALS_LABEL),
             Paragraph(f"- \u20ac {_fmt(ritenuta)}", STYLE_TOTALS_VALUE)],
            [Paragraph("<b>NETTO A PAGARE:</b>", STYLE_TOTALS_LABEL),
             Paragraph(f"\u20ac {_fmt(netto)}", STYLE_TOTALS_VALUE)],
        ]
        rit_table = Table(rit_rows, colWidths=totals_inner)
        rit_table.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("LINEABOVE", (0, 0), (-1, 0), 0.5, GREY_BORDER),
        ]))
        ritenuta_elements.append(rit_table)

    # --- Blocco banca con bordo sinistro blu ---
    bank = co.get("bank_details", {}) or {}
    bank_name = _s(bank.get("bank_name", ""))
    bank_iban = _s(bank.get("iban", ""))
    bank_bic = _s(bank.get("bic_swift", ""))

    payment_cond_label = _s(payment_label)
    payment_type_label = _s(invoice.get("payment_type_label", ""))
    if payment_type_label:
        payment_cond_label = payment_type_label

    bank_lines_content = []
    bank_lines_content.append(Paragraph("COORDINATE BANCARIE", STYLE_SECTION_TITLE))
    if payment_cond_label:
        bank_lines_content.append(Paragraph(
            f"<b>Pagamento:</b> {payment_cond_label}", STYLE_BANK_LINE))
    if bank_name:
        bank_lines_content.append(Paragraph(f"<b>Banca:</b> {bank_name}", STYLE_BANK_LINE))
    if bank_iban:
        bank_lines_content.append(Paragraph(f"<b>IBAN:</b> {bank_iban}", STYLE_BANK_LINE))
    if bank_bic:
        bank_lines_content.append(Paragraph(f"<b>BIC/SWIFT:</b> {bank_bic}", STYLE_BANK_LINE))

    bank_col_w = usable_w * 0.46
    bank_rows = [[content] for content in bank_lines_content]
    bank_table = Table(bank_rows, colWidths=[bank_col_w - 4 * mm])
    bank_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (0, 0), 6),
        ("BOTTOMPADDING", (0, -1), (0, -1), 6),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, BLUE),
    ]))

    # Assemblaggio footer row: banca a sinistra, totali a destra
    right_elements = [totals_table, Spacer(1, 1 * mm), grand_table]
    right_elements.extend(ritenuta_elements)

    # Creo una table contenitore per i totali
    right_container_rows = [[el] for el in right_elements]
    right_container = Table(right_container_rows, colWidths=[totals_col_w])
    right_container.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    footer_row_data = [[bank_table, right_container]]
    footer_row_table = Table(footer_row_data, colWidths=[bank_col_w, totals_col_w + 2 * mm])
    footer_row_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(footer_row_table)
    elements.append(Spacer(1, 4 * mm))

    # ══════════════════════════════════════════════════════════════
    # 9. Scadenze pagamento con bordo sinistro blu
    # ══════════════════════════════════════════════════════════════
    scadenze = invoice.get("scadenze_pagamento", [])
    if scadenze:
        scad_content = [Paragraph("SCADENZA PAGAMENTI", STYLE_SECTION_TITLE)]
        for sc in scadenze:
            rata = sc.get("rata", "")
            data_sc = _date(sc.get("data_scadenza", ""))
            importo = _fmt(sc.get("importo", 0))
            pagata = sc.get("pagata", False)
            stato = " (Pagata)" if pagata else ""
            scad_content.append(Paragraph(
                f"<b>Rata {rata}:</b> {data_sc} - \u20ac {importo}{stato}",
                STYLE_BANK_LINE,
            ))

        scad_rows = [[c] for c in scad_content]
        scad_table = Table(scad_rows, colWidths=[usable_w - 4 * mm])
        scad_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (0, 0), 6),
            ("BOTTOMPADDING", (0, -1), (0, -1), 6),
            ("LINEBEFORE", (0, 0), (0, -1), 2.5, BLUE),
        ]))
        elements.append(scad_table)
        elements.append(Spacer(1, 3 * mm))

    # Due date prominente (se non ci sono scadenze ma c'è due_date)
    due_date = invoice.get("due_date")
    if due_date and not scadenze:
        due_style = ParagraphStyle(
            "DueDate", fontName=_fb(), fontSize=9, leading=12,
            textColor=HexColor("#991B1B"),
        )
        due_content = [
            [Paragraph("SCADENZA PAGAMENTO", STYLE_SECTION_TITLE)],
            [Paragraph(f"{_date(due_date)}", due_style)],
        ]
        due_table = Table(due_content, colWidths=[usable_w - 4 * mm])
        due_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (0, 0), 6),
            ("BOTTOMPADDING", (0, -1), (0, -1), 6),
            ("LINEBEFORE", (0, 0), (0, -1), 2.5, BLUE),
        ]))
        elements.append(due_table)
        elements.append(Spacer(1, 3 * mm))

    # ══════════════════════════════════════════════════════════════
    # 10. Note legali
    # ══════════════════════════════════════════════════════════════
    legal_style = ParagraphStyle(
        "Legal", fontName=_fn(), fontSize=6.5, leading=9,
        textColor=HexColor("#94A3B8"),
    )
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(
        "Condizioni Generali di Vendita: Riserva di propriet\u00e0 ex art. 1523 C.C. \u2014 "
        "Interessi moratori ex D.Lgs 231/02 \u2014 "
        "Foro competente esclusivo quello della sede legale del venditore.",
        legal_style,
    ))

    # ══════════════════════════════════════════════════════════════
    # 11. Pagina Condizioni (SOLO per Preventivi)
    # ══════════════════════════════════════════════════════════════
    condizioni = co.get("condizioni_vendita", "") or ""
    if condizioni.strip() and doc_type == "PRV":
        from reportlab.platypus import PageBreak
        elements.append(PageBreak())
        elements.append(Paragraph("CONDIZIONI GENERALI DI VENDITA", STYLE_COND_TITLE))
        elements.append(Spacer(1, 2 * mm))

        for paragraph in condizioni.split("\n"):
            p_text = paragraph.strip()
            if p_text:
                elements.append(Paragraph(p_text, STYLE_COND_TEXT))
                elements.append(Spacer(1, 1.5 * mm))

        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph("<b>Firma e timbro per accettazione</b>", STYLE_COND_TEXT))
        elements.append(Spacer(1, 12 * mm))
        elements.append(HRFlowable(width=180, thickness=0.5, color=black))
        elements.append(Paragraph(
            "Data di accettazione (legale rappresentante)", STYLE_COND_LEGAL))

        elements.append(Spacer(1, 6 * mm))
        elements.append(Paragraph(
            "Ai sensi e per gli effetti dell'Art. 1341 e segg. del Codice Civile, "
            "il sottoscritto Acquirente dichiara di aver preso specifica, precisa e "
            "dettagliata visione di tutte le disposizioni del contratto e di approvarle "
            "integralmente senza alcuna riserva.",
            STYLE_COND_LEGAL,
        ))
        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph("li _______________", STYLE_COND_TEXT))
        elements.append(Spacer(1, 12 * mm))
        elements.append(HRFlowable(width=180, thickness=0.5, color=black))
        elements.append(Paragraph(
            "Firma e timbro (il legale rappresentante)", STYLE_COND_LEGAL))

        elements.append(Spacer(1, 15 * mm))
        doc_footer_style = ParagraphStyle(
            "DocFooterCond", fontName=_fn(), fontSize=8, leading=10,
            textColor=HexColor("#555555"), alignment=TA_RIGHT,
        )
        elements.append(Paragraph(company_name, doc_footer_style))
        elements.append(Paragraph(f"Documento {display_num}", doc_footer_style))

    # ══════════════════════════════════════════════════════════════
    # BUILD
    # ══════════════════════════════════════════════════════════════
    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf.getvalue()
