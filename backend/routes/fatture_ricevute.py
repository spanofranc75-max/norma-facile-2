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
from core.config import settings
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

    # Smart Import: auto-detect welding consumables
    try:
        from routes.consumables import analyze_and_import_invoice_consumables
        consumable_doc = {**doc, "fattura_id": fr_id}
        consumables = await analyze_and_import_invoice_consumables(consumable_doc, user["user_id"])
        if consumables:
            logger.info(f"Auto-imported {len(consumables)} consumables from invoice {fr_id}")
    except Exception as e:
        logger.warning(f"Consumable auto-import failed for {fr_id}: {e}")

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

    # Smart Import: auto-detect welding consumables
    try:
        from routes.consumables import analyze_and_import_invoice_consumables
        consumable_doc = {**doc, "fattura_id": fr_id}
        consumables = await analyze_and_import_invoice_consumables(consumable_doc, user["user_id"])
        if consumables:
            logger.info(f"Auto-imported {len(consumables)} consumables from XML invoice {fr_id}")
    except Exception as e:
        logger.warning(f"Consumable auto-import failed for XML {fr_id}: {e}")

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

        um = (linea.get("unita_misura") or "pz").lower()
        if um not in ["pz", "ml", "mq", "kg", "h", "corpo", "lt"]:
            um = "pz"

        iva = (linea.get("aliquota_iva") or "22").replace('.00', '')

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



# ── Cost Imputation (Assign to Commessa or Magazzino) ────────────

class ImputazioneDestinazione(str, Enum):
    COMMESSA = "commessa"
    MAGAZZINO = "magazzino"


class ImputazioneRequest(BaseModel):
    destinazione: ImputazioneDestinazione
    commessa_id: Optional[str] = None
    righe_selezionate: Optional[List[int]] = None  # line indexes, None = all
    note: Optional[str] = None


