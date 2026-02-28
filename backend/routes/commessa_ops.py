"""Commessa Operations — Approvvigionamento, Produzione, Conto Lavoro, Repository.

All operational workflows within a commessa. Routes are nested under
/commesse/{commessa_id}/... to keep the commessa as the single source of truth.
"""
import uuid
import logging
import base64
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/commesse", tags=["commessa-ops"])
logger = logging.getLogger(__name__)

COLL = "commesse"
DOC_COLL = "commessa_documents"


# ── Helpers ──────────────────────────────────────────────────────

async def get_commessa_or_404(commessa_id, uid):
    doc = await db[COLL].find_one({"commessa_id": commessa_id, "user_id": uid})
    if not doc:
        raise HTTPException(404, "Commessa non trovata")
    return doc


async def ensure_ops_fields(commessa_id):
    """Ensure operational fields exist in commessa document for backward compat."""
    await db[COLL].update_one(
        {"commessa_id": commessa_id, "approvvigionamento": {"$exists": False}},
        {"$set": {"approvvigionamento": {"richieste": [], "ordini": [], "arrivi": []}}}
    )
    await db[COLL].update_one(
        {"commessa_id": commessa_id, "fasi_produzione": {"$exists": False}},
        {"$set": {"fasi_produzione": []}}
    )
    await db[COLL].update_one(
        {"commessa_id": commessa_id, "conto_lavoro": {"$exists": False}},
        {"$set": {"conto_lavoro": []}}
    )


def ts():
    return datetime.now(timezone.utc)


def new_id(prefix=""):
    return f"{prefix}{uuid.uuid4().hex[:10]}"


def push_event(commessa_id, tipo, user, note="", payload=None):
    """Returns a complete MongoDB update dict with $push for eventi and $set for updated_at.
    Use this for standalone event pushes (separate update_one call).
    """
    return {
        "$push": {"eventi": {
            "tipo": tipo,
            "data": ts().isoformat(),
            "operatore_id": user.get("user_id", ""),
            "operatore_nome": user.get("name", user.get("email", "")),
            "note": note,
            "payload": payload or {},
        }},
        "$set": {"updated_at": ts()},
    }


def build_update_with_event(push_items=None, set_items=None, commessa_id="", tipo="", user=None, note="", payload=None):
    """Build a MongoDB update with both data operations and event push."""
    update = {}
    
    push_dict = {}
    if push_items:
        push_dict.update(push_items)
    
    # Add event push
    if user:
        push_dict["eventi"] = {
            "tipo": tipo,
            "data": ts().isoformat(),
            "operatore_id": user.get("user_id", ""),
            "operatore_nome": user.get("name", user.get("email", "")),
            "note": note,
            "payload": payload or {},
        }
    
    if push_dict:
        update["$push"] = push_dict
    
    set_dict = {"updated_at": ts()}
    if set_items:
        set_dict.update(set_items)
    update["$set"] = set_dict
    
    return update


# ══════════════════════════════════════════════════════════════════
#  APPROVVIGIONAMENTO (Procurement)
# ══════════════════════════════════════════════════════════════════

class RigaRdP(BaseModel):
    descrizione: str
    quantita: float = 1
    unita_misura: str = "pz"
    richiede_cert_31: bool = False
    note: Optional[str] = ""

class RichiestaPreventivo(BaseModel):
    fornitore_nome: str
    fornitore_id: Optional[str] = None
    righe: Optional[List[RigaRdP]] = []
    note: Optional[str] = ""
    # Legacy field for backward compatibility
    materiali_richiesti: Optional[str] = ""

class RigaOdA(BaseModel):
    descrizione: str
    quantita: float = 1
    unita_misura: str = "pz"
    prezzo_unitario: float = 0
    richiede_cert_31: bool = False
    note: Optional[str] = ""

class OrdineFornitore(BaseModel):
    fornitore_nome: str
    fornitore_id: Optional[str] = None
    righe: Optional[List[RigaOdA]] = []
    importo_totale: Optional[float] = 0
    note: Optional[str] = ""
    riferimento_rdp_id: Optional[str] = None

class MaterialeRicevuto(BaseModel):
    """Singolo materiale ricevuto con possibile certificato."""
    descrizione: str
    quantita: float = 1
    unita_misura: str = "kg"
    ordine_id: Optional[str] = None  # Riferimento a OdA
    commessa_id: Optional[str] = None  # Per smistamento multi-commessa
    richiede_cert_31: bool = False
    # Dati certificato (se presente)
    certificato_doc_id: Optional[str] = None  # Riferimento a documento caricato
    numero_colata: Optional[str] = None
    qualita_materiale: Optional[str] = None
    fornitore_materiale: Optional[str] = None
    # Collegamento a tracciabilità EN 1090
    material_batch_id: Optional[str] = None

