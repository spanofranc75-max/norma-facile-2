"""Routes for EN 13241 (Gates) & EN 12453 (Automation) certification."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from core.security import get_current_user
from core.database import db
from models.gate_certification import (
    GateCertificationCreate, GateCertificationUpdate,
    RischioItem, Azionamento
)
import uuid
import logging
from datetime import datetime, timezone
from io import BytesIO

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gate-cert", tags=["Gate Certification"])

# Default risk analysis checklist for motorized gates (EN 12453)
DEFAULT_RISCHI = [
    {"id": "R01", "descrizione": "Schiacciamento bordo primario di chiusura", "presente": True, "misura_adottata": "", "conforme": False},
    {"id": "R02", "descrizione": "Schiacciamento bordo secondario di apertura", "presente": True, "misura_adottata": "", "conforme": False},
    {"id": "R03", "descrizione": "Cesoiamento tra anta e struttura fissa", "presente": True, "misura_adottata": "", "conforme": False},
    {"id": "R04", "descrizione": "Trascinamento e urto (cancelli scorrevoli)", "presente": True, "misura_adottata": "", "conforme": False},
    {"id": "R05", "descrizione": "Caduta dell'anta (cancelli a battente verticali)", "presente": False, "misura_adottata": "", "conforme": False},
    {"id": "R06", "descrizione": "Accesso a parti in movimento (motore, cremagliera)", "presente": True, "misura_adottata": "", "conforme": False},
    {"id": "R07", "descrizione": "Sollevamento non intenzionale (serrande)", "presente": False, "misura_adottata": "", "conforme": False},
    {"id": "R08", "descrizione": "Impigliamento e intrappolamento", "presente": True, "misura_adottata": "", "conforme": False},
]


@router.post("/")
async def create_gate_certification(
    data: GateCertificationCreate,
    user: dict = Depends(get_current_user)
):
    """Create a gate certification record for a commessa."""
    # Verify commessa exists
    commessa = await db.commesse.find_one(
        {"commessa_id": data.commessa_id, "user_id": user["user_id"]},
        {"_id": 0, "commessa_id": 1, "numero": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    # Check if already exists
    existing = await db.gate_certifications.find_one(
        {"commessa_id": data.commessa_id}, {"_id": 0, "cert_id": 1}
    )
    if existing:
        raise HTTPException(409, "Certificazione cancello già esistente per questa commessa")

    now = datetime.now(timezone.utc)
    cert_id = f"gate_{uuid.uuid4().hex[:12]}"

    # Auto-populate risk analysis for motorized gates
    rischi = data.analisi_rischi
    if not rischi and data.azionamento == Azionamento.MOTORIZZATO:
        rischi = [RischioItem(**r) for r in DEFAULT_RISCHI]

    doc = {
        "cert_id": cert_id,
        "commessa_id": data.commessa_id,
        "user_id": user["user_id"],
        "tipo_chiusura": data.tipo_chiusura.value,
        "azionamento": data.azionamento.value,
        "larghezza_mm": data.larghezza_mm,
        "altezza_mm": data.altezza_mm,
        "peso_kg": data.peso_kg,
        "resistenza_vento": data.resistenza_vento.value,
        "permeabilita_aria": data.permeabilita_aria,
        "resistenza_termica": data.resistenza_termica,
        "sicurezza_apertura": data.sicurezza_apertura,
        "sostanze_pericolose": data.sostanze_pericolose,
        "resistenza_acqua": data.resistenza_acqua,
        "analisi_rischi": [r.dict() for r in rischi] if rischi else [],
        "prove_forza": [p.dict() for p in data.prove_forza] if data.prove_forza else [],
        "motore_marca": data.motore_marca,
        "motore_modello": data.motore_modello,
        "motore_matricola": data.motore_matricola,
        "fotocellule": data.fotocellule,
        "costola_sicurezza": data.costola_sicurezza,
        "centralina": data.centralina,
        "telecomando": data.telecomando,
        "strumento_id": data.strumento_id,
        "sistema_cascata": data.sistema_cascata,
        "note": data.note,
        "created_at": now,
        "updated_at": now,
    }
    await db.gate_certifications.insert_one(doc)
    doc.pop("_id", None)

    # Update commessa to link
    await db.commesse.update_one(
        {"commessa_id": data.commessa_id},
        {"$set": {"gate_cert_id": cert_id, "normativa_tipo": "EN_13241", "updated_at": now}}
    )

    return {"message": "Certificazione cancello creata", "certification": doc}


@router.get("/{commessa_id}")
async def get_gate_certification(commessa_id: str, user: dict = Depends(get_current_user)):
    """Get gate certification for a commessa."""
    doc = await db.gate_certifications.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        return {"certification": None}
    return {"certification": doc}


@router.put("/{cert_id}")
async def update_gate_certification(
    cert_id: str,
    data: GateCertificationUpdate,
    user: dict = Depends(get_current_user)
):
    """Update gate certification data."""
    existing = await db.gate_certifications.find_one(
        {"cert_id": cert_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not existing:
        raise HTTPException(404, "Certificazione non trovata")

    update = {k: v for k, v in data.dict(exclude_none=True).items()}
    if "analisi_rischi" in update and update["analisi_rischi"]:
        update["analisi_rischi"] = [r if isinstance(r, dict) else r.dict() for r in update["analisi_rischi"]]
    if "prove_forza" in update and update["prove_forza"]:
        update["prove_forza"] = [p if isinstance(p, dict) else p.dict() for p in update["prove_forza"]]

    update["updated_at"] = datetime.now(timezone.utc)

    await db.gate_certifications.update_one({"cert_id": cert_id}, {"$set": update})
    updated = await db.gate_certifications.find_one({"cert_id": cert_id}, {"_id": 0})
    return {"message": "Aggiornato", "certification": updated}


# ── PDF Generation ──────────────────────────────────────────────

def _gate_pdf_css():
    return """
    body{font-family:Helvetica,Arial,sans-serif;font-size:9pt;color:#1E293B;margin:0;padding:0;}
    .page{padding:20mm 15mm 15mm 15mm;}
    h1{font-size:16pt;color:#0055FF;margin:0 0 4mm 0;}
    h2{font-size:12pt;color:#1E293B;margin:8mm 0 3mm 0;border-bottom:1px solid #e2e8f0;padding-bottom:2mm;}
    table{width:100%;border-collapse:collapse;margin:3mm 0;}
    th,td{border:1px solid #e2e8f0;padding:2mm 3mm;text-align:left;font-size:8.5pt;}
    th{background:#f1f5f9;font-weight:700;font-size:8pt;text-transform:uppercase;color:#64748b;}
    .ok{color:#059669;font-weight:700;} .ko{color:#dc2626;font-weight:700;} .npd{color:#94a3b8;}
    .header{display:flex;justify-content:space-between;border-bottom:2px solid #0055FF;padding-bottom:3mm;margin-bottom:5mm;}
    .info td{border:none;padding:1mm 3mm;} .info .lbl{font-weight:700;width:35%;color:#64748b;}
    .ce-label{border:3px solid #1E293B;padding:8mm;margin:5mm 0;text-align:center;}
    .ce-label .ce{font-size:36pt;font-weight:900;letter-spacing:3mm;}
    .note-box{background:#fefce8;border:1px solid #fde68a;border-radius:2mm;padding:3mm;font-size:8pt;color:#92400e;}
    """


@router.get("/{commessa_id}/dop-pdf")
async def generate_dop_pdf(commessa_id: str, user: dict = Depends(get_current_user)):
    """Generate Declaration of Performance (DoP) PDF per EN 13241."""
    cert = await db.gate_certifications.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not cert:
        raise HTTPException(404, "Certificazione non trovata")

    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id}, {"_id": 0, "numero": 1, "title": 1, "client_id": 1}
    )
    client_name = ""
    if commessa and commessa.get("client_id"):
        cl = await db.clients.find_one({"client_id": commessa["client_id"]}, {"_id": 0, "business_name": 1})
        client_name = cl.get("business_name", "") if cl else ""

    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

    tipo_label = cert.get("tipo_chiusura", "").replace("_", " ").title()
    vento = cert.get("resistenza_vento", "NPD")
    num = commessa.get("numero", "") if commessa else ""

    html = f"""<!DOCTYPE html><html><head><style>{_gate_pdf_css()}</style></head><body>
    <div class="page">
        <h1>DICHIARAZIONE DI PRESTAZIONE (DoP)</h1>
        <p style="font-size:8pt;color:#64748b;">Ai sensi del Regolamento (UE) n. 305/2011</p>

        <h2>1. Identificazione del Prodotto</h2>
        <table class="info">
            <tr><td class="lbl">Tipo di prodotto:</td><td>{tipo_label}</td></tr>
            <tr><td class="lbl">Azionamento:</td><td>{cert.get("azionamento", "").title()}</td></tr>
            <tr><td class="lbl">Norma armonizzata:</td><td>EN 13241:2003+A2:2016</td></tr>
            <tr><td class="lbl">Commessa:</td><td>{num} — {commessa.get("title", "") if commessa else ""}</td></tr>
            <tr><td class="lbl">Cliente:</td><td>{client_name or "—"}</td></tr>
            <tr><td class="lbl">Dimensioni:</td><td>{cert.get("larghezza_mm") or "—"} x {cert.get("altezza_mm") or "—"} mm</td></tr>
            <tr><td class="lbl">Peso:</td><td>{cert.get("peso_kg") or "—"} kg</td></tr>
        </table>

        <h2>2. Fabbricante</h2>
        <table class="info">
            <tr><td class="lbl">Ragione Sociale:</td><td>{company.get("business_name", "")}</td></tr>
            <tr><td class="lbl">Indirizzo:</td><td>{company.get("address", "")} {company.get("cap", "")} {company.get("city", "")}</td></tr>
            <tr><td class="lbl">P.IVA:</td><td>{company.get("partita_iva", "")}</td></tr>
        </table>

        {"<h2>3. Sistema di Cascata</h2><p>Sistema di valutazione: <strong>" + cert.get("sistema_cascata", "") + "</strong></p>" if cert.get("sistema_cascata") else ""}

        <h2>{"4" if cert.get("sistema_cascata") else "3"}. Prestazioni Dichiarate</h2>
        <table>
            <thead><tr><th>Caratteristica essenziale</th><th>Norma</th><th>Prestazione</th></tr></thead>
            <tbody>
                <tr><td>Resistenza al carico del vento</td><td>EN 12424</td><td><strong>{vento}</strong></td></tr>
                <tr><td>Permeabilit&agrave; all'aria</td><td>EN 12426</td><td>{_npd(cert.get("permeabilita_aria", "NPD"))}</td></tr>
                <tr><td>Resistenza termica</td><td>EN 12428</td><td>{_npd(cert.get("resistenza_termica", "NPD"))}</td></tr>
                <tr><td>Sicurezza apertura</td><td>EN 13241</td><td class="ok">{cert.get("sicurezza_apertura", "Conforme")}</td></tr>
                <tr><td>Sostanze pericolose</td><td>EN 13241</td><td>{_npd(cert.get("sostanze_pericolose", "NPD"))}</td></tr>
                <tr><td>Resistenza all'acqua</td><td>EN 12425</td><td>{_npd(cert.get("resistenza_acqua", "NPD"))}</td></tr>
            </tbody>
        </table>

        <p style="margin-top:8mm;font-size:8pt;">
            La presente dichiarazione di prestazione &egrave; rilasciata sotto la responsabilit&agrave; esclusiva del fabbricante.
        </p>
        <p style="margin-top:10mm;font-size:8pt;">
            Data: {datetime.now().strftime("%d/%m/%Y")}<br/>
            Firma: ______________________________
        </p>
    </div>
    </body></html>"""

    pdf_bytes = _render_gate_pdf(html)
    output = BytesIO(pdf_bytes)
    return StreamingResponse(output, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="DoP_{num}.pdf"'
    })


@router.get("/{commessa_id}/ce-label-pdf")
async def generate_ce_label_pdf(commessa_id: str, user: dict = Depends(get_current_user)):
    """Generate CE Label PDF for the gate."""
    cert = await db.gate_certifications.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not cert:
        raise HTTPException(404, "Certificazione non trovata")

    commessa = await db.commesse.find_one({"commessa_id": commessa_id}, {"_id": 0, "numero": 1})
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

    tipo_label = cert.get("tipo_chiusura", "").replace("_", " ").title()
    num = commessa.get("numero", "") if commessa else ""

    html = f"""<!DOCTYPE html><html><head><style>{_gate_pdf_css()}
    @page {{ size: 148mm 105mm; margin: 5mm; }}
    </style></head><body>
    <div style="padding:5mm;">
        <div class="ce-label">
            <div class="ce">CE</div>
            <p style="font-size:10pt;font-weight:700;margin:3mm 0 1mm 0;">{company.get("business_name", "")}</p>
            <p style="font-size:7pt;color:#64748b;">{company.get("address", "")} {company.get("cap", "")} {company.get("city", "")}</p>
            <hr style="margin:3mm 0;border:none;border-top:1px solid #ccc;"/>
            <table style="width:90%;margin:0 auto;font-size:8pt;border:none;">
                <tr><td style="border:none;text-align:right;width:50%;font-weight:700;padding:1mm;">Tipo:</td><td style="border:none;text-align:left;padding:1mm;">{tipo_label}</td></tr>
                <tr><td style="border:none;text-align:right;font-weight:700;padding:1mm;">Norma:</td><td style="border:none;text-align:left;padding:1mm;">EN 13241:2003+A2:2016</td></tr>
                <tr><td style="border:none;text-align:right;font-weight:700;padding:1mm;">Dimensioni:</td><td style="border:none;text-align:left;padding:1mm;">{cert.get("larghezza_mm") or "—"} x {cert.get("altezza_mm") or "—"} mm</td></tr>
                <tr><td style="border:none;text-align:right;font-weight:700;padding:1mm;">Vento:</td><td style="border:none;text-align:left;padding:1mm;">{cert.get("resistenza_vento", "NPD")}</td></tr>
                <tr><td style="border:none;text-align:right;font-weight:700;padding:1mm;">Commessa:</td><td style="border:none;text-align:left;padding:1mm;">{num}</td></tr>
                <tr><td style="border:none;text-align:right;font-weight:700;padding:1mm;">Anno:</td><td style="border:none;text-align:left;padding:1mm;">{datetime.now().year}</td></tr>
            </table>
        </div>
    </div>
    </body></html>"""

    pdf_bytes = _render_gate_pdf(html)
    output = BytesIO(pdf_bytes)
    return StreamingResponse(output, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="Etichetta_CE_{num}.pdf"'
    })


@router.get("/{commessa_id}/maintenance-pdf")
async def generate_maintenance_register_pdf(commessa_id: str, user: dict = Depends(get_current_user)):
    """Generate empty Maintenance Register (Registro Manutenzione) for motorized gates."""
    cert = await db.gate_certifications.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not cert:
        raise HTTPException(404, "Certificazione non trovata")

    commessa = await db.commesse.find_one({"commessa_id": commessa_id}, {"_id": 0, "numero": 1, "title": 1})
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    client_name = ""
    if commessa and commessa.get("client_id"):
        cl = await db.clients.find_one({"client_id": commessa.get("client_id")}, {"_id": 0, "business_name": 1})
        client_name = cl.get("business_name", "") if cl else ""

    num = commessa.get("numero", "") if commessa else ""
    tipo_label = cert.get("tipo_chiusura", "").replace("_", " ").title()

    # 12 empty rows for maintenance entries
    rows = ""
    for _ in range(12):
        rows += "<tr><td style='height:8mm;'></td><td></td><td></td><td></td><td></td></tr>"

    html = f"""<!DOCTYPE html><html><head><style>{_gate_pdf_css()}</style></head><body>
    <div class="page">
        <h1>REGISTRO DI MANUTENZIONE</h1>
        <p style="font-size:8pt;color:#64748b;">Obbligatorio ai sensi della Direttiva Macchine 2006/42/CE — Cancelli motorizzati</p>

        <h2>Dati Impianto</h2>
        <table class="info">
            <tr><td class="lbl">Tipo:</td><td>{tipo_label} — {cert.get("azionamento", "").title()}</td></tr>
            <tr><td class="lbl">Commessa:</td><td>{num} — {commessa.get("title", "") if commessa else ""}</td></tr>
            <tr><td class="lbl">Cliente:</td><td>{client_name or "—"}</td></tr>
            <tr><td class="lbl">Installatore:</td><td>{company.get("business_name", "")}</td></tr>
            <tr><td class="lbl">Motore:</td><td>{cert.get("motore_marca", "")} {cert.get("motore_modello", "")} — Matr. {cert.get("motore_matricola", "")}</td></tr>
            <tr><td class="lbl">Fotocellule:</td><td>{cert.get("fotocellule", "")}</td></tr>
            <tr><td class="lbl">Costa sensibile:</td><td>{cert.get("costola_sicurezza", "")}</td></tr>
            <tr><td class="lbl">Centralina:</td><td>{cert.get("centralina", "")}</td></tr>
        </table>

        <h2>Registro Interventi</h2>
        <table>
            <thead><tr><th>Data</th><th>Tipo Intervento</th><th>Descrizione</th><th>Tecnico</th><th>Firma</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>

        <div class="note-box" style="margin-top:5mm;">
            La manutenzione programmata deve essere effettuata almeno ogni 6 mesi per cancelli ad uso residenziale
            e ogni 3 mesi per uso industriale/condominiale.
        </div>
    </div>
    </body></html>"""

    pdf_bytes = _render_gate_pdf(html)
    output = BytesIO(pdf_bytes)
    return StreamingResponse(output, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="Registro_Manutenzione_{num}.pdf"'
    })


@router.get("/{commessa_id}/dichiarazione-ce-pdf")
async def generate_ce_declaration_pdf(commessa_id: str, user: dict = Depends(get_current_user)):
    """Generate CE Declaration (Dichiarazione CE di Conformita) for motorized gate assembly."""
    cert = await db.gate_certifications.find_one(
        {"commessa_id": commessa_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not cert:
        raise HTTPException(404, "Certificazione non trovata")

    commessa = await db.commesse.find_one({"commessa_id": commessa_id}, {"_id": 0, "numero": 1, "title": 1, "client_id": 1})
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    client_name = ""
    if commessa and commessa.get("client_id"):
        cl = await db.clients.find_one({"client_id": commessa.get("client_id")}, {"_id": 0, "business_name": 1})
        client_name = cl.get("business_name", "") if cl else ""

    num = commessa.get("numero", "") if commessa else ""
    tipo_label = cert.get("tipo_chiusura", "").replace("_", " ").title()

    # Risk analysis table
    risk_rows = ""
    for r in cert.get("analisi_rischi", []):
        if r.get("presente"):
            stato = '<span class="ok">CONFORME</span>' if r.get("conforme") else '<span class="ko">DA VERIFICARE</span>'
            risk_rows += f"""<tr>
                <td>{r.get("id", "")}</td>
                <td>{r.get("descrizione", "")}</td>
                <td>{r.get("misura_adottata", "—")}</td>
                <td style="text-align:center;">{stato}</td>
            </tr>"""

    # Force test table
    force_rows = ""
    for p in cert.get("prove_forza", []):
        stato = '<span class="ok">OK</span>' if p.get("conforme") else '<span class="ko">KO</span>'
        force_rows += f"""<tr>
            <td>{p.get("punto_misura", "").replace("_", " ").title()}</td>
            <td>{p.get("forza_dinamica_n", "—")} N</td>
            <td>{p.get("forza_statica_n", "—")} N</td>
            <td style="text-align:center;">{stato}</td>
        </tr>"""

    html = f"""<!DOCTYPE html><html><head><style>{_gate_pdf_css()}</style></head><body>
    <div class="page">
        <h1>DICHIARAZIONE CE DI CONFORMIT&Agrave;</h1>
        <p style="font-size:8pt;color:#64748b;">Ai sensi della Direttiva Macchine 2006/42/CE</p>

        <h2>1. Identificazione</h2>
        <table class="info">
            <tr><td class="lbl">Tipo:</td><td>{tipo_label}</td></tr>
            <tr><td class="lbl">Azionamento:</td><td>{cert.get("azionamento", "").title()}</td></tr>
            <tr><td class="lbl">Dimensioni:</td><td>{cert.get("larghezza_mm") or "—"} x {cert.get("altezza_mm") or "—"} mm — Peso: {cert.get("peso_kg") or "—"} kg</td></tr>
            <tr><td class="lbl">Commessa:</td><td>{num} — {commessa.get("title", "") if commessa else ""}</td></tr>
            <tr><td class="lbl">Cliente:</td><td>{client_name or "—"}</td></tr>
        </table>

        <h2>2. Fabbricante / Installatore</h2>
        <table class="info">
            <tr><td class="lbl">Ragione Sociale:</td><td>{company.get("business_name", "")}</td></tr>
            <tr><td class="lbl">Indirizzo:</td><td>{company.get("address", "")} {company.get("cap", "")} {company.get("city", "")}</td></tr>
        </table>

        <h2>3. Componenti Installati</h2>
        <table class="info">
            <tr><td class="lbl">Motore:</td><td>{cert.get("motore_marca", "")} {cert.get("motore_modello", "")} — Matr. {cert.get("motore_matricola", "")}</td></tr>
            <tr><td class="lbl">Fotocellule:</td><td>{cert.get("fotocellule", "")}</td></tr>
            <tr><td class="lbl">Costa sensibile:</td><td>{cert.get("costola_sicurezza", "")}</td></tr>
            <tr><td class="lbl">Centralina:</td><td>{cert.get("centralina", "")}</td></tr>
        </table>

        {"<h2>4. Analisi dei Rischi (EN 12453)</h2><table><thead><tr><th>ID</th><th>Rischio</th><th>Misura adottata</th><th>Esito</th></tr></thead><tbody>" + risk_rows + "</tbody></table>" if risk_rows else ""}

        {"<h2>5. Prove di Forza (EN 12453)</h2><div class='note-box' style='margin-bottom:3mm;'>Limiti: Forza dinamica &lt; 400N — Forza statica residua &lt; 150N</div><table><thead><tr><th>Punto di misura</th><th>F. Dinamica</th><th>F. Statica</th><th>Esito</th></tr></thead><tbody>" + force_rows + "</tbody></table>" if force_rows else ""}

        <h2>{"6" if risk_rows or force_rows else "4"}. Norme applicate</h2>
        <table class="info">
            <tr><td class="lbl">Prodotto:</td><td>EN 13241:2003+A2:2016</td></tr>
            {"<tr><td class='lbl'>Automazione:</td><td>EN 12453:2017 — EN 12445:2000</td></tr>" if cert.get("azionamento") == "motorizzato" else ""}
            <tr><td class="lbl">Direttiva:</td><td>2006/42/CE (Macchine) — Reg. (UE) 305/2011 (CPR)</td></tr>
        </table>

        <p style="margin-top:8mm;font-size:8pt;">
            Il sottoscritto dichiara sotto la propria responsabilit&agrave; che il prodotto sopra descritto
            &egrave; conforme alle disposizioni delle direttive e norme citate.
        </p>
        <p style="margin-top:10mm;font-size:8pt;">
            Data: {datetime.now().strftime("%d/%m/%Y")}<br/>
            Firma: ______________________________
        </p>
    </div>
    </body></html>"""

    pdf_bytes = _render_gate_pdf(html)
    output = BytesIO(pdf_bytes)
    return StreamingResponse(output, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="Dichiarazione_CE_{num}.pdf"'
    })


def _npd(val):
    if not val or val.upper() == "NPD":
        return '<span class="npd">NPD</span>'
    return val


def _render_gate_pdf(html: str) -> bytes:
    """Render HTML to PDF using WeasyPrint."""
    from weasyprint import HTML
    return HTML(string=html).write_pdf()