@router.post("/{fr_id}/imputa")
async def imputa_costi(
    fr_id: str,
    data: ImputazioneRequest,
    user: dict = Depends(get_current_user)
):
    """Assign invoice costs to a commessa or magazzino."""
    fr = await db.fatture_ricevute.find_one(
        {"fr_id": fr_id, "user_id": user["user_id"]}, {"_id": 0, "xml_raw": 0}
    )
    if not fr:
        raise HTTPException(404, "Fattura ricevuta non trovata")

    linee = fr.get("linee", [])
    if data.righe_selezionate:
        selected = [linee[i] for i in data.righe_selezionate if i < len(linee)]
    else:
        selected = linee

    if not selected:
        raise HTTPException(400, "Nessuna riga selezionata")

    totale_imputato = sum(abs(l.get("importo", 0)) for l in selected)
    now = datetime.now(timezone.utc)

    if data.destinazione == ImputazioneDestinazione.COMMESSA:
        if not data.commessa_id:
            raise HTTPException(400, "commessa_id obbligatorio per destinazione commessa")

        commessa = await db.commesse.find_one(
            {"commessa_id": data.commessa_id, "user_id": user["user_id"]},
            {"_id": 0, "commessa_id": 1, "numero": 1}
        )
        if not commessa:
            raise HTTPException(404, "Commessa non trovata")

        # Add cost entry to commessa
        cost_entry = {
            "cost_id": f"cost_{uuid.uuid4().hex[:8]}",
            "tipo": "materiale",
            "descrizione": f"Fatt. {fr.get('numero_documento', '')} — {fr.get('fornitore_nome', '')}",
            "fornitore": fr.get("fornitore_nome", ""),
            "importo": round(totale_imputato, 2),
            "data": now.isoformat(),
            "fr_id": fr_id,
            "note": data.note or "",
            "righe": [{
                "descrizione": l.get("descrizione", ""),
                "quantita": l.get("quantita", 0),
                "prezzo_unitario": l.get("prezzo_unitario", 0),
                "importo": l.get("importo", 0),
            } for l in selected],
        }

        await db.commesse.update_one(
            {"commessa_id": data.commessa_id},
            {"$push": {"costi_reali": cost_entry}, "$set": {"updated_at": now}}
        )

        # Mark fattura as processed
        await db.fatture_ricevute.update_one(
            {"fr_id": fr_id},
            {"$set": {
                "imputazione": {
                    "destinazione": "commessa",
                    "commessa_id": data.commessa_id,
                    "commessa_numero": commessa.get("numero", ""),
                    "importo": round(totale_imputato, 2),
                    "data": now.isoformat(),
                },
                "status": "registrata",
                "updated_at": now,
            }}
        )

        return {
            "message": f"Costo di {totale_imputato:.2f}€ imputato alla commessa {commessa.get('numero', '')}",
            "destinazione": "commessa",
            "commessa_numero": commessa.get("numero", ""),
            "importo": round(totale_imputato, 2),
        }

    else:  # MAGAZZINO
        updated_count = 0
        created_count = 0
        for linea in selected:
            desc = linea.get("descrizione", "").strip()
            if not desc or len(desc) < 3:
                continue

            prezzo = abs(linea.get("prezzo_unitario", 0))
            qty = abs(linea.get("quantita", 0))
            codice = (linea.get("codice_articolo") or "").strip()

            if codice:
                existing = await db.articoli.find_one(
                    {"user_id": user["user_id"], "codice": codice}, {"_id": 0}
                )
            else:
                existing = None

            if existing:
                # Update stock and price
                old_price = existing.get("prezzo_unitario", 0)
                old_stock = existing.get("giacenza", 0)
                new_stock = old_stock + qty

                # Weighted average price
                if old_stock + qty > 0:
                    new_price = ((old_price * old_stock) + (prezzo * qty)) / (old_stock + qty)
                else:
                    new_price = prezzo

                await db.articoli.update_one(
                    {"articolo_id": existing["articolo_id"]},
                    {
                        "$set": {
                            "prezzo_unitario": round(new_price, 4),
                            "giacenza": new_stock,
                            "updated_at": now,
                        },
                        "$push": {"storico_prezzi": {
                            "prezzo": prezzo,
                            "data": now.isoformat(),
                            "fonte": f"Fatt. {fr.get('numero_documento', '')} — {fr.get('fornitore_nome', '')}",
                            "quantita": qty,
                        }}
                    }
                )
                updated_count += 1
            else:
                # Create new article with stock
                words = re.sub(r'[^a-zA-Z0-9\s]', '', desc).upper().split()[:3]
                auto_codice = "-".join(words) if words else f"ART-{uuid.uuid4().hex[:4].upper()}"
                um = (linea.get("unita_misura") or "pz").lower()

                doc = {
                    "articolo_id": f"art_{uuid.uuid4().hex[:12]}",
                    "user_id": user["user_id"],
                    "codice": codice or auto_codice,
                    "descrizione": desc,
                    "categoria": "materiale",
                    "unita_misura": um,
                    "prezzo_unitario": prezzo,
                    "giacenza": qty,
                    "aliquota_iva": (linea.get("aliquota_iva") or "22").replace('.00', ''),
                    "fornitore_nome": fr.get("fornitore_nome", ""),
                    "fornitore_id": fr.get("fornitore_id"),
                    "storico_prezzi": [{"prezzo": prezzo, "data": now.isoformat(),
                        "fonte": f"Fatt. {fr.get('numero_documento', '')} — {fr.get('fornitore_nome', '')}",
                        "quantita": qty}],
                    "created_at": now,
                    "updated_at": now,
                }
                await db.articoli.insert_one(doc)
                created_count += 1

        # Mark fattura as processed
        await db.fatture_ricevute.update_one(
            {"fr_id": fr_id},
            {"$set": {
                "imputazione": {
                    "destinazione": "magazzino",
                    "importo": round(totale_imputato, 2),
                    "data": now.isoformat(),
                    "articoli_aggiornati": updated_count,
                    "articoli_creati": created_count,
                },
                "status": "registrata",
                "updated_at": now,
            }}
        )

        return {
            "message": f"Magazzino aggiornato: {created_count} articoli creati, {updated_count} aggiornati",
            "destinazione": "magazzino",
            "importo": round(totale_imputato, 2),
            "created": created_count,
            "updated": updated_count,
        }


# ── FattureInCloud Sync ─────────────────────────────────────────