class ArrivoMateriale(BaseModel):
    """Registrazione arrivo materiale dal fornitore.
    Supporta un DDT che contiene materiali per più ordini/commesse.
    """
    ddt_fornitore: str  # Numero DDT fornitore (obbligatorio)
    data_ddt: Optional[str] = None  # Data del DDT fornitore
    fornitore_nome: Optional[str] = None
    fornitore_id: Optional[str] = None
    materiali: Optional[List[MaterialeRicevuto]] = []
    # Per retrocompatibilità - link a singolo ordine
    ordine_id: Optional[str] = None
    note: Optional[str] = ""


@router.post("/{cid}/approvvigionamento/richieste")
async def create_richiesta_preventivo(cid: str, data: RichiestaPreventivo, user: dict = Depends(get_current_user)):
    """Create a Request for Quote (RdP) to a supplier with detailed line items."""
    await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    
    # Convert righe to dict for MongoDB
    righe_dict = [r.model_dump() if hasattr(r, 'model_dump') else r.dict() for r in (data.righe or [])]
    
    rdp = {
        "rdp_id": new_id("rdp_"),
        "fornitore_nome": data.fornitore_nome,
        "fornitore_id": data.fornitore_id or "",
        "righe": righe_dict,
        "note": data.note or "",
        # Legacy field
        "materiali_richiesti": data.materiali_richiesti or "",
        "stato": "inviata",
        "data_richiesta": ts().isoformat(),
        "data_risposta": None,
        "importo_proposto": None,
    }
    
    # Build summary for event note
    n_righe = len(righe_dict)
    cert_count = sum(1 for r in righe_dict if r.get("richiede_cert_31"))
    note_summary = f"RdP inviata a {data.fornitore_nome} — {n_righe} righe"
    if cert_count > 0:
        note_summary += f" ({cert_count} con Cert. 3.1)"
    
    await db[COLL].update_one(
        {"commessa_id": cid},
        build_update_with_event(
            push_items={"approvvigionamento.richieste": rdp},
            tipo="RDP_INVIATA", user=user, note=note_summary
        ),
    )
    return {"message": f"RdP inviata a {data.fornitore_nome}", "rdp": rdp}


@router.put("/{cid}/approvvigionamento/richieste/{rdp_id}")
async def update_richiesta(cid: str, rdp_id: str, stato: str = Form(...), importo: Optional[float] = Form(None), user: dict = Depends(get_current_user)):
    """Update RdP status: ricevuta, accettata, rifiutata."""
    await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    upd = {"approvvigionamento.richieste.$[elem].stato": stato, "approvvigionamento.richieste.$[elem].data_risposta": ts().isoformat()}
    if importo is not None:
        upd["approvvigionamento.richieste.$[elem].importo_proposto"] = importo
    await db[COLL].update_one(
        {"commessa_id": cid},
        {"$set": upd},
        array_filters=[{"elem.rdp_id": rdp_id}],
    )
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, "RDP_AGGIORNATA", user, f"RdP {rdp_id} → {stato}"))
    return {"message": f"RdP aggiornata: {stato}"}


@router.post("/{cid}/approvvigionamento/ordini")
async def create_ordine_fornitore(cid: str, data: OrdineFornitore, user: dict = Depends(get_current_user)):
    """Create a Purchase Order (OdA) to a supplier with detailed line items."""
    await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    
    # Convert righe to dict for MongoDB
    righe_dict = [r.model_dump() if hasattr(r, 'model_dump') else (r.dict() if hasattr(r, 'dict') else r) for r in (data.righe or [])]
    
    # Calculate total from lines if not provided
    importo_totale = data.importo_totale or 0
    if righe_dict and importo_totale == 0:
        importo_totale = sum(
            (r.get("quantita", 1) * r.get("prezzo_unitario", 0)) 
            for r in righe_dict
        )
    
    oda = {
        "ordine_id": new_id("oda_"),
        "fornitore_nome": data.fornitore_nome,
        "fornitore_id": data.fornitore_id or "",
        "righe": righe_dict,
        "importo_totale": round(importo_totale, 2),
        "note": data.note or "",
        "riferimento_rdp_id": data.riferimento_rdp_id or "",
        "stato": "inviato",
        "data_ordine": ts().isoformat(),
        "data_conferma": None,
        "data_consegna_prevista": None,
    }
    
    # Build summary for event note
    n_righe = len(righe_dict)
    cert_count = sum(1 for r in righe_dict if r.get("richiede_cert_31"))
    note_summary = f"OdA a {data.fornitore_nome} — EUR {importo_totale:.2f}"
    if n_righe > 0:
        note_summary += f" ({n_righe} righe"
        if cert_count > 0:
            note_summary += f", {cert_count} Cert. 3.1"
        note_summary += ")"
    
    await db[COLL].update_one(
        {"commessa_id": cid},
        build_update_with_event(
            push_items={"approvvigionamento.ordini": oda},
            tipo="ORDINE_EMESSO", user=user, note=note_summary
        ),
    )
    return {"message": f"Ordine emesso a {data.fornitore_nome}", "ordine": oda}


