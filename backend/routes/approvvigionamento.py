"""Approvvigionamento (Procurement) — RdP, OdA, Arrivi, PDF, Email."""
import uuid
import re
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO

from core.database import db
from core.security import get_current_user
from routes.commessa_ops_common import (
    COLL, get_commessa_or_404, ensure_ops_fields,
    ts, new_id, push_event, build_update_with_event, logger,
)

router = APIRouter()


# ── Models ──

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
    descrizione: str
    quantita: float = 1
    unita_misura: str = "kg"
    quantita_utilizzata: Optional[float] = None
    prezzo_unitario: Optional[float] = None
    ordine_id: Optional[str] = None
    commessa_id: Optional[str] = None
    richiede_cert_31: bool = False
    certificato_doc_id: Optional[str] = None
    numero_colata: Optional[str] = None
    qualita_materiale: Optional[str] = None
    fornitore_materiale: Optional[str] = None
    material_batch_id: Optional[str] = None

class ArrivoMateriale(BaseModel):
    ddt_fornitore: str
    data_ddt: Optional[str] = None
    fornitore_nome: Optional[str] = None
    fornitore_id: Optional[str] = None
    materiali: Optional[List[MaterialeRicevuto]] = []
    ordine_id: Optional[str] = None
    note: Optional[str] = ""


# ── Routes ──

@router.post("/{cid}/approvvigionamento/richieste")
async def create_richiesta_preventivo(cid: str, data: RichiestaPreventivo, user: dict = Depends(get_current_user)):
    await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    righe_dict = [r.model_dump() if hasattr(r, 'model_dump') else r.dict() for r in (data.righe or [])]
    rdp = {
        "rdp_id": new_id("rdp_"),
        "fornitore_nome": data.fornitore_nome,
        "fornitore_id": data.fornitore_id or "",
        "righe": righe_dict,
        "note": data.note or "",
        "materiali_richiesti": data.materiali_richiesti or "",
        "stato": "inviata",
        "data_richiesta": ts().isoformat(),
        "data_risposta": None,
        "importo_proposto": None,
    }
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
    await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    upd = {"approvvigionamento.richieste.$[elem].stato": stato, "approvvigionamento.richieste.$[elem].data_risposta": ts().isoformat()}
    if importo is not None:
        upd["approvvigionamento.richieste.$[elem].importo_proposto"] = importo
    await db[COLL].update_one({"commessa_id": cid}, {"$set": upd}, array_filters=[{"elem.rdp_id": rdp_id}])
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, "RDP_AGGIORNATA", user, f"RdP {rdp_id} → {stato}"))
    return {"message": f"RdP aggiornata: {stato}"}


@router.post("/{cid}/approvvigionamento/ordini")
async def create_ordine_fornitore(cid: str, data: OrdineFornitore, user: dict = Depends(get_current_user)):
    await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    righe_dict = [r.model_dump() if hasattr(r, 'model_dump') else (r.dict() if hasattr(r, 'dict') else r) for r in (data.righe or [])]
    importo_totale = data.importo_totale or 0
    if righe_dict and importo_totale == 0:
        importo_totale = sum((r.get("quantita", 1) * r.get("prezzo_unitario", 0)) for r in righe_dict)
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
    await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    upd = {"approvvigionamento.ordini.$[elem].stato": stato}
    if stato == "confermato":
        upd["approvvigionamento.ordini.$[elem].data_conferma"] = ts().isoformat()
    await db[COLL].update_one({"commessa_id": cid}, {"$set": upd}, array_filters=[{"elem.ordine_id": ordine_id}])
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, "ORDINE_AGGIORNATO", user, f"Ordine {ordine_id} → {stato}"))
    return {"message": f"Ordine aggiornato: {stato}"}


