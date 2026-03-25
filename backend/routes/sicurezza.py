"""
Sicurezza & PNRR Compliance — Modulo Sicurezza Operatore + DNSH + CSE Export.

1. Profilo Sicurezza Operatore: scadenzario corsi D.Lgs 81/08, blocco diario se scaduto
2. Archivio DNSH/PNRR: analisi AI per diciture materiale riciclato/sostenibilità
3. Diario Sicurezza Cantiere: checklist + foto panoramica obbligatoria
4. Cartella Documentale CSE: export ZIP (DURC, POS, Attestati, Certificati macchine)
5. Workflow: Targa CE + Scadenzario Manutenzioni post-firma
"""
import io
import os
import uuid
import json
import base64
import zipfile
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.database import db
from core.security import get_current_user, tenant_match
from core.rate_limiter import limiter

router = APIRouter(prefix="/sicurezza", tags=["sicurezza"])
logger = logging.getLogger(__name__)

SICUREZZA_CANTIERE_COLL = "sicurezza_cantiere"
DNSH_COLL = "dnsh_data"
TARGA_COLL = "targhe_ce"
MANUTENZIONI_COLL = "scadenzario_manutenzioni"


# ══════════════════════════════════════════════════════════════
#  1. PROFILO SICUREZZA OPERATORE — Corsi D.Lgs 81/08
# ══════════════════════════════════════════════════════════════

CORSI_OBBLIGATORI = [
    {"codice": "formazione_base", "nome": "Formazione Base Sicurezza (4h)", "durata_mesi": 60},
    {"codice": "formazione_specifica", "nome": "Formazione Specifica Rischio Alto (12h)", "durata_mesi": 60},
    {"codice": "primo_soccorso", "nome": "Primo Soccorso", "durata_mesi": 36},
    {"codice": "antincendio", "nome": "Antincendio Rischio Medio", "durata_mesi": 60},
    {"codice": "lavori_quota", "nome": "Lavori in Quota", "durata_mesi": 60},
    {"codice": "ple", "nome": "PLE (Piattaforme Elevabili)", "durata_mesi": 60},
]


class CorsoSicurezza(BaseModel):
    codice: str
    data_conseguimento: str
    data_scadenza: str
    ente_formatore: Optional[str] = ""
    attestato_doc_id: Optional[str] = ""


@router.get("/corsi-obbligatori")
async def get_corsi_obbligatori():
    """Returns the list of mandatory safety courses."""
    return {"corsi": CORSI_OBBLIGATORI}


@router.post("/operatore/{op_id}/corsi")
async def add_corso_sicurezza(op_id: str, data: CorsoSicurezza, user: dict = Depends(get_current_user)):
    """Add or update a safety course for an operator."""
    await db.operatori.update_one(
        {"op_id": op_id, "admin_id": user["user_id"]},
        {"$pull": {"corsi_sicurezza": {"codice": data.codice}}}
    )
    await db.operatori.update_one(
        {"op_id": op_id, "admin_id": user["user_id"]},
        {"$push": {"corsi_sicurezza": data.model_dump()}}
    )
    logger.info(f"[SICUREZZA] Corso {data.codice} aggiunto a operatore {op_id}")
    return {"message": "Corso aggiunto", "codice": data.codice}


@router.get("/operatore/{op_id}/corsi")
async def get_corsi_operatore(op_id: str, user: dict = Depends(get_current_user)):
    """Get all safety courses for an operator with expiry status."""
    op = await db.operatori.find_one(
        {"op_id": op_id, "admin_id": user["user_id"]},
        {"_id": 0, "op_id": 1, "nome": 1, "corsi_sicurezza": 1}
    )
    if not op:
        raise HTTPException(404, "Operatore non trovato")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    corsi = op.get("corsi_sicurezza", [])
    for c in corsi:
        c["scaduto"] = c.get("data_scadenza", "") < today if c.get("data_scadenza") else False

    return {"operatore": op["nome"], "corsi": corsi}