@router.put("/{cid}/approvvigionamento/ordini/{ordine_id}")
async def update_ordine(cid: str, ordine_id: str, stato: str = Form(...), user: dict = Depends(get_current_user)):
    """Update order status: confermato, in_consegna, consegnato."""
    await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    upd = {"approvvigionamento.ordini.$[elem].stato": stato}
    if stato == "confermato":
        upd["approvvigionamento.ordini.$[elem].data_conferma"] = ts().isoformat()
    await db[COLL].update_one(
        {"commessa_id": cid},
        {"$set": upd},
        array_filters=[{"elem.ordine_id": ordine_id}],
    )
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, "ORDINE_AGGIORNATO", user, f"Ordine {ordine_id} → {stato}"))
    return {"message": f"Ordine aggiornato: {stato}"}


@router.post("/{cid}/approvvigionamento/arrivi")
async def register_arrivo_materiale(cid: str, data: ArrivoMateriale, user: dict = Depends(get_current_user)):
    """Register material arrival with detailed tracking.
    
    Supports:
    - Single DDT containing materials for multiple orders
    - Certificate linking per material
    - EN 1090 traceability integration
    """
    doc = await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    
    # Convert materiali to dict for MongoDB
    materiali_dict = []
    for m in (data.materiali or []):
        mat = m.model_dump() if hasattr(m, 'model_dump') else (m.dict() if hasattr(m, 'dict') else m)
        # Default commessa_id to current if not specified
        if not mat.get("commessa_id"):
            mat["commessa_id"] = cid
        materiali_dict.append(mat)
    
    arrivo = {
        "arrivo_id": new_id("arr_"),
        "ddt_fornitore": data.ddt_fornitore,
        "data_ddt": data.data_ddt or ts().isoformat()[:10],
        "fornitore_nome": data.fornitore_nome or "",
        "fornitore_id": data.fornitore_id or "",
        "materiali": materiali_dict,
        "ordine_id": data.ordine_id or "",  # Legacy support
        "note": data.note or "",
        "stato": "da_verificare",
        "data_arrivo": ts().isoformat(),
        "data_verifica": None,
    }
    
    # Build summary for event
    n_mat = len(materiali_dict)
    cert_count = sum(1 for m in materiali_dict if m.get("certificato_doc_id") or m.get("numero_colata"))
    note_summary = f"DDT {data.ddt_fornitore} — {n_mat} materiali"
    if cert_count:
        note_summary += f" ({cert_count} con certificato)"
    
    await db[COLL].update_one(
        {"commessa_id": cid},
        build_update_with_event(
            push_items={"approvvigionamento.arrivi": arrivo},
            tipo="MATERIALE_ARRIVATO", user=user, note=note_summary
        ),
    )
    
    # If linked to a specific order, mark it as consegnato
    if data.ordine_id:
        await db[COLL].update_one(
            {"commessa_id": cid},
            {"$set": {"approvvigionamento.ordini.$[elem].stato": "consegnato"}},
            array_filters=[{"elem.ordine_id": data.ordine_id}],
        )
    
    # Also mark orders for materials that reference different orders
    order_ids_to_update = set()
    for mat in materiali_dict:
        if mat.get("ordine_id") and mat["ordine_id"] != data.ordine_id:
            order_ids_to_update.add(mat["ordine_id"])
    
    for oid in order_ids_to_update:
        await db[COLL].update_one(
            {"commessa_id": cid},
            {"$set": {"approvvigionamento.ordini.$[elem].stato": "consegnato"}},
            array_filters=[{"elem.ordine_id": oid}],
        )
    
    return {"message": f"Arrivo materiale registrato (DDT: {data.ddt_fornitore})", "arrivo": arrivo}