@router.post("/{cid}/approvvigionamento/arrivi")
async def register_arrivo_materiale(cid: str, data: ArrivoMateriale, user: dict = Depends(get_current_user)):
    doc = await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    materiali_dict = []
    for m in (data.materiali or []):
        mat = m.model_dump() if hasattr(m, 'model_dump') else (m.dict() if hasattr(m, 'dict') else m)
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
        "ordine_id": data.ordine_id or "",
        "note": data.note or "",
        "stato": "da_verificare",
        "data_arrivo": ts().isoformat(),
        "data_verifica": None,
    }
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
    if data.ordine_id:
        await db[COLL].update_one({"commessa_id": cid}, {"$set": {"approvvigionamento.ordini.$[elem].stato": "consegnato"}}, array_filters=[{"elem.ordine_id": data.ordine_id}])
    order_ids_to_update = set()
    for mat in materiali_dict:
        if mat.get("ordine_id") and mat["ordine_id"] != data.ordine_id:
            order_ids_to_update.add(mat["ordine_id"])
    for oid in order_ids_to_update:
        await db[COLL].update_one({"commessa_id": cid}, {"$set": {"approvvigionamento.ordini.$[elem].stato": "consegnato"}}, array_filters=[{"elem.ordine_id": oid}])
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
                codice_words = re.sub(r'[^a-zA-Z0-9\s]', '', desc).upper().split()[:3]
                auto_codice = "-".join(codice_words) if codice_words else f"ART-{uuid.uuid4().hex[:4].upper()}"
                existing_art = await db.articoli.find_one(
                    {"user_id": user["user_id"], "tenant_id": user["tenant_id"], "descrizione": {"$regex": f"^{re.escape(desc[:30])}", "$options": "i"}}, {"_id": 0}
                )
                now_stock = ts()
                if existing_art:
                    old_stock = float(existing_art.get("giacenza", 0))
                    new_stock = round(old_stock + qty_remainder, 4)
                    await db.articoli.update_one({"articolo_id": existing_art["articolo_id"]}, {"$set": {"giacenza": new_stock, "updated_at": now_stock}})
                    stock_updates.append(f"{qty_remainder} {um} di {desc[:40]} → magazzino (tot: {new_stock})")
                else:
                    art_doc = {
                        "articolo_id": f"art_{uuid.uuid4().hex[:12]}",
                        "user_id": user["user_id"], "tenant_id": user["tenant_id"],
                        "codice": auto_codice, "descrizione": desc, "categoria": "materiale",
                        "unita_misura": um, "prezzo_unitario": prezzo, "giacenza": qty_remainder,
                        "aliquota_iva": "22", "fornitore_nome": data.fornitore_nome or "",
                        "fornitore_id": data.fornitore_id or "",
                        "storico_prezzi": [{"prezzo": prezzo, "data": now_stock.isoformat(), "fonte": f"Resto arrivo DDT {data.ddt_fornitore}"}],
                        "note": f"Creato automaticamente da resto arrivo DDT {data.ddt_fornitore}",
                        "created_at": now_stock, "updated_at": now_stock,
                        "numero_colata": None, "heat_number": None, "acciaieria": None,
                        "qualita_acciaio": None, "normativa_riferimento": None, "source_cert_id": None,
                        "metodo_produttivo": None, "percentuale_riciclato": None,
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
    cid: str, arrivo_id: str, mat_idx: int,
    certificato_doc_id: str = Form(None), numero_colata: str = Form(None),
    qualita_materiale: str = Form(None), fornitore_materiale: str = Form(None),
    user: dict = Depends(get_current_user)
):
    doc = await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    approv = doc.get("approvvigionamento", {})
    arrivo = next((a for a in approv.get("arrivi", []) if a.get("arrivo_id") == arrivo_id), None)
    if not arrivo:
        raise HTTPException(404, "Arrivo non trovato")
    materiali = arrivo.get("materiali", [])
    if mat_idx < 0 or mat_idx >= len(materiali):
        raise HTTPException(400, "Indice materiale non valido")
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
        await db[COLL].update_one({"commessa_id": cid}, {"$set": update_fields}, array_filters=[{"arr.arrivo_id": arrivo_id}])
    normativa_tipo = doc.get("normativa_tipo") or (doc.get("moduli") or {}).get("normativa_tipo")
    if normativa_tipo == "EN_1090" and numero_colata:
        materiale = materiali[mat_idx]
        batch_data = {
            "user_id": user["user_id"], "tenant_id": user["tenant_id"], "commessa_id": cid,
            "fornitore": fornitore_materiale or arrivo.get("fornitore_nome", ""),
            "supplier_name": fornitore_materiale or arrivo.get("fornitore_nome", ""),
            "tipo_materiale": materiale.get("descrizione", ""),
            "material_type": materiale.get("descrizione", ""),
            "numero_colata": numero_colata, "heat_number": numero_colata,
            "dimensions": materiale.get("descrizione", ""),
            "qualita": qualita_materiale or "",
            "ddt_riferimento": arrivo.get("ddt_fornitore", ""),
            "certificato_31_base64": "", "certificato_doc_id": certificato_doc_id or "",
            "data_registrazione": ts().isoformat(),
            "note": f"Auto-registrato da arrivo {arrivo_id}",
        }
        batch_id = new_id("batch_")
        await db.material_batches.update_one(
            {"commessa_id": cid, "numero_colata": numero_colata, "tipo_materiale": materiale.get("descrizione", "")},
            {"$set": batch_data, "$setOnInsert": {"batch_id": batch_id}}, upsert=True,
        )
        cert_meta = {}
        if numero_colata: cert_meta["numero_colata"] = numero_colata
        if qualita_materiale: cert_meta["qualita_acciaio"] = qualita_materiale
        if fornitore_materiale: cert_meta["fornitore_nome"] = fornitore_materiale
        if certificato_doc_id: cert_meta["source_cert_id"] = certificato_doc_id
        if cert_meta:
            cert_meta["updated_at"] = ts()
            await db.articoli.update_one(
                {"user_id": user["user_id"], "tenant_id": user["tenant_id"], "descrizione": {"$regex": f"^{re.escape(materiale.get('descrizione', '')[:30])}", "$options": "i"}},
                {"$set": cert_meta},
            )
        await db[COLL].update_one(
            {"commessa_id": cid},
            {"$set": {f"approvvigionamento.arrivi.$[arr].materiali.{mat_idx}.material_batch_id": batch_data["batch_id"]}},
            array_filters=[{"arr.arrivo_id": arrivo_id}],
        )
        await db[COLL].update_one({"commessa_id": cid}, push_event(cid, "MATERIALE_TRACCIATO", user, f"Colata {numero_colata} registrata per EN 1090"))
    return {"message": "Certificato collegato al materiale"}