@router.post("/sync-fic")
async def sync_fatture_from_fic(
    user: dict = Depends(get_current_user)
):
    """Sync received invoices from FattureInCloud API."""
    from services.fattureincloud_api import get_fic_client

    # Get user's FIC credentials from settings or user profile
    user_doc = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    fic_token = (user_doc or {}).get("fic_access_token") or getattr(settings, 'fic_access_token', None)
    fic_company_id = (user_doc or {}).get("fic_company_id") or getattr(settings, 'fic_company_id', None)

    if not fic_token or not fic_company_id:
        raise HTTPException(400, "FattureInCloud non configurato. Inserisci il token API nelle impostazioni.")

    client = get_fic_client(access_token=fic_token, company_id=int(fic_company_id))
    if not client.is_configured:
        raise HTTPException(400, "Configurazione FattureInCloud incompleta")

    imported = 0
    skipped = 0
    errors = []
    page = 1

    try:
        while True:
            resp = await client.list_received_invoices(page=page, per_page=50)
            data_list = resp.get("data", [])
            if not data_list:
                break

            for doc_fic in data_list:
                fic_id = str(doc_fic.get("id", ""))
                # Skip if already imported
                existing = await db.fatture_ricevute.find_one(
                    {"user_id": user["user_id"], "fic_id": fic_id}, {"_id": 0, "fr_id": 1}
                )
                if existing:
                    skipped += 1
                    continue

                # Map FIC document to our schema
                entity = doc_fic.get("entity", {}) or {}
                items = doc_fic.get("items_list", []) or []

                linee = []
                for i, item in enumerate(items):
                    linee.append({
                        "numero_linea": i + 1,
                        "codice_articolo": item.get("code", ""),
                        "descrizione": item.get("name", ""),
                        "quantita": float(item.get("qty", 1)),
                        "unita_misura": item.get("measure", "pz") or "pz",
                        "prezzo_unitario": abs(float(item.get("net_price", 0))),
                        "sconto_percent": float(item.get("discount", 0)),
                        "aliquota_iva": str(int(item.get("vat", {}).get("value", 22))) if isinstance(item.get("vat"), dict) else "22",
                        "importo": float(item.get("net_price", 0)) * float(item.get("qty", 1)),
                    })

                amount_net = float(doc_fic.get("amount_net", 0))
                amount_vat = float(doc_fic.get("amount_vat", 0))
                amount_gross = float(doc_fic.get("amount_gross", amount_net + amount_vat))

                # Payment info
                payments_list = doc_fic.get("payments_list", []) or []
                data_scadenza = ""
                if payments_list:
                    data_scadenza = payments_list[0].get("due_date", "")

                now = datetime.now(timezone.utc)
                fr_id = f"fr_{uuid.uuid4().hex[:12]}"

                # Match supplier by VAT
                fornitore_id = None
                piva = entity.get("vat_number", "")
                if piva:
                    supplier = await db.clients.find_one(
                        {"user_id": user["user_id"], "partita_iva": piva},
                        {"_id": 0, "client_id": 1}
                    )
                    if supplier:
                        fornitore_id = supplier["client_id"]

                fr_doc = {
                    "fr_id": fr_id,
                    "fic_id": fic_id,
                    "user_id": user["user_id"],
                    "fornitore_id": fornitore_id,
                    "fornitore_nome": entity.get("name", ""),
                    "fornitore_piva": piva,
                    "fornitore_cf": entity.get("tax_code", ""),
                    "tipo_documento": "TD01",
                    "numero_documento": str(doc_fic.get("number", "")),
                    "data_documento": str(doc_fic.get("date", "")),
                    "data_ricezione": now.strftime("%Y-%m-%d"),
                    "status": "pagata" if doc_fic.get("is_marked") else "da_registrare",
                    "linee": linee,
                    "imponibile": round(amount_net, 2),
                    "imposta": round(amount_vat, 2),
                    "totale_documento": round(amount_gross, 2),
                    "modalita_pagamento": "",
                    "condizioni_pagamento": "",
                    "data_scadenza_pagamento": data_scadenza,
                    "note": doc_fic.get("notes", ""),
                    "has_xml": False,
                    "sdi_id": None,
                    "pagamenti": [],
                    "totale_pagato": round(amount_gross, 2) if doc_fic.get("is_marked") else 0.0,
                    "residuo": 0.0 if doc_fic.get("is_marked") else round(amount_gross, 2),
                    "payment_status": "pagata" if doc_fic.get("is_marked") else "non_pagata",
                    "created_at": now,
                    "updated_at": now,
                }
                try:
                    await db.fatture_ricevute.insert_one(fr_doc)
                    imported += 1
                except Exception as e:
                    errors.append(f"Errore importazione doc {fic_id}: {str(e)}")

            # Check pagination
            total_pages = resp.get("last_page", resp.get("total_pages", 1))
            if page >= total_pages:
                break
            page += 1

    except Exception as e:
        logger.error(f"FIC sync error: {e}")
        if imported == 0:
            raise HTTPException(502, f"Errore comunicazione FattureInCloud: {str(e)}")

    return {
        "message": f"Sincronizzazione completata: {imported} importate, {skipped} già presenti",
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
    }


# ── Scadenziario Dashboard ──────────────────────────────────────