@router.put("/{cid}/approvvigionamento/arrivi/{arrivo_id}/materiale/{mat_idx}/certificato")
async def link_certificato_to_materiale(
    cid: str, 
    arrivo_id: str, 
    mat_idx: int,
    certificato_doc_id: str = Form(None),
    numero_colata: str = Form(None),
    qualita_materiale: str = Form(None),
    fornitore_materiale: str = Form(None),
    user: dict = Depends(get_current_user)
):
    """Link a certificate to a specific material in an arrival.
    Also registers in EN 1090 material_batches if normativa is 1090.
    """
    doc = await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    
    # Find the arrival and material
    approv = doc.get("approvvigionamento", {})
    arrivo = next((a for a in approv.get("arrivi", []) if a.get("arrivo_id") == arrivo_id), None)
    if not arrivo:
        raise HTTPException(404, "Arrivo non trovato")
    
    materiali = arrivo.get("materiali", [])
    if mat_idx < 0 or mat_idx >= len(materiali):
        raise HTTPException(400, "Indice materiale non valido")
    
    # Update the material with certificate info
    update_fields = {}
    if certificato_doc_id:
        update_fields[f"approvvigionamento.arrivi.$[arr].materiali.{mat_idx}.certificato_doc_id"] = certificato_doc_id
    if numero_colata:
        update_fields[f"approvvigionamento.arrivi.$[arr].materiali.{mat_idx}.numero_colata"] = numero_colata
    if qualita_materiale:
        update_fields[f"approvvigionamento.arrivi.$[arr].materiali.{mat_idx}.qualita_materiale"] = qualita_materiale
    if fornitore_materiale:
        update_fields[f"approvvigionamento.arrivi.$[arr].materiali.{mat_idx}.fornitore_materiale"] = fornitore_materiale
    
    if update_fields:
        await db[COLL].update_one(
            {"commessa_id": cid},
            {"$set": update_fields},
            array_filters=[{"arr.arrivo_id": arrivo_id}],
        )
    
    # If this is an EN 1090 project, also register in material_batches
    normativa = doc.get("normativa") or doc.get("moduli", {}).get("normativa")
    if normativa == "EN_1090" and numero_colata:
        materiale = materiali[mat_idx]
        batch_data = {
            "batch_id": new_id("batch_"),
            "user_id": user["user_id"],
            "commessa_id": cid,
            "fornitore": fornitore_materiale or arrivo.get("fornitore_nome", ""),
            "tipo_materiale": materiale.get("descrizione", ""),
            "numero_colata": numero_colata,
            "qualita": qualita_materiale or "",
            "ddt_riferimento": arrivo.get("ddt_fornitore", ""),
            "certificato_31_base64": "",  # Will be filled if document is uploaded
            "certificato_doc_id": certificato_doc_id or "",
            "data_registrazione": ts().isoformat(),
            "note": f"Auto-registrato da arrivo {arrivo_id}",
        }
        await db.material_batches.insert_one(batch_data)
        
        # Update material with batch reference
        await db[COLL].update_one(
            {"commessa_id": cid},
            {"$set": {f"approvvigionamento.arrivi.$[arr].materiali.{mat_idx}.material_batch_id": batch_data["batch_id"]}},
            array_filters=[{"arr.arrivo_id": arrivo_id}],
        )
        
        await db[COLL].update_one({"commessa_id": cid}, push_event(
            cid, "MATERIALE_TRACCIATO", user, 
            f"Colata {numero_colata} registrata per EN 1090"
        ))
    
    return {"message": "Certificato collegato al materiale"}


@router.put("/{cid}/approvvigionamento/arrivi/{arrivo_id}/verifica")
async def verifica_arrivo(cid: str, arrivo_id: str, user: dict = Depends(get_current_user)):
    """Mark arrival as verified."""
    await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    await db[COLL].update_one(
        {"commessa_id": cid},
        {"$set": {
            "approvvigionamento.arrivi.$[elem].stato": "verificato",
            "approvvigionamento.arrivi.$[elem].data_verifica": ts().isoformat(),
        }},
        array_filters=[{"elem.arrivo_id": arrivo_id}],
    )
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, "MATERIALE_VERIFICATO", user, f"Arrivo {arrivo_id} verificato"))
    return {"message": "Arrivo verificato"}


# ══════════════════════════════════════════════════════════════════
#  PDF GENERATION & EMAIL SENDING (RdP, OdA)
# ══════════════════════════════════════════════════════════════════

@router.get("/{cid}/approvvigionamento/richieste/{rdp_id}/pdf")
async def get_rdp_pdf(cid: str, rdp_id: str, user: dict = Depends(get_current_user)):
    """Generate PDF preview for a Request for Quote (RdP)."""
    doc = await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    
    # Find the RdP
    approv = doc.get("approvvigionamento", {})
    rdp = next((r for r in approv.get("richieste", []) if r.get("rdp_id") == rdp_id), None)
    if not rdp:
        raise HTTPException(404, "RdP non trovata")
    
    # Get company info
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    
    # Get fornitore details if available
    fornitore = None
    if rdp.get("fornitore_id"):
        fornitore = await db.clients.find_one({"client_id": rdp["fornitore_id"]}, {"_id": 0})
    
    # Generate PDF using V2 template
    from services.pdf_template_v2 import generate_rdp_pdf_v2
    pdf_bytes = generate_rdp_pdf_v2(rdp, doc, company, fornitore)
    
    filename = f"RdP_{rdp_id}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


