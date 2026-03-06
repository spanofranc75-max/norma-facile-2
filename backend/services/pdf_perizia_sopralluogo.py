"""PDF Perizia Professionale — Design "Pro" con Tachimetro Risk Score.

Layout multi-pagina A4:
- COPERTINA: Logo + tachimetro SVG conformità + dati sopralluogo + foto hero
- SEZIONE 1: Documentazione fotografica (griglia 2 colonne)
- SEZIONE 2: Schede criticità PRO (problema + foto SX | soluzione + img esempio DX)
- SEZIONE 3: Dispositivi sicurezza (presenti vs mancanti)
- SEZIONE 4: Tabella materiali/interventi con prezzi
- SEZIONE 5: Note e firme
"""
import base64
import math
import logging
from datetime import datetime, timezone

from services.ref_images_library import get_ref_image_b64

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML
    WEASYPRINT_OK = True
except ImportError:
    WEASYPRINT_OK = False

# ── Brand Colors ──
NAVY = "#0B1F3A"
NAVY_LIGHT = "#162d50"
BLUE_ACCENT = "#0066FF"
LIGHT_BG = "#F4F6FA"
RED_RISK = "#DC2626"
AMBER_RISK = "#D97706"
GREEN_OK = "#16A34A"
WHITE_70 = "rgba(255,255,255,0.7)"
WHITE_50 = "rgba(255,255,255,0.5)"
WHITE_15 = "rgba(255,255,255,0.15)"


def _esc(t):
    if t is None:
        return ""
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _gauge_svg(pct: int) -> str:
    """Generate an inline SVG semicircular tachometer gauge for conformity %."""
    pct = max(0, min(100, pct))
    # Arc geometry — semicircle from 180° to 0° (left to right)
    cx, cy, r = 100, 90, 72
    stroke_w = 14
    circumference = math.pi * r  # half-circle
    dash_filled = circumference * pct / 100
    dash_gap = circumference - dash_filled

    # Color based on percentage
    if pct < 35:
        color = RED_RISK
    elif pct < 65:
        color = AMBER_RISK
    else:
        color = GREEN_OK

    # Tick marks
    ticks = ""
    for i in range(0, 101, 10):
        angle_deg = 180 - (i * 180 / 100)
        angle_rad = math.radians(angle_deg)
        x1 = cx + (r + 10) * math.cos(angle_rad)
        y1 = cy - (r + 10) * math.sin(angle_rad)
        x2 = cx + (r + 15) * math.cos(angle_rad)
        y2 = cy - (r + 15) * math.sin(angle_rad)
        ticks += f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="rgba(255,255,255,0.25)" stroke-width="1.5"/>'

    # Needle position
    needle_angle_deg = 180 - (pct * 180 / 100)
    needle_rad = math.radians(needle_angle_deg)
    nx = cx + (r - 20) * math.cos(needle_rad)
    ny = cy - (r - 20) * math.sin(needle_rad)

    return f"""<svg viewBox="0 0 200 115" xmlns="http://www.w3.org/2000/svg" width="200" height="115">
  <!-- Background arc -->
  <path d="M {cx - r} {cy} A {r} {r} 0 0 1 {cx + r} {cy}"
        fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="{stroke_w}" stroke-linecap="round"/>
  <!-- Filled arc -->
  <path d="M {cx - r} {cy} A {r} {r} 0 0 1 {cx + r} {cy}"
        fill="none" stroke="{color}" stroke-width="{stroke_w}" stroke-linecap="round"
        stroke-dasharray="{dash_filled:.1f} {dash_gap:.1f}"/>
  {ticks}
  <!-- Center dot -->
  <circle cx="{cx}" cy="{cy}" r="5" fill="white" opacity="0.9"/>
  <!-- Needle -->
  <line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
  <!-- Score text -->
  <text x="{cx}" y="{cy - 18}" text-anchor="middle" font-size="32" font-weight="900" fill="{color}" font-family="Arial, sans-serif">{pct}%</text>
</svg>"""


def _match_photo_to_risk(risk: dict, photos_b64: list) -> dict:
    """Try to find a user photo that matches a risk zone. Returns the best match or the first photo."""
    if not photos_b64:
        return None
    zona = (risk.get("zona") or "").lower()
    tipo = (risk.get("tipo_rischio") or "").lower()
    soluzione = (risk.get("soluzione") or "").lower()
    keyword_map = {
        "motore": ["motore", "automazione", "encoder", "impatto"],
        "guide": ["guida", "guide", "binari", "scorrimento", "convogliamento"],
        "chiusura": ["chiusura", "schiacciamento", "costa", "bordo"],
        "sicurezza": ["sicurezza", "fotocell", "sensore", "dispositiv"],
        "rete": ["rete", "cesoiamento", "maglia", "tamponamento"],
        "ancoraggio": ["ancoraggio", "base", "struttur"],
    }
    for photo in photos_b64:
        lbl = (photo.get("label") or "").lower()
        if lbl in keyword_map:
            for kw in keyword_map[lbl]:
                if kw in zona or kw in tipo or kw in soluzione:
                    return photo
    # Fallback: first non-panoramic photo, or just the first one
    for photo in photos_b64:
        if (photo.get("label") or "").lower() != "panoramica":
            return photo
    return photos_b64[0]


def _get_solution_image(risk: dict) -> str:
    """Get a reference solution image for a risk based on its solution text."""
    soluzione = (risk.get("soluzione") or "").lower()
    zona = (risk.get("zona") or "").lower()
    tipo = (risk.get("tipo_rischio") or "").lower()
    combined = f"{soluzione} {zona} {tipo}"

    keywords_to_try = ["costa", "fotocellula", "fotocellule", "rete", "encoder", "limitatore", "motore"]
    for kw in keywords_to_try:
        if kw in combined:
            b64 = get_ref_image_b64(kw)
            if b64:
                return b64
    return ""


