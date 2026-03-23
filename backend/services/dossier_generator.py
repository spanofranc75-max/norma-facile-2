"""Dossier Generator — One-Click Technical Dossier (Fascicolo Tecnico).

Merges all compliance documents into a single PDF:
  1. Cover Page
  2. DoP (Declaration of Performance)
  3. CE Label
  4. Material Certificates (3.1) from linked batches
  5. Welder Qualification Summary
  6. FPC Controls Checklist
"""
from io import BytesIO
from datetime import datetime, timezone
import base64
import logging

from pypdf import PdfWriter, PdfReader
from services.pdf_template import (
    safe, render_pdf,
)

logger = logging.getLogger(__name__)


def _section_pdf(body_html: str) -> bytes:
    """Render a section body to PDF bytes via shared template."""
    buf = render_pdf(body_html)
    return buf.getvalue()


def _build_cover_page(project: dict, company: dict) -> bytes:
    """Generate the cover page for the dossier."""
    co = company or {}
    fpc = project.get("fpc_data", {})
    now = datetime.now(timezone.utc)

    company_name = safe(co.get("business_name"))
    logo_html = ""
    logo_url = co.get("logo_url", "")
    if logo_url and logo_url.startswith("data:image"):
        logo_html = f'<img src="{logo_url}" style="max-width:160px;max-height:60px;display:block;margin:0 auto 10px;" />'

    body = f"""
    <div style="text-align:center; padding-top:120px;">
        {logo_html}
        <div style="font-size:14pt; color:#555; margin-bottom:8px;">{company_name}</div>
        <div style="border-top:3px solid #0055FF; width:60%; margin:15px auto;"></div>
        <h1 style="font-size:26pt; font-weight:bold; color:#222; margin:20px 0 8px;">FASCICOLO TECNICO</h1>
        <h2 style="font-size:16pt; color:#333; margin:0 0 6px;">Commessa {safe(project.get('preventivo_number', project.get('project_id')))}</h2>
        <div style="font-size:11pt; color:#555; margin-top:15px;">
            Classe di Esecuzione: <strong>{safe(fpc.get('execution_class'))}</strong>
        </div>
        <div style="font-size:10pt; color:#666; margin-top:6px;">
            Cliente: {safe(project.get('client_name', 'N/A'))}
        </div>
        <div style="font-size:10pt; color:#666; margin-top:3px;">
            {safe(project.get('subject', ''))}
        </div>
    </div>
    <div style="position:fixed; bottom:30px; left:0; right:0; text-align:center; font-size:8pt; color:#999;">
        Documento generato il {now.strftime('%d/%m/%Y alle %H:%M')} — {company_name}
        <br>Conforme EN 1090-1:2009+A1:2011 — Marcatura CE strutture in acciaio
    </div>"""
    return _section_pdf(body)