@router.put("/{cid}/approvvigionamento/arrivi/{arrivo_id}/verifica")
async def verifica_arrivo(cid: str, arrivo_id: str, user: dict = Depends(get_current_user)):
    await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    await db[COLL].update_one(
        {"commessa_id": cid},
        {"$set": {"approvvigionamento.arrivi.$[elem].stato": "verificato", "approvvigionamento.arrivi.$[elem].data_verifica": ts().isoformat()}},
        array_filters=[{"elem.arrivo_id": arrivo_id}],
    )
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, "MATERIALE_VERIFICATO", user, f"Arrivo {arrivo_id} verificato"))
    return {"message": "Arrivo verificato"}


# ── PDF & Email ──

@router.get("/{cid}/approvvigionamento/richieste/{rdp_id}/pdf")
async def get_rdp_pdf(cid: str, rdp_id: str, user: dict = Depends(get_current_user)):
    doc = await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    approv = doc.get("approvvigionamento", {})
    rdp = next((r for r in approv.get("richieste", []) if r.get("rdp_id") == rdp_id), None)
    if not rdp: raise HTTPException(404, "RdP non trovata")
    company = await db.company_settings.find_one({"user_id": user["user_id"], "tenant_id": user["tenant_id"]}, {"_id": 0}) or {}
    fornitore = None
    if rdp.get("fornitore_id"):
        fornitore = await db.clients.find_one({"client_id": rdp["fornitore_id"]}, {"_id": 0})
    from services.pdf_template_v2 import generate_rdp_pdf_v2
    pdf_bytes = generate_rdp_pdf_v2(rdp, doc, company, fornitore)
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf", headers={"Content-Disposition": f"inline; filename=RdP_{rdp_id}.pdf"})