@router.get("/scadenziario/dashboard")
async def get_scadenziario_dashboard(
    user: dict = Depends(get_current_user)
):
    """Aggregated deadline dashboard: payments, documents, commesse milestones."""
    uid = user["user_id"]
    today = date.today().isoformat()
    fine_mese = date(date.today().year, date.today().month + 1 if date.today().month < 12 else 1, 1).isoformat() if date.today().month < 12 else f"{date.today().year + 1}-01-01"

    scadenze = []

    # 1. Payment deadlines from fatture ricevute
    fr_cursor = db.fatture_ricevute.find(
        {"user_id": uid, "payment_status": {"$ne": "pagata"}},
        {"_id": 0, "xml_raw": 0}
    ).sort("data_scadenza_pagamento", 1)
    async for fr in fr_cursor:
        scad = fr.get("data_scadenza_pagamento", "")
        scadenze.append({
            "tipo": "pagamento",
            "id": fr.get("fr_id"),
            "titolo": f"Fatt. {fr.get('numero_documento', '?')}",
            "sottotitolo": fr.get("fornitore_nome", ""),
            "data_scadenza": scad,
            "importo": fr.get("residuo", fr.get("totale_documento", 0)),
            "stato": "scaduto" if scad and scad < today else ("in_scadenza" if scad and scad <= fine_mese else "ok"),
            "link": f"/fatture-ricevute",
            "processata": bool(fr.get("imputazione")),
        })

    # 2. Welder certificate expiries
    async for w in db.welders.find({"is_active": True}, {"_id": 0}):
        for q in w.get("qualifications", []):
            exp = q.get("expiry_date", "")
            if exp:
                scadenze.append({
                    "tipo": "patentino",
                    "id": w.get("welder_id"),
                    "titolo": f"Patentino {q.get('standard', '')}",
                    "sottotitolo": w.get("name", ""),
                    "data_scadenza": exp,
                    "importo": None,
                    "stato": "scaduto" if exp < today else ("in_scadenza" if exp <= fine_mese else "ok"),
                    "link": "/quality-hub/welders",
                })

    # 3. Instrument calibration expiries
    async for inst in db.instruments.find({"status": {"$nin": ["fuori_uso"]}}, {"_id": 0}):
        exp = inst.get("next_calibration", "")
        if exp:
            scadenze.append({
                "tipo": "taratura",
                "id": inst.get("instrument_id"),
                "titolo": f"Taratura {inst.get('name', '')}",
                "sottotitolo": inst.get("serial_number", ""),
                "data_scadenza": exp,
                "importo": None,
                "stato": "scaduto" if exp < today else ("in_scadenza" if exp <= fine_mese else "ok"),
                "link": "/quality-hub/equipment",
            })

    # 4. Commesse delivery deadlines
    async for c in db.commesse.find(
        {"user_id": uid, "stato": {"$nin": ["bozza", "chiuso", "fatturato"]}},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1, "data_consegna": 1}
    ):
        dc = c.get("data_consegna", "")
        if dc:
            scadenze.append({
                "tipo": "consegna",
                "id": c.get("commessa_id"),
                "titolo": f"Consegna {c.get('numero', '')}",
                "sottotitolo": c.get("title", ""),
                "data_scadenza": dc,
                "importo": None,
                "stato": "scaduto" if dc < today else ("in_scadenza" if dc <= fine_mese else "ok"),
                "link": f"/commesse/{c.get('commessa_id')}",
            })

    # Sort by date
    scadenze.sort(key=lambda x: x.get("data_scadenza") or "9999-12-31")

    # KPIs
    scadute = [s for s in scadenze if s["stato"] == "scaduto"]
    in_scadenza = [s for s in scadenze if s["stato"] == "in_scadenza"]
    pagamenti_scaduti = sum(s.get("importo", 0) or 0 for s in scadute if s["tipo"] == "pagamento")
    pagamenti_mese = sum(s.get("importo", 0) or 0 for s in in_scadenza if s["tipo"] == "pagamento")

    # Fatture da processare (inbox)
    inbox_count = await db.fatture_ricevute.count_documents(
        {"user_id": uid, "imputazione": {"$exists": False}, "status": {"$ne": "pagata"}}
    )

    # Totale acquisti anno
    year = date.today().year
    pipeline = [
        {"$match": {"user_id": uid, "data_documento": {"$regex": f"^{year}"}}},
        {"$group": {"_id": None, "totale": {"$sum": "$totale_documento"}}}
    ]
    agg = await db.fatture_ricevute.aggregate(pipeline).to_list(1)
    totale_anno = agg[0]["totale"] if agg else 0

    return {
        "scadenze": scadenze,
        "kpi": {
            "pagamenti_scaduti": round(pagamenti_scaduti, 2),
            "pagamenti_mese_corrente": round(pagamenti_mese, 2),
            "totale_acquisti_anno": round(totale_anno, 2),
            "scadenze_totali": len(scadenze),
            "scadute": len(scadute),
            "in_scadenza": len(in_scadenza),
            "inbox_da_processare": inbox_count,
        }
    }