def _build_dop_page(project: dict, company: dict) -> bytes:
    """Generate a Declaration of Performance (DoP) page."""
    co = company or {}
    fpc = project.get("fpc_data", {})
    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    body = f"""
    <h1 style="font-size:16pt; text-align:center; margin-bottom:15px;">
        DICHIARAZIONE DI PRESTAZIONE (DoP)
    </h1>
    <p style="font-size:8pt; text-align:center; color:#666; margin-bottom:20px;">
        ai sensi del Regolamento UE n. 305/2011 (CPR)
    </p>
    <table style="width:100%; border-collapse:collapse; font-size:9pt;">
        <tr><td style="border:1px solid #bbb; padding:5px; width:40%; background:#f5f5f5; font-weight:bold;">
            1. Codice prodotto</td>
            <td style="border:1px solid #bbb; padding:5px;">{safe(project.get('preventivo_number'))}</td></tr>
        <tr><td style="border:1px solid #bbb; padding:5px; background:#f5f5f5; font-weight:bold;">
            2. Uso previsto</td>
            <td style="border:1px solid #bbb; padding:5px;">Componenti strutturali in acciaio — EN 1090-1</td></tr>
        <tr><td style="border:1px solid #bbb; padding:5px; background:#f5f5f5; font-weight:bold;">
            3. Fabbricante</td>
            <td style="border:1px solid #bbb; padding:5px;">
                {safe(co.get('business_name'))}<br>
                {safe(co.get('address'))} {safe(co.get('cap'))} {safe(co.get('city'))}
                {"<br>P.IVA: " + safe(co.get('partita_iva')) if co.get('partita_iva') else ""}
            </td></tr>
        <tr><td style="border:1px solid #bbb; padding:5px; background:#f5f5f5; font-weight:bold;">
            4. Sistema AVCP</td>
            <td style="border:1px solid #bbb; padding:5px;">Sistema 2+</td></tr>
        <tr><td style="border:1px solid #bbb; padding:5px; background:#f5f5f5; font-weight:bold;">
            5. Norma armonizzata</td>
            <td style="border:1px solid #bbb; padding:5px;">EN 1090-1:2009+A1:2011</td></tr>
        <tr><td style="border:1px solid #bbb; padding:5px; background:#f5f5f5; font-weight:bold;">
            6. Classe di esecuzione</td>
            <td style="border:1px solid #bbb; padding:5px; font-weight:bold;">{safe(fpc.get('execution_class'))}</td></tr>
        <tr><td style="border:1px solid #bbb; padding:5px; background:#f5f5f5; font-weight:bold;">
            7. WPS applicata</td>
            <td style="border:1px solid #bbb; padding:5px;">{safe(fpc.get('wps_id', 'N/A'))}</td></tr>
        <tr><td style="border:1px solid #bbb; padding:5px; background:#f5f5f5; font-weight:bold;">
            8. Saldatore qualificato</td>
            <td style="border:1px solid #bbb; padding:5px;">{safe(fpc.get('welder_name', 'N/A'))}</td></tr>
    </table>
    <div style="margin-top:30px; font-size:8.5pt;">
        <p>Le prestazioni del prodotto sopra identificato sono conformi alle prestazioni dichiarate.</p>
        <p>La presente dichiarazione di prestazione è rilasciata sotto la responsabilità esclusiva del fabbricante.</p>
    </div>
    <div style="margin-top:40px;">
        <table style="width:100%; border:none;">
            <tr>
                <td style="border:none; width:50%; font-size:8.5pt;">
                    Luogo e data: ________________, {now_str}
                </td>
                <td style="border:none; width:50%; text-align:right; font-size:8.5pt;">
                    Firma: ________________________<br>
                    <span style="font-size:7pt; color:#666;">(legale rappresentante)</span>
                </td>
            </tr>
        </table>
    </div>"""
    return _section_pdf(body)


def _build_ce_label_page(project: dict, company: dict) -> bytes:
    """Generate a CE Label page."""
    co = company or {}
    fpc = project.get("fpc_data", {})
    year = datetime.now(timezone.utc).year

    body = f"""
    <div style="max-width:400px; margin:40px auto; border:3px solid #222; padding:25px; text-align:center;">
        <div style="font-size:48pt; font-weight:bold; letter-spacing:6px; margin-bottom:10px;">CE</div>
        <div style="border-top:2px solid #222; margin:10px 0;"></div>
        <div style="font-size:10pt; text-align:left; line-height:1.8;">
            <p><strong>Fabbricante:</strong> {safe(co.get('business_name'))}</p>
            <p><strong>Indirizzo:</strong> {safe(co.get('address'))} {safe(co.get('cap'))} {safe(co.get('city'))}</p>
            <p><strong>Anno di apposizione:</strong> {year}</p>
            <p><strong>N. DoP:</strong> {safe(project.get('preventivo_number'))}-DoP</p>
            <p><strong>EN 1090-1:2009+A1:2011</strong></p>
            <p><strong>Componenti strutturali in acciaio</strong></p>
            <p><strong>Classe di esecuzione:</strong> <span style="font-size:14pt; font-weight:bold;">{safe(fpc.get('execution_class'))}</span></p>
        </div>
    </div>"""
    return _section_pdf(body)


