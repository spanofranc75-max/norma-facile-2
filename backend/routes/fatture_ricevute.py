"""Fatture Ricevute (Received/Purchase Invoices) routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, date
from core.security import get_current_user
from core.database import db
import logging
import re

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fatture-ricevute", tags=["fatture_ricevute"])


# ── Models ───────────────────────────────────────────────────────

class FRStatus(str, Enum):
    DA_REGISTRARE = "da_registrare"
    REGISTRATA = "registrata"
    PAGATA = "pagata"
    CONTESTATA = "contestata"


class FRLineItem(BaseModel):
    numero_linea: int = 0
    codice_articolo: Optional[str] = None
    descrizione: str = ""
    quantita: float = 1.0
    unita_misura: str = "pz"
    prezzo_unitario: float = 0.0
    sconto_percent: float = 0.0
    aliquota_iva: str = "22"
    importo: float = 0.0


class FRCreate(BaseModel):
    fornitore_id: Optional[str] = None
    fornitore_nome: str = ""
    fornitore_piva: Optional[str] = None
    fornitore_cf: Optional[str] = None
    tipo_documento: str = "TD01"  # TD01=Fattura, TD04=Nota credito
    numero_documento: str = ""
    data_documento: str = ""  # ISO date
    data_ricezione: Optional[str] = None
    divisa: str = "EUR"
    linee: List[FRLineItem] = []
    imponibile: float = 0.0
    imposta: float = 0.0
    totale_documento: float = 0.0
    modalita_pagamento: Optional[str] = None
    condizioni_pagamento: Optional[str] = None
    data_scadenza_pagamento: Optional[str] = None
    note: Optional[str] = None
    xml_raw: Optional[str] = None
    sdi_id: Optional[str] = None


class FRUpdate(BaseModel):
    fornitore_id: Optional[str] = None
    fornitore_nome: Optional[str] = None
    status: Optional[FRStatus] = None
    note: Optional[str] = None
    linee: Optional[List[FRLineItem]] = None


class FRResponse(BaseModel):
    fr_id: str
    fornitore_id: Optional[str] = None
    fornitore_nome: str = ""
    fornitore_piva: Optional[str] = None
    fornitore_cf: Optional[str] = None
    tipo_documento: str = "TD01"
    numero_documento: str = ""
    data_documento: Optional[str] = None
    data_ricezione: Optional[str] = None
    status: str = "da_registrare"
    linee: List[dict] = []
    imponibile: float = 0.0
    imposta: float = 0.0
    totale_documento: float = 0.0
    modalita_pagamento: Optional[str] = None
    condizioni_pagamento: Optional[str] = None
    data_scadenza_pagamento: Optional[str] = None
    note: Optional[str] = None
    has_xml: bool = False
    sdi_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Payment tracking
    pagamenti: List[dict] = []
    totale_pagato: float = 0.0
    residuo: float = 0.0
    payment_status: str = "non_pagata"


# ── FatturaPA XML Parser ────────────────────────────────────────

NS_MAP = {
    'p': 'http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2',
}


def find_text(elem, path, default=""):
    """Find text in XML element with namespace handling."""
    if elem is None:
        return default
    # Try with namespace
    for prefix, uri in NS_MAP.items():
        full_path = path.replace('/', f'/{{{uri}}}')
        if not full_path.startswith('{'):
            full_path = f'{{{uri}}}' + full_path
        node = elem.find(full_path)
        if node is not None and node.text:
            return node.text.strip()
    # Try without namespace
    node = elem.find(path)
    if node is not None and node.text:
        return node.text.strip()
    # Try all children recursively for simple tag names
    tag_name = path.split('/')[-1]
    for child in elem.iter():
        local_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if local_name == tag_name and child.text:
            return child.text.strip()
    return default


def find_all(elem, tag_name):
    """Find all elements with given tag name (namespace-agnostic)."""
    results = []
    if elem is None:
        return results
    for child in elem.iter():
        local_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if local_name == tag_name:
            results.append(child)
    return results


def find_elem(elem, tag_name):
    """Find first element with given tag name (namespace-agnostic)."""
    if elem is None:
        return None
    for child in elem.iter():
        local_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if local_name == tag_name:
            return child
    return None


def parse_fattura_xml(xml_content: str) -> dict:
    """Parse a FatturaPA XML and extract invoice data."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise ValueError(f"XML non valido: {str(e)}")

    # Header — Fornitore (CedentePrestatore)
    cedente = find_elem(root, 'CedentePrestatore')
    fornitore_piva = find_text(cedente, 'IdFiscaleIVA/IdCodice') or find_text(cedente, 'IdCodice')
    fornitore_cf = find_text(cedente, 'CodiceFiscale')
    fornitore_denominazione = find_text(cedente, 'Denominazione')
    if not fornitore_denominazione:
        nome = find_text(cedente, 'Nome')
        cognome = find_text(cedente, 'Cognome')
        fornitore_denominazione = f"{nome} {cognome}".strip()

    fornitore_sede = find_elem(cedente, 'Sede')
    fornitore_indirizzo = find_text(fornitore_sede, 'Indirizzo') if fornitore_sede else ""

    # Body — DatiGeneraliDocumento
    body = find_elem(root, 'FatturaElettronicaBody')
    dati_generali = find_elem(body, 'DatiGeneraliDocumento')

    tipo_doc = find_text(dati_generali, 'TipoDocumento') or "TD01"
    divisa = find_text(dati_generali, 'Divisa') or "EUR"
    data_doc = find_text(dati_generali, 'Data')
    numero_doc = find_text(dati_generali, 'Numero')
    importo_totale = find_text(dati_generali, 'ImportoTotaleDocumento')

    # Lines — DettaglioLinee
    linee_xml = find_all(body, 'DettaglioLinee')
    linee = []
    for i, linea in enumerate(linee_xml):
        num = find_text(linea, 'NumeroLinea') or str(i + 1)
        desc = find_text(linea, 'Descrizione')
        qty_str = find_text(linea, 'Quantita') or "1"
        um = find_text(linea, 'UnitaMisura') or "pz"
        prezzo_str = find_text(linea, 'PrezzoUnitario') or "0"
        importo_str = find_text(linea, 'PrezzoTotale') or "0"
        iva_str = find_text(linea, 'AliquotaIVA') or "22.00"

        # Parse codice articolo
        codice_art = ""
        codice_elems = find_all(linea, 'CodiceArticolo')
        if codice_elems:
            codice_art = find_text(codice_elems[0], 'CodiceValore')

        # Parse sconto
        sconto = 0.0
        sconto_elem = find_elem(linea, 'ScontoMaggiorazione')
        if sconto_elem:
            sc_perc = find_text(sconto_elem, 'Percentuale')
            if sc_perc:
                sconto = float(sc_perc)

        linee.append({
            "numero_linea": int(num) if num.isdigit() else i + 1,
            "codice_articolo": codice_art,
            "descrizione": desc,
            "quantita": float(qty_str),
            "unita_misura": um.lower(),
            "prezzo_unitario": abs(float(prezzo_str)),
            "sconto_percent": sconto,
            "aliquota_iva": iva_str.replace('.00', ''),
            "importo": float(importo_str),
        })

    # Riepilogo IVA
    riepiloghi = find_all(body, 'DatiRiepilogo')
    imponibile_tot = 0.0
    imposta_tot = 0.0
    for riep in riepiloghi:
        imp_str = find_text(riep, 'ImponibileImporto') or "0"
        iva_str = find_text(riep, 'Imposta') or "0"
        imponibile_tot += float(imp_str)
        imposta_tot += float(iva_str)

    # Pagamento
    dati_pagamento = find_elem(body, 'DatiPagamento')
    modalita = ""
    condizioni = ""
    data_scadenza = ""
    if dati_pagamento:
        condizioni = find_text(dati_pagamento, 'CondizioniPagamento')
        dettaglio_pag = find_elem(dati_pagamento, 'DettaglioPagamento')
        if dettaglio_pag:
            modalita = find_text(dettaglio_pag, 'ModalitaPagamento')
            data_scadenza = find_text(dettaglio_pag, 'DataScadenzaPagamento')

    totale = float(importo_totale) if importo_totale else round(imponibile_tot + imposta_tot, 2)

    return {
        "fornitore_nome": fornitore_denominazione,
        "fornitore_piva": fornitore_piva,
        "fornitore_cf": fornitore_cf,
        "fornitore_indirizzo": fornitore_indirizzo,
        "tipo_documento": tipo_doc,
        "numero_documento": numero_doc,
        "data_documento": data_doc,
        "divisa": divisa,
        "linee": linee,
        "imponibile": round(imponibile_tot, 2),
        "imposta": round(imposta_tot, 2),
        "totale_documento": round(totale, 2),
        "modalita_pagamento": modalita,
        "condizioni_pagamento": condizioni,
        "data_scadenza_pagamento": data_scadenza,
    }