@router.get("/{cid}/approvvigionamento/richieste/{rdp_id}/preview-email")
async def preview_rdp_email(cid: str, rdp_id: str, user: dict = Depends(get_current_user)):
    doc = await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    approv = doc.get("approvvigionamento", {})
    rdp = next((r for r in approv.get("richieste", []) if r.get("rdp_id") == rdp_id), None)
    if not rdp: raise HTTPException(404, "RdP non trovata")
    fornitore_id = rdp.get("fornitore_id")
    to_email = ""
    if fornitore_id:
        forn = await db.clients.find_one({"client_id": fornitore_id}, {"_id": 0})
        if forn:
            to_email = forn.get("pec") or forn.get("email") or ""
            if not to_email:
                for c in forn.get("contacts", []):
                    if c.get("email"): to_email = c["email"]; break
    company = await db.company_settings.find_one({"user_id": user["user_id"], "tenant_id": user["tenant_id"]}, {"_id": 0}) or {}
    from services.email_preview import build_rdp_email
    preview = build_rdp_email(fornitore_name=rdp.get("fornitore_nome", ""), rdp_id=rdp_id, commessa_numero=doc.get("numero", "N/D"), company_name=company.get("business_name", ""), num_righe=len(rdp.get("righe", [])))
    return {"to_email": to_email, "to_name": rdp.get("fornitore_nome", ""), "subject": preview["subject"], "html_body": preview["html_body"], "has_attachment": True, "attachment_name": f"RdP_{rdp_id}.pdf"}


@router.post("/{cid}/approvvigionamento/richieste/{rdp_id}/send-email")
async def send_rdp_email_endpoint(cid: str, rdp_id: str, payload: dict = None, user: dict = Depends(get_current_user)):
    doc = await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    approv = doc.get("approvvigionamento", {})
    rdp = next((r for r in approv.get("richieste", []) if r.get("rdp_id") == rdp_id), None)
    if not rdp: raise HTTPException(404, "RdP non trovata")
    fornitore_id = rdp.get("fornitore_id")
    fornitore_nome = rdp.get("fornitore_nome", "Fornitore")
    to_email = None
    if fornitore_id:
        fornitore = await db.clients.find_one({"client_id": fornitore_id}, {"_id": 0})
        if fornitore:
            to_email = fornitore.get("pec") or fornitore.get("email")
            if not to_email:
                for contact in fornitore.get("contacts", []):
                    if contact.get("email"): to_email = contact["email"]; break
    if not to_email:
        raise HTTPException(400, f"Nessun indirizzo email trovato per {fornitore_nome}. Aggiungi un'email nella scheda fornitore.")
    company = await db.company_settings.find_one({"user_id": user["user_id"], "tenant_id": user["tenant_id"]}, {"_id": 0}) or {}
    fornitore_doc = None
    if fornitore_id:
        fornitore_doc = await db.clients.find_one({"client_id": fornitore_id}, {"_id": 0})
    from services.pdf_template_v2 import generate_rdp_pdf_v2
    try:
        pdf_bytes = generate_rdp_pdf_v2(rdp, doc, company, fornitore_doc)
    except Exception as pdf_err:
        logger.error(f"PDF generation failed for RdP {rdp_id}: {pdf_err}")
        raise HTTPException(500, f"Generazione PDF fallita: {pdf_err}")
    filename = f"RdP_{rdp_id}.pdf"
    from services.email_service import send_rdp_email, send_email_with_attachment, check_email_service
    check_email_service()
    payload = payload or {}
    cc = payload.get("cc") or []
    commessa_numero = doc.get("numero", "N/D")
    if payload.get("custom_subject") or payload.get("custom_body"):
        success = await send_email_with_attachment(to_email=to_email, subject=payload.get("custom_subject") or f"Richiesta Preventivo {rdp_id} - Commessa {commessa_numero} - {company.get('business_name', '')}", body=payload.get("custom_body") or "", pdf_bytes=pdf_bytes, filename=filename, user_id=user["user_id"], cc=cc if cc else None)
    else:
        success = await send_rdp_email(to_email=to_email, fornitore_name=fornitore_nome, rdp_id=rdp_id, commessa_numero=commessa_numero, company_name=company.get("business_name", ""), num_righe=len(rdp.get("righe", [])), pdf_bytes=pdf_bytes, filename=filename, cc=cc if cc else None)
    if not success:
        raise HTTPException(500, "Invio email fallito. Verifica la chiave API Resend nelle Impostazioni Azienda.")
    await db[COLL].update_one({"commessa_id": cid}, {"$set": {"approvvigionamento.richieste.$[elem].email_sent": True, "approvvigionamento.richieste.$[elem].email_sent_to": to_email, "approvvigionamento.richieste.$[elem].email_sent_at": ts().isoformat()}}, array_filters=[{"elem.rdp_id": rdp_id}])
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, "RDP_EMAIL_INVIATA", user, f"RdP {rdp_id} inviata via email a {to_email}"))
    return {"message": f"Email inviata con successo a {to_email}", "to": to_email}