@router.get("/check-operatore/{op_id}")
async def check_sicurezza_operatore(op_id: str):
    """
    WORKFLOW GATE: Check if an operator can work.
    Returns bloccato=true if any mandatory course is expired or missing.
    Used by Officina timer START to enforce safety compliance.
    """
    op = await db.operatori.find_one(
        {"op_id": op_id},
        {"_id": 0, "op_id": 1, "nome": 1, "corsi_sicurezza": 1, "patentini": 1}
    )
    if not op:
        return {"bloccato": False, "motivi": []}

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    motivi = []

    corsi = op.get("corsi_sicurezza", [])
    corsi_map = {c["codice"]: c for c in corsi}

    for obbligatorio in CORSI_OBBLIGATORI:
        codice = obbligatorio["codice"]
        if codice in corsi_map:
            corso = corsi_map[codice]
            if corso.get("data_scadenza", "") < today:
                motivi.append(f"Corso scaduto: {obbligatorio['nome']} (scad. {corso['data_scadenza']})")
        elif codice in ["formazione_base", "formazione_specifica"]:
            motivi.append(f"Corso mancante: {obbligatorio['nome']}")

    for pat in op.get("patentini", []):
        scadenza = pat.get("scadenza", "")
        if scadenza and scadenza < today:
            motivi.append(f"Patentino scaduto: {pat.get('tipo', 'N/D')} (scad. {scadenza})")

    return {
        "bloccato": len(motivi) > 0,
        "motivi": motivi,
        "operatore": op.get("nome", ""),
    }


# ══════════════════════════════════════════════════════════════
#  2. ARCHIVIO DNSH / PNRR — Requisiti Ambientali
# ══════════════════════════════════════════════════════════════

DNSH_ANALYSIS_PROMPT = """Sei un analista documentale specializzato in requisiti DNSH (Do No Significant Harm) per il PNRR.

Analizza questo documento e cerca TUTTE le diciture relative a:
- Percentuale di materiale riciclato
- Certificazioni ambientali (EPD, ISO 14001, ISO 14025, EMAS)
- Sostenibilita' (prodotto sostenibile, basso impatto ambientale)
- Provenienza (acciaio da forno elettrico, EAF)
- Emissioni CO2 (carbon footprint, GWP)
- Conformita' REACH, RoHS
- CAM (Criteri Ambientali Minimi)

RISPONDI SOLO con JSON:
{
    "ha_riferimenti_dnsh": true/false,
    "percentuale_riciclato": "30%" o null,
    "certificazioni_ambientali": ["EPD", "ISO 14001"],
    "diciture_sostenibilita": ["acciaio da forno elettrico"],
    "conformita_cam": true/false,
    "note": "breve riepilogo"
}"""


@router.post("/dnsh/analyze")
@limiter.limit("10/minute")
async def analyze_dnsh(
    request: Request,
    file: UploadFile = File(...),
    commessa_id: str = Form(""),
    user: dict = Depends(get_current_user),
):
    """AI Vision analysis of a document for DNSH/sustainability keywords."""
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "File troppo grande (max 15MB)")

    image_b64 = base64.b64encode(content).decode("utf-8")

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            return {"analysis": {"error": "EMERGENT_LLM_KEY mancante", "ha_riferimenti_dnsh": False}}

        chat = LlmChat(
            api_key=api_key,
            session_id=f"dnsh-{uuid.uuid4().hex[:8]}",
            system_message=DNSH_ANALYSIS_PROMPT,
        ).with_model("openai", "gpt-4o")

        user_msg = UserMessage(
            text="Analizza questo documento per riferimenti DNSH/sostenibilita'.",
            file_contents=[ImageContent(image_base64=image_b64)],
        )

        response_text = await chat.send_message(user_msg)
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

        result = json.loads(cleaned)
    except Exception as e:
        logger.error(f"DNSH AI analysis failed: {e}")
        result = {"error": str(e), "ha_riferimenti_dnsh": False}

    return {"analysis": result, "commessa_id": commessa_id}