# ── CRUD Endpoints ──────────────────────────────────────────────

@router.get("/")
async def list_fatture_ricevute(
    q: Optional[str] = None,
    status: Optional[FRStatus] = None,
    year: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user)
):
    """List received invoices."""
    query = {"user_id": user["user_id"]}
    if status:
        query["status"] = status.value
    if year:
        query["data_documento"] = {"$regex": f"^{year}"}
    if q:
        query["$or"] = [
            {"fornitore_nome": {"$regex": q, "$options": "i"}},
            {"numero_documento": {"$regex": q, "$options": "i"}},
        ]

    total = await db.fatture_ricevute.count_documents(query)
    cursor = db.fatture_ricevute.find(query, {"_id": 0, "xml_raw": 0}).skip(skip).limit(limit).sort("created_at", -1)
    items = await cursor.to_list(length=limit)

    # Calculate KPIs
    all_query = {"user_id": user["user_id"]}
    if year:
        all_query["data_documento"] = {"$regex": f"^{year}"}
    pipeline = [
        {"$match": all_query},
        {"$group": {
            "_id": None,
            "totale": {"$sum": "$totale_documento"},
            "pagato": {"$sum": {"$ifNull": ["$totale_pagato", 0]}},
            "count": {"$sum": 1},
        }}
    ]
    agg = await db.fatture_ricevute.aggregate(pipeline).to_list(1)
    kpi = agg[0] if agg else {"totale": 0, "pagato": 0, "count": 0}

    return {
        "fatture": items,
        "total": total,
        "kpi": {
            "totale_fatture": round(kpi.get("totale", 0), 2),
            "totale_pagato": round(kpi.get("pagato", 0), 2),
            "da_pagare": round(kpi.get("totale", 0) - kpi.get("pagato", 0), 2),
            "count": kpi.get("count", 0),
        }
    }