CSS = f"""
@page {{
    size: A4;
    margin: 0;
}}
@page :first {{
    margin: 0;
}}
@page content {{
    margin: 16mm 14mm 22mm 14mm;
    @bottom-center {{
        content: "Pag. " counter(page) " di " counter(pages);
        font-size: 7pt; color: #999;
    }}
    @bottom-left {{
        content: "__FOOTER_NORM_TEXT__";
        font-size: 6.5pt; color: #bbb;
    }}
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Segoe UI', Calibri, Arial, sans-serif; font-size: 9pt; color: #1a1a1a; line-height: 1.55; }}

/* ══════════ COVER PAGE ══════════ */
.cover {{ width: 210mm; height: 297mm; position: relative; overflow: hidden; page-break-after: always; }}
.cover-bg {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(165deg, {NAVY} 0%, {NAVY_LIGHT} 55%, #1a3f62 100%); }}
.cover-accent-bar {{ position: absolute; top: 0; left: 0; width: 100%; height: 5mm; background: linear-gradient(90deg, {BLUE_ACCENT}, #00AAFF); }}
.cover-side-accent {{ position: absolute; top: 5mm; left: 0; width: 4mm; height: 100%; background: {BLUE_ACCENT}; opacity: 0.6; }}

.cover-content {{ position: relative; z-index: 2; padding: 18mm 18mm 12mm 18mm; color: white; height: 100%; }}
.cover-header {{ margin-bottom: 5mm; }}
.cover-logo img {{ height: 16mm; }}
.cover-company-name {{ font-size: 14pt; font-weight: 800; color: white; margin-bottom: 1mm; }}
.cover-company-info {{ font-size: 7.5pt; color: {WHITE_70}; }}

.cover-divider {{ width: 50mm; height: 0.7mm; background: {BLUE_ACCENT}; margin: 6mm 0; }}

.cover-doc-badge {{ display: inline-block; background: rgba(0,102,255,0.25); border: 1px solid rgba(0,102,255,0.5); padding: 1.5mm 5mm; border-radius: 2mm; font-size: 9pt; font-weight: 700; color: #66B2FF; letter-spacing: 0.5px; margin-bottom: 6mm; }}

.cover-title {{ font-size: 26pt; font-weight: 900; letter-spacing: -0.3px; line-height: 1.15; margin-bottom: 2mm; color: white; }}
.cover-subtitle {{ font-size: 11pt; color: {WHITE_70}; font-weight: 300; margin-bottom: 10mm; }}

.cover-info-grid {{ display: table; width: 60%; margin-bottom: 6mm; }}
.cover-info-row {{ display: table-row; }}
.cover-info-label {{ display: table-cell; padding: 1.5mm 0; color: {WHITE_50}; font-size: 7.5pt; width: 35%; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 600; }}
.cover-info-value {{ display: table-cell; padding: 1.5mm 0; color: white; font-size: 9.5pt; font-weight: 500; }}

/* Gauge area */
.cover-gauge-container {{ text-align: center; margin-top: 6mm; padding: 5mm 0; }}
.cover-gauge-label {{ font-size: 7pt; text-transform: uppercase; letter-spacing: 3px; color: {WHITE_50}; margin-bottom: 2mm; font-weight: 700; }}
.cover-gauge-status {{ font-size: 9.5pt; font-weight: 700; margin-top: 1mm; }}

/* Photo overlay */
.cover-photo {{ position: absolute; bottom: 0; right: 0; width: 50%; height: 42%; overflow: hidden; }}
.cover-photo img {{ width: 100%; height: 100%; object-fit: cover; opacity: 0.3; }}
.cover-photo-overlay {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(to right, {NAVY} 0%, transparent 50%); }}
.cover-photo-overlay2 {{ position: absolute; bottom: 0; left: 0; width: 100%; height: 30%; background: linear-gradient(to top, {NAVY}, transparent); }}

.cover-footer {{ position: absolute; bottom: 6mm; left: 18mm; right: 18mm; z-index: 3; display: table; width: calc(100% - 36mm); }}
.cover-footer-left {{ display: table-cell; vertical-align: bottom; }}
.cover-footer-right {{ display: table-cell; text-align: right; vertical-align: bottom; }}
.cover-footer-text {{ font-size: 6.5pt; color: rgba(255,255,255,0.3); }}
.cover-norms {{ display: inline-block; background: rgba(255,255,255,0.08); padding: 1.5mm 4mm; border-radius: 1.5mm; font-size: 7pt; color: rgba(255,255,255,0.5); }}

/* ══════════ CONTENT PAGES ══════════ */
.content-page {{ page: content; }}

/* Professional header bar on content pages */
.content-header {{ background: {NAVY}; padding: 4mm 5mm; margin-bottom: 6mm; border-radius: 0 0 2mm 2mm; display: table; width: 100%; }}
.content-header-logo {{ display: table-cell; width: 20mm; vertical-align: middle; }}
.content-header-logo img {{ height: 10mm; }}
.content-header-title {{ display: table-cell; vertical-align: middle; text-align: center; color: white; font-size: 11pt; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; }}
.content-header-doc {{ display: table-cell; width: 28mm; vertical-align: middle; text-align: right; color: {BLUE_ACCENT}; font-size: 7.5pt; font-weight: 600; }}

.section {{ margin-bottom: 7mm; }}
.section-header {{ background: {NAVY}; color: white; padding: 2.5mm 5mm; font-size: 10pt; font-weight: 700; letter-spacing: 0.3px; margin-bottom: 4mm; border-radius: 1.5mm; display: table; width: 100%; }}
.section-header-num {{ display: table-cell; width: 8mm; font-size: 12pt; font-weight: 900; color: {BLUE_ACCENT}; vertical-align: middle; }}
.section-header-text {{ display: table-cell; vertical-align: middle; }}

/* Info table */
.info-table {{ width: 100%; border: 1px solid #e2e8f0; border-radius: 2mm; overflow: hidden; margin-bottom: 5mm; }}
.info-table td {{ padding: 2.5mm 4mm; font-size: 9pt; border-bottom: 1px solid #f1f5f9; }}
.info-table .label {{ background: {LIGHT_BG}; font-weight: 600; color: #475569; width: 30%; font-size: 8pt; text-transform: uppercase; letter-spacing: 0.3px; }}

/* Photos */
.photos-grid {{ width: 100%; }}
.photos-row {{ display: flex; gap: 3mm; margin-bottom: 3mm; }}
.photo-card {{ flex: 1; border: 1px solid #e2e8f0; border-radius: 2mm; overflow: hidden; background: white; }}
.photo-card img {{ width: 100%; height: 50mm; display: block; object-fit: cover; }}
.photo-card-label {{ padding: 1.5mm 3mm; font-size: 7pt; font-weight: 700; color: #475569; background: {LIGHT_BG}; text-transform: uppercase; letter-spacing: 0.5px; border-top: 2px solid {BLUE_ACCENT}; }}

/* ══════════ RISK CARDS PRO ══════════ */
.risk-card-pro {{ border: 1px solid #e2e8f0; border-radius: 2.5mm; margin-bottom: 5mm; overflow: hidden; page-break-inside: avoid; }}
.risk-card-pro-header {{ display: table; width: 100%; }}
.risk-card-pro-sidebar {{ display: table-cell; width: 6mm; }}
.risk-card-pro-sidebar-alta {{ background: {RED_RISK}; }}
.risk-card-pro-sidebar-media {{ background: {AMBER_RISK}; }}
.risk-card-pro-sidebar-bassa {{ background: {BLUE_ACCENT}; }}
.risk-card-pro-title-area {{ display: table-cell; padding: 2.5mm 4mm; vertical-align: middle; background: #fafbfc; }}
.risk-card-pro-zona {{ font-weight: 800; font-size: 10pt; color: #0f172a; }}
.risk-card-pro-badges {{ margin-top: 1mm; }}
.risk-badge {{ display: inline-block; padding: 0.5mm 2.5mm; border-radius: 1mm; font-size: 6.5pt; font-weight: 700; margin-right: 2mm; text-transform: uppercase; letter-spacing: 0.3px; }}
.risk-badge-alta {{ background: #fee2e2; color: #991b1b; }}
.risk-badge-media {{ background: #fef3c7; color: #92400e; }}
.risk-badge-bassa {{ background: #dbeafe; color: #1e40af; }}
.risk-badge-norm {{ background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; font-family: 'Courier New', monospace; }}

.risk-card-pro-body {{ display: table; width: 100%; }}
.risk-col-left {{ display: table-cell; width: 45%; vertical-align: top; padding: 3mm; border-right: 1px solid #f1f5f9; }}
.risk-col-right {{ display: table-cell; width: 55%; vertical-align: top; padding: 3mm; }}

.risk-problem-title {{ font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; font-weight: 700; margin-bottom: 1.5mm; }}
.risk-problem-text {{ font-size: 8.5pt; color: #1e293b; line-height: 1.5; }}
.risk-photo {{ width: 100%; border-radius: 1.5mm; margin-top: 2mm; max-height: 40mm; object-fit: cover; display: block; border: 1px solid #e2e8f0; }}

.risk-solution-box {{ background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 1.5mm; padding: 2.5mm 3.5mm; margin-bottom: 2mm; }}
.risk-solution-title {{ font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.5px; color: #15803d; font-weight: 700; margin-bottom: 1mm; }}
.risk-solution-text {{ font-size: 8.5pt; color: #166534; line-height: 1.5; }}

.risk-ref-image-container {{ margin-top: 2mm; }}
.risk-ref-image-label {{ font-size: 6.5pt; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; font-weight: 600; margin-bottom: 1mm; }}
.risk-ref-image {{ width: 100%; max-height: 35mm; object-fit: contain; border-radius: 1.5mm; border: 1px solid #e2e8f0; display: block; }}

/* Devices */
.devices-container {{ display: table; width: 100%; border: 1px solid #e2e8f0; border-radius: 2mm; overflow: hidden; }}
.devices-col {{ display: table-cell; width: 50%; vertical-align: top; padding: 3.5mm 4mm; }}
.devices-col:first-child {{ border-right: 1px solid #e2e8f0; }}
.devices-col-title {{ font-size: 9pt; font-weight: 700; margin-bottom: 2.5mm; padding-bottom: 1.5mm; border-bottom: 2px solid; }}
.devices-col-title-ok {{ color: {GREEN_OK}; border-color: {GREEN_OK}; }}
.devices-col-title-ko {{ color: {RED_RISK}; border-color: {RED_RISK}; }}
.device-item {{ font-size: 8.5pt; padding: 1.2mm 0 1.2mm 4mm; }}
.device-ok {{ color: #166534; }}
.device-ko {{ color: #991b1b; font-weight: 600; }}

/* Materials table */
.mat-table {{ width: 100%; border-collapse: separate; border-spacing: 0; border: 1px solid #e2e8f0; border-radius: 2mm; overflow: hidden; }}
.mat-table th {{ background: {NAVY}; color: white; padding: 2.5mm 4mm; font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.4px; text-align: left; }}
.mat-table th:nth-child(3), .mat-table th:nth-child(4), .mat-table th:nth-child(5) {{ text-align: right; }}
.mat-table td {{ padding: 2.5mm 4mm; font-size: 8.5pt; border-bottom: 1px solid #f1f5f9; }}
.mat-table td:nth-child(3), .mat-table td:nth-child(4), .mat-table td:nth-child(5) {{ text-align: right; font-family: 'Courier New', monospace; }}
.mat-table tr:last-child td {{ border-bottom: none; }}
.mat-total {{ background: {LIGHT_BG}; font-weight: 700; }}
.badge-pri {{ display: inline-block; padding: 0.5mm 2.5mm; border-radius: 1mm; font-size: 6.5pt; font-weight: 700; text-transform: uppercase; }}
.badge-obbligatorio {{ background: #fee2e2; color: #991b1b; }}
.badge-consigliato {{ background: #dbeafe; color: #1e40af; }}

/* Signature */
.signature-area {{ margin-top: 10mm; display: table; width: 100%; }}
.signature-col {{ display: table-cell; width: 45%; vertical-align: bottom; }}
.signature-col:first-child {{ padding-right: 10%; }}
.signature-label {{ font-size: 7.5pt; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 18mm; }}
.signature-line {{ border-top: 1px solid {NAVY}; padding-top: 1.5mm; font-size: 8.5pt; font-weight: 600; color: #475569; }}

/* Notes */
.notes-box {{ background: {LIGHT_BG}; border-left: 3px solid {BLUE_ACCENT}; padding: 3mm 4mm; margin: 4mm 0; font-size: 8.5pt; border-radius: 0 1.5mm 1.5mm 0; }}
.notes-box strong {{ color: {NAVY}; }}

/* Summary box */
.summary-box {{ background: linear-gradient(135deg, {NAVY} 0%, {NAVY_LIGHT} 100%); color: white; padding: 5mm; border-radius: 2.5mm; margin-bottom: 6mm; }}
.summary-title {{ font-size: 11pt; font-weight: 800; margin-bottom: 3mm; }}
.summary-grid {{ display: table; width: 100%; }}
.summary-item {{ display: table-cell; text-align: center; padding: 2mm; }}
.summary-number {{ font-size: 18pt; font-weight: 900; line-height: 1.2; }}
.summary-label {{ font-size: 7pt; text-transform: uppercase; letter-spacing: 0.8px; color: {WHITE_70}; margin-top: 1mm; }}

/* Disclaimer */
.disclaimer {{ text-align: center; font-size: 6.5pt; color: #94a3b8; margin-top: 8mm; padding-top: 3mm; border-top: 1px solid #e2e8f0; }}

/* ══════════ VARIANTS PAGE ══════════ */
.variant-box {{ border: 1.5px solid #e2e8f0; border-radius: 2.5mm; margin-bottom: 5mm; overflow: hidden; page-break-inside: avoid; }}
.variant-box-recommended {{ border-color: {BLUE_ACCENT}; box-shadow: 0 0 0 0.5mm rgba(0,102,255,0.15); }}
.variant-header {{ display: table; width: 100%; }}
.variant-letter {{ display: table-cell; width: 14mm; background: {NAVY}; color: white; text-align: center; vertical-align: middle; font-size: 20pt; font-weight: 900; }}
.variant-letter-recommended {{ background: {BLUE_ACCENT}; }}
.variant-title-area {{ display: table-cell; padding: 3mm 4mm; vertical-align: middle; }}
.variant-title {{ font-size: 11pt; font-weight: 800; color: #0f172a; }}
.variant-subtitle {{ font-size: 8pt; color: #64748b; margin-top: 0.5mm; }}
.variant-recommended-badge {{ display: inline-block; background: {BLUE_ACCENT}; color: white; font-size: 6.5pt; font-weight: 700; padding: 0.5mm 2.5mm; border-radius: 1mm; text-transform: uppercase; letter-spacing: 0.5px; margin-left: 3mm; vertical-align: middle; }}
.variant-body {{ padding: 3mm 4mm; border-top: 1px solid #f1f5f9; }}
.variant-desc {{ font-size: 8.5pt; color: #334155; margin-bottom: 2mm; line-height: 1.5; }}
.variant-interventi {{ margin: 0; padding: 0 0 0 4mm; }}
.variant-interventi li {{ font-size: 8pt; color: #475569; padding: 0.5mm 0; }}
.variant-footer {{ display: table; width: 100%; background: {LIGHT_BG}; border-top: 1px solid #e2e8f0; }}
.variant-footer-cell {{ display: table-cell; padding: 2.5mm 4mm; }}
.variant-cost {{ font-size: 14pt; font-weight: 900; color: {NAVY}; }}
.variant-cost-label {{ font-size: 7pt; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }}
.variant-time {{ font-size: 9pt; font-weight: 600; color: #475569; text-align: right; }}
.variant-time-label {{ font-size: 7pt; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; text-align: right; }}
.variant-mano {{ font-size: 9pt; font-weight: 600; color: #475569; text-align: right; }}

/* Residual Risks */
.residual-risk-box {{ background: #fffbeb; border: 1px solid #fde68a; border-radius: 2mm; padding: 3mm 4mm; margin-top: 3mm; }}
.residual-risk-title {{ font-size: 8pt; font-weight: 700; color: #92400e; margin-bottom: 1.5mm; text-transform: uppercase; letter-spacing: 0.3px; }}
.residual-risk-item {{ font-size: 8pt; color: #78350f; padding: 0.5mm 0 0.5mm 4mm; line-height: 1.5; }}

/* Checklist */
.checklist-box {{ background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 2mm; padding: 3mm 4mm; }}
.checklist-title {{ font-size: 8.5pt; font-weight: 700; color: #15803d; margin-bottom: 2mm; }}
.checklist-item {{ font-size: 8pt; color: #166534; padding: 1mm 0 1mm 4mm; }}

/* ══════════ LEGAL NOTES PAGE ══════════ */
.legal-section {{ margin-bottom: 5mm; }}
.legal-title {{ font-size: 10pt; font-weight: 700; color: {NAVY}; margin-bottom: 2mm; padding-bottom: 1.5mm; border-bottom: 1.5px solid {BLUE_ACCENT}; }}
.legal-text {{ font-size: 8pt; color: #475569; line-height: 1.6; }}
.legal-text p {{ margin-bottom: 2mm; }}
.legal-highlight {{ background: #fefce8; border-left: 3px solid {AMBER_RISK}; padding: 2.5mm 4mm; border-radius: 0 1.5mm 1.5mm 0; margin: 3mm 0; font-size: 8pt; color: #713f12; }}
.legal-stamp-area {{ margin-top: 10mm; padding: 4mm; border: 1.5px solid #e2e8f0; border-radius: 2.5mm; text-align: center; }}
.legal-stamp-text {{ font-size: 7.5pt; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12mm; }}
.legal-stamp-line {{ border-top: 1px solid {NAVY}; width: 60%; margin: 0 auto; padding-top: 1.5mm; font-size: 8pt; font-weight: 600; color: #475569; }}
"""