@router.post("/{cid}/approvvigionamento/richieste/{rdp_id}/send-email")
async def send_rdp_email_endpoint(cid: str, rdp_id: str, user: dict = Depends(get_current_user)):
    """Generate PDF and send RdP via email to supplier."""
    doc = await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    
    # Find the RdP
    approv = doc.get("approvvigionamento", {})
    rdp = next((r for r in approv.get("richieste", []) if r.get("rdp_id") == rdp_id), None)
    if not rdp:
        raise HTTPException(404, "RdP non trovata")
    
    # Get supplier email
    fornitore_id = rdp.get("fornitore_id")
    fornitore_nome = rdp.get("fornitore_nome", "Fornitore")
    to_email = None
    
    if fornitore_id:
        fornitore = await db.clients.find_one({"client_id": fornitore_id}, {"_id": 0})
        if fornitore:
            to_email = fornitore.get("pec") or fornitore.get("email")
            # Check contacts for procurement preferences
            if not to_email:
                for contact in fornitore.get("contacts", []):
                    if contact.get("email"):
                        to_email = contact["email"]
                        break
    
    if not to_email:
        raise HTTPException(400, f"Nessun indirizzo email trovato per {fornitore_nome}. Aggiungi un'email nella scheda fornitore.")
    
    # Get company info
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    company_name = company.get("business_name", "")
    
    # Generate PDF
    from services.pdf_procurement import generate_rdp_pdf
    pdf_bytes = generate_rdp_pdf(rdp, doc, company)
    filename = f"RdP_{rdp_id}.pdf"
    
    # Send email
    from services.email_service import send_rdp_email
    num_righe = len(rdp.get("righe", []))
    commessa_numero = doc.get("numero", "N/D")
    
    success = await send_rdp_email(
        to_email=to_email,
        fornitore_name=fornitore_nome,
        rdp_id=rdp_id,
        commessa_numero=commessa_numero,
        company_name=company_name,
        num_righe=num_righe,
        pdf_bytes=pdf_bytes,
        filename=filename,
    )
    
    if not success:
        raise HTTPException(500, "Invio email fallito. Verifica la configurazione Resend in Impostazioni.")
    
    # Track email sent on the RdP
    await db[COLL].update_one(
        {"commessa_id": cid},
        {"$set": {
            "approvvigionamento.richieste.$[elem].email_sent": True,
            "approvvigionamento.richieste.$[elem].email_sent_to": to_email,
            "approvvigionamento.richieste.$[elem].email_sent_at": ts().isoformat(),
        }},
        array_filters=[{"elem.rdp_id": rdp_id}],
    )
    
    # Add event
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, "RDP_EMAIL_INVIATA", user, f"RdP {rdp_id} inviata via email a {to_email}"))
    
    logger.info(f"RdP {rdp_id} sent via email to {to_email}")
    return {"message": f"Email inviata con successo a {to_email}", "to": to_email}


@router.get("/{cid}/approvvigionamento/ordini/{ordine_id}/pdf")
async def get_oda_pdf(cid: str, ordine_id: str, user: dict = Depends(get_current_user)):
    """Generate PDF preview for a Purchase Order (OdA)."""
    doc = await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    
    # Find the OdA
    approv = doc.get("approvvigionamento", {})
    oda = next((o for o in approv.get("ordini", []) if o.get("ordine_id") == ordine_id), None)
    if not oda:
        raise HTTPException(404, "Ordine non trovato")
    
    # Get company info
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    
    # Generate PDF
    from services.pdf_procurement import generate_oda_pdf
    pdf_bytes = generate_oda_pdf(oda, doc, company)
    
    filename = f"OdA_{ordine_id}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


@router.post("/{cid}/approvvigionamento/ordini/{ordine_id}/send-email")
async def send_oda_email_endpoint(cid: str, ordine_id: str, user: dict = Depends(get_current_user)):
    """Generate PDF and send OdA via email to supplier."""
    doc = await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    
    # Find the OdA
    approv = doc.get("approvvigionamento", {})
    oda = next((o for o in approv.get("ordini", []) if o.get("ordine_id") == ordine_id), None)
    if not oda:
        raise HTTPException(404, "Ordine non trovato")
    
    # Get supplier email
    fornitore_id = oda.get("fornitore_id")
    fornitore_nome = oda.get("fornitore_nome", "Fornitore")
    to_email = None
    
    if fornitore_id:
        fornitore = await db.clients.find_one({"client_id": fornitore_id}, {"_id": 0})
        if fornitore:
            to_email = fornitore.get("pec") or fornitore.get("email")
            if not to_email:
                for contact in fornitore.get("contacts", []):
                    if contact.get("email"):
                        to_email = contact["email"]
                        break
    
    if not to_email:
        raise HTTPException(400, f"Nessun indirizzo email trovato per {fornitore_nome}. Aggiungi un'email nella scheda fornitore.")
    
    # Get company info
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    company_name = company.get("business_name", "")
    
    # Generate PDF
    from services.pdf_procurement import generate_oda_pdf
    pdf_bytes = generate_oda_pdf(oda, doc, company)
    filename = f"OdA_{ordine_id}.pdf"
    
    # Send email
    from services.email_service import send_oda_email
    importo_totale = oda.get("importo_totale", 0)
    commessa_numero = doc.get("numero", "N/D")
    
    success = await send_oda_email(
        to_email=to_email,
        fornitore_name=fornitore_nome,
        ordine_id=ordine_id,
        commessa_numero=commessa_numero,
        company_name=company_name,
        importo_totale=importo_totale,
        pdf_bytes=pdf_bytes,
        filename=filename,
    )
    
    if not success:
        raise HTTPException(500, "Invio email fallito. Verifica la configurazione Resend in Impostazioni.")
    
    # Track email sent on the OdA
    await db[COLL].update_one(
        {"commessa_id": cid},
        {"$set": {
            "approvvigionamento.ordini.$[elem].email_sent": True,
            "approvvigionamento.ordini.$[elem].email_sent_to": to_email,
            "approvvigionamento.ordini.$[elem].email_sent_at": ts().isoformat(),
        }},
        array_filters=[{"elem.ordine_id": ordine_id}],
    )
    
    # Add event
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, "ODA_EMAIL_INVIATA", user, f"Ordine {ordine_id} inviato via email a {to_email}"))
    
    logger.info(f"OdA {ordine_id} sent via email to {to_email}")
    return {"message": f"Email inviata con successo a {to_email}", "to": to_email}


