"""Conto Lavoro (Subcontracting) — verniciatura, zincatura, sabbiatura, DDT, NCR."""
import base64
import uuid
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO

from core.database import db
from core.security import get_current_user
from routes.commessa_ops_common import (
    COLL, DOC_COLL, get_commessa_or_404, ensure_ops_fields,
    ts, new_id, push_event, build_update_with_event,
)

router = APIRouter()
logger = logging.getLogger(__name__)


class RigaCL(BaseModel):
    descrizione: str
    quantita: float = 0
    unita: str = "pz"
    peso_kg: float = 0
    note: str = ""

class ContoLavoroCreate(BaseModel):
    tipo: str  # verniciatura, zincatura, sabbiatura, altro
    fornitore_nome: str
    fornitore_id: Optional[str] = None
    note: Optional[str] = ""
    ral: Optional[str] = ""  # RAL color for verniciatura
    righe: List[dict] = []
    causale_trasporto: str = "Conto Lavorazione"

class ContoLavoroUpdate(BaseModel):
    stato: str  # da_inviare, inviato, in_lavorazione, rientrato, verificato
    ddt_invio_id: Optional[str] = None
    ddt_rientro_id: Optional[str] = None
    certificato_doc_id: Optional[str] = None
    note: Optional[str] = None


class RientroData(BaseModel):
    data_rientro: Optional[str] = None
    ddt_fornitore_numero: Optional[str] = ""
    ddt_fornitore_data: Optional[str] = ""
    peso_rientrato_kg: Optional[float] = 0
    esito_qc: Optional[str] = "conforme"  # conforme, non_conforme, conforme_con_riserva
    note_rientro: Optional[str] = ""
    motivo_non_conformita: Optional[str] = ""


@router.post("/{cid}/conto-lavoro")
async def create_conto_lavoro(cid: str, data: ContoLavoroCreate, user: dict = Depends(get_current_user)):
    await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    cl = {
        "cl_id": new_id("cl_"),
        "tipo": data.tipo,
        "fornitore_nome": data.fornitore_nome,
        "fornitore_id": data.fornitore_id or "",
        "stato": "da_inviare",
        "ral": data.ral or "",
        "righe": data.righe or [],
        "causale_trasporto": data.causale_trasporto or "Conto Lavorazione",
        "ddt_invio_id": None,
        "ddt_rientro_id": None,
        "certificato_doc_id": None,
        "note": data.note or "",
        "stato_email": None,
        "data_invio": None,
        "data_rientro": None,
        "created_at": ts().isoformat(),
    }
    await db[COLL].update_one(
        {"commessa_id": cid},
        build_update_with_event(
            push_items={"conto_lavoro": cl},
            tipo="CL_CREATO", user=user, note=f"C/L {data.tipo} → {data.fornitore_nome}"
        ),
    )
    return {"message": f"Conto lavoro creato: {data.tipo}", "conto_lavoro": cl}


