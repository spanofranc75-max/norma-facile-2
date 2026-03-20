"""Consegne, Ops Data, Scheda Rintracciabilità, Fascicolo Tecnico, Prelievo Magazzino."""
import uuid
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from io import BytesIO

from core.database import db
from core.security import get_current_user
from routes.commessa_ops_common import (
    COLL, DOC_COLL, get_commessa_or_404, ensure_ops_fields,
    ts, new_id, push_event, build_update_with_event,
)

router = APIRouter()
logger = logging.getLogger(__name__)


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
    prev_id = comm.get("preventivo_id") or (comm.get("moduli") or {}).get("preventivo_id") or comm.get("linked_preventivo_id")
    if prev_id:
        preventivo = await db.preventivi.find_one(
            {"preventivo_id": prev_id}, {"_id": 0}
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
                "unit_price": float(pl.get("unit_price") or pl.get("prezzo_unitario") or 0),
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
        {"$push": {"consegne": consegna, "moduli.ddt_ids": ddt_id}},
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
    
    # EN 1090: crea material_batch se articolo ha metadati certificato
    normativa_tipo = comm.get("normativa_tipo") or (comm.get("moduli") or {}).get("normativa_tipo")
    numero_colata = articolo.get("numero_colata") or articolo.get("heat_number")
    if normativa_tipo == "EN_1090" and numero_colata:
        batch_data = {
            "user_id": user["user_id"],
            "commessa_id": cid,
            "fornitore": articolo.get("fornitore_nome", ""),
            "supplier_name": articolo.get("fornitore_nome", ""),
            "tipo_materiale": articolo.get("descrizione", ""),
            "material_type": articolo.get("descrizione", ""),
            "dimensions": articolo.get("descrizione", ""),
            "numero_colata": numero_colata,
            "heat_number": articolo.get("heat_number") or numero_colata,
            "qualita": articolo.get("qualita_acciaio", ""),
            "acciaieria": articolo.get("acciaieria", ""),
            "normativa_riferimento": articolo.get("normativa_riferimento", ""),
            "peso_kg": data.quantita,
            "source": "magazzino",
            "articolo_id": data.articolo_id,
            "source_cert_id": articolo.get("source_cert_id", ""),
            "data_registrazione": now.isoformat(),
            "note": f"Prelievo da magazzino — {data.note or ''}".strip(" —"),
        }
        await db.material_batches.update_one(
            {"commessa_id": cid, "numero_colata": numero_colata, "tipo_materiale": articolo.get("descrizione", "")},
            {"$set": batch_data, "$setOnInsert": {"batch_id": new_id("batch_")}},
            upsert=True,
        )
        # lotto_cam
        lotto_cam = {
            "user_id": user["user_id"],
            "commessa_id": cid,
            "numero_colata": numero_colata,
            "descrizione": articolo.get("descrizione", ""),
            "peso_kg": data.quantita,
            "fornitore": articolo.get("fornitore_nome", ""),
            "percentuale_riciclato": articolo.get("percentuale_riciclato"),
            "metodo_produttivo": articolo.get("metodo_produttivo"),
            "source": "magazzino",
            "data_registrazione": now.isoformat(),
        }
        await db.lotti_cam.update_one(
            {"commessa_id": cid, "numero_colata": numero_colata, "descrizione": articolo.get("descrizione", "")},
            {"$set": lotto_cam, "$setOnInsert": {"lotto_id": new_id("lotto_")}},
            upsert=True,
        )

    return {
        "message": f"Prelevati {data.quantita} {articolo.get('unita_misura', 'pz')} di {articolo.get('codice', '')} — {importo_totale:.2f}€ imputati alla commessa {comm.get('numero', cid)}",
        "cost_entry": cost_entry,
        "giacenza_residua": new_giacenza,
    }