# ══════════════════════════════════════════════════════════════════
#  PRODUZIONE (Production Phases)
# ══════════════════════════════════════════════════════════════════

DEFAULT_FASI = [
    {"tipo": "taglio",                "label": "Taglio",                 "order": 0},
    {"tipo": "foratura",              "label": "Foratura",               "order": 1},
    {"tipo": "assemblaggio",          "label": "Assemblaggio",           "order": 2},
    {"tipo": "saldatura",             "label": "Saldatura",              "order": 3},
    {"tipo": "pulizia",               "label": "Pulizia / Sbavatura",    "order": 4},
    {"tipo": "preparazione_superfici","label": "Preparazione Superfici", "order": 5},
]


@router.post("/{cid}/produzione/init")
async def init_produzione(cid: str, user: dict = Depends(get_current_user)):
    """Initialize production phases for a commessa."""
    doc = await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    if doc.get("fasi_produzione"):
        return {"message": "Fasi gia' inizializzate", "fasi": doc["fasi_produzione"]}

    fasi = []
    for f in DEFAULT_FASI:
        fasi.append({
            **f,
            "stato": "da_fare",
            "operatore": None,
            "data_inizio": None,
            "data_fine": None,
            "note": "",
        })
    await db[COLL].update_one(
        {"commessa_id": cid},
        build_update_with_event(
            set_items={"fasi_produzione": fasi},
            tipo="PRODUZIONE_INIZIALIZZATA", user=user, note="Fasi produzione create"
        ),
    )
    return {"message": "Fasi produzione inizializzate", "fasi": fasi}


@router.get("/{cid}/produzione")
async def get_produzione(cid: str, user: dict = Depends(get_current_user)):
    doc = await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    return {"fasi": doc.get("fasi_produzione", []), "conto_lavoro": doc.get("conto_lavoro", [])}


class FaseUpdate(BaseModel):
    stato: str  # da_fare, in_corso, completato
    operatore: Optional[str] = None
    note: Optional[str] = None


@router.put("/{cid}/produzione/{fase_tipo}")
async def update_fase(cid: str, fase_tipo: str, data: FaseUpdate, user: dict = Depends(get_current_user)):
    """Update a production phase."""
    await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    now = ts().isoformat()
    upd = {"fasi_produzione.$[elem].stato": data.stato}
    if data.stato == "in_corso":
        upd["fasi_produzione.$[elem].data_inizio"] = now
    elif data.stato == "completato":
        upd["fasi_produzione.$[elem].data_fine"] = now
    if data.operatore is not None:
        upd["fasi_produzione.$[elem].operatore"] = data.operatore
    if data.note is not None:
        upd["fasi_produzione.$[elem].note"] = data.note

    await db[COLL].update_one(
        {"commessa_id": cid},
        {"$set": upd},
        array_filters=[{"elem.tipo": fase_tipo}],
    )
    label_map = {f["tipo"]: f["label"] for f in DEFAULT_FASI}
    label = label_map.get(fase_tipo, fase_tipo)
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, f"FASE_{data.stato.upper()}", user, f"{label} → {data.stato}", {"fase": fase_tipo}))
    return {"message": f"{label} → {data.stato}"}


# ══════════════════════════════════════════════════════════════════
#  CONTO LAVORO (Subcontracting: verniciatura, zincatura, etc.)
# ══════════════════════════════════════════════════════════════════

class ContoLavoroCreate(BaseModel):
    tipo: str  # verniciatura, zincatura, sabbiatura, altro
    fornitore_nome: str
    fornitore_id: Optional[str] = None
    note: Optional[str] = ""

class ContoLavoroUpdate(BaseModel):
    stato: str  # da_inviare, inviato, in_lavorazione, rientrato, verificato
    ddt_invio_id: Optional[str] = None
    ddt_rientro_id: Optional[str] = None
    certificato_doc_id: Optional[str] = None
    note: Optional[str] = None


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
        "ddt_invio_id": None,
        "ddt_rientro_id": None,
        "certificato_doc_id": None,
        "note": data.note or "",
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
    await get_commessa_or_404(cid, user["user_id"])
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

    await db[COLL].update_one(
        {"commessa_id": cid},
        {"$set": upd},
        array_filters=[{"elem.cl_id": cl_id}],
    )
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, f"CL_{data.stato.upper()}", user, f"C/L {cl_id} → {data.stato}"))
    return {"message": f"Conto lavoro aggiornato: {data.stato}"}