def _build_materials_summary(project: dict, batches_data: list) -> bytes:
    """Generate a materials traceability summary page."""
    lines = project.get("lines", [])
    batch_map = {b["batch_id"]: b for b in batches_data}

    rows = ""
    for i, ln in enumerate(lines):
        bid = ln.get("batch_id", "")
        b = batch_map.get(bid, {})
        rows += f"""<tr>
            <td style="border:1px solid #bbb; padding:4px; font-size:8pt;">{i+1}</td>
            <td style="border:1px solid #bbb; padding:4px; font-size:8pt;">{safe(ln.get('description','')[:60])}</td>
            <td style="border:1px solid #bbb; padding:4px; font-size:8pt; font-weight:bold;">{safe(b.get('heat_number', ln.get('heat_number','-')))}</td>
            <td style="border:1px solid #bbb; padding:4px; font-size:8pt;">{safe(b.get('material_type', ln.get('material_type','-')))}</td>
            <td style="border:1px solid #bbb; padding:4px; font-size:8pt;">{safe(b.get('supplier_name','-'))}</td>
            <td style="border:1px solid #bbb; padding:4px; font-size:8pt; text-align:center;">{'Si' if b.get('has_certificate') else 'No'}</td>
        </tr>"""

    body = f"""
    <h1 style="font-size:14pt; text-align:center; margin-bottom:15px;">
        TRACCIABILITA' MATERIALI
    </h1>
    <p style="font-size:8pt; text-align:center; color:#666; margin-bottom:12px;">
        Riepilogo lotti e numeri di colata associati alle righe di commessa
    </p>
    <table style="width:100%; border-collapse:collapse;">
        <thead>
            <tr style="background:#eee;">
                <th style="border:1px solid #999; padding:5px; font-size:7.5pt; text-transform:uppercase;">#</th>
                <th style="border:1px solid #999; padding:5px; font-size:7.5pt; text-transform:uppercase;">Descrizione</th>
                <th style="border:1px solid #999; padding:5px; font-size:7.5pt; text-transform:uppercase;">N. Colata</th>
                <th style="border:1px solid #999; padding:5px; font-size:7.5pt; text-transform:uppercase;">Materiale</th>
                <th style="border:1px solid #999; padding:5px; font-size:7.5pt; text-transform:uppercase;">Fornitore</th>
                <th style="border:1px solid #999; padding:5px; font-size:7.5pt; text-transform:uppercase;">Cert 3.1</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>"""
    return _section_pdf(body)


def _build_welder_page(welder: dict) -> bytes:
    """Generate welder qualification summary."""
    body = f"""
    <h1 style="font-size:14pt; text-align:center; margin-bottom:15px;">
        QUALIFICA SALDATORE
    </h1>
    <table style="width:80%; margin:20px auto; border-collapse:collapse; font-size:10pt;">
        <tr><td style="border:1px solid #bbb; padding:6px; background:#f5f5f5; font-weight:bold; width:40%;">
            Nome</td><td style="border:1px solid #bbb; padding:6px;">{safe(welder.get('name'))}</td></tr>
        <tr><td style="border:1px solid #bbb; padding:6px; background:#f5f5f5; font-weight:bold;">
            Qualifica</td><td style="border:1px solid #bbb; padding:6px;">{safe(welder.get('qualification_level'))}</td></tr>
        <tr><td style="border:1px solid #bbb; padding:6px; background:#f5f5f5; font-weight:bold;">
            Scadenza</td><td style="border:1px solid #bbb; padding:6px;">{safe(welder.get('license_expiry', 'N/A'))}</td></tr>
        <tr><td style="border:1px solid #bbb; padding:6px; background:#f5f5f5; font-weight:bold;">
            Note</td><td style="border:1px solid #bbb; padding:6px;">{safe(welder.get('notes', ''))}</td></tr>
    </table>"""
    return _section_pdf(body)


