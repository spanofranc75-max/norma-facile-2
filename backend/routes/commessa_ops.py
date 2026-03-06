"""Commessa Operations — Approvvigionamento, Produzione, Conto Lavoro, Repository.

All operational workflows within a commessa. Routes are nested under
/commesse/{commessa_id}/... to keep the commessa as the single source of truth.
"""
import uuid
import re
import logging
import base64
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
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
    await db[COLL].update_one(
        {"commessa_id": commessa_id, "consegne": {"$exists": False}},
        {"$set": {"consegne": []}}
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
    quantita_utilizzata: Optional[float] = None  # If set, only this qty is costed to commessa; remainder goes to stock
    prezzo_unitario: Optional[float] = None  # Unit price for cost calculation
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
    
    # Handle partial usage: remainder goes to warehouse stock
    stock_updates = []
    for mat in materiali_dict:
        qty_arrived = float(mat.get("quantita", 0))
        qty_used = mat.get("quantita_utilizzata")
        if qty_used is not None and qty_used < qty_arrived:
            qty_remainder = round(qty_arrived - float(qty_used), 4)
            desc = mat.get("descrizione", "").strip()
            um = (mat.get("unita_misura") or "kg").lower()
            prezzo = float(mat.get("prezzo_unitario", 0))
            
            if desc and qty_remainder > 0:
                # Try to find existing article by description
                codice_words = re.sub(r'[^a-zA-Z0-9\s]', '', desc).upper().split()[:3]
                auto_codice = "-".join(codice_words) if codice_words else f"ART-{uuid.uuid4().hex[:4].upper()}"
                
                existing_art = await db.articoli.find_one(
                    {"user_id": user["user_id"], "descrizione": {"$regex": f"^{re.escape(desc[:30])}", "$options": "i"}},
                    {"_id": 0}
                )
                
                now_stock = ts()
                if existing_art:
                    old_stock = float(existing_art.get("giacenza", 0))
                    new_stock = round(old_stock + qty_remainder, 4)
                    await db.articoli.update_one(
                        {"articolo_id": existing_art["articolo_id"]},
                        {"$set": {"giacenza": new_stock, "updated_at": now_stock}}
                    )
                    stock_updates.append(f"{qty_remainder} {um} di {desc[:40]} → magazzino (tot: {new_stock})")
                else:
                    art_doc = {
                        "articolo_id": f"art_{uuid.uuid4().hex[:12]}",
                        "user_id": user["user_id"],
                        "codice": auto_codice,
                        "descrizione": desc,
                        "categoria": "materiale",
                        "unita_misura": um,
                        "prezzo_unitario": prezzo,
                        "giacenza": qty_remainder,
                        "aliquota_iva": "22",
                        "fornitore_nome": data.fornitore_nome or "",
                        "fornitore_id": data.fornitore_id or "",
                        "storico_prezzi": [{"prezzo": prezzo, "data": now_stock.isoformat(), "fonte": f"Resto arrivo DDT {data.ddt_fornitore}"}],
                        "note": f"Creato automaticamente da resto arrivo DDT {data.ddt_fornitore}",
                        "created_at": now_stock,
                        "updated_at": now_stock,
                    }
                    await db.articoli.insert_one(art_doc)
                    stock_updates.append(f"{qty_remainder} {um} di {desc[:40]} → nuovo articolo magazzino")
    
    result = {"message": f"Arrivo materiale registrato (DDT: {data.ddt_fornitore})", "arrivo": arrivo}
    if stock_updates:
        result["stock_updates"] = stock_updates
        result["message"] += f" — {len(stock_updates)} materiali con resto a magazzino"
    
    return result


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


@router.get("/{cid}/approvvigionamento/richieste/{rdp_id}/preview-email")
async def preview_rdp_email(cid: str, rdp_id: str, user: dict = Depends(get_current_user)):
    """Preview email that would be sent for RdP."""
    doc = await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    approv = doc.get("approvvigionamento", {})
    rdp = next((r for r in approv.get("richieste", []) if r.get("rdp_id") == rdp_id), None)
    if not rdp:
        raise HTTPException(404, "RdP non trovata")

    fornitore_id = rdp.get("fornitore_id")
    to_email = ""
    if fornitore_id:
        forn = await db.clients.find_one({"client_id": fornitore_id}, {"_id": 0})
        if forn:
            to_email = forn.get("pec") or forn.get("email") or ""
            if not to_email:
                for c in forn.get("contacts", []):
                    if c.get("email"):
                        to_email = c["email"]
                        break

    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    company_name = company.get("business_name", "")

    from services.email_preview import build_rdp_email
    preview = build_rdp_email(
        fornitore_name=rdp.get("fornitore_nome", ""),
        rdp_id=rdp_id,
        commessa_numero=doc.get("numero", "N/D"),
        company_name=company_name,
        num_righe=len(rdp.get("righe", [])),
    )
    return {
        "to_email": to_email,
        "to_name": rdp.get("fornitore_nome", ""),
        "subject": preview["subject"],
        "html_body": preview["html_body"],
        "has_attachment": True,
        "attachment_name": f"RdP_{rdp_id}.pdf",
    }



@router.post("/{cid}/approvvigionamento/richieste/{rdp_id}/send-email")
async def send_rdp_email_endpoint(cid: str, rdp_id: str, payload: dict = None, user: dict = Depends(get_current_user)):
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
    
    # Get fornitore details for PDF
    fornitore_doc = None
    if fornitore_id:
        fornitore_doc = await db.clients.find_one({"client_id": fornitore_id}, {"_id": 0})
    
    # Generate PDF using V2 template
    from services.pdf_template_v2 import generate_rdp_pdf_v2
    pdf_bytes = generate_rdp_pdf_v2(rdp, doc, company, fornitore_doc)
    filename = f"RdP_{rdp_id}.pdf"
    
    # Send email
    from services.email_service import send_rdp_email, send_email_with_attachment
    payload = payload or {}
    num_righe = len(rdp.get("righe", []))
    commessa_numero = doc.get("numero", "N/D")

    if payload.get("custom_subject") or payload.get("custom_body"):
        custom_subject = payload.get("custom_subject") or f"Richiesta Preventivo {rdp_id} - Commessa {commessa_numero} - {company_name}"
        custom_body = payload.get("custom_body") or ""
        success = await send_email_with_attachment(
            to_email=to_email, subject=custom_subject, body=custom_body,
            pdf_bytes=pdf_bytes, filename=filename, user_id=user["user_id"],
        )
    else:
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
    
    # Get fornitore details if available
    fornitore = None
    if oda.get("fornitore_id"):
        fornitore = await db.clients.find_one({"client_id": oda["fornitore_id"]}, {"_id": 0})
    
    # Generate PDF using V2 template
    from services.pdf_template_v2 import generate_oda_pdf_v2
    pdf_bytes = generate_oda_pdf_v2(oda, doc, company, fornitore)
    
    filename = f"OdA_{ordine_id}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


@router.get("/{cid}/approvvigionamento/ordini/{ordine_id}/preview-email")
async def preview_oda_email(cid: str, ordine_id: str, user: dict = Depends(get_current_user)):
    """Preview email that would be sent for OdA."""
    doc = await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    approv = doc.get("approvvigionamento", {})
    oda = next((o for o in approv.get("ordini", []) if o.get("ordine_id") == ordine_id), None)
    if not oda:
        raise HTTPException(404, "Ordine non trovato")

    fornitore_id = oda.get("fornitore_id")
    to_email = ""
    if fornitore_id:
        forn = await db.clients.find_one({"client_id": fornitore_id}, {"_id": 0})
        if forn:
            to_email = forn.get("pec") or forn.get("email") or ""
            if not to_email:
                for c in forn.get("contacts", []):
                    if c.get("email"):
                        to_email = c["email"]
                        break

    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    company_name = company.get("business_name", "")

    from services.email_preview import build_oda_email
    preview = build_oda_email(
        fornitore_name=oda.get("fornitore_nome", ""),
        ordine_id=ordine_id,
        commessa_numero=doc.get("numero", "N/D"),
        company_name=company_name,
        importo_totale=oda.get("importo_totale", 0),
    )
    return {
        "to_email": to_email,
        "to_name": oda.get("fornitore_nome", ""),
        "subject": preview["subject"],
        "html_body": preview["html_body"],
        "has_attachment": True,
        "attachment_name": f"OdA_{ordine_id}.pdf",
    }



@router.post("/{cid}/approvvigionamento/ordini/{ordine_id}/send-email")
async def send_oda_email_endpoint(cid: str, ordine_id: str, payload: dict = None, user: dict = Depends(get_current_user)):
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
    
    # Get fornitore details for PDF
    fornitore_doc = None
    if fornitore_id:
        fornitore_doc = await db.clients.find_one({"client_id": fornitore_id}, {"_id": 0})
    
    # Generate PDF using V2 template
    from services.pdf_template_v2 import generate_oda_pdf_v2
    pdf_bytes = generate_oda_pdf_v2(oda, doc, company, fornitore_doc)
    filename = f"OdA_{ordine_id}.pdf"
    
    # Send email
    from services.email_service import send_oda_email, send_email_with_attachment
    payload = payload or {}
    importo_totale = oda.get("importo_totale", 0)
    commessa_numero = doc.get("numero", "N/D")

    if payload.get("custom_subject") or payload.get("custom_body"):
        custom_subject = payload.get("custom_subject") or f"Ordine n. {ordine_id} - Commessa {commessa_numero} - {company_name}"
        custom_body = payload.get("custom_body") or ""
        success = await send_email_with_attachment(
            to_email=to_email, subject=custom_subject, body=custom_body,
            pdf_bytes=pdf_bytes, filename=filename, user_id=user["user_id"],
        )
    else:
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

    # Calculate expected dates based on deadline
    deadline_str = doc.get("deadline")
    fasi = []
    total_phases = len(DEFAULT_FASI)
    for i, f in enumerate(DEFAULT_FASI):
        data_prevista = None
        if deadline_str:
            try:
                from datetime import date as date_cls
                deadline_date = date_cls.fromisoformat(deadline_str)
                today = date_cls.today()
                total_days = (deadline_date - today).days
                if total_days > 0:
                    phase_end_day = int(total_days * (i + 1) / total_phases)
                    data_prevista = (today + timedelta(days=phase_end_day)).isoformat()
            except (ValueError, TypeError):
                pass
        fasi.append({
            **f,
            "stato": "da_fare",
            "operatore": None,
            "data_inizio": None,
            "data_fine": None,
            "data_prevista": data_prevista,
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
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    operator_name: Optional[str] = None
    data_prevista: Optional[str] = None  # Expected completion date YYYY-MM-DD


@router.put("/{cid}/produzione/{fase_tipo}")
async def update_fase(cid: str, fase_tipo: str, data: FaseUpdate, user: dict = Depends(get_current_user)):
    """Update a production phase."""
    await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    now = ts().isoformat()
    upd = {"fasi_produzione.$[elem].stato": data.stato}
    if data.stato == "in_corso":
        upd["fasi_produzione.$[elem].data_inizio"] = data.started_at or now
    elif data.stato == "completato":
        upd["fasi_produzione.$[elem].data_fine"] = data.completed_at or now
        if data.started_at:
            upd["fasi_produzione.$[elem].data_inizio"] = data.started_at
    if data.started_at:
        upd["fasi_produzione.$[elem].started_at"] = data.started_at
    if data.completed_at:
        upd["fasi_produzione.$[elem].completed_at"] = data.completed_at
    if data.operator_name:
        upd["fasi_produzione.$[elem].operator_name"] = data.operator_name
    if data.operatore is not None:
        upd["fasi_produzione.$[elem].operatore"] = data.operatore
    if data.note is not None:
        upd["fasi_produzione.$[elem].note"] = data.note
    if data.data_prevista is not None:
        upd["fasi_produzione.$[elem].data_prevista"] = data.data_prevista

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


# ── RIENTRO CONTO LAVORO ──
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


# ── VERIFICA CONTO LAVORO (chiusura + automazioni) ──
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
        doc_entry = {
            "doc_id": doc_id,
            "titolo": f"Certificato {cl.get('tipo','')} — {cl.get('fornitore_nome','')}",
            "tipo": "certificato_fornitore",
            "source": "conto_lavoro_rientro",
            "cl_id": cl_id,
            "uploaded_at": ts().isoformat(),
            "filename": cl.get("certificato_rientro_filename", "certificato.pdf"),
        }
        await db[COLL].update_one(
            {"commessa_id": cid},
            {"$push": {"documenti": doc_entry}},
        )

    await db[COLL].update_one(
        {"commessa_id": cid},
        push_event(cid, "CL_VERIFICATO", user, f"C/L {cl.get('tipo','')} verificato e chiuso")
    )
    return {"message": "Conto lavoro verificato e chiuso", "stato": "verificato"}


# ── NCR PDF (Non Conformity Report) ──
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


# ── DDT CONTO LAVORO: Preview PDF ──
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


# ── DDT CONTO LAVORO: Preview Email ──
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



# ── DDT CONTO LAVORO: Send Email ──
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
    # ══════════════════════════════════════════════════════════════════════
    # ⚠️ CASCADE DELETE BLINDATA — NON TOCCARE ⚠️
    # Quando si elimina un certificato, DEVONO essere eliminati anche:
    # - material_batches (tracciabilità)
    # - lotti_cam (CAM)
    # - archivio_certificati
    # - copie del documento
    # Usa 3 strategie di ricerca per garantire pulizia totale.
    # ══════════════════════════════════════════════════════════════════════

    doc = await db[DOC_COLL].find_one({"doc_id": doc_id, "commessa_id": cid, "user_id": user["user_id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    await db[DOC_COLL].delete_one({"doc_id": doc_id, "commessa_id": cid, "user_id": user["user_id"]})

    # ── STRATEGY 1: Delete by source_doc_id ──
    cam_1 = await db.lotti_cam.delete_many({"source_doc_id": doc_id, "user_id": user["user_id"]})
    batch_1 = await db.material_batches.delete_many({"source_doc_id": doc_id, "user_id": user["user_id"]})
    copies_del = await db[DOC_COLL].delete_many({"source_doc_id": doc_id, "user_id": user["user_id"]})
    archive_del = await db.archivio_certificati.delete_many({"source_doc_id": doc_id, "user_id": user["user_id"]})

    # ── STRATEGY 2: Delete by colata numbers (from ALL possible field locations) ──
    colate = set()
    # Check metadata_estratti.profili
    meta = doc.get("metadata_estratti") or {}
    for p in meta.get("profili", []):
        c = p.get("numero_colata", "")
        if c:
            colate.add(c)
    if meta.get("numero_colata"):
        colate.add(meta["numero_colata"])
    # Check risultati_match (new format)
    for r in doc.get("risultati_match", []):
        c = r.get("numero_colata", "")
        if c:
            colate.add(c)
    # Check extracted_profiles
    for p in doc.get("extracted_profiles", []):
        c = p.get("numero_colata", "") or p.get("heat_number", "")
        if c:
            colate.add(c)

    cam_2 = 0
    batch_2 = 0
    if colate:
        r1 = await db.lotti_cam.delete_many({
            "commessa_id": cid, "user_id": user["user_id"],
            "numero_colata": {"$in": list(colate)},
        })
        r2 = await db.material_batches.delete_many({
            "commessa_id": cid, "user_id": user["user_id"],
            "heat_number": {"$in": list(colate)},
        })
        cam_2 = r1.deleted_count
        batch_2 = r2.deleted_count

    # ── STRATEGY 3: If NO certificates remain for this commessa, nuke all orphans ──
    remaining_certs = await db[DOC_COLL].count_documents({
        "commessa_id": cid, "user_id": user["user_id"],
        "tipo": {"$in": ["certificato_31", "certificato_32", "certificato_ispezione"]},
    })
    cam_3 = 0
    batch_3 = 0
    if remaining_certs == 0:
        r1 = await db.lotti_cam.delete_many({"commessa_id": cid, "user_id": user["user_id"]})
        r2 = await db.material_batches.delete_many({"commessa_id": cid, "user_id": user["user_id"]})
        cam_3 = r1.deleted_count
        batch_3 = r2.deleted_count
        if cam_3 or batch_3:
            logger.info(f"[NUKE ORPHANS] No certs left for {cid}: deleted {cam_3} CAM, {batch_3} batches")

    total_cam = cam_1.deleted_count + cam_2 + cam_3
    total_batch = batch_1.deleted_count + batch_2 + batch_3
    cascade_info = f"CAM:{total_cam} Batch:{total_batch} Copie:{copies_del.deleted_count} Archivio:{archive_del.deleted_count}"
    logger.info(f"Cascade delete for doc {doc_id}: {cascade_info}")

    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, "DOCUMENTO_ELIMINATO", user, f"Doc {doc_id} eliminato ({cascade_info})"))
    return {"message": "Documento e dati collegati eliminati", "cascade": cascade_info}


# ══════════════════════════════════════════════════════════════════
#  AI OCR: Parse Certificate 3.1 (GPT-4o Vision)
# ══════════════════════════════════════════════════════════════════

@router.post("/{cid}/documenti/{doc_id}/parse-certificato")
async def parse_certificato_31(cid: str, doc_id: str, user: dict = Depends(get_current_user)):
    """Use GPT-4o Vision to extract data from a 3.1 material certificate.
    Supports PDF (converts to image) and image files.
    """
    import os
    import base64
    from io import BytesIO
    
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
        content_type = doc.get("content_type", "")
        
        # Check if it's a PDF and convert to images
        if content_type == "application/pdf" or doc.get("nome_file", "").lower().endswith(".pdf"):
            try:
                from pdf2image import convert_from_bytes
                
                # Decode PDF bytes
                pdf_bytes = base64.b64decode(file_b64)
                
                # Convert ALL pages (up to 3) at high DPI for accurate reading
                images = convert_from_bytes(pdf_bytes, first_page=1, last_page=3, dpi=300)
                if not images:
                    raise HTTPException(400, "Impossibile convertire il PDF in immagine")
                
                # Build image list for multi-page analysis
                file_contents = []
                for i, img in enumerate(images):
                    img_buffer = BytesIO()
                    img.save(img_buffer, format='PNG', optimize=True)
                    img_buffer.seek(0)
                    page_b64 = base64.b64encode(img_buffer.read()).decode('utf-8')
                    file_contents.append(ImageContent(image_base64=page_b64))
                    logger.info(f"Converted PDF page {i+1} to PNG for AI analysis: {doc_id}")
                
            except ImportError:
                raise HTTPException(500, "pdf2image non installato per la conversione PDF")
            except HTTPException:
                raise
            except Exception as pdf_err:
                logger.error(f"PDF conversion error: {pdf_err}")
                raise HTTPException(400, f"Errore conversione PDF: {str(pdf_err)}")
        else:
            file_contents = [ImageContent(image_base64=file_b64)]

        # Add filename context to help AI understand the document
        filename = doc.get("nome_file", "")
        filename_hint = ""
        if filename:
            filename_hint = "\n\nCONTESTO: Il file si chiama '" + filename + "'. Questo può indicare il tipo di profilo principale nel certificato."

        prompt = """Analizza questo certificato di materiale 3.1 (EN 10204) per acciaio strutturale.""" + filename_hint + """

COMPITO CRITICO: Devi estrarre OGNI SINGOLA RIGA della tabella del certificato come un profilo separato.

REGOLE FONDAMENTALI:
1. OGNI RIGA della tabella con un numero IT. diverso O un numero di colata diverso = UN ELEMENTO SEPARATO nell'array "profili"
2. NON saltare nessuna riga, nemmeno quelle con pallino nero, asterisco o simboli speciali
3. NON confondere i tipi di sezione: FLAT (piatto), UPN (profilo U), IPE, HEB, HEA, L (angolare), tubo sono TIPI DIVERSI
4. Le colonne tipiche sono: IT., CAST (colata), SECTION (sezione), DIMENSIONS (dimensioni in mm)
5. Se due righe hanno lo stesso IT. ma CAST diversi, sono DUE profili separati
6. Il tipo sezione va letto dalla colonna SECTION/B01, NON inventato
7. Le dimensioni vanno lette dalla colonna DIMENSIONS/B09-B10-B11

Rispondi in formato JSON PURO (senza markdown, senza ```):
{
  "fornitore": "nome del produttore/acciaieria",
  "n_certificato": "numero del certificato (campo A03)",
  "data_certificato": "data se presente",
  "normativa_riferimento": "norma di riferimento (es. EN 10025-2)",
  "percentuale_riciclato": "percentuale di contenuto riciclato se indicata (numero), altrimenti null",
  "metodo_produttivo": "forno_elettrico_non_legato oppure forno_elettrico_legato oppure ciclo_integrale se desumibile, altrimenti null",
  "certificazione_ambientale": "tipo di certificazione ambientale se presente (es. EPD), altrimenti null",
  "ente_certificatore_ambientale": "ente certificatore se indicato, altrimenti null",
  "profili": [
    {
      "numero_it": "numero IT dalla prima colonna della tabella",
      "dimensioni": "TIPO SEZIONE + dimensioni esatte dalla tabella (es. FLAT 120X12, UPN 100X50X6, IPE 200)",
      "numero_colata": "numero colata/heat/cast per questa riga (es. BE 228700)",
      "qualita_acciaio": "grado acciaio (es. S275JR, S355J2)",
      "peso_kg": "peso in kg se indicato, altrimenti null",
      "lunghezza_mt": "lunghezza in metri se indicata, altrimenti null",
      "normativa_prodotto": "norma prodotto specifica (es. EN 10058, EN 10279) se indicata",
      "composizione_chimica": "breve riepilogo composizione se presente (es. C=0.12, Mn=0.54, Ceq=0.30)",
      "proprieta_meccaniche": "ReH, Rm, A% se presenti (es. ReH=321, Rm=438, A=30.4%)",
      "conforme": true
    }
  ]
}

ESEMPIO: Se la tabella ha 5 righe (IT 3, 23, 24, 24, 25), l'array "profili" DEVE avere ESATTAMENTE 5 elementi.

ATTENZIONE SPECIALE:
- "Steel from electric arc furnace" → metodo_produttivo = "forno_elettrico_non_legato"
- "Environmental product declaration EPD" → certificazione_ambientale = "EPD"
- Se B02/GRADE indica "S275JR+AR", il grado è "S275JR+AR"
- Leggi TUTTE le righe della tabella, dall'alto al basso, senza saltarne nessuna

Se un campo non è leggibile, usa null. Rispondi SOLO con il JSON."""

        chat = LlmChat(
            api_key=LLM_KEY,
            session_id=f"cert31-{doc_id}",
            system_message="Sei un tecnico esperto di certificati materiale 3.1 per acciaio strutturale EN 10204. Estrai dati tecnici con precisione assoluta. Leggi OGNI riga della tabella, incluse le righe con simboli o pallini. I certificati spesso contengono profili di TIPO DIVERSO (FLAT/PIATTO, UPN, IPE, HEB) nella stessa tabella."
        ).with_model("anthropic", "claude-sonnet-4-20250514")

        response = await chat.send_message(UserMessage(
            text=prompt,
            file_contents=file_contents,
        ))

        # Parse JSON response
        import json
        # emergentintegrations returns string directly
        response_text = response if isinstance(response, str) else getattr(response, 'text', str(response))
        response_text = response_text.strip()
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

        # ── NORMALIZE: Ensure profili array exists ──
        profili = metadata.get("profili", [])
        if not profili and metadata.get("numero_colata"):
            # Old single-profile format → wrap in array
            profili = [{
                "dimensioni": metadata.get("dimensioni", ""),
                "numero_colata": metadata.get("numero_colata", ""),
                "qualita_acciaio": metadata.get("qualita_acciaio", ""),
                "peso_kg": metadata.get("peso_kg"),
                "composizione_chimica": metadata.get("composizione_chimica", ""),
                "proprieta_meccaniche": metadata.get("proprieta_meccaniche", ""),
                "conforme": metadata.get("conforme", True),
            }]
        metadata["profili"] = profili

        # Save extracted metadata to the document
        await db[DOC_COLL].update_one(
            {"doc_id": doc_id},
            {"$set": {"metadata_estratti": metadata, "tipo": "certificato_31"}},
        )

        # ── SMART MATCHING: Match profiles to commesse via OdA, RdP, DDT ──
        # ══════════════════════════════════════════════════════════════════════
        # ⚠️ DO NOT TOUCH: CLEANUP VECCHI DATI PRIMA DEL RE-MATCHING ⚠️
        # Se il certificato è stato già analizzato in precedenza, i vecchi
        # material_batches e lotti_cam devono essere ELIMINATI prima di creare
        # i nuovi match corretti. Altrimenti i profili non più corrispondenti
        # rimangono nella tracciabilità.
        # ══════════════════════════════════════════════════════════════════════
        old_batches = await db.material_batches.delete_many({
            "source_doc_id": doc_id, "user_id": user["user_id"]
        })
        old_cam = await db.lotti_cam.delete_many({
            "source_doc_id": doc_id, "user_id": user["user_id"]
        })
        old_archive = await db.archivio_certificati.delete_many({
            "source_doc_id": doc_id, "user_id": user["user_id"]
        })
        if old_batches.deleted_count or old_cam.deleted_count:
            logger.info(
                f"[RE-ANALYZE] Cleaned up old data for doc {doc_id}: "
                f"{old_batches.deleted_count} batches, {old_cam.deleted_count} CAM lotti, "
                f"{old_archive.deleted_count} archivio entries"
            )

        risultati_match = await _match_profili_to_commesse(
            profili=profili,
            metadata_cert=metadata,
            current_commessa_id=cid,
            doc_id=doc_id,
            doc=doc,
            user=user,
            dry_run=True,  # DON'T create batches — user must confirm first
        )

        # Store match results in document for later confirmation
        await db[DOC_COLL].update_one(
            {"doc_id": doc_id},
            {"$set": {"risultati_match": risultati_match, "match_pending_confirm": True}},
        )

        # Build backward-compatible metadata with first matched profile
        first_matched = next((r for r in risultati_match if r["commessa_id"] == cid), None)
        if first_matched:
            metadata["numero_colata"] = first_matched["numero_colata"]
            metadata["qualita_acciaio"] = first_matched.get("qualita_acciaio", "")
            metadata["dimensioni"] = first_matched.get("dimensioni", "")
            metadata["peso_kg"] = first_matched.get("peso_kg")

        matched_count = sum(1 for r in risultati_match if r['tipo'] == 'commessa_corrente')
        await db[COLL].update_one({"commessa_id": cid}, push_event(
            cid, "CERTIFICATO_ANALIZZATO", user,
            f"{len(profili)} profili trovati — {matched_count} corrispondenti all'OdA (da confermare)",
            {"doc_id": doc_id, "risultati_match": risultati_match, "metadata": metadata}
        ))

        return {
            "message": f"Certificato analizzato: {matched_count} profili corrispondono all'OdA. Conferma quali importare.",
            "metadata": metadata,
            "profili_trovati": len(profili),
            "risultati_match": risultati_match,
            "pending_confirm": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Certificate parsing error: {e}")
        raise HTTPException(500, f"Errore analisi certificato: {str(e)}")


class ConfirmProfiliRequest(BaseModel):
    """Request body for confirming which profiles to import."""
    selected_indices: List[int] = []  # Indices of profiles to import from risultati_match


@router.post("/{cid}/documenti/{doc_id}/confirm-profili")
async def confirm_profili(cid: str, doc_id: str, data: ConfirmProfiliRequest, user: dict = Depends(get_current_user)):
    """
    Step 2 of certificate analysis: User confirms which profiles to import.
    Only selected profiles create material_batches and CAM lotti.
    """
    comm = await get_commessa_or_404(cid, user["user_id"])

    # Get stored match results from the document
    doc = await db[DOC_COLL].find_one(
        {"doc_id": doc_id, "commessa_id": cid, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    risultati_match = doc.get("risultati_match", [])
    if not risultati_match:
        raise HTTPException(400, "Nessun risultato di matching da confermare. Rianalizza il certificato.")

    # Clean up any existing batches from previous imports for this document
    await db.material_batches.delete_many({"source_doc_id": doc_id, "user_id": user["user_id"]})
    await db.lotti_cam.delete_many({"source_doc_id": doc_id, "user_id": user["user_id"]})
    await db.archivio_certificati.delete_many({"source_doc_id": doc_id, "user_id": user["user_id"]})

    # Process only selected profiles
    metadata = doc.get("metadata", {})
    n_cert = metadata.get("numero_certificato", "")
    fornitore = metadata.get("fornitore", "")
    ente_cert = metadata.get("ente_certificatore", "")

    imported_count = 0
    archived_count = 0

    for i, r in enumerate(risultati_match):
        colata = r.get("numero_colata", "")
        dim = r.get("dimensioni", "")
        qualita = r.get("qualita_acciaio", "")
        peso = r.get("peso_kg", 0)
        target_cid = r.get("commessa_id", "")

        if i in data.selected_indices and target_cid:
            # USER SELECTED: create material_batch + CAM lotto
            batch_id = f"bat_{uuid.uuid4().hex[:10]}"
            await db.material_batches.insert_one({
                "batch_id": batch_id, "user_id": user["user_id"],
                "heat_number": colata, "material_type": qualita,
                "supplier_name": fornitore, "dimensions": dim,
                "normativa": metadata.get("normativa_riferimento", ""),
                "source_doc_id": doc_id, "commessa_id": target_cid,
                "numero_certificato": n_cert,
                "peso_kg": float(peso or 0),
                "notes": f"Confermato da utente - cert {n_cert}", "created_at": ts(),
            })

            # CAM lotto
            metodo = r.get("metodo_produttivo", metadata.get("metodo_produttivo", "forno_elettrico_non_legato"))
            perc = r.get("percentuale_riciclato")
            if perc is None:
                perc = {"forno_elettrico_non_legato": 80, "forno_elettrico_legato": 65, "ciclo_integrale": 10}.get(metodo, 75)
            perc = float(perc)
            soglie = {"forno_elettrico_non_legato": 75, "forno_elettrico_legato": 60, "ciclo_integrale": 12}
            soglia = soglie.get(metodo, 75)

            cam_id = f"cam_{uuid.uuid4().hex[:10]}"
            await db.lotti_cam.insert_one({
                "lotto_id": cam_id, "user_id": user["user_id"],
                "commessa_id": target_cid,
                "descrizione": dim or qualita or "Materiale da certificato",
                "fornitore": fornitore, "numero_colata": colata,
                "peso_kg": float(peso or 0), "qualita_acciaio": qualita,
                "percentuale_riciclato": perc, "metodo_produttivo": metodo,
                "tipo_certificazione": "dichiarazione_produttore",
                "numero_certificazione": n_cert,
                "ente_certificatore": ente_cert,
                "uso_strutturale": True, "soglia_minima_cam": soglia,
                "conforme_cam": perc >= soglia, "source_doc_id": doc_id,
                "note": f"Confermato da utente - {r.get('match_source', '')}",
                "created_at": ts(),
            })
            imported_count += 1
            logger.info(f"[CONFIRM] Imported profile '{dim}' colata={colata} to commessa {target_cid}")
        else:
            # NOT SELECTED or NO MATCH: archive
            await db.archivio_certificati.update_one(
                {"heat_number": colata, "source_doc_id": doc_id, "user_id": user["user_id"]},
                {"$set": {
                    "user_id": user["user_id"],
                    "heat_number": colata, "material_type": qualita,
                    "supplier_name": fornitore, "dimensions": dim,
                    "source_doc_id": doc_id, "numero_certificato": n_cert,
                    "peso_kg": float(peso or 0),
                    "note": "Non selezionato dall'utente" if target_cid else "Nessun match OdA",
                    "created_at": ts(),
                }},
                upsert=True,
            )
            archived_count += 1

    # Mark as confirmed
    await db[DOC_COLL].update_one(
        {"doc_id": doc_id},
        {"$set": {"match_pending_confirm": False, "profili_confermati": imported_count}},
    )

    logger.info(f"[CONFIRM] doc {doc_id}: {imported_count} imported, {archived_count} archived")
    return {
        "message": f"{imported_count} profili importati, {archived_count} in archivio",
        "imported": imported_count,
        "archived": archived_count,
    }


# ── Helper: normalize profile name for matching ──
def _normalize_profilo(text: str) -> str:
    """Normalize profile description for fuzzy matching.
    Translates English/Italian equivalents: FLAT = PIATTO, ANGLE = ANGOLARE, etc.
    """
    t = (text or "").upper().strip()
    # Compound descriptions → family names
    t = re.sub(r'\bFLAT\b', 'PIATTO', t)
    t = re.sub(r'\bCHANNEL\b', 'UPN', t)
    t = re.sub(r'\bBEAM\b', 'IPE', t)
    t = re.sub(r'\bTUBE\b', 'TUBO', t)
    t = re.sub(r'\bROUND\b', 'TONDO', t)
    t = re.sub(r'\bANGLE\b', 'ANGOLARE', t)
    t = re.sub(r'\bBARRA\s+FERRO\s+PIATT[AO]?\b', 'PIATTO', t)
    t = re.sub(r'\bBARRA\s+PIATT[AO]?\b', 'PIATTO', t)
    t = re.sub(r'\bFERRO\s+PIATT[AO]?\b', 'PIATTO', t)
    t = re.sub(r'\bPIATTA\b', 'PIATTO', t)
    t = re.sub(r'\bPROF\.?\s*FERRO\s+A\s+ELLE\b', 'L', t)
    t = re.sub(r'\bTUBO\s+FERRO\s+(QUADRO|RETT\.?|RETTANGOLARE)\s*(NERO)?\b', 'TUBO', t)
    t = re.sub(r'\bTUBO\s+FERRO\b', 'TUBO', t)
    # Remove filler words
    t = re.sub(r'\b(L\.?C\.?|MM\.?|IN|S\d{3}\w*|JR|J2|NERO|ZINCATO|BARRA|FERRO|PROF\.?|A|DI|DA)\b', '', t)
    t = re.sub(r'\.', '', t)
    t = re.sub(r'[x×\*]', 'X', t)
    t = re.sub(r'\s+', '', t)
    return t


def _extract_profile_base(text: str) -> str:
    # ══════════════════════════════════════════════════════════════════════════
    # ⚠️⚠️⚠️  DO NOT TOUCH — BLINDATA CON 26 TEST UNITARI  ⚠️⚠️⚠️
    # Questa funzione genera chiavi SPECIFICHE per dimensione:
    #   "FLAT 120X12" → "PIATTO120X12"
    #   "FLAT 120X7"  → "PIATTO120X7"   ← DEVE essere DIVERSA!
    # Se la tocchi, corri i test: pytest tests/test_profile_matching.py -v
    # ══════════════════════════════════════════════════════════════════════════
    """
    Extract the profile identifier from a description.
    For standard profiles (IPE, HEB, UPN): family + main size (e.g. IPE100, HEB200)
    For flat/tube/angle: family + FULL dimensions (e.g. PIATTO120X12, TUBO60X60X3)
    """
    t = (text or "").upper().strip()
    if not t:
        return ""

    # Product codes first (e.g., "FEPILC-120X12" → PIATTO120X12)
    prodcode = re.search(r'FEPIL[CA]-?(\d+)\s*[Xx×\*]\s*(\d+)', t)
    if prodcode:
        return f"PIATTO{prodcode.group(1)}X{prodcode.group(2)}"

    # Normalize compound descriptions → family names
    t = re.sub(r'\bFLAT\b', 'PIATTO', t)
    t = re.sub(r'\bBARRA\s+FERRO\s+PIATT[AO]?\b', 'PIATTO', t)
    t = re.sub(r'\bBARRA\s+PIATT[AO]?\b', 'PIATTO', t)
    t = re.sub(r'\bFERRO\s+PIATT[AO]?\b', 'PIATTO', t)
    t = re.sub(r'\bPIATTA\b', 'PIATTO', t)
    t = re.sub(r'\bPROF\.?\s*FERRO\s+A\s+ELLE\b', 'L', t)
    t = re.sub(r'\bTUBO\s+FERRO\s+(QUADRO|RETT\.?|RETTANGOLARE)\s*(NERO)?\b', 'TUBO', t)
    t = re.sub(r'\bTUBO\s+FERRO\b', 'TUBO', t)
    t = re.sub(r'\bCHANNEL\b', 'UPN', t)
    t = re.sub(r'\bANGLE\b', 'ANGOLARE', t)

    # Remove filler words BEFORE pattern matching
    t = re.sub(r'\b(L\.?C\.?|MM\.?|IN|NERO|ZINCATO|BARRA|FERRO|A|DI|DA)\b', '', t)
    t = re.sub(r'\.', ' ', t)
    t = re.sub(r'[x×\*]', 'X', t)
    # Collapse spaces around X in dimension patterns (e.g. "120 X 12" → "120X12")
    t = re.sub(r'(\d)\s*X\s*(\d)', r'\1X\2', t)
    t = re.sub(r'\s+', ' ', t).strip()

    # Profiles that need FULL dimensions (width x thickness or width x height x thickness)
    full_dim_families = r'(PIATTO|TUBO|ANGOLARE|L)'
    match_full = re.search(full_dim_families + r'\s*(\d+X\d+(?:X\d+)?)', t)
    if match_full:
        return f"{match_full.group(1)}{match_full.group(2)}"

    # Standard profiles: family + main size only (IPE 100, HEB 200, UPN 120)
    std_families = r'(IPE|HEB|HEA|HEM|INP|UPN|UNP|IPN|TONDO|OMEGA)'
    match_std = re.search(std_families + r'\s*(\d+)', t)
    if match_std:
        return f"{match_std.group(1)}{match_std.group(2)}"

    # Reverse: Number + Family (e.g., "120X55X7 UPN")
    reverse = r'(\d+X\d+(?:X\d+)?)\s*(?:' + std_families[1:-1] + r'|' + full_dim_families[1:-1] + r')'
    match_rev = re.search(reverse, t)
    if match_rev:
        family = re.search(std_families + r'|' + full_dim_families, t[match_rev.start():])
        if family:
            fam = family.group(0)
            dims = match_rev.group(1)
            if fam in ('PIATTO', 'TUBO', 'ANGOLARE', 'L'):
                return f"{fam}{dims}"
            else:
                return f"{fam}{dims.split('X')[0]}"

    return ""


async def _match_profili_to_commesse(
    # ══════════════════════════════════════════════════════════════════════════
    # ⚠️⚠️⚠️  DO NOT TOUCH — LOGICA DI MATCHING BLINDATA  ⚠️⚠️⚠️
    # Solo i profili del certificato che corrispondono ESATTAMENTE
    # a una riga OdA/RdP vengono associati alla commessa.
    # Profili senza match vanno in ARCHIVIO, non alla commessa!
    # Se OdA ha 2 profili e certificato ne ha 5, SOLO 2 vengono associati.
    # Test: pytest tests/test_oda_matching.py -v
    # ══════════════════════════════════════════════════════════════════════════
    profili: list, metadata_cert: dict, current_commessa_id: str,
    doc_id: str, doc: dict, user: dict, dry_run: bool = False,
) -> list:
    """
    Smart matching: for each profile in the certificate, find which commessa it belongs to.
    Cross-references: OdA righe, RdP righe, DDT arrivi.
    
    Flow:
    1. Build lookup of profile bases (e.g. "IPE100") → commessa_ids from ALL user's OdA/RdP/arrivi
    2. For each certificate profile:
       a. Try match by profile base (IPE100 from cert vs IPE100 from OdA) → preferred
       b. Try exact normalized match → secondary
       c. Try partial substring match → tertiary
       d. No match → ARCHIVIO (the profile doesn't belong to any commessa)
    3. Create material_batch + CAM lotto for the assigned commessa
    4. If assigned to another commessa, copy the certificate document there
    5. If no match → archive in archivio_certificati
    """
    risultati = []
    fornitore = metadata_cert.get("fornitore", "")
    metodo = metadata_cert.get("metodo_produttivo") or "forno_elettrico_non_legato"
    if metodo not in ("forno_elettrico_non_legato", "forno_elettrico_legato", "ciclo_integrale"):
        metodo = "forno_elettrico_non_legato"
    perc_ric = metadata_cert.get("percentuale_riciclato")
    cert_amb = metadata_cert.get("certificazione_ambientale", "")
    ente_cert = metadata_cert.get("ente_certificatore_ambientale", "")
    n_cert = metadata_cert.get("n_certificato", "")

    # 1. Get ALL user's commesse with their procurement data
    cursor = db[COLL].find(
        {"user_id": user["user_id"]},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "approvvigionamento": 1}
    )
    all_commesse = await cursor.to_list(500)
    logger.info(f"Smart matching: {len(profili)} profili, {len(all_commesse)} commesse, current={current_commessa_id}")

    # 2. Build TWO lookups from OdA/RdP/DDT:
    #    a) profile_base → set of commessa_ids  (e.g. "IPE100" → {"com_abc"})
    #    b) normalized_full → set of commessa_ids (e.g. "TRAVEIPE100INS275JR" → {"com_abc"})
    base_to_commesse = {}    # "IPE100" → {cid1, cid2}
    norm_to_commesse = {}    # "TRAVEIPE100INS275JR" → {cid1}
    for comm in all_commesse:
        cid_item = comm["commessa_id"]
        approv = comm.get("approvvigionamento", {})
        descriptions = []
        for oda in approv.get("ordini", []):
            for riga in oda.get("righe", []):
                descriptions.append(riga.get("descrizione", ""))
        for rdp in approv.get("richieste", []):
            for riga in rdp.get("righe", []):
                descriptions.append(riga.get("descrizione", ""))
        for arrivo in approv.get("arrivi", []):
            for mat in arrivo.get("materiali", []):
                descriptions.append(mat.get("descrizione", ""))

        for desc in descriptions:
            # Full normalized
            norm = _normalize_profilo(desc)
            if norm:
                norm_to_commesse.setdefault(norm, set()).add(cid_item)
            # Profile base (e.g. "IPE100")
            base = _extract_profile_base(desc)
            if base:
                base_to_commesse.setdefault(base, set()).add(cid_item)

    logger.info(f"Smart matching lookup: {len(base_to_commesse)} profili base, {len(norm_to_commesse)} normalizzati (basi: {list(base_to_commesse.keys())[:10]})")

    # 3. For each profile, find the matching commessa
    for profilo in profili:
        dim = profilo.get("dimensioni", "")
        norm_dim = _normalize_profilo(dim)
        colata = profilo.get("numero_colata", "")
        qualita = profilo.get("qualita_acciaio", "")
        peso = profilo.get("peso_kg")

        matched_commessa_id = None
        match_source = "nessuno"

        # Extract profile base from certificate (e.g. "IPE 100X55X4.1" → "IPE100")
        cert_base = _extract_profile_base(dim)

        # STEP A: Match by profile base (most reliable)
        # "IPE100" from certificate matches "IPE100" extracted from OdA "Trave IPE 100 in S275 JR"
        if cert_base and cert_base in base_to_commesse:
            matched_ids = base_to_commesse[cert_base]
            if current_commessa_id in matched_ids:
                matched_commessa_id = current_commessa_id
                match_source = f"profilo base {cert_base} (ordine/richiesta)"
            else:
                matched_commessa_id = next(iter(matched_ids))
                match_source = f"profilo base {cert_base} (altra commessa)"

        # STEP B: Try exact normalized match (fallback)
        if not matched_commessa_id and norm_dim and norm_dim in norm_to_commesse:
            matched_ids = norm_to_commesse[norm_dim]
            if current_commessa_id in matched_ids:
                matched_commessa_id = current_commessa_id
                match_source = "match esatto normalizzato"
            else:
                matched_commessa_id = next(iter(matched_ids))
                match_source = "match esatto normalizzato (altra commessa)"

        # STEP C: Try match by profile base with same family only (strict partial)
        # We do NOT do generic substring/dimension matching to avoid false positives
        # (e.g. "120X12" appearing in unrelated profiles like "ANGOLARE120X12X3")
        if not matched_commessa_id and cert_base:
            # Try to find commesse where the cert profile base is a PREFIX of an OdA base
            # e.g. cert "PIATTO120X12" matches OdA "PIATTO120X12" (already handled in Step A)
            # This step only handles edge cases where normalization differs slightly
            cert_family = re.match(r'([A-Z]+)', cert_base)
            if cert_family:
                fam = cert_family.group(1)
                for base_key, cids_set in base_to_commesse.items():
                    if base_key.startswith(fam) and base_key != cert_base:
                        # Only match if dimensions are identical (not just substring)
                        cert_dims = re.findall(r'\d+', cert_base)
                        oda_dims = re.findall(r'\d+', base_key)
                        if cert_dims and cert_dims == oda_dims:
                            if current_commessa_id in cids_set:
                                matched_commessa_id = current_commessa_id
                                match_source = f"famiglia+dimensioni {base_key}"
                            else:
                                matched_commessa_id = next(iter(cids_set))
                                match_source = f"famiglia+dimensioni {base_key} (altra commessa)"
                            break

        # NO FALLBACK: if no match found, profile goes to archive
        # This is by design — only profiles that match OdA/RdP/DDT belong to a commessa

        # Determine tipo
        if matched_commessa_id == current_commessa_id:
            tipo = "commessa_corrente"
        elif matched_commessa_id:
            tipo = "altra_commessa"
        else:
            tipo = "archivio"

        logger.info(f"Profile '{dim}' base='{cert_base}' (colata={colata}): tipo={tipo}, match={match_source}, commessa={matched_commessa_id or 'ARCHIVIO'}")

        # Get commessa info
        comm_info = next((c for c in all_commesse if c["commessa_id"] == matched_commessa_id), {})

        result_entry = {
            "dimensioni": dim,
            "numero_colata": colata,
            "qualita_acciaio": qualita,
            "peso_kg": peso,
            "tipo": tipo,
            "commessa_id": matched_commessa_id or "",
            "commessa_numero": comm_info.get("numero", ""),
            "commessa_titolo": comm_info.get("title", ""),
            "match_source": match_source,
            "profile_index": len(risultati),  # For user selection
        }

        # ── Create CAM lotto and material_batch ONLY if not dry_run ──
        if not dry_run and colata and matched_commessa_id:
            target_cid = matched_commessa_id
            existing_batch = await db.material_batches.find_one(
                {"heat_number": colata, "commessa_id": target_cid, "user_id": user["user_id"]}
            )
            if not existing_batch:
                batch_id = f"bat_{uuid.uuid4().hex[:10]}"
                await db.material_batches.insert_one({
                    "batch_id": batch_id, "user_id": user["user_id"],
                    "heat_number": colata, "material_type": qualita,
                    "supplier_name": fornitore, "dimensions": dim,
                    "normativa": metadata_cert.get("normativa_riferimento", ""),
                    "source_doc_id": doc_id, "commessa_id": target_cid,
                    "numero_certificato": n_cert,
                    "notes": f"Auto da cert {n_cert}", "created_at": ts(),
                })
                result_entry["batch_id"] = batch_id
                logger.info(f"Created material_batch {batch_id} for commessa {target_cid}, colata {colata}")

            # CAM lotto
            existing_cam = await db.lotti_cam.find_one(
                {"numero_colata": colata, "commessa_id": target_cid, "user_id": user["user_id"]}
            )
            if not existing_cam:
                perc = perc_ric if perc_ric is not None else {"forno_elettrico_non_legato": 80, "forno_elettrico_legato": 65, "ciclo_integrale": 10}.get(metodo, 75)
                perc = float(perc)
                cert_type = "dichiarazione_produttore"
                if cert_amb and "epd" in cert_amb.lower():
                    cert_type = "epd"
                elif cert_amb and "remade" in cert_amb.lower():
                    cert_type = "remade_in_italy"
                soglie = {"forno_elettrico_non_legato": 75, "forno_elettrico_legato": 60, "ciclo_integrale": 12}
                soglia = soglie.get(metodo, 75)

                cam_id = f"cam_{uuid.uuid4().hex[:10]}"
                await db.lotti_cam.insert_one({
                    "lotto_id": cam_id, "user_id": user["user_id"],
                    "commessa_id": target_cid,
                    "descrizione": dim or qualita or "Materiale da certificato",
                    "fornitore": fornitore, "numero_colata": colata,
                    "peso_kg": float(peso or 0), "qualita_acciaio": qualita,
                    "percentuale_riciclato": perc, "metodo_produttivo": metodo,
                    "tipo_certificazione": cert_type,
                    "numero_certificazione": n_cert,
                    "ente_certificatore": ente_cert,
                    "uso_strutturale": True, "soglia_minima_cam": soglia,
                    "conforme_cam": perc >= soglia, "source_doc_id": doc_id,
                    "note": f"Auto AI - Match: {match_source}",
                    "created_at": ts(),
                })
                result_entry["cam_lotto_id"] = cam_id
                logger.info(f"Created CAM lotto {cam_id} for commessa {target_cid}, colata {colata}")

        # ── If matched to another commessa, copy the certificate there ──
        if tipo == "altra_commessa" and matched_commessa_id:
            existing_copy = await db[DOC_COLL].find_one({
                "commessa_id": matched_commessa_id,
                "source_doc_id": doc_id,
                "user_id": user["user_id"],
            })
            if not existing_copy:
                copy_doc = {
                    "doc_id": f"doc_{uuid.uuid4().hex[:10]}",
                    "user_id": user["user_id"],
                    "commessa_id": matched_commessa_id,
                    "nome_file": doc.get("nome_file", "certificato.pdf"),
                    "tipo": "certificato_31",
                    "content_type": doc.get("content_type", ""),
                    "file_base64": doc.get("file_base64", ""),
                    "metadata_estratti": metadata_cert,
                    "source_doc_id": doc_id,
                    "note": f"Copia automatica da {current_commessa_id} — profilo {dim}",
                    "created_at": ts(),
                }
                await db[DOC_COLL].insert_one(copy_doc)
                result_entry["certificato_copiato"] = True
                logger.info(f"Certificate {doc_id} copied to commessa {matched_commessa_id} for profile {dim}")

        # ── Archive unmatched profiles ──
        if tipo == "archivio" and colata:
            await db.archivio_certificati.update_one(
                {"numero_colata": colata, "user_id": user["user_id"]},
                {"$set": {
                    "numero_colata": colata, "user_id": user["user_id"],
                    "dimensioni": dim, "qualita_acciaio": qualita,
                    "fornitore": fornitore, "peso_kg": peso,
                    "n_certificato": n_cert,
                    "source_doc_id": doc_id,
                    "percentuale_riciclato": perc_ric,
                    "metodo_produttivo": metodo,
                    "updated_at": ts(),
                }, "$setOnInsert": {"created_at": ts()}},
                upsert=True,
            )
            result_entry["archiviato"] = True
            logger.info(f"Profile '{dim}' (colata={colata}) archived — no OdA/RdP match found")

        risultati.append(result_entry)

    return risultati



# ══════════════════════════════════════════════════════════════════
#  GET ALL OPS DATA (for hub enrichment)
# ══════════════════════════════════════════════════════════════════

@router.get("/{cid}/ops")
async def get_commessa_ops(cid: str, user: dict = Depends(get_current_user)):
    """Get all operational data for a commessa: procurement, production, subcontracting, deliveries, documents."""
    doc = await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    
    # Refresh doc after ensure_ops_fields
    doc = await db[COLL].find_one({"commessa_id": cid, "user_id": user["user_id"]}, {"_id": 0})
    
    approv = doc.get("approvvigionamento", {"richieste": [], "ordini": [], "arrivi": []})
    fasi = doc.get("fasi_produzione", [])
    cl = doc.get("conto_lavoro", [])
    consegne = doc.get("consegne", [])

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
        "consegne": consegne,
        "documenti_count": doc_count,
    }


# ══════════════════════════════════════════════════════════════════
#  SCHEDA RINTRACCIABILITA' MATERIALI PDF (MOD. 07 — EN 1090)
# ══════════════════════════════════════════════════════════════════

class BatchUpdate(BaseModel):
    acciaieria: Optional[str] = None
    supplier_name: Optional[str] = None
    ddt_numero: Optional[str] = None
    posizione: Optional[str] = None
    n_pezzi: Optional[int] = None
    numero_certificato: Optional[str] = None

@router.patch("/{cid}/material-batches/{batch_id}")
async def update_material_batch(cid: str, batch_id: str, data: BatchUpdate, user: dict = Depends(get_current_user)):
    """Update editable fields on a material batch."""
    update_fields = {k: v for k, v in data.dict().items() if v is not None}
    if not update_fields:
        raise HTTPException(400, "Nessun campo da aggiornare")
    result = await db.material_batches.update_one(
        {"batch_id": batch_id, "commessa_id": cid, "user_id": user["user_id"]},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Lotto non trovato")
    return {"message": "Lotto aggiornato"}



@router.get("/{cid}/scheda-rintracciabilita-pdf")
async def scheda_rintracciabilita_pdf(cid: str, user: dict = Depends(get_current_user)):
    """Generate the EN 1090 Materials Traceability Sheet PDF for a commessa."""
    from fastapi.responses import StreamingResponse
    from services.pdf_scheda_rintracciabilita import generate_scheda_rintracciabilita_pdf

    commessa = await get_commessa_or_404(cid, user["user_id"])

    # Get company settings
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

    # Get client name
    client_name = ""
    if commessa.get("client_id"):
        client_doc = await db.clients.find_one({"client_id": commessa["client_id"]}, {"_id": 0, "name": 1})
        client_name = client_doc.get("name", "") if client_doc else ""

    # Get linked preventivo (for disegno number)
    preventivo = None
    if commessa.get("preventivo_id"):
        preventivo = await db.preventivi.find_one(
            {"preventivo_id": commessa["preventivo_id"]}, {"_id": 0}
        )

    # Get material batches for this commessa
    cursor = db.material_batches.find(
        {"commessa_id": cid, "user_id": user["user_id"]},
        {"_id": 0, "certificate_base64": 0}
    )
    batches = await cursor.to_list(200)

    # Get OdA (ordini acquisto) for fornitore info
    ordini = []
    approv = commessa.get("approvvigionamento", {})
    if approv:
        ordini = approv.get("ordini", [])

    buf = generate_scheda_rintracciabilita_pdf(
        company=company,
        commessa=commessa,
        preventivo=preventivo,
        batches=batches,
        client_name=client_name,
        ordini=ordini,
    )

    filename = f"Scheda_Rintracciabilita_{commessa.get('numero', cid)}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# ═══════════════════════════════════════════════════════════════
# SUPER FASCICOLO TECNICO UNICO (Aggregazione completa)
# ═══════════════════════════════════════════════════════════════

@router.get("/{commessa_id}/fascicolo-tecnico-completo")
async def download_super_fascicolo(commessa_id: str, user: dict = Depends(get_current_user)):
    """Generate the complete unified Technical Dossier (Fascicolo Tecnico Unico).
    Aggregates: Dossier + Riesame/ITT + Materials/CAM/Green + Welding + CE/DoP."""
    from services.pdf_super_fascicolo import generate_super_fascicolo

    try:
        pdf_buf = await generate_super_fascicolo(commessa_id, user["user_id"])
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"Super fascicolo generation error: {e}")
        raise HTTPException(500, f"Errore generazione fascicolo: {str(e)}")

    commessa = await get_commessa_or_404(commessa_id, user["user_id"])
    numero = commessa.get("numero", commessa_id).replace("/", "-")
    filename = f"Fascicolo_Tecnico_Completo_{numero}.pdf"

    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ═══════════════════════════════════════════════════════════════
# CONSEGNE — DDT Cliente + DoP + Etichetta CE
# ═══════════════════════════════════════════════════════════════

class ConsegnaCreate(BaseModel):
    note: Optional[str] = ""
    peso_kg: Optional[float] = 0
    num_colli: Optional[int] = 1
    ddt_number: Optional[str] = None  # User-editable DDT number
    selected_line_indices: Optional[List[int]] = None  # Which preventivo lines to include


@router.post("/{cid}/consegne")
async def crea_consegna(cid: str, data: ConsegnaCreate, user: dict = Depends(get_current_user)):
    """Create a new delivery (consegna) for this commessa.
    Auto-creates a DDT linked to the commessa and marks DoP + CE as generated."""
    comm = await get_commessa_or_404(cid, user["user_id"])
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

    # Resolve client (full data for DDT)
    client_name = ""
    client_doc = None
    if comm.get("client_id"):
        client_doc = await db.clients.find_one({"client_id": comm["client_id"]}, {"_id": 0})
        if client_doc:
            client_name = client_doc.get("business_name") or client_doc.get("name", "")

    # Count existing consegne for this commessa
    existing = comm.get("consegne", [])
    suffix = len(existing) + 1
    comm_num = comm.get("numero", cid)

    # Determine DDT type based on commessa type
    is_conto_lavoro = comm.get("tipo_commessa") == "conto_lavoro" or comm.get("is_conto_lavoro", False)
    ddt_type = "conto_lavoro" if is_conto_lavoro else "vendita"

    # Create DDT number: user-provided or auto-generated with separate numbering
    ddt_id = f"ddt_{uuid.uuid4().hex[:12]}"
    year = ts().strftime("%Y")

    if data.ddt_number and data.ddt_number.strip():
        ddt_number = data.ddt_number.strip()
    else:
        if is_conto_lavoro:
            ddt_count = await db.ddt_documents.count_documents({"user_id": user["user_id"], "ddt_type": "conto_lavoro"})
            ddt_number = f"CL-{year}-{ddt_count + 1:04d}"
        else:
            ddt_count = await db.ddt_documents.count_documents({"user_id": user["user_id"], "ddt_type": "vendita"})
            ddt_number = f"DDT-{year}-{ddt_count + 1:04d}"

    # Build DDT lines from PREVENTIVO descriptions (not material batches)
    lines = []
    preventivo = None
    if comm.get("preventivo_id"):
        preventivo = await db.preventivi.find_one(
            {"preventivo_id": comm["preventivo_id"]}, {"_id": 0}
        )

    if preventivo and preventivo.get("lines"):
        prev_lines = preventivo["lines"]
        # If user selected specific lines, filter them
        if data.selected_line_indices is not None:
            selected = [prev_lines[i] for i in data.selected_line_indices if i < len(prev_lines)]
        else:
            selected = prev_lines

        for i, pl in enumerate(selected):
            lines.append({
                "line_id": f"ln_{uuid.uuid4().hex[:8]}",
                "codice_articolo": pl.get("codice_articolo", ""),
                "description": pl.get("description", ""),
                "unit": pl.get("unit", "pz"),
                "quantity": float(pl.get("quantity", 1) or 1),
                "qta_fatturata": 0,
                "unit_price": 0,
                "sconto_1": 0, "sconto_2": 0,
                "vat_rate": pl.get("vat_rate", "22"),
                "notes": "",
            })

    if not lines:
        # Fallback: use commessa title
        lines.append({
            "line_id": f"ln_{uuid.uuid4().hex[:8]}",
            "codice_articolo": comm_num,
            "description": comm.get("title", "Struttura metallica"),
            "unit": "pz",
            "quantity": 1,
            "qta_fatturata": 0,
            "unit_price": 0,
            "sconto_1": 0, "sconto_2": 0,
            "vat_rate": "22",
            "notes": "",
        })

    now = ts()
    ddt_doc = {
        "ddt_id": ddt_id,
        "user_id": user["user_id"],
        "number": ddt_number,
        "ddt_type": ddt_type,
        "ddt_type_label": "DDT Conto Lavoro" if is_conto_lavoro else "DDT di Vendita",
        "client_id": comm.get("client_id", ""),
        "client_name": client_name,
        "client_address": client_doc.get("address", "") if client_doc else "",
        "client_cap": client_doc.get("cap", "") if client_doc else "",
        "client_city": client_doc.get("city", "") if client_doc else "",
        "client_province": client_doc.get("province", "") if client_doc else "",
        "client_piva": client_doc.get("partita_iva", "") if client_doc else "",
        "client_cf": client_doc.get("codice_fiscale", "") if client_doc else "",
        "client_pec": client_doc.get("pec", "") if client_doc else "",
        "client_sdi": client_doc.get("codice_sdi", "") if client_doc else "",
        "subject": f"Consegna {suffix} — Commessa {comm_num}",
        "destinazione": {},
        "causale_trasporto": "Conto Lavoro" if is_conto_lavoro else "Vendita",
        "aspetto_beni": "Strutture metalliche",
        "vettore": "Franco Mittente",
        "mezzo_trasporto": "Mittente",
        "porto": "Franco",
        "data_ora_trasporto": now.strftime("%d/%m/%Y %H:%M"),
        "num_colli": data.num_colli or 1,
        "peso_lordo_kg": data.peso_kg or 0,
        "peso_netto_kg": data.peso_kg or 0,
        "payment_type_id": None,
        "payment_type_label": None,
        "stampa_prezzi": False,
        "riferimento": f"Commessa {comm_num}",
        "acconto": 0, "sconto_globale": 0,
        "notes": data.note or "",
        "lines": lines,
        "totals": {"subtotal": 0, "total": 0, "line_count": len(lines)},
        "status": "non_fatturato",
        "commessa_id": cid,
        "created_at": now,
        "updated_at": now,
    }
    await db.ddt_documents.insert_one(ddt_doc)

    # Add consegna record to commessa
    consegna = {
        "consegna_id": f"cons_{uuid.uuid4().hex[:8]}",
        "numero": suffix,
        "ddt_id": ddt_id,
        "ddt_number": ddt_number,
        "data": now.isoformat()[:10],
        "peso_kg": data.peso_kg or 0,
        "num_colli": data.num_colli or 1,
        "note": data.note or "",
        "dop_generata": False,
        "ce_generata": False,
    }
    await db[COLL].update_one(
        {"commessa_id": cid},
        {"$push": {"consegne": consegna}},
    )
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, "CONSEGNA_CREATA", user, f"Consegna {suffix} — DDT {ddt_number}"))

    return {
        "message": f"Consegna {suffix} creata — DDT {ddt_number}",
        "consegna": consegna,
        "ddt_id": ddt_id,
    }


@router.get("/{cid}/consegne/{consegna_id}/pacchetto-pdf")
async def download_pacchetto_consegna(cid: str, consegna_id: str, user: dict = Depends(get_current_user)):
    """Generate combined PDF: DDT + DoP + Etichetta CE for a delivery."""
    from pypdf import PdfWriter, PdfReader
    from services.pdf_fascicolo_tecnico import generate_dop_pdf, generate_ce_pdf

    comm = await get_commessa_or_404(cid, user["user_id"])
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

    consegne = comm.get("consegne", [])
    cons = next((c for c in consegne if c["consegna_id"] == consegna_id), None)
    if not cons:
        raise HTTPException(404, "Consegna non trovata")

    # Client name
    client_name = ""
    if comm.get("client_id"):
        cl = await db.clients.find_one({"client_id": comm["client_id"]}, {"_id": 0, "business_name": 1, "name": 1})
        if cl:
            client_name = cl.get("business_name") or cl.get("name", "")

    ft = comm.get("fascicolo_tecnico", {})
    if not ft.get("mandatario"):
        ft["mandatario"] = client_name
    if not ft.get("redatto_da"):
        ft["redatto_da"] = company.get("responsabile_nome", "")

    # Auto-populate from company settings if not set in fascicolo_tecnico
    if not ft.get("certificato_numero"):
        ft["certificato_numero"] = company.get("certificato_en1090_numero", "")
    if not ft.get("ente_notificato"):
        ft["ente_notificato"] = company.get("ente_certificatore", "")
    if not ft.get("ente_numero"):
        ft["ente_numero"] = company.get("ente_certificatore_numero", "")
    if not ft.get("firmatario"):
        ft["firmatario"] = company.get("responsabile_nome", "")
    if not ft.get("ruolo_firmatario"):
        ft["ruolo_firmatario"] = company.get("ruolo_firmatario", "Legale Rappresentante")

    # Auto-populate luogo e data from company city + DDT date
    if not ft.get("luogo_data_firma"):
        ddt_doc_check = await db.ddt_documents.find_one({"ddt_id": cons["ddt_id"]}, {"_id": 0, "data_ora_trasporto": 1})
        ddt_date = ""
        if ddt_doc_check:
            raw_date = ddt_doc_check.get("data_ora_trasporto", "")
            ddt_date = raw_date.split(" ")[0] if raw_date else ""
        company_city = company.get("city", "")
        ft["luogo_data_firma"] = f"{company_city}, {ddt_date}".strip(", ")

    # Auto-populate DDT reference
    if not ft.get("ddt_riferimento"):
        ft["ddt_riferimento"] = cons.get("ddt_number", "")
    if not ft.get("ddt_data"):
        ddt_doc_check2 = await db.ddt_documents.find_one({"ddt_id": cons["ddt_id"]}, {"_id": 0, "data_ora_trasporto": 1})
        if ddt_doc_check2:
            raw = ddt_doc_check2.get("data_ora_trasporto", "")
            ft["ddt_data"] = raw.split(" ")[0] if raw else ""

    # Auto-populate disegno and ingegnere from preventivo
    preventivo = None
    if comm.get("preventivo_id"):
        preventivo = await db.preventivi.find_one(
            {"preventivo_id": comm["preventivo_id"]}, {"_id": 0}
        )
    if preventivo:
        if not ft.get("disegno_riferimento"):
            ft["disegno_riferimento"] = preventivo.get("numero_disegno", "")
        if not ft.get("ingegnere_disegno"):
            ft["ingegnere_disegno"] = preventivo.get("ingegnere_disegno", "")
        if not ft.get("disegno_numero"):
            ft["disegno_numero"] = preventivo.get("numero_disegno", "")

    # ── DYNAMIC MATERIAL PROPERTIES from real lotti_cam ──
    from services.pdf_fascicolo_tecnico import _get_material_properties, _get_durabilita
    lotti = await db.lotti_cam.find(
        {"commessa_id": cid, "user_id": user["user_id"]}, {"_id": 0}
    ).to_list(200)

    mat_props = _get_material_properties(lotti)
    ft["materiali_saldabilita"] = mat_props["materiali_saldabilita"]
    ft["resilienza"] = mat_props["resilienza"]
    ft["durabilita"] = _get_durabilita(comm)

    # ── PESO DDT: sum from material_batches ──
    ddt_doc_for_weight = await db.ddt_documents.find_one({"ddt_id": cons["ddt_id"], "user_id": user["user_id"]}, {"_id": 0})
    if ddt_doc_for_weight and (ddt_doc_for_weight.get("peso_lordo_kg") or 0) == 0:
        batches_for_weight = await db.material_batches.find(
            {"commessa_id": cid, "user_id": user["user_id"]}, {"_id": 0, "peso_kg": 1}
        ).to_list(200)
        total_weight = sum(float(b.get("peso_kg", 0) or 0) for b in batches_for_weight)
        if total_weight > 0:
            await db.ddt_documents.update_one(
                {"ddt_id": cons["ddt_id"]},
                {"$set": {"peso_lordo_kg": total_weight, "peso_netto_kg": total_weight}},
            )

    merger = PdfWriter()

    # 1. DDT PDF
    ddt_doc = await db.ddt_documents.find_one({"ddt_id": cons["ddt_id"], "user_id": user["user_id"]}, {"_id": 0})
    if ddt_doc:
        from services.ddt_pdf_service import generate_ddt_pdf
        ddt_buf = generate_ddt_pdf(ddt_doc, company)
        reader = PdfReader(ddt_buf)
        for page in reader.pages:
            merger.add_page(page)

    # 2. DoP PDF
    try:
        dop_buf = generate_dop_pdf(company, comm, client_name, ft)
        reader = PdfReader(dop_buf)
        for page in reader.pages:
            merger.add_page(page)
    except Exception as e:
        logger.warning(f"DoP generation error: {e}")

    # 3. Etichetta CE PDF
    try:
        ce_buf = generate_ce_pdf(company, comm, client_name, ft)
        reader = PdfReader(ce_buf)
        for page in reader.pages:
            merger.add_page(page)
    except Exception as e:
        logger.warning(f"CE generation error: {e}")

    # Mark as generated
    for i, c in enumerate(consegne):
        if c["consegna_id"] == consegna_id:
            await db[COLL].update_one(
                {"commessa_id": cid},
                {"$set": {f"consegne.{i}.dop_generata": True, f"consegne.{i}.ce_generata": True}},
            )
            break

    output = BytesIO()
    merger.write(output)
    output.seek(0)

    comm_num = comm.get("numero", cid).replace("/", "-")
    filename = f"Pacchetto_Consegna_{cons['numero']}_{comm_num}.pdf"
    return StreamingResponse(
        output, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



# ══════════════════════════════════════════════════════════════════
#  PRELIEVO DA MAGAZZINO (Withdraw from warehouse stock to commessa)
# ══════════════════════════════════════════════════════════════════

class PrelievoMagazzinoRequest(BaseModel):
    articolo_id: str
    quantita: float = Field(..., gt=0)
    note: Optional[str] = ""


@router.post("/{cid}/preleva-da-magazzino")
async def preleva_da_magazzino(cid: str, data: PrelievoMagazzinoRequest, user: dict = Depends(get_current_user)):
    """Withdraw material from warehouse stock and assign cost to commessa."""
    comm = await get_commessa_or_404(cid, user["user_id"])
    await ensure_ops_fields(cid)
    
    # Get the article from catalog
    articolo = await db.articoli.find_one(
        {"articolo_id": data.articolo_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not articolo:
        raise HTTPException(404, "Articolo non trovato nel catalogo")
    
    giacenza = float(articolo.get("giacenza", 0))
    if giacenza < data.quantita:
        raise HTTPException(
            400,
            f"Giacenza insufficiente: disponibili {giacenza} {articolo.get('unita_misura', 'pz')}, "
            f"richiesti {data.quantita} {articolo.get('unita_misura', 'pz')}"
        )
    
    prezzo_unitario = float(articolo.get("prezzo_unitario", 0))
    importo_totale = round(prezzo_unitario * data.quantita, 2)
    now = ts()
    
    # 1. Decrease stock in articoli
    new_giacenza = round(giacenza - data.quantita, 4)
    await db.articoli.update_one(
        {"articolo_id": data.articolo_id},
        {"$set": {"giacenza": new_giacenza, "updated_at": now}}
    )
    
    # 2. Add cost entry to commessa
    cost_entry = {
        "cost_id": new_id("cost_"),
        "tipo": "materiale_magazzino",
        "descrizione": f"Prelievo magazzino: {articolo.get('codice', '')} — {articolo.get('descrizione', '')}",
        "fornitore": articolo.get("fornitore_nome", ""),
        "importo": importo_totale,
        "quantita": data.quantita,
        "prezzo_unitario": prezzo_unitario,
        "unita_misura": articolo.get("unita_misura", "pz"),
        "articolo_id": data.articolo_id,
        "data": now.isoformat(),
        "note": data.note or "",
    }
    
    await db[COLL].update_one(
        {"commessa_id": cid},
        build_update_with_event(
            push_items={"costi_reali": cost_entry},
            tipo="PRELIEVO_MAGAZZINO", user=user,
            note=f"Prelievo {data.quantita} {articolo.get('unita_misura', 'pz')} di {articolo.get('codice', '')} — {importo_totale:.2f}€",
            payload={"articolo_id": data.articolo_id, "quantita": data.quantita, "importo": importo_totale}
        ),
    )
    
    return {
        "message": f"Prelevati {data.quantita} {articolo.get('unita_misura', 'pz')} di {articolo.get('codice', '')} — {importo_totale:.2f}€ imputati alla commessa {comm.get('numero', cid)}",
        "cost_entry": cost_entry,
        "giacenza_residua": new_giacenza,
    }