# ══════════════════════════════════════════════════════════════════
#  REPOSITORY DOCUMENTI (per commessa)
# ══════════════════════════════════════════════════════════════════

ALLOWED_DOC_TYPES = [
    "certificato_31", "conferma_ordine", "disegno", "certificato_verniciatura",
    "certificato_zincatura", "ddt_fornitore", "foto", "relazione", "altro",
]


@router.post("/{cid}/documenti")
async def upload_document(
    cid: str,
    file: UploadFile = File(...),
    tipo: str = Form("altro"),
    note: str = Form(""),
    user: dict = Depends(get_current_user),
):
    """Upload a document to the commessa repository."""
    await get_commessa_or_404(cid, user["user_id"])
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "File troppo grande (max 15MB)")

    doc_id = new_id("doc_")
    doc = {
        "doc_id": doc_id,
        "commessa_id": cid,
        "user_id": user["user_id"],
        "nome_file": file.filename or "documento",
        "tipo": tipo if tipo in ALLOWED_DOC_TYPES else "altro",
        "content_type": file.content_type or "application/octet-stream",
        "file_base64": base64.b64encode(content).decode("utf-8"),
        "size_bytes": len(content),
        "metadata_estratti": None,  # Will be filled by AI OCR
        "note": note,
        "uploaded_at": ts().isoformat(),
        "uploaded_by": user.get("name", user.get("email", "")),
    }
    await db[DOC_COLL].insert_one(doc)
    await db[COLL].update_one({"commessa_id": cid}, push_event(
        cid, "DOCUMENTO_CARICATO", user,
        f"{file.filename} ({tipo})", {"doc_id": doc_id}
    ))
    return {
        "message": f"Documento caricato: {file.filename}",
        "doc_id": doc_id,
        "nome_file": file.filename,
        "tipo": tipo,
    }


@router.get("/{cid}/documenti")
async def list_documents(cid: str, user: dict = Depends(get_current_user)):
    """List all documents for a commessa (without file content)."""
    await get_commessa_or_404(cid, user["user_id"])
    docs = await db[DOC_COLL].find(
        {"commessa_id": cid, "user_id": user["user_id"]},
        {"_id": 0, "file_base64": 0}  # Exclude heavy content
    ).sort("uploaded_at", -1).to_list(200)
    return {"documents": docs, "total": len(docs)}


@router.get("/{cid}/documenti/{doc_id}/download")
async def download_document(cid: str, doc_id: str, user: dict = Depends(get_current_user)):
    """Download a document."""
    doc = await db[DOC_COLL].find_one(
        {"doc_id": doc_id, "commessa_id": cid, "user_id": user["user_id"]}
    )
    if not doc:
        raise HTTPException(404, "Documento non trovato")
    content = base64.b64decode(doc["file_base64"])
    return StreamingResponse(
        BytesIO(content),
        media_type=doc.get("content_type", "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{doc.get("nome_file", "file")}"'},
    )


@router.delete("/{cid}/documenti/{doc_id}")
async def delete_document(cid: str, doc_id: str, user: dict = Depends(get_current_user)):
    r = await db[DOC_COLL].delete_one({"doc_id": doc_id, "commessa_id": cid, "user_id": user["user_id"]})
    if r.deleted_count == 0:
        raise HTTPException(404, "Documento non trovato")
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, "DOCUMENTO_ELIMINATO", user, f"Doc {doc_id} eliminato"))
    return {"message": "Documento eliminato"}


# ══════════════════════════════════════════════════════════════════
#  AI OCR: Parse Certificate 3.1 (GPT-4o Vision)
# ══════════════════════════════════════════════════════════════════