def _build_controls_page(project: dict) -> bytes:
    """Generate FPC controls checklist page."""
    fpc = project.get("fpc_data", {})
    controls = fpc.get("controls", [])

    rows = ""
    for c in controls:
        icon = "&#10004;" if c.get("checked") else "&#10008;"
        color = "#059669" if c.get("checked") else "#DC2626"
        rows += f"""<tr>
            <td style="border:1px solid #bbb; padding:5px; font-size:9pt;">{safe(c.get('label',''))}</td>
            <td style="border:1px solid #bbb; padding:5px; text-align:center; font-size:14pt; color:{color};">{icon}</td>
            <td style="border:1px solid #bbb; padding:5px; font-size:8pt; color:#666;">{safe(c.get('checked_at','')) if c.get('checked') else ''}</td>
        </tr>"""

    all_ok = all(c.get("checked") for c in controls)
    verdict_color = "#059669" if all_ok else "#DC2626"
    verdict = "TUTTI I CONTROLLI SUPERATI" if all_ok else "CONTROLLI INCOMPLETI"

    body = f"""
    <h1 style="font-size:14pt; text-align:center; margin-bottom:15px;">
        CHECKLIST CONTROLLI FPC
    </h1>
    <p style="font-size:8pt; text-align:center; color:#666; margin-bottom:12px;">
        Classe di esecuzione: {safe(fpc.get('execution_class'))} — WPS: {safe(fpc.get('wps_id','N/A'))}
    </p>
    <table style="width:90%; margin:0 auto; border-collapse:collapse;">
        <thead>
            <tr style="background:#eee;">
                <th style="border:1px solid #999; padding:5px; font-size:8pt; text-align:left;">Controllo</th>
                <th style="border:1px solid #999; padding:5px; font-size:8pt; width:60px;">Esito</th>
                <th style="border:1px solid #999; padding:5px; font-size:8pt; width:120px;">Data</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    <div style="text-align:center; margin-top:25px; font-size:13pt; font-weight:bold; color:{verdict_color};">
        {verdict}
    </div>
    <div style="margin-top:50px;">
        <table style="width:100%; border:none;">
            <tr>
                <td style="border:none; width:50%; font-size:8.5pt;">
                    Responsabile Qualita': ________________________
                </td>
                <td style="border:none; width:50%; text-align:right; font-size:8.5pt;">
                    Data: ________________________
                </td>
            </tr>
        </table>
    </div>"""
    return _section_pdf(body)


def _decode_cert_pdf(base64_str: str) -> bytes:
    """Decode a base64 PDF string (handles data URI prefix)."""
    if "," in base64_str:
        base64_str = base64_str.split(",", 1)[1]
    return base64.b64decode(base64_str)


async def generate_dossier(project_id: str, user_id: str) -> BytesIO:
    """Generate the complete technical dossier for a project.

    Returns a BytesIO with the merged PDF.
    """
    from core.database import db

    # 1. Load project
    project = await db.fpc_projects.find_one(
        {"project_id": project_id, "user_id": user_id}, {"_id": 0}
    )
    if not project:
        raise ValueError("Progetto non trovato")

    # 2. Load company settings
    company = await db.company_settings.find_one(
        {"user_id": user_id}, {"_id": 0}
    ) or {}

    fpc = project.get("fpc_data", {})

    # 3. Load welder
    welder = None
    if fpc.get("welder_id"):
        welder = await db.welders.find_one(
            {"welder_id": fpc["welder_id"]}, {"_id": 0}
        )

    # 4. Load linked batch data (with certificates)
    batch_ids = list(set(
        ln.get("batch_id") for ln in project.get("lines", []) if ln.get("batch_id")
    ))
    batches_data = []
    certs_raw = []
    if batch_ids:
        cursor = db.material_batches.find(
            {"batch_id": {"$in": batch_ids}, "user_id": user_id},
            {"_id": 0}
        )
        batches_data = await cursor.to_list(100)
        for b in batches_data:
            cert = b.pop("certificate_base64", None)
            if cert:
                try:
                    certs_raw.append({
                        "heat_number": b.get("heat_number", ""),
                        "pdf_bytes": _decode_cert_pdf(cert),
                    })
                except Exception as e:
                    logger.warning(f"Failed to decode cert for batch {b.get('batch_id')}: {e}")

    # ── Build individual PDFs ──
    merger = PdfWriter()

    def _add_section(pdf_bytes: bytes):
        reader = PdfReader(BytesIO(pdf_bytes))
        for page in reader.pages:
            merger.add_page(page)

    # Section 1: Cover Page
    _add_section(_build_cover_page(project, company))

    # Section 2: DoP
    _add_section(_build_dop_page(project, company))

    # Section 3: CE Label
    _add_section(_build_ce_label_page(project, company))

    # Section 4: Materials Traceability Summary
    _add_section(_build_materials_summary(project, batches_data))

    # Section 5: Attached Material Certificates (3.1)
    for cert_info in certs_raw:
        try:
            reader = PdfReader(BytesIO(cert_info["pdf_bytes"]))
            for page in reader.pages:
                merger.add_page(page)
        except Exception as e:
            logger.warning(f"Could not merge cert PDF for {cert_info['heat_number']}: {e}")

    # Section 6: Welder Qualification
    if welder:
        _add_section(_build_welder_page(welder))

    # Section 7: FPC Controls Checklist
    _add_section(_build_controls_page(project))

    # ── Merge and return ──
    output = BytesIO()
    merger.write(output)
    output.seek(0)
    return output