@router.get("/{cid}/approvvigionamento/ordini/{ordine_id}/pdf")
async def get_oda_pdf(cid: str, ordine_id: str, user: dict = Depends(get_current_user)):
    doc = await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    approv = doc.get("approvvigionamento", {})
    oda = next((o for o in approv.get("ordini", []) if o.get("ordine_id") == ordine_id), None)
    if not oda: raise HTTPException(404, "Ordine non trovato")
    company = await db.company_settings.find_one({"user_id": user["user_id"], "tenant_id": user["tenant_id"]}, {"_id": 0}) or {}
    fornitore = None
    if oda.get("fornitore_id"):
        fornitore = await db.clients.find_one({"client_id": oda["fornitore_id"]}, {"_id": 0})
    from services.pdf_template_v2 import generate_oda_pdf_v2
    pdf_bytes = generate_oda_pdf_v2(oda, doc, company, fornitore)
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf", headers={"Content-Disposition": f"inline; filename=OdA_{ordine_id}.pdf"})


@router.get("/{cid}/approvvigionamento/ordini/{ordine_id}/preview-email")
async def preview_oda_email(cid: str, ordine_id: str, user: dict = Depends(get_current_user)):
    doc = await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    approv = doc.get("approvvigionamento", {})
    oda = next((o for o in approv.get("ordini", []) if o.get("ordine_id") == ordine_id), None)
    if not oda: raise HTTPException(404, "Ordine non trovato")
    fornitore_id = oda.get("fornitore_id")
    to_email = ""
    if fornitore_id:
        forn = await db.clients.find_one({"client_id": fornitore_id}, {"_id": 0})
        if forn:
            to_email = forn.get("pec") or forn.get("email") or ""
            if not to_email:
                for c in forn.get("contacts", []):
                    if c.get("email"): to_email = c["email"]; break
    company = await db.company_settings.find_one({"user_id": user["user_id"], "tenant_id": user["tenant_id"]}, {"_id": 0}) or {}
    from services.email_preview import build_oda_email
    preview = build_oda_email(fornitore_name=oda.get("fornitore_nome", ""), ordine_id=ordine_id, commessa_numero=doc.get("numero", "N/D"), company_name=company.get("business_name", ""), importo_totale=oda.get("importo_totale", 0))
    return {"to_email": to_email, "to_name": oda.get("fornitore_nome", ""), "subject": preview["subject"], "html_body": preview["html_body"], "has_attachment": True, "attachment_name": f"OdA_{ordine_id}.pdf"}