@router.get("/{fr_id}")
async def get_fattura_ricevuta(
    fr_id: str,
    user: dict = Depends(get_current_user)
):
    """Get a single received invoice."""
    item = await db.fatture_ricevute.find_one(
        {"fr_id": fr_id, "user_id": user["user_id"]},
        {"_id": 0, "xml_raw": 0}
    )
    if not item:
        raise HTTPException(404, "Fattura ricevuta non trovata")
    return item


@router.post("/", status_code=201)
async def create_fattura_ricevuta(
    data: FRCreate,
    user: dict = Depends(get_current_user)
):
    """Create a received invoice manually."""
    now = datetime.now(timezone.utc)
    fr_id = f"fr_{uuid.uuid4().hex[:12]}"

    # Try to link supplier
    fornitore_id = data.fornitore_id
    if not fornitore_id and data.fornitore_piva:
        supplier = await db.clients.find_one(
            {"user_id": user["user_id"], "partita_iva": data.fornitore_piva},
            {"_id": 0, "client_id": 1}
        )
        if supplier:
            fornitore_id = supplier["client_id"]

    doc = {
        "fr_id": fr_id,
        "user_id": user["user_id"],
        "fornitore_id": fornitore_id,
        "fornitore_nome": data.fornitore_nome,
        "fornitore_piva": data.fornitore_piva,
        "fornitore_cf": data.fornitore_cf,
        "tipo_documento": data.tipo_documento,
        "numero_documento": data.numero_documento,
        "data_documento": data.data_documento,
        "data_ricezione": data.data_ricezione or now.strftime("%Y-%m-%d"),
        "status": FRStatus.DA_REGISTRARE.value,
        "linee": [l.model_dump() for l in data.linee],
        "imponibile": data.imponibile,
        "imposta": data.imposta,
        "totale_documento": data.totale_documento,
        "modalita_pagamento": data.modalita_pagamento,
        "condizioni_pagamento": data.condizioni_pagamento,
        "data_scadenza_pagamento": data.data_scadenza_pagamento,
        "note": data.note,
        "has_xml": bool(data.xml_raw),
        "xml_raw": data.xml_raw,
        "sdi_id": data.sdi_id,
        "pagamenti": [],
        "totale_pagato": 0.0,
        "residuo": data.totale_documento,
        "payment_status": "non_pagata",
        "created_at": now,
        "updated_at": now,
    }
    await db.fatture_ricevute.insert_one(doc)
    created = await db.fatture_ricevute.find_one({"fr_id": fr_id}, {"_id": 0, "xml_raw": 0})
    return created