@router.post("/{cid}/documenti/{doc_id}/parse-certificato")
async def parse_certificato_31(cid: str, doc_id: str, user: dict = Depends(get_current_user)):
    """Use GPT-4o Vision to extract data from a 3.1 material certificate."""
    import os
    LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
    if not LLM_KEY:
        raise HTTPException(500, "Chiave AI non configurata")

    doc = await db[DOC_COLL].find_one({"doc_id": doc_id, "commessa_id": cid, "user_id": user["user_id"]})
    if not doc:
        raise HTTPException(404, "Documento non trovato")
    if not doc.get("file_base64"):
        raise HTTPException(400, "Documento senza contenuto")

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

        file_b64 = doc["file_base64"]
        file_contents = [ImageContent(image_base64=file_b64)]

        prompt = """Analizza questo certificato di materiale 3.1 (EN 10204) per acciaio strutturale.
Estrai i seguenti dati in formato JSON PURO (senza markdown, senza ```):
{
  "numero_colata": "il numero di colata/heat number",
  "fornitore": "nome del produttore/acciaieria",
  "qualita_acciaio": "grado dell'acciaio (es. S275JR, S355J2, ecc.)",
  "normativa_riferimento": "norma di riferimento (es. EN 10025-2)",
  "dimensioni": "profilo/dimensione del prodotto (es. IPE 200, HEB 160, L80x8)",
  "peso_kg": "peso in kg se indicato, altrimenti null",
  "data_certificato": "data del certificato se presente",
  "n_certificato": "numero del certificato",
  "composizione_chimica": "breve riepilogo (C, Mn, Si, P, S, ecc.)",
  "proprieta_meccaniche": "Rp0.2, Rm, A%, KV se presenti",
  "conforme": true/false se il certificato indica conformità,
  "note": "eventuali note aggiuntive"
}

Se un campo non è leggibile o non presente, usa null. Rispondi SOLO con il JSON."""

        chat = LlmChat(
            api_key=LLM_KEY,
            session_id=f"cert31-{doc_id}",
            system_message="Sei un tecnico esperto di certificati materiale 3.1 per acciaio strutturale EN 10204. Estrai dati tecnici con precisione."
        ).with_model("openai", "gpt-4o")

        response = await chat.send_message(UserMessage(
            text=prompt,
            file_contents=file_contents,
        ))

        # Parse JSON response
        import json
        response_text = response.text.strip()
        # Clean markdown wrapping if present
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1] if "\n" in response_text else response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        try:
            metadata = json.loads(response_text)
        except json.JSONDecodeError:
            metadata = {"raw_response": response_text, "parse_error": True}

        # Save extracted metadata to the document
        await db[DOC_COLL].update_one(
            {"doc_id": doc_id},
            {"$set": {"metadata_estratti": metadata, "tipo": "certificato_31"}},
        )

        # Auto-register in material_batches if heat number found
        batch_id = None
        if metadata.get("numero_colata") and not metadata.get("parse_error"):
            existing = await db.material_batches.find_one({"heat_number": metadata["numero_colata"], "user_id": user["user_id"]})
            if not existing:
                batch_id = f"bat_{uuid.uuid4().hex[:10]}"
                batch_doc = {
                    "batch_id": batch_id,
                    "user_id": user["user_id"],
                    "heat_number": metadata["numero_colata"],
                    "material_type": metadata.get("qualita_acciaio", ""),
                    "supplier_name": metadata.get("fornitore", ""),
                    "dimensions": metadata.get("dimensioni", ""),
                    "normativa": metadata.get("normativa_riferimento", ""),
                    "certificate_base64": doc.get("file_base64", ""),
                    "source_doc_id": doc_id,
                    "commessa_id": cid,
                    "notes": f"Auto-registrato da certificato {metadata.get('n_certificato', '')}",
                    "created_at": ts(),
                }
                await db.material_batches.insert_one(batch_doc)
                logger.info(f"Auto-registered batch {batch_id} (colata: {metadata['numero_colata']})")
            else:
                batch_id = existing.get("batch_id")

        await db[COLL].update_one({"commessa_id": cid}, push_event(
            cid, "CERTIFICATO_ANALIZZATO", user,
            f"Colata: {metadata.get('numero_colata', '?')} — {metadata.get('qualita_acciaio', '?')} — {metadata.get('fornitore', '?')}",
            {"doc_id": doc_id, "batch_id": batch_id, "metadata": metadata}
        ))

        return {
            "message": "Certificato analizzato con successo",
            "metadata": metadata,
            "batch_id": batch_id,
            "auto_registered": batch_id is not None,
        }

    except Exception as e:
        logger.error(f"Certificate parsing error: {e}")
        raise HTTPException(500, f"Errore analisi certificato: {str(e)}")


# ══════════════════════════════════════════════════════════════════
#  GET ALL OPS DATA (for hub enrichment)
# ══════════════════════════════════════════════════════════════════

@router.get("/{cid}/ops")
async def get_commessa_ops(cid: str, user: dict = Depends(get_current_user)):
    """Get all operational data for a commessa: procurement, production, subcontracting, documents."""
    doc = await get_commessa_or_404(cid, user["user_id"])
    approv = doc.get("approvvigionamento", {"richieste": [], "ordini": [], "arrivi": []})
    fasi = doc.get("fasi_produzione", [])
    cl = doc.get("conto_lavoro", [])

    # Count documents
    doc_count = await db[DOC_COLL].count_documents({"commessa_id": cid, "user_id": user["user_id"]})

    # Compute production progress
    fasi_total = len(fasi)
    fasi_completed = sum(1 for f in fasi if f.get("stato") == "completato")

    return {
        "approvvigionamento": approv,
        "fasi_produzione": fasi,
        "produzione_progress": {
            "total": fasi_total,
            "completed": fasi_completed,
            "percentage": round(fasi_completed / fasi_total * 100) if fasi_total > 0 else 0,
        },
        "conto_lavoro": cl,
        "documenti_count": doc_count,
    }