@router.put("/{cid}/conto-lavoro/{cl_id}")
async def update_conto_lavoro(cid: str, cl_id: str, data: ContoLavoroUpdate, user: dict = Depends(get_current_user)):
    comm = await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    upd = {"conto_lavoro.$[elem].stato": data.stato}
    if data.stato == "inviato":
        upd["conto_lavoro.$[elem].data_invio"] = ts().isoformat()
    if data.stato == "rientrato":
        upd["conto_lavoro.$[elem].data_rientro"] = ts().isoformat()
    if data.ddt_invio_id is not None:
        upd["conto_lavoro.$[elem].ddt_invio_id"] = data.ddt_invio_id
    if data.ddt_rientro_id is not None:
        upd["conto_lavoro.$[elem].ddt_rientro_id"] = data.ddt_rientro_id
    if data.certificato_doc_id is not None:
        upd["conto_lavoro.$[elem].certificato_doc_id"] = data.certificato_doc_id
    if data.note is not None:
        upd["conto_lavoro.$[elem].note"] = data.note

    # ── Auto-create DDT when transitioning to "inviato" ──
    ddt_invio_id = None
    if data.stato == "inviato":
        cl_list = comm.get("conto_lavoro", [])
        cl_item = next((c for c in cl_list if c.get("cl_id") == cl_id), None)
        if cl_item and not cl_item.get("ddt_invio_id"):
            comm_num = comm.get("numero", cid)
            year = ts().strftime("%Y")
            ddt_count = await db.ddt_documents.count_documents({"user_id": user["user_id"]})
            ddt_invio_id = f"ddt_{uuid.uuid4().hex[:12]}"
            ddt_number = f"DDT-{year}-{ddt_count + 1:04d}"
            tipo_lav = cl_item.get("tipo", "lavorazione")
            fornitore = cl_item.get("fornitore_nome", "")
            lines = []
            for r in cl_item.get("righe", []):
                lines.append({
                    "description": r.get("descrizione", r.get("description", "")),
                    "quantity": r.get("quantita", r.get("quantity", 1)),
                    "unit": r.get("um", r.get("unit", "pz")),
                    "weight": f'{r.get("peso_kg", 0)} kg',
                    "unit_price": 0, "sconto_1": 0, "sconto_2": 0, "vat_rate": "22",
                    "notes": r.get("note", ""),
                })
            now = ts()
            ddt_doc = {
                "ddt_id": ddt_invio_id,
                "user_id": user["user_id"],
                "number": ddt_number,
                "ddt_type": "conto_lavoro",
                "ddt_type_label": f"DDT C/Lavoro — {tipo_lav.capitalize()}",
                "client_id": cl_item.get("fornitore_id", ""),
                "client_name": fornitore,
                "subject": f"C/Lavoro {tipo_lav} — Commessa {comm_num}",
                "destinazione": {},
                "causale_trasporto": cl_item.get("causale_trasporto", "Conto Lavorazione"),
                "aspetto_beni": "Strutture metalliche",
                "vettore": "", "mezzo_trasporto": "Mittente", "porto": "Franco",
                "data_ora_trasporto": now.strftime("%d/%m/%Y %H:%M"),
                "num_colli": 1,
                "peso_lordo_kg": sum(float(r.get("peso_kg", 0)) for r in cl_item.get("righe", [])),
                "peso_netto_kg": sum(float(r.get("peso_kg", 0)) for r in cl_item.get("righe", [])),
                "stampa_prezzi": False,
                "riferimento": f"Commessa {comm_num} — C/L {tipo_lav}",
                "notes": cl_item.get("note", ""),
                "lines": lines,
                "totals": {"subtotal": 0, "total": 0, "line_count": len(lines)},
                "status": "non_fatturato",
                "commessa_id": cid,
                "cl_id": cl_id,
                "created_at": now,
                "updated_at": now,
            }
            await db.ddt_documents.insert_one(ddt_doc)
            upd["conto_lavoro.$[elem].ddt_invio_id"] = ddt_invio_id

    await db[COLL].update_one(
        {"commessa_id": cid},
        {"$set": upd},
        array_filters=[{"elem.cl_id": cl_id}],
    )
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, f"CL_{data.stato.upper()}", user, f"C/L {cl_id} → {data.stato}"))
    result = {"message": f"Conto lavoro aggiornato: {data.stato}"}
    if ddt_invio_id:
        result["ddt_invio_id"] = ddt_invio_id
    return result