def generate_perizia_pdf(sopralluogo: dict, company: dict, photos_b64: list = None) -> bytes:
    if not WEASYPRINT_OK:
        raise RuntimeError("WeasyPrint non disponibile")

    photos_b64 = photos_b64 or []
    analisi = sopralluogo.get("analisi_ai") or {}
    tipo_perizia = sopralluogo.get("tipo_perizia", "cancelli")
    conformita = analisi.get("conformita_percentuale", 0)
    c_status_color = RED_RISK if conformita < 35 else AMBER_RISK if conformita < 65 else GREEN_OK
    c_status = ("NON CONFORME — Intervento urgente" if conformita < 35
                else "PARZIALMENTE CONFORME — Intervento consigliato" if conformita < 65
                else "CONFORME — Manutenzione ordinaria")

    # Dynamic titles and norms based on tipo_perizia
    PERIZIA_CONFIG = {
        "cancelli": {
            "cover_title": "PERIZIA TECNICA<br/>MESSA A NORMA",
            "cover_subtitle": "Analisi di conformita UNI EN 12453 / EN 13241",
            "content_header_title": "Relazione Tecnica di Sopralluogo",
            "norms_badge": "EN 12453 &bull; EN 13241 &bull; Dir. 2006/42/CE",
            "footer_norm_text": "Norma Facile 2.0 — Perizia Tecnica Professionale",
            "legal_title": "Responsabilita del Proprietario / Amministratore",
            "legal_text_1": "Ai sensi della Direttiva Macchine 2006/42/CE e del D.Lgs. 17/2010, il proprietario o l'amministratore dell'immobile in cui e installata la chiusura automatica e responsabile della sicurezza dell'impianto e del suo mantenimento in conformita alle norme vigenti.",
            "legal_text_2": "La presente perizia tecnica evidenzia le non conformita riscontrate durante il sopralluogo. Il mancato adeguamento espone il proprietario a responsabilita civile e penale in caso di infortunio.",
            "legal_highlight": "<strong>Attenzione:</strong> In caso di incidente, l'assenza dei dispositivi di sicurezza obbligatori previsti dalla norma EN 12453 costituisce elemento di colpa grave ai sensi dell'art. 2051 C.C. (responsabilita per cose in custodia).",
            "legal_norms": """<p><strong>UNI EN 12453:2017</strong> — Porte e cancelli industriali, commerciali e da garage. Sicurezza in uso di porte motorizzate.</p>
                <p><strong>UNI EN 13241:2003+A2:2016</strong> — Porte e cancelli industriali, commerciali e da garage. Norma di prodotto.</p>
                <p><strong>Direttiva Macchine 2006/42/CE</strong> — Requisiti essenziali di sicurezza per la progettazione di macchine.</p>
                <p><strong>UNI EN 12978</strong> — Dispositivi di protezione per porte motorizzate.</p>""",
            "checklist_items": [
                "Misurazione forze d'impatto con strumento certificato (EN 12453 Allegato A)",
                "Verifica funzionamento coste sensibili (test pressione e rilascio)",
                "Test fotocellule (interruzione fascio e risposta impianto)",
                "Verifica finecorsa apertura e chiusura",
                "Test arresto di emergenza e inversione marcia",
                "Verifica limitazione forza motore / encoder",
                "Controllo visivo e funzionale segnalazione ottica (lampeggiante)",
                "Rilascio Dichiarazione di Adeguamento e aggiornamento Libretto Impianto",
            ],
        },
        "barriere": {
            "cover_title": "RELAZIONE<br/>ACCESSIBILITA",
            "cover_subtitle": "Analisi di conformita D.M. 236/1989 — Barriere Architettoniche",
            "content_header_title": "Relazione Tecnica Accessibilita",
            "norms_badge": "D.M. 236/89 &bull; L. 13/89 &bull; D.P.R. 503/96",
            "footer_norm_text": "Norma Facile 2.0 — Relazione Accessibilita",
            "legal_title": "Responsabilita del Proprietario / Amministratore",
            "legal_text_1": "Ai sensi della Legge 13/1989 e del D.M. 236/1989, il proprietario o l'amministratore dell'immobile e responsabile della garanzia dell'accessibilita e dell'eliminazione delle barriere architettoniche negli spazi comuni e negli accessi.",
            "legal_text_2": "La presente relazione tecnica evidenzia le non conformita riscontrate. Il mancato adeguamento puo costituire violazione della normativa vigente in materia di accessibilita.",
            "legal_highlight": "<strong>Attenzione:</strong> La mancata eliminazione delle barriere architettoniche negli edifici privati aperti al pubblico e negli spazi condominiali comuni puo comportare sanzioni amministrative e responsabilita civile ai sensi della L. 13/89 e del D.P.R. 503/96.",
            "legal_norms": """<p><strong>D.M. 236/1989</strong> — Prescrizioni tecniche necessarie a garantire l'accessibilita, l'adattabilita e la visitabilita degli edifici.</p>
                <p><strong>Legge 13/1989</strong> — Disposizioni per favorire il superamento e l'eliminazione delle barriere architettoniche.</p>
                <p><strong>D.P.R. 503/1996</strong> — Regolamento per l'eliminazione delle barriere architettoniche negli edifici, spazi e servizi pubblici.</p>
                <p><strong>UNI 11168</strong> — Criteri di progettazione per l'accessibilita delle scale fisse.</p>""",
            "checklist_items": [
                "Verifica pendenza rampe (max 8%)",
                "Misurazione larghezze percorsi e porte (min 80/90/150cm)",
                "Controllo altezza e doppio livello corrimano (90cm + 75cm)",
                "Verifica segnalazione tattile/cromatica gradini",
                "Controllo soglie (max 2.5cm)",
                "Verifica spazi di manovra per sedia a rotelle (150x150cm)",
                "Test antiscivolosita pavimentazione",
                "Rilascio Relazione di Conformita Accessibilita",
            ],
        },
        "strutture": {
            "cover_title": "DIAGNOSTICA<br/>STRUTTURALE",
            "cover_subtitle": "Analisi di conformita NTC 2018 / EN 1090",
            "content_header_title": "Relazione Diagnostica Strutturale",
            "norms_badge": "NTC 2018 &bull; EN 1090 &bull; EN 1993",
            "footer_norm_text": "Norma Facile 2.0 — Diagnostica Strutturale",
            "legal_title": "Responsabilita del Proprietario / Committente",
            "legal_text_1": "Ai sensi delle NTC 2018 (D.M. 17/01/2018, cap. 8), il proprietario o il committente e responsabile della sicurezza strutturale e della manutenzione delle opere in acciaio e delle strutture metalliche presenti nell'immobile.",
            "legal_text_2": "La presente relazione diagnostica evidenzia le criticita riscontrate. Il mancato intervento di consolidamento espone il proprietario a responsabilita civile e penale in caso di cedimento strutturale.",
            "legal_highlight": "<strong>Attenzione:</strong> Strutture metalliche esistenti non conformi alle NTC 2018 devono essere sottoposte a valutazione della sicurezza (cap. 8.3). L'omissione degli interventi di adeguamento necessari costituisce rischio per l'incolumita pubblica.",
            "legal_norms": """<p><strong>NTC 2018 — D.M. 17/01/2018</strong> — Norme Tecniche per le Costruzioni (cap. 4.2 — Costruzioni in acciaio, cap. 8 — Costruzioni esistenti).</p>
                <p><strong>Circolare 21/01/2019 n.7</strong> — Istruzioni per l'applicazione delle NTC 2018.</p>
                <p><strong>UNI EN 1090-1/2</strong> — Esecuzione di strutture in acciaio e alluminio — Requisiti per la valutazione di conformita.</p>
                <p><strong>UNI EN 1993 (Eurocodice 3)</strong> — Progettazione delle strutture in acciaio.</p>
                <p><strong>UNI EN ISO 5817</strong> — Saldatura — Livelli di qualita delle imperfezioni.</p>""",
            "checklist_items": [
                "Ispezione visiva stato corrosione e trattamento protettivo",
                "Verifica serraggio bulloneria critica (chiave dinamometrica)",
                "Controllo visivo saldature (cricche, porosita, sottosquadri)",
                "Verifica allineamento e verticalita elementi strutturali",
                "Controllo stato controventi e collegamenti",
                "Verifica piastre di base e ancoraggi",
                "Misura spessori residui (ultrasuoni se necessario)",
                "Rilascio Relazione di Valutazione Sicurezza Strutturale",
            ],
        },
    }

    cfg = PERIZIA_CONFIG.get(tipo_perizia, PERIZIA_CONFIG["cancelli"])

    # Company info
    c_name = _esc(company.get("company_name", ""))
    c_addr = _esc(f'{company.get("address", "")} — {company.get("cap", "")} {company.get("city", "")} ({company.get("province", "")})')
    c_piva = _esc(company.get("partita_iva", ""))
    logo_url = company.get("logo_url", "")

    # Sopralluogo info
    doc_num = _esc(sopralluogo.get("document_number", ""))
    client_name = _esc(sopralluogo.get("client_name", ""))
    indirizzo = _esc(sopralluogo.get("indirizzo", ""))
    comune = _esc(sopralluogo.get("comune", ""))
    provincia = _esc(sopralluogo.get("provincia", ""))
    tipo_chiusura = _esc(analisi.get("tipo_chiusura", "").replace("_", " ").title())
    desc_gen = _esc(analisi.get("descrizione_generale", sopralluogo.get("descrizione_utente", "")))
    created = sopralluogo.get("created_at", "")[:10]
    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")

    # Counts for summary
    rischi = [r for r in analisi.get("rischi", []) if r.get("confermato", True)]
    n_rischi_alta = sum(1 for r in rischi if r.get("gravita") == "alta")
    n_rischi_media = sum(1 for r in rischi if r.get("gravita") == "media")
    n_dispositivi_mancanti = len(analisi.get("dispositivi_mancanti", []))
    n_materiali = len(analisi.get("materiali_suggeriti", []))

    # ═══════════════ COVER PAGE ═══════════════
    logo_html = f'<img src="{logo_url}" style="height:16mm;" />' if logo_url else f'<div class="cover-company-name">{c_name}</div>'

    cover_photo_html = ""
    if photos_b64:
        p = photos_b64[0]
        cover_photo_html = f"""
        <div class="cover-photo">
            <img src="data:{p['mime_type']};base64,{p['base64']}" />
            <div class="cover-photo-overlay"></div>
            <div class="cover-photo-overlay2"></div>
        </div>"""

    gauge_svg = _gauge_svg(conformita)

    cover = f"""
    <div class="cover">
        <div class="cover-bg"></div>
        <div class="cover-accent-bar"></div>
        <div class="cover-side-accent"></div>
        {cover_photo_html}
        <div class="cover-content">
            <div class="cover-header">
                {logo_html}
                <div class="cover-company-info">{c_addr} | P.IVA {c_piva}</div>
            </div>

            <div class="cover-divider"></div>

            <div class="cover-doc-badge">{doc_num}</div>
            <div class="cover-title">{cfg["cover_title"]}</div>
            <div class="cover-subtitle">{cfg["cover_subtitle"]}</div>

            <div class="cover-info-grid">
                <div class="cover-info-row"><div class="cover-info-label">Cliente</div><div class="cover-info-value">{client_name}</div></div>
                <div class="cover-info-row"><div class="cover-info-label">Localita</div><div class="cover-info-value">{indirizzo}, {comune} ({provincia})</div></div>
                <div class="cover-info-row"><div class="cover-info-label">Tipo Chiusura</div><div class="cover-info-value">{tipo_chiusura}</div></div>
                <div class="cover-info-row"><div class="cover-info-label">Data Sopralluogo</div><div class="cover-info-value">{created}</div></div>
            </div>

            <div class="cover-gauge-container">
                <div class="cover-gauge-label">Indice di Conformita</div>
                {gauge_svg}
                <div class="cover-gauge-status" style="color:{c_status_color};">{c_status}</div>
            </div>
        </div>

        <div class="cover-footer">
            <div class="cover-footer-left">
                <div class="cover-norms">{cfg["norms_badge"]}</div>
            </div>
            <div class="cover-footer-right">
                <div class="cover-footer-text">Generato il {now_str} — Norma Facile 2.0</div>
            </div>
        </div>
    </div>"""

    # ═══════════════ SUMMARY BOX ═══════════════
    summary_html = f"""
    <div class="summary-box">
        <div class="summary-title">Riepilogo Ispezione</div>
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-number" style="color:{c_status_color};">{conformita}%</div>
                <div class="summary-label">Conformita</div>
            </div>
            <div class="summary-item">
                <div class="summary-number" style="color:#f87171;">{n_rischi_alta}</div>
                <div class="summary-label">Rischi Critici</div>
            </div>
            <div class="summary-item">
                <div class="summary-number" style="color:#fbbf24;">{n_rischi_media}</div>
                <div class="summary-label">Rischi Medi</div>
            </div>
            <div class="summary-item">
                <div class="summary-number" style="color:#f87171;">{n_dispositivi_mancanti}</div>
                <div class="summary-label">Dispositivi Mancanti</div>
            </div>
            <div class="summary-item">
                <div class="summary-number" style="color:{BLUE_ACCENT};">{n_materiali}</div>
                <div class="summary-label">Interventi Previsti</div>
            </div>
        </div>
    </div>"""

    # ═══════════════ PHOTOS SECTION (2x2 Grid, no empty placeholders, unique labels) ═══════════════
    photos_html = ""
    if photos_b64:
        all_cards = []
        seen_labels = {}
        for idx, p in enumerate(photos_b64):
            raw_lbl = (p.get("label") or f"Foto {idx + 1}").strip().upper()
            # Deduplicate labels: "PANORAMICA" → "PANORAMICA 1", "PANORAMICA 2"
            if raw_lbl in seen_labels:
                seen_labels[raw_lbl] += 1
                lbl = f"{raw_lbl} {seen_labels[raw_lbl]}"
            else:
                seen_labels[raw_lbl] = 1
                lbl = raw_lbl
            lbl = _esc(lbl)
            all_cards.append(f'<div class="photo-card"><img src="data:{p["mime_type"]};base64,{p["base64"]}" /><div class="photo-card-label">{lbl}</div></div>')

        rows = []
        for i in range(0, len(all_cards), 2):
            chunk = all_cards[i:i + 2]
            rows.append(f'<div class="photos-row">{"".join(chunk)}</div>')

        photos_html = f"""
        <div class="section">
            <div class="section-header"><div class="section-header-num">01</div><div class="section-header-text">DOCUMENTAZIONE FOTOGRAFICA</div></div>
            {"".join(rows)}
        </div>"""

    # ═══════════════ RISK CARDS PRO (2-COLUMN) ═══════════════
    risks_html = ""
    if rischi:
        cards = []
        for idx, r in enumerate(rischi):
            g = r.get("gravita", "media")
            norma = _esc(r.get("norma_riferimento", ""))
            tipo_r = _esc(r.get("tipo_rischio", "").replace("_", " ").title())

            # Left column: problem + user photo
            matched_photo = _match_photo_to_risk(r, photos_b64)
            photo_html = ""
            if matched_photo:
                photo_html = f'<img class="risk-photo" src="data:{matched_photo["mime_type"]};base64,{matched_photo["base64"]}" />'

            # Right column: solution + reference image
            ref_b64 = _get_solution_image(r)
            ref_img_html = ""
            if ref_b64:
                ref_img_html = f"""
                <div class="risk-ref-image-container">
                    <img class="risk-ref-image" src="data:image/png;base64,{ref_b64}" />
                </div>"""

            cards.append(f"""
            <div class="risk-card-pro">
                <div class="risk-card-pro-header">
                    <div class="risk-card-pro-sidebar risk-card-pro-sidebar-{g}"></div>
                    <div class="risk-card-pro-title-area">
                        <div class="risk-card-pro-zona">{_esc(r.get('zona', ''))}</div>
                        <div class="risk-card-pro-badges">
                            <span class="risk-badge risk-badge-{g}">{g.upper()}</span>
                            <span class="risk-badge risk-badge-norm">{norma}</span>
                            <span class="risk-badge" style="background:#f8fafc;color:#64748b;">{tipo_r}</span>
                        </div>
                    </div>
                </div>
                <div class="risk-card-pro-body">
                    <div class="risk-col-left">
                        <div class="risk-problem-title">Problema Rilevato</div>
                        <div class="risk-problem-text">{_esc(r.get('problema', ''))}</div>
                        {photo_html}
                    </div>
                    <div class="risk-col-right">
                        <div class="risk-solution-box">
                            <div class="risk-solution-title">Soluzione Proposta</div>
                            <div class="risk-solution-text">{_esc(r.get('soluzione', ''))}</div>
                        </div>
                        {ref_img_html}
                    </div>
                </div>
            </div>""")

        risks_html = f"""
        <div class="section">
            <div class="section-header"><div class="section-header-num">02</div><div class="section-header-text">CRITICITA RISCONTRATE ({len(rischi)})</div></div>
            {"".join(cards)}
        </div>"""

    # ═══════════════ DEVICES SECTION ═══════════════
    presenti = analisi.get("dispositivi_presenti", [])
    mancanti = analisi.get("dispositivi_mancanti", [])
    devices_html = ""
    if presenti or mancanti:
        p_items = "".join(f'<div class="device-item device-ok">&#10003; {_esc(d)}</div>' for d in presenti) or '<div class="device-item" style="color:#999;">Nessuno rilevato</div>'
        m_items = "".join(f'<div class="device-item device-ko">&#10007; {_esc(d)}</div>' for d in mancanti) or '<div class="device-item" style="color:#999;">Nessuno</div>'
        devices_html = f"""
        <div class="section">
            <div class="section-header"><div class="section-header-num">03</div><div class="section-header-text">DISPOSITIVI DI SICUREZZA</div></div>
            <div class="devices-container">
                <div class="devices-col"><div class="devices-col-title devices-col-title-ok">Presenti</div>{p_items}</div>
                <div class="devices-col"><div class="devices-col-title devices-col-title-ko">Mancanti / Non Verificabili</div>{m_items}</div>
            </div>
        </div>"""

    # ═══════════════ MATERIALS TABLE — REMOVED from PDF (internal data only) ═══════════════
    # Section 04 rimossa: il cliente non deve vedere i costi materiali interni

    # ═══════════════ GENERAL DESCRIPTION ═══════════════
    desc_html = ""
    if desc_gen:
        desc_html = f"""
        <div class="section">
            <div class="section-header"><div class="section-header-num">00</div><div class="section-header-text">DESCRIZIONE GENERALE</div></div>
            <div class="notes-box">{desc_gen}</div>
        </div>"""

    # ═══════════════ NOTES (solo note tecnico, no menzione AI) ═══════════════
    notes_html = ""
    note_utente = sopralluogo.get("note_tecnico", "")
    if note_utente:
        notes_html = f"""
        <div class="section">
            <div class="section-header"><div class="section-header-num">04</div><div class="section-header-text">NOTE DEL TECNICO</div></div>
            <div class="notes-box">{_esc(note_utente)}</div>
        </div>"""

    # ═══════════════ SIGNATURES ═══════════════
    signature_html = """
    <div class="signature-area">
        <div class="signature-col">
            <div class="signature-label">Il Tecnico Incaricato</div>
            <div class="signature-line">Data e Firma</div>
        </div>
        <div class="signature-col">
            <div class="signature-label">Il Cliente (per presa visione)</div>
            <div class="signature-line">Data e Firma</div>
        </div>
    </div>"""

    disclaimer = f"""
    <div class="disclaimer">
        Documento redatto con il supporto di strumenti di analisi assistita e validato e sottoscritto dal tecnico responsabile ai sensi delle normative vigenti.<br/>
        Riferimenti: UNI EN 12453, UNI EN 13241, Direttiva Macchine 2006/42/CE, D.Lgs. 17/2010 — Generato il {now_str}
    </div>"""

    # ═══════════════ CONTENT PAGE HEADER ═══════════════
    content_logo = f'<img src="{logo_url}" />' if logo_url else f'<div style="font-size:8pt;font-weight:800;color:white;">{c_name}</div>'
    content_header = f"""
    <div class="content-header">
        <div class="content-header-logo">{content_logo}</div>
        <div class="content-header-title">{cfg["content_header_title"]}</div>
        <div class="content-header-doc">{doc_num}</div>
    </div>"""

    # ═══════════════ VARIANTS PAGE ═══════════════
    varianti = analisi.get("varianti", {})
    variants_html = ""
    if varianti and any(varianti.get(k, {}).get("descrizione") for k in ("A", "B", "C")):
        variant_cards = []
        for key, label_default in [("A", "Adeguamento Minimo"), ("B", "Adeguamento Completo"), ("C", "Sostituzione Totale")]:
            v = varianti.get(key, {})
            if not v:
                continue
            titolo = _esc(v.get("titolo", label_default))
            desc = _esc(v.get("descrizione", ""))
            costo = v.get("costo_stimato", 0)
            interventi = v.get("interventi", [])
            is_recommended = key == "B"

            box_cls = "variant-box variant-box-recommended" if is_recommended else "variant-box"
            letter_cls = "variant-letter variant-letter-recommended" if is_recommended else "variant-letter"
            badge = '<span class="variant-recommended-badge">Consigliato</span>' if is_recommended else ""

            interventi_html = ""
            if interventi:
                items = "".join(f"<li>{_esc(i)}</li>" for i in interventi)
                interventi_html = f'<ul class="variant-interventi">{items}</ul>'

            costo_str = f"{costo:,.0f} &euro;" if costo > 0 else "Da Quotare"
            stima_mano = _esc(v.get("stima_manodopera", ""))
            mano_html = f'<div class="variant-mano">{stima_mano}</div>' if stima_mano else ""

            variant_cards.append(f"""
            <div class="{box_cls}">
                <div class="variant-header">
                    <div class="{letter_cls}">{key}</div>
                    <div class="variant-title-area">
                        <div class="variant-title">{titolo}{badge}</div>
                        <div class="variant-subtitle">Variante {key}</div>
                    </div>
                </div>
                <div class="variant-body">
                    <div class="variant-desc">{desc}</div>
                    {interventi_html}
                </div>
                <div class="variant-footer">
                    <div class="variant-footer-cell">
                        <div class="variant-cost-label">Costo Stimato (IVA escl.)</div>
                        <div class="variant-cost">{costo_str}</div>
                    </div>
                    <div class="variant-footer-cell" style="text-align:right;">
                        <div class="variant-cost-label">Manodopera Stimata</div>
                        {mano_html}
                    </div>
                </div>
            </div>""")

        if variant_cards:
            sec_num = "05" if notes_html else "04"
            variants_html = f"""
            <div class="section" style="page-break-before:always;">
                <div class="section-header"><div class="section-header-num">{sec_num}</div><div class="section-header-text">PROPOSTE DI INTERVENTO</div></div>
                {"".join(variant_cards)}
            </div>"""

    # ═══════════════ RESIDUAL RISKS ═══════════════
    rischi_residui = analisi.get("rischi_residui", [])
    residual_html = ""
    if rischi_residui:
        items = "".join(f'<div class="residual-risk-item">&#9888; {_esc(r)}</div>' for r in rischi_residui)
        residual_html = f"""
        <div class="residual-risk-box">
            <div class="residual-risk-title">Rischi Residui (post-adeguamento)</div>
            <div style="font-size:7.5pt;color:#92400e;margin-bottom:1.5mm;">Anche dopo l'intervento di adeguamento completo, i seguenti rischi residui minimi permangono per caratteristiche strutturali dell'impianto:</div>
            {items}
        </div>"""

    # ═══════════════ LEGAL NOTES PAGE ═══════════════
    sec_legal = "06" if variants_html and notes_html else "05" if variants_html or notes_html else "04"
    checklist_items_html = "".join(f'<div class="checklist-item">&#9745; {_esc(item)}</div>' for item in cfg["checklist_items"])
    legal_html = f"""
    <div style="page-break-before:always;">
        <div class="section-header"><div class="section-header-num">{sec_legal}</div><div class="section-header-text">NOTE LEGALI E RESPONSABILITA</div></div>

        <div class="legal-section">
            <div class="legal-title">{cfg["legal_title"]}</div>
            <div class="legal-text">
                <p>{cfg["legal_text_1"]}</p>
                <p>{cfg["legal_text_2"]}</p>
            </div>
        </div>

        <div class="legal-highlight">
            {cfg["legal_highlight"]}
        </div>

        <div class="legal-section">
            <div class="legal-title">Riferimenti Normativi</div>
            <div class="legal-text">
                {cfg["legal_norms"]}
            </div>
        </div>

        <div class="legal-section">
            <div class="legal-title">Limitazioni della Perizia</div>
            <div class="legal-text">
                <p>La presente relazione tecnica si basa sull'ispezione visiva e fotografica effettuata in data {created}. Le valutazioni sono limitate a quanto osservabile al momento del sopralluogo.</p>
                <p>Non sostituisce una verifica strumentale completa ne un collaudo finale post-intervento. Si raccomanda di eseguire tali verifiche a completamento dei lavori di adeguamento.</p>
            </div>
        </div>

        <div class="legal-section">
            <div class="legal-title">Check-list Verifiche Post-Intervento</div>
            <div class="checklist-box">
                <div class="checklist-title">Al completamento dei lavori, verranno eseguiti i seguenti test:</div>
                {checklist_items_html}
            </div>
        </div>

        <div class="legal-section">
            <div class="legal-title">Validita del Documento</div>
            <div class="legal-text">
                <p>Il presente documento ha validita tecnica e non costituisce certificazione di conformita. La perizia ha validita 12 mesi dalla data del sopralluogo, salvo modifiche all'impianto o aggiornamenti normativi.</p>
            </div>
        </div>

        <div class="legal-stamp-area">
            <div class="legal-stamp-text">Timbro e Firma del Tecnico Responsabile</div>
            <div class="legal-stamp-line">{c_name}</div>
        </div>
    </div>"""

    # ═══════════════ ASSEMBLE ═══════════════
    final_css = CSS.replace("__FOOTER_NORM_TEXT__", cfg["footer_norm_text"])
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{final_css}</style></head><body>
    {cover}
    <div class="content-page">
        {content_header}
        {summary_html}
        {desc_html}
        {photos_html}
        {risks_html}
        {devices_html}
        {notes_html}
        {signature_html}
        {variants_html}
        {residual_html}
        {legal_html}
        {disclaimer}
    </div>
    </body></html>"""

    return HTML(string=html).write_pdf()