@router.put("/{fr_id}")
async def update_fattura_ricevuta(
    fr_id: str,
    data: FRUpdate,
    user: dict = Depends(get_current_user)
):
    """Update a received invoice."""
    existing = await db.fatture_ricevute.find_one(
        {"fr_id": fr_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not existing:
        raise HTTPException(404, "Fattura ricevuta non trovata")

    update_dict = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if "linee" in update_dict:
        update_dict["linee"] = [l.model_dump() if hasattr(l, 'model_dump') else l for l in update_dict["linee"]]
    if "status" in update_dict:
        update_dict["status"] = update_dict["status"].value if hasattr(update_dict["status"], 'value') else update_dict["status"]

    update_dict["updated_at"] = datetime.now(timezone.utc)
    await db.fatture_ricevute.update_one({"fr_id": fr_id}, {"$set": update_dict})

    updated = await db.fatture_ricevute.find_one({"fr_id": fr_id}, {"_id": 0, "xml_raw": 0})
    return updated


@router.delete("/{fr_id}")
async def delete_fattura_ricevuta(
    fr_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete a received invoice."""
    result = await db.fatture_ricevute.delete_one(
        {"fr_id": fr_id, "user_id": user["user_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Fattura ricevuta non trovata")
    return {"message": "Fattura eliminata"}


# ── XML Import ──────────────────────────────────────────────────

@router.post("/import-xml")
async def import_xml_fattura(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """Import a FatturaPA XML file and create a received invoice."""
    if not file.filename.lower().endswith('.xml'):
        raise HTTPException(400, "Il file deve essere in formato XML")

    content = await file.read()
    xml_str = content.decode('utf-8', errors='replace')

    try:
        parsed = parse_fattura_xml(xml_str)
    except ValueError as e:
        raise HTTPException(400, str(e))

    now = datetime.now(timezone.utc)
    fr_id = f"fr_{uuid.uuid4().hex[:12]}"

    # Try to match supplier
    fornitore_id = None
    if parsed.get("fornitore_piva"):
        supplier = await db.clients.find_one(
            {"user_id": user["user_id"], "partita_iva": parsed["fornitore_piva"]},
            {"_id": 0, "client_id": 1}
        )
        if supplier:
            fornitore_id = supplier["client_id"]

    doc = {
        "fr_id": fr_id,
        "user_id": user["user_id"],
        "fornitore_id": fornitore_id,
        "fornitore_nome": parsed.get("fornitore_nome", ""),
        "fornitore_piva": parsed.get("fornitore_piva"),
        "fornitore_cf": parsed.get("fornitore_cf"),
        "tipo_documento": parsed.get("tipo_documento", "TD01"),
        "numero_documento": parsed.get("numero_documento", ""),
        "data_documento": parsed.get("data_documento", ""),
        "data_ricezione": now.strftime("%Y-%m-%d"),
        "status": FRStatus.DA_REGISTRARE.value,
        "linee": parsed.get("linee", []),
        "imponibile": parsed.get("imponibile", 0),
        "imposta": parsed.get("imposta", 0),
        "totale_documento": parsed.get("totale_documento", 0),
        "modalita_pagamento": parsed.get("modalita_pagamento"),
        "condizioni_pagamento": parsed.get("condizioni_pagamento"),
        "data_scadenza_pagamento": parsed.get("data_scadenza_pagamento"),
        "note": None,
        "has_xml": True,
        "xml_raw": xml_str,
        "sdi_id": None,
        "pagamenti": [],
        "totale_pagato": 0.0,
        "residuo": parsed.get("totale_documento", 0),
        "payment_status": "non_pagata",
        "created_at": now,
        "updated_at": now,
    }
    await db.fatture_ricevute.insert_one(doc)
    created = await db.fatture_ricevute.find_one({"fr_id": fr_id}, {"_id": 0, "xml_raw": 0})

    return {
        "message": f"Fattura importata: {parsed.get('numero_documento', 'N/A')} da {parsed.get('fornitore_nome', 'N/A')}",
        "fattura": created,
        "fornitore_trovato": fornitore_id is not None,
    }


# ── Parse XML Preview (no save) ─────────────────────────────────

@router.post("/preview-xml")
async def preview_xml_fattura(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """Parse a FatturaPA XML file and return preview without saving."""
    content = await file.read()
    xml_str = content.decode('utf-8', errors='replace')

    try:
        parsed = parse_fattura_xml(xml_str)
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {"preview": parsed}


# ── Extract Articles to Catalog ─────────────────────────────────

@router.post("/{fr_id}/extract-articoli")
async def extract_articoli(
    fr_id: str,
    user: dict = Depends(get_current_user)
):
    """Extract line items from a received invoice into the Catalogo Articoli."""
    fr = await db.fatture_ricevute.find_one(
        {"fr_id": fr_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not fr:
        raise HTTPException(404, "Fattura ricevuta non trovata")

    linee = fr.get("linee", [])
    fornitore_nome = fr.get("fornitore_nome", "")
    now = datetime.now(timezone.utc)

    created_count = 0
    updated_count = 0
    skipped_count = 0

    for linea in linee:
        desc = linea.get("descrizione", "").strip()
        if not desc or len(desc) < 3:
            skipped_count += 1
            continue

        prezzo = abs(linea.get("prezzo_unitario", 0))
        codice = (linea.get("codice_articolo") or "").strip()
        if not codice:
            # Generate code from first 3 words of description
            words = re.sub(r'[^a-zA-Z0-9\s]', '', desc).upper().split()[:3]
            codice = "-".join(words) if words else f"ART-{uuid.uuid4().hex[:4].upper()}"

        um = linea.get("unita_misura", "pz").lower()
        if um not in ["pz", "ml", "mq", "kg", "h", "corpo", "lt"]:
            um = "pz"

        iva = linea.get("aliquota_iva", "22").replace('.00', '')

        # Check existing
        existing = await db.articoli.find_one(
            {"user_id": user["user_id"], "codice": codice},
            {"_id": 0}
        )

        if existing:
            # Update price if different
            if abs(prezzo - existing.get("prezzo_unitario", 0)) > 0.01:
                await db.articoli.update_one(
                    {"articolo_id": existing["articolo_id"]},
                    {
                        "$set": {"prezzo_unitario": prezzo, "updated_at": now},
                        "$push": {"storico_prezzi": {
                            "prezzo": prezzo,
                            "data": now.isoformat(),
                            "fonte": f"Fatt. {fr.get('numero_documento', '')} — {fornitore_nome}"
                        }}
                    }
                )
                updated_count += 1
            else:
                skipped_count += 1
        else:
            doc = {
                "articolo_id": f"art_{uuid.uuid4().hex[:12]}",
                "user_id": user["user_id"],
                "codice": codice,
                "descrizione": desc,
                "categoria": "materiale",
                "unita_misura": um,
                "prezzo_unitario": prezzo,
                "aliquota_iva": iva,
                "fornitore_nome": fornitore_nome,
                "fornitore_id": fr.get("fornitore_id"),
                "note": f"Importato da fattura {fr.get('numero_documento', '')}",
                "storico_prezzi": [{"prezzo": prezzo, "data": now.isoformat(), "fonte": f"Fatt. {fr.get('numero_documento', '')} — {fornitore_nome}"}],
                "created_at": now,
                "updated_at": now,
            }
            await db.articoli.insert_one(doc)
            created_count += 1

    return {
        "message": f"Estrazione completata: {created_count} creati, {updated_count} aggiornati, {skipped_count} saltati",
        "created": created_count,
        "updated": updated_count,
        "skipped": skipped_count,
    }


# ── Payment Tracking ────────────────────────────────────────────

class FRPayment(BaseModel):
    importo: float = Field(..., gt=0)
    data_pagamento: str
    metodo: Optional[str] = None
    note: Optional[str] = None


@router.get("/{fr_id}/pagamenti")
async def get_fr_pagamenti(
    fr_id: str,
    user: dict = Depends(get_current_user)
):
    """Get payment info for a received invoice."""
    fr = await db.fatture_ricevute.find_one(
        {"fr_id": fr_id, "user_id": user["user_id"]},
        {"_id": 0, "xml_raw": 0}
    )
    if not fr:
        raise HTTPException(404, "Fattura ricevuta non trovata")

    pagamenti = fr.get("pagamenti", [])
    pagato = sum(p.get("importo", 0) for p in pagamenti)
    total_doc = fr.get("totale_documento", 0)
    residuo = round(total_doc - pagato, 2)

    return {
        "fr_id": fr_id,
        "total_document": total_doc,
        "pagamenti": pagamenti,
        "totale_pagato": round(pagato, 2),
        "residuo": max(residuo, 0),
        "payment_status": "pagata" if residuo <= 0.01 else ("parzialmente_pagata" if pagato > 0 else "non_pagata"),
    }


@router.post("/{fr_id}/pagamenti")
async def record_fr_payment(
    fr_id: str,
    payment: FRPayment,
    user: dict = Depends(get_current_user)
):
    """Record payment for a received invoice."""
    fr = await db.fatture_ricevute.find_one(
        {"fr_id": fr_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not fr:
        raise HTTPException(404, "Fattura ricevuta non trovata")

    pagamenti = fr.get("pagamenti", [])
    paid_so_far = sum(p.get("importo", 0) for p in pagamenti)
    total_doc = fr.get("totale_documento", 0)

    if payment.importo > (total_doc - paid_so_far + 0.01):
        raise HTTPException(400, "Importo supera il residuo")

    new_payment = {
        "payment_id": f"pay_{uuid.uuid4().hex[:8]}",
        "importo": payment.importo,
        "data_pagamento": payment.data_pagamento,
        "metodo": payment.metodo,
        "note": payment.note,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    new_paid = paid_so_far + payment.importo
    residuo = round(total_doc - new_paid, 2)
    ps = "pagata" if residuo <= 0.01 else "parzialmente_pagata"

    update = {
        "$push": {"pagamenti": new_payment},
        "$set": {
            "totale_pagato": round(new_paid, 2),
            "residuo": max(residuo, 0),
            "payment_status": ps,
            "updated_at": datetime.now(timezone.utc),
        }
    }
    if residuo <= 0.01:
        update["$set"]["status"] = "pagata"

    await db.fatture_ricevute.update_one({"fr_id": fr_id}, update)
    return {"message": "Pagamento registrato", "totale_pagato": round(new_paid, 2), "residuo": max(residuo, 0), "payment_status": ps}