# ── Rientro ──
@router.post("/{cid}/conto-lavoro/{cl_id}/rientro")
async def registra_rientro_cl(
    cid: str, cl_id: str,
    data_rientro: str = Form(""),
    ddt_fornitore_numero: str = Form(""),
    ddt_fornitore_data: str = Form(""),
    peso_rientrato_kg: float = Form(0),
    esito_qc: str = Form("conforme"),
    note_rientro: str = Form(""),
    motivo_non_conformita: str = Form(""),
    certificato_file: Optional[UploadFile] = File(None),
    user: dict = Depends(get_current_user),
):
    """Register material return from subcontractor with document upload."""
    comm = await get_commessa_or_404(cid, user["user_id"])
    cl_list = comm.get("conto_lavoro", [])
    cl = next((c for c in cl_list if c["cl_id"] == cl_id), None)
    if not cl:
        raise HTTPException(404, "Conto Lavoro non trovato")
    if cl.get("stato") not in ("inviato", "in_lavorazione"):
        raise HTTPException(400, f"Stato attuale '{cl.get('stato')}' non consente il rientro")

    if not data_rientro:
        data_rientro = ts().strftime("%Y-%m-%d")

    # Save uploaded certificate
    cert_b64 = None
    cert_filename = None
    if certificato_file:
        cert_bytes = await certificato_file.read()
        cert_b64 = base64.b64encode(cert_bytes).decode("utf-8")
        cert_filename = certificato_file.filename

    upd = {
        "conto_lavoro.$[elem].stato": "rientrato",
        "conto_lavoro.$[elem].data_rientro": data_rientro,
        "conto_lavoro.$[elem].ddt_fornitore_numero": ddt_fornitore_numero,
        "conto_lavoro.$[elem].ddt_fornitore_data": ddt_fornitore_data,
        "conto_lavoro.$[elem].peso_rientrato_kg": peso_rientrato_kg,
        "conto_lavoro.$[elem].esito_qc": esito_qc,
        "conto_lavoro.$[elem].note_rientro": note_rientro,
        "conto_lavoro.$[elem].motivo_non_conformita": motivo_non_conformita if esito_qc == "non_conforme" else "",
    }
    if cert_b64:
        upd["conto_lavoro.$[elem].certificato_rientro_base64"] = cert_b64
        upd["conto_lavoro.$[elem].certificato_rientro_filename"] = cert_filename

    await db[COLL].update_one(
        {"commessa_id": cid},
        {"$set": upd},
        array_filters=[{"elem.cl_id": cl_id}],
    )
    await db[COLL].update_one(
        {"commessa_id": cid},
        push_event(cid, "CL_RIENTRATO", user, f"C/L {cl.get('tipo','')} rientrato — QC: {esito_qc}")
    )
    return {
        "message": f"Rientro registrato — Esito QC: {esito_qc}",
        "stato": "rientrato",
        "esito_qc": esito_qc,
    }


# ── Verifica ──
@router.patch("/{cid}/conto-lavoro/{cl_id}/verifica")
async def verifica_cl(cid: str, cl_id: str, user: dict = Depends(get_current_user)):
    """Verify returned material — closes C/L, updates production phase, links cert to fascicolo."""
    comm = await get_commessa_or_404(cid, user["user_id"])
    cl_list = comm.get("conto_lavoro", [])
    cl = next((c for c in cl_list if c["cl_id"] == cl_id), None)
    if not cl:
        raise HTTPException(404, "Conto Lavoro non trovato")
    if cl.get("stato") != "rientrato":
        raise HTTPException(400, "Il C/L deve essere nello stato 'rientrato' per la verifica")

    upd = {"conto_lavoro.$[elem].stato": "verificato"}
    await db[COLL].update_one(
        {"commessa_id": cid}, {"$set": upd},
        array_filters=[{"elem.cl_id": cl_id}],
    )

    # Auto-complete related production phase (trattamenti superficiali)
    tipo_cl = (cl.get("tipo") or "").lower()
    fase_map = {
        "verniciatura": "trattamenti superficiali",
        "zincatura": "trattamenti superficiali",
        "sabbiatura": "sabbiatura",
        "galvanica": "trattamenti superficiali",
    }
    fase_target = fase_map.get(tipo_cl, "trattamenti superficiali")
    fasi = comm.get("fasi_produzione", [])
    for i, f in enumerate(fasi):
        nome = (f.get("nome") or "").lower()
        if fase_target in nome or tipo_cl in nome:
            await db[COLL].update_one(
                {"commessa_id": cid},
                {"$set": {
                    f"fasi_produzione.{i}.stato": "completata",
                    f"fasi_produzione.{i}.progresso": 100,
                    f"fasi_produzione.{i}.data_completamento": ts().isoformat(),
                }},
            )
            break

    # Link certificate to document repository (if uploaded)
    cert_b64 = cl.get("certificato_rientro_base64")
    if cert_b64:
        doc_id = new_id("doc_")
        tipo_cert = f"certificato_{cl.get('tipo', 'trattamento')}"
        doc_entry = {
            "doc_id": doc_id,
            "titolo": f"Certificato {cl.get('tipo','').capitalize()} — {cl.get('fornitore_nome','')}",
            "tipo": tipo_cert,
            "source": "conto_lavoro_rientro",
            "cl_id": cl_id,
            "uploaded_at": ts().isoformat(),
            "filename": cl.get("certificato_rientro_filename", "certificato.pdf"),
        }
        await db[COLL].update_one(
            {"commessa_id": cid},
            {"$push": {"documenti": doc_entry}},
        )

        # Also save to commessa_documents for Pulsante Magico
        await db.commessa_documents.insert_one({
            "doc_id": doc_id,
            "commessa_id": cid,
            "nome_file": cl.get("certificato_rientro_filename", "certificato.pdf"),
            "titolo": f"Cert. {cl.get('tipo','').capitalize()} — {cl.get('fornitore_nome','')}",
            "tipo": tipo_cert,
            "content_type": "application/pdf",
            "file_base64": cert_b64,
            "uploaded_at": ts().isoformat(),
            "metadata_estratti": {
                "source": "conto_lavoro_rientro",
                "cl_id": cl_id,
                "tipo_trattamento": cl.get("tipo", ""),
                "fornitore": cl.get("fornitore_nome", ""),
                "esito_qc": cl.get("esito_qc", "conforme"),
                "ral": cl.get("ral", ""),
            },
        })

    await db[COLL].update_one(
        {"commessa_id": cid},
        push_event(cid, "CL_VERIFICATO", user, f"C/L {cl.get('tipo','')} verificato e chiuso")
    )
    return {"message": "Conto lavoro verificato e chiuso", "stato": "verificato"}