@router.post("/{cid}/approvvigionamento/ordini/{ordine_id}/send-email")
async def send_oda_email_endpoint(cid: str, ordine_id: str, payload: dict = None, user: dict = Depends(get_current_user)):
    doc = await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)
    approv = doc.get("approvvigionamento", {})
    oda = next((o for o in approv.get("ordini", []) if o.get("ordine_id") == ordine_id), None)
    if not oda: raise HTTPException(404, "Ordine non trovato")
    fornitore_id = oda.get("fornitore_id")
    fornitore_nome = oda.get("fornitore_nome", "Fornitore")
    to_email = None
    if fornitore_id:
        fornitore = await db.clients.find_one({"client_id": fornitore_id}, {"_id": 0})
        if fornitore:
            to_email = fornitore.get("pec") or fornitore.get("email")
            if not to_email:
                for contact in fornitore.get("contacts", []):
                    if contact.get("email"): to_email = contact["email"]; break
    if not to_email:
        raise HTTPException(400, f"Nessun indirizzo email trovato per {fornitore_nome}. Aggiungi un'email nella scheda fornitore.")
    company = await db.company_settings.find_one({"user_id": user["user_id"], "tenant_id": user["tenant_id"]}, {"_id": 0}) or {}
    fornitore_doc = None
    if fornitore_id:
        fornitore_doc = await db.clients.find_one({"client_id": fornitore_id}, {"_id": 0})
    from services.pdf_template_v2 import generate_oda_pdf_v2
    try:
        pdf_bytes = generate_oda_pdf_v2(oda, doc, company, fornitore_doc)
    except Exception as pdf_err:
        logger.error(f"PDF generation failed for OdA {ordine_id}: {pdf_err}")
        raise HTTPException(500, f"Generazione PDF fallita: {pdf_err}")
    filename = f"OdA_{ordine_id}.pdf"
    from services.email_service import send_oda_email, send_email_with_attachment, check_email_service
    check_email_service()
    payload = payload or {}
    cc = payload.get("cc") or []
    commessa_numero = doc.get("numero", "N/D")
    if payload.get("custom_subject") or payload.get("custom_body"):
        success = await send_email_with_attachment(to_email=to_email, subject=payload.get("custom_subject") or f"Ordine n. {ordine_id} - Commessa {commessa_numero} - {company.get('business_name', '')}", body=payload.get("custom_body") or "", pdf_bytes=pdf_bytes, filename=filename, user_id=user["user_id"], cc=cc if cc else None)
    else:
        success = await send_oda_email(to_email=to_email, fornitore_name=fornitore_nome, ordine_id=ordine_id, commessa_numero=commessa_numero, company_name=company.get("business_name", ""), importo_totale=oda.get("importo_totale", 0), pdf_bytes=pdf_bytes, filename=filename, cc=cc if cc else None)
    if not success:
        raise HTTPException(500, "Invio email fallito. Verifica la chiave API Resend nelle Impostazioni Azienda.")
    await db[COLL].update_one({"commessa_id": cid}, {"$set": {"approvvigionamento.ordini.$[elem].email_sent": True, "approvvigionamento.ordini.$[elem].email_sent_to": to_email, "approvvigionamento.ordini.$[elem].email_sent_at": ts().isoformat()}}, array_filters=[{"elem.ordine_id": ordine_id}])
    await db[COLL].update_one({"commessa_id": cid}, push_event(cid, "ODA_EMAIL_INVIATA", user, f"Ordine {ordine_id} inviato via email a {to_email}"))
    return {"message": f"Email inviata con successo a {to_email}", "to": to_email}