@router.post("/dnsh/save")
async def save_dnsh_data(data: dict, user: dict = Depends(get_current_user)):
    """Save DNSH analysis results for a commessa."""
    now = datetime.now(timezone.utc)
    dnsh_id = f"dnsh_{uuid.uuid4().hex[:10]}"

    doc = {
        "dnsh_id": dnsh_id,
        "commessa_id": data.get("commessa_id", ""),
        "voce_id": data.get("voce_id", ""),
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "ha_riferimenti_dnsh": data.get("ha_riferimenti_dnsh", False),
        "percentuale_riciclato": data.get("percentuale_riciclato"),
        "certificazioni_ambientali": data.get("certificazioni_ambientali", []),
        "diciture_sostenibilita": data.get("diciture_sostenibilita", []),
        "conformita_cam": data.get("conformita_cam", False),
        "note": data.get("note", ""),
        "created_at": now.isoformat(),
    }

    await db[DNSH_COLL].insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/dnsh/{commessa_id}")
async def get_dnsh_data(commessa_id: str, user: dict = Depends(get_current_user)):
    """Get all DNSH data for a commessa."""
    items = await db[DNSH_COLL].find(
        {"commessa_id": commessa_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return {"dnsh_data": items, "count": len(items)}


# ══════════════════════════════════════════════════════════════
#  3. DIARIO SICUREZZA CANTIERE — Checklist + foto panoramica
# ══════════════════════════════════════════════════════════════

SICUREZZA_CANTIERE_CHECKLIST = [
    {"codice": "area_delimitata", "label": "Area delimitata?"},
    {"codice": "dpi_indossati", "label": "DPI indossati?"},
    {"codice": "attrezzature_verificate", "label": "Attrezzature verificate?"},
]


class SicurezzaCantiereSubmit(BaseModel):
    commessa_id: str
    voce_id: str = ""
    operatore_id: str
    operatore_nome: str
    checklist: list
    foto_panoramica_doc_id: str


@router.post("/cantiere")
async def save_sicurezza_cantiere(data: SicurezzaCantiereSubmit):
    """Save safety checklist + mandatory panoramic photo before assembly work."""
    if not data.foto_panoramica_doc_id:
        raise HTTPException(400, "Foto panoramica del cantiere obbligatoria")

    now = datetime.now(timezone.utc)
    sc_id = f"sc_{uuid.uuid4().hex[:10]}"

    doc = {
        "sicurezza_id": sc_id,
        "commessa_id": data.commessa_id,
        "voce_id": data.voce_id or "",
        "operatore_id": data.operatore_id,
        "operatore_nome": data.operatore_nome,
        "checklist": data.checklist,
        "foto_panoramica_doc_id": data.foto_panoramica_doc_id,
        "all_ok": all(c.get("esito", False) for c in data.checklist),
        "created_at": now.isoformat(),
    }

    await db[SICUREZZA_CANTIERE_COLL].insert_one(doc)
    doc.pop("_id", None)

    logger.info(f"[SICUREZZA] Cantiere check saved: {sc_id} — all_ok={doc['all_ok']}")
    return doc


@router.get("/cantiere/{commessa_id}")
async def get_sicurezza_cantiere(commessa_id: str, voce_id: str = ""):
    """Get safety check for a commessa (latest)."""
    query = {"commessa_id": commessa_id}
    if voce_id:
        query["voce_id"] = voce_id
    item = await db[SICUREZZA_CANTIERE_COLL].find_one(
        query, {"_id": 0}, sort=[("created_at", -1)]
    )
    return {"sicurezza": item}


@router.get("/cantiere-checklist")
async def get_sicurezza_checklist():
    """Return the safety checklist items."""
    return {"items": SICUREZZA_CANTIERE_CHECKLIST}


# ══════════════════════════════════════════════════════════════
#  4. CARTELLA DOCUMENTALE CSE — Export ZIP
# ══════════════════════════════════════════════════════════════

@router.post("/export-cse/{commessa_id}")
async def export_cse(commessa_id: str, user: dict = Depends(get_current_user)):
    """Generate ZIP: DURC, POS, operator certifications, machine certificates."""
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id}, {"_id": 0, "numero": 1, "user_id": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    numero = commessa.get("numero", commessa_id)
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # DURC/POS from commessa-specific docs
        safety_docs = await db.commessa_documents.find(
            {"commessa_id": commessa_id, "tipo": {"$in": ["durc", "pos", "dvr", "pimus", "sicurezza"]}},
            {"_id": 0}
        ).to_list(50)
        for doc in safety_docs:
            b64 = doc.get("file_base64", "")
            if b64:
                nome = doc.get("nome_file", doc.get("doc_id", "doc"))
                zf.writestr(f"01_DURC_POS/{nome}", base64.b64decode(b64))

        # Global safety documents (DURC, Visura, White List, Patente a Crediti)
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "company_docs")
        global_docs = await db.company_documents.find(
            {"category": "sicurezza_globale"},
            {"_id": 0}
        ).to_list(20)
        for gdoc in global_docs:
            safe_fn = gdoc.get("safe_filename", "")
            filepath = os.path.join(upload_dir, safe_fn)
            if safe_fn and os.path.exists(filepath):
                tag = (gdoc.get("tags", [None]) or [None])[0] or "doc"
                label = gdoc.get("title", tag).upper().replace(" ", "_")
                filename = gdoc.get("filename", safe_fn)
                with open(filepath, "rb") as f:
                    zf.writestr(f"00_DOCUMENTI_AZIENDA/{label}_{filename}", f.read())

        # Allegati Tecnici POS (Rumore, Vibrazioni, MMC) — solo quelli con includi_pos=True
        allegati_pos = await db.company_documents.find(
            {"category": "allegati_pos", "includi_pos": True},
            {"_id": 0}
        ).to_list(20)
        for adoc in allegati_pos:
            safe_fn = adoc.get("safe_filename", "")
            apath = os.path.join(upload_dir, safe_fn)
            if safe_fn and os.path.exists(apath):
                tag = (adoc.get("tags", [None]) or [None])[0] or "doc"
                label = adoc.get("title", tag).upper().replace(" ", "_")
                filename = adoc.get("filename", safe_fn)
                with open(apath, "rb") as f:
                    zf.writestr(f"05_ALLEGATI_POS/{label}_{filename}", f.read())

        # Attestati operatori
        operators = await db.operatori.find(
            {"admin_id": user["user_id"]}, {"_id": 0, "nome": 1, "corsi_sicurezza": 1}
        ).to_list(50)
        lines = ["NOME;CORSO;CONSEGUIMENTO;SCADENZA;ENTE"]
        for op in operators:
            for c in op.get("corsi_sicurezza", []):
                corso_info = next((o for o in CORSI_OBBLIGATORI if o["codice"] == c.get("codice")), {})
                lines.append(f"{op['nome']};{corso_info.get('nome', c.get('codice', ''))};{c.get('data_conseguimento', '')};{c.get('data_scadenza', '')};{c.get('ente_formatore', '')}")
        zf.writestr("02_ATTESTATI_OPERAI/riepilogo_corsi.csv", "\n".join(lines))

        # Certificati macchine
        attrezzature = await db.attrezzature.find(
            {"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
        ).to_list(50)
        a_lines = ["TIPO;MODELLO;SERIE;MARCA;TARATURA;PROSSIMA"]
        for a in attrezzature:
            a_lines.append(f"{a['tipo']};{a['modello']};{a.get('numero_serie', '')};{a.get('marca', '')};{a.get('data_taratura', '')};{a.get('prossima_taratura', '')}")
        zf.writestr("03_CERTIFICATI_MACCHINE/riepilogo_attrezzature.csv", "\n".join(a_lines))

        # Sicurezza cantiere
        sic = await db[SICUREZZA_CANTIERE_COLL].find({"commessa_id": commessa_id}, {"_id": 0}).to_list(20)
        if sic:
            zf.writestr("04_SICUREZZA_CANTIERE/checklist.json", json.dumps(sic, indent=2, ensure_ascii=False))

        zf.writestr("INFO.txt", f"Cartella CSE — Commessa {numero}\nGenerata: {datetime.now(timezone.utc).isoformat()}\n")

    zip_buffer.seek(0)
    filename = f"CSE_{numero}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.zip"
    return StreamingResponse(
        zip_buffer, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ══════════════════════════════════════════════════════════════
#  5. WORKFLOW: Firma → Targa CE + Scadenzario Manutenzioni
# ══════════════════════════════════════════════════════════════

@router.post("/targa-ce")
async def generate_targa_ce(data: dict):
    """WORKFLOW: Generate CE Plate data with QR code link after client signature."""
    now = datetime.now(timezone.utc)
    commessa_id = data.get("commessa_id", "")
    commessa = await db.commesse.find_one({"commessa_id": commessa_id}, {"_id": 0, "numero": 1, "title": 1, "user_id": 1})
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    targa_id = f"tce_{uuid.uuid4().hex[:10]}"
    numero = commessa.get("numero", commessa_id)
    qr_data = f"CE|{numero}|{targa_id}|{now.strftime('%Y-%m-%d')}"

    targa = {
        "targa_id": targa_id, "commessa_id": commessa_id,
        "montaggio_id": data.get("montaggio_id", ""),
        "numero_commessa": numero, "titolo": commessa.get("title", ""),
        "data_marcatura": now.strftime("%Y-%m-%d"), "qr_data": qr_data,
        "admin_id": commessa["user_id"], "created_at": now.isoformat(),
    }
    await db[TARGA_COLL].insert_one(targa)
    targa.pop("_id", None)
    logger.info(f"[WORKFLOW] Targa CE generata: {targa_id} per {numero}")
    return targa


@router.post("/manutenzione-schedule")
async def create_manutenzione_schedule(data: dict):
    """WORKFLOW: Create maintenance entries at 12 and 24 months after client signature."""
    now = datetime.now(timezone.utc)
    commessa_id = data.get("commessa_id", "")
    commessa = await db.commesse.find_one({"commessa_id": commessa_id}, {"_id": 0, "numero": 1, "title": 1, "user_id": 1, "client_id": 1})
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    schedules = []
    for mesi in [12, 24]:
        from dateutil.relativedelta import relativedelta
        data_scadenza = (now + relativedelta(months=mesi)).strftime("%Y-%m-%d")
        man_id = f"man_{uuid.uuid4().hex[:10]}"
        entry = {
            "manutenzione_id": man_id, "commessa_id": commessa_id,
            "montaggio_id": data.get("montaggio_id", ""),
            "admin_id": commessa["user_id"], "client_id": commessa.get("client_id", ""),
            "numero_commessa": commessa.get("numero", ""),
            "titolo_commessa": commessa.get("title", ""),
            "tipo": f"Manutenzione programmata {mesi} mesi",
            "data_scadenza": data_scadenza, "stato": "programmata",
            "created_at": now.isoformat(),
        }
        await db[MANUTENZIONI_COLL].insert_one(entry)
        entry.pop("_id", None)
        schedules.append(entry)

    logger.info(f"[WORKFLOW] Manutenzioni 12/24 mesi create per {commessa.get('numero', '')}")
    return {"schedules": schedules}


@router.get("/manutenzioni")
async def list_manutenzioni(user: dict = Depends(get_current_user)):
    """List all scheduled maintenances."""
    items = await db[MANUTENZIONI_COLL].find({"admin_id": user["user_id"]}, {"_id": 0}).sort("data_scadenza", 1).to_list(200)
    return {"manutenzioni": items}


@router.get("/targhe-ce")
async def list_targhe(user: dict = Depends(get_current_user)):
    """List all CE plates."""
    items = await db[TARGA_COLL].find({"admin_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"targhe": items}