# ── NCR PDF ──
@router.get("/{cid}/conto-lavoro/{cl_id}/ncr-pdf")
async def generate_ncr_pdf(cid: str, cl_id: str, user: dict = Depends(get_current_user)):
    """Generate Non-Conformity Report when QC fails."""
    comm = await get_commessa_or_404(cid, user["user_id"])
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    cl_list = comm.get("conto_lavoro", [])
    cl = next((c for c in cl_list if c["cl_id"] == cl_id), None)
    if not cl:
        raise HTTPException(404, "Conto Lavoro non trovato")

    from services.pdf_ncr import generate_ncr_pdf as gen_ncr
    pdf_buf = gen_ncr(company, comm, cl)
    filename = f"NCR_{cl.get('tipo','')}_{cl_id}.pdf"
    return StreamingResponse(
        pdf_buf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── DDT Preview PDF ──
@router.get("/{cid}/conto-lavoro/{cl_id}/preview-pdf")
async def preview_cl_pdf(cid: str, cl_id: str, user: dict = Depends(get_current_user)):
    """Generate DDT PDF for Conto Lavoro."""
    comm = await get_commessa_or_404(cid, user["user_id"])
    cl_list = comm.get("conto_lavoro", [])
    cl = next((c for c in cl_list if c["cl_id"] == cl_id), None)
    if not cl:
        raise HTTPException(404, "Conto lavoro non trovato")

    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

    from services.pdf_procurement import generate_cl_pdf

    pdf_bytes = generate_cl_pdf(cl, comm, company)

    return StreamingResponse(
        BytesIO(pdf_bytes), media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="DDT_CL_{cl_id}.pdf"'}
    )


# ── DDT Preview Email ──
@router.get("/{cid}/conto-lavoro/{cl_id}/preview-email")
async def preview_cl_email(cid: str, cl_id: str, user: dict = Depends(get_current_user)):
    """Preview email for Conto Lavoro DDT."""
    comm = await get_commessa_or_404(cid, user["user_id"])
    cl_list = comm.get("conto_lavoro", [])
    cl = next((c for c in cl_list if c["cl_id"] == cl_id), None)
    if not cl:
        raise HTTPException(404, "Conto lavoro non trovato")

    fornitore_id = cl.get("fornitore_id")
    to_email = ""
    if fornitore_id:
        forn = await db.clients.find_one({"client_id": fornitore_id, "user_id": user["user_id"]}, {"_id": 0})
        if forn:
            to_email = forn.get("pec") or forn.get("email") or ""
            if not to_email:
                for c in forn.get("contacts", []):
                    if c.get("email"):
                        to_email = c["email"]
                        break

    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

    from services.email_preview import build_cl_email
    preview = build_cl_email(
        fornitore_nome=cl.get("fornitore_nome", ""),
        tipo=cl.get("tipo", ""),
        ral=cl.get("ral", ""),
        commessa_numero=comm.get("numero", "N/D"),
        company_name=company.get("business_name", ""),
    )
    return {
        "to_email": to_email,
        "to_name": cl.get("fornitore_nome", ""),
        "subject": preview["subject"],
        "html_body": preview["html_body"],
        "has_attachment": True,
        "attachment_name": f"DDT_CL_{cl_id}.pdf",
    }



# ── DDT Send Email ──
@router.post("/{cid}/conto-lavoro/{cl_id}/send-email")
async def send_cl_email(cid: str, cl_id: str, payload: dict = None, user: dict = Depends(get_current_user)):
    """Send DDT Conto Lavoro via email to the supplier."""
    payload = payload or {}
    comm = await get_commessa_or_404(cid, user["user_id"])
    cl_list = comm.get("conto_lavoro", [])
    cl = next((c for c in cl_list if c["cl_id"] == cl_id), None)
    if not cl:
        raise HTTPException(404, "Conto lavoro non trovato")

    # Get supplier email
    fornitore_id = cl.get("fornitore_id")
    supplier = None
    if fornitore_id:
        supplier = await db.clients.find_one(
            {"client_id": fornitore_id, "user_id": user["user_id"]}, {"_id": 0}
        )
    supplier_email = ""
    if supplier:
        supplier_email = supplier.get("pec") or supplier.get("email") or ""
        if not supplier_email:
            for contact in supplier.get("contacts", []):
                if contact.get("email"):
                    supplier_email = contact["email"]
                    break
    if not supplier_email:
        raise HTTPException(400, "Email fornitore non disponibile. Aggiungila nell'anagrafica fornitori.")

    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

    # Generate PDF
    from services.pdf_procurement import generate_cl_pdf

    pdf_bytes = generate_cl_pdf(cl, comm, company)

    # Send email
    from services.email_service import send_email_with_attachment
    company_name = company.get("business_name", "Officina")
    tipo_labels = {"verniciatura": "VERNICIATURA", "zincatura": "ZINCATURA A CALDO", "sabbiatura": "SABBIATURA", "altro": "LAVORAZIONE ESTERNA"}
    tipo_label = tipo_labels.get(cl["tipo"], cl["tipo"].upper())
    subject = payload.get("custom_subject") or f"DDT Conto Lavoro {tipo_label} — {company_name} — Rif. {comm.get('numero', cid)}"
    if payload.get("custom_body"):
        body = payload["custom_body"]
    else:
        ral_note = f"\nColore RAL: {cl['ral']}" if cl.get("ral") else ""
        body = f"""Gentile {cl.get('fornitore_nome', '')},

in allegato il DDT per lavorazione in conto terzi.
Tipo: {tipo_label}
Commessa: {comm.get('numero', cid)}{ral_note}
Causale: {cl.get('causale_trasporto', 'Conto Lavorazione')}

Cordiali saluti,
{company_name}"""

    await send_email_with_attachment(
        to_email=supplier_email,
        subject=subject,
        body=body,
        pdf_bytes=pdf_bytes,
        filename=f"DDT_CL_{cl_id}.pdf",
        user_id=user["user_id"],
    )

    # Update status
    await db[COLL].update_one(
        {"commessa_id": cid},
        {"$set": {
            "conto_lavoro.$[elem].stato": "inviato",
            "conto_lavoro.$[elem].stato_email": "inviata",
            "conto_lavoro.$[elem].data_invio": ts().isoformat(),
        }},
        array_filters=[{"elem.cl_id": cl_id}],
    )
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, "CL_EMAIL_INVIATA", user, f"DDT C/L inviato a {supplier_email}"))

    return {"message": f"DDT inviato a {supplier_email}"}


# ══════════════════════════════════════════════════════════════════
#  REPOSITORY DOCUMENTI (per commessa)
# ══════════════════════════════════════════════════════════════════

ALLOWED_DOC_TYPES = [
    "certificato_31", "conferma_ordine", "disegno", "certificato_verniciatura",
    "certificato_zincatura", "ddt_fornitore", "foto", "relazione", "altro",
]


