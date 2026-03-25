"""Repository Documenti per Commessa — Upload, AI parsing certificati 3.1, DDT, profili."""
import re
import uuid
import logging
import base64
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from io import BytesIO

from core.database import db
from core.security import get_current_user, tenant_match
from routes.commessa_ops_common import (
    COLL, DOC_COLL, get_commessa_or_404, ensure_ops_fields,
    ts, new_id, push_event, build_update_with_event,
)

router = APIRouter()
logger = logging.getLogger(__name__)


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
    await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "File troppo grande (max 15MB)")

    doc_id = new_id("doc_")
    doc = {
        "doc_id": doc_id,
        "commessa_id": cid,
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
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
    await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    docs = await db[DOC_COLL].find(
        {"commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "file_base64": 0}  # Exclude heavy content
    ).sort("uploaded_at", -1).to_list(200)
    return {"documents": docs, "total": len(docs)}


@router.get("/{cid}/documenti/{doc_id}/download")
async def download_document(cid: str, doc_id: str, user: dict = Depends(get_current_user)):
    """Download a document."""
    doc = await db[DOC_COLL].find_one(
        {"doc_id": doc_id, "commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
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

    doc = await db[DOC_COLL].find_one({"doc_id": doc_id, "commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    await db[DOC_COLL].delete_one({"doc_id": doc_id, "commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user)})

    # ── STRATEGY 1: Delete by source_doc_id ──
    cam_1 = await db.lotti_cam.delete_many({"source_doc_id": doc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)})
    batch_1 = await db.material_batches.delete_many({"source_doc_id": doc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)})
    copies_del = await db[DOC_COLL].delete_many({"source_doc_id": doc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)})
    archive_del = await db.archivio_certificati.delete_many({"source_doc_id": doc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)})

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
            "commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user),
            "numero_colata": {"$in": list(colate)},
        })
        r2 = await db.material_batches.delete_many({
            "commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user),
            "heat_number": {"$in": list(colate)},
        })
        cam_2 = r1.deleted_count
        batch_2 = r2.deleted_count

    # ── STRATEGY 3: If NO certificates remain for this commessa, nuke all orphans ──
    remaining_certs = await db[DOC_COLL].count_documents({
        "commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "tipo": {"$in": ["certificato_31", "certificato_32", "certificato_ispezione"]},
    })
    cam_3 = 0
    batch_3 = 0
    if remaining_certs == 0:
        r1 = await db.lotti_cam.delete_many({"commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user)})
        r2 = await db.material_batches.delete_many({"commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user)})
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

    doc = await db[DOC_COLL].find_one({"doc_id": doc_id, "commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user)})
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
  "acciaieria": "nome commerciale dell'acciaieria produttrice — è il testo più grande e prominente nell'intestazione del documento, spesso con logo (es. 'AFV Beltrame', 'NLMK', 'Riva Acciai', 'Arvedi', 'Marcegaglia', 'Feralpi', 'Duferco'). Se non identificabile, null",
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
        colate_estratte = list({
            p.get("colata", "").strip()
            for p in metadata.get("profili", [])
            if p.get("colata", "").strip()
        })
        await db[DOC_COLL].update_one(
            {"doc_id": doc_id},
            {"$set": {
                "metadata_estratti": metadata,
                "tipo": "certificato_31",
                "heat_numbers": colate_estratte
            }},
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
            "source_doc_id": doc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)
        })
        old_cam = await db.lotti_cam.delete_many({
            "source_doc_id": doc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)
        })
        old_archive = await db.archivio_certificati.delete_many({
            "source_doc_id": doc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)
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

        # ── VINCOLO DDT: verifica che ogni profilo abbia un arrivo registrato ──
        comm = await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
        arrivi = comm.get("approvvigionamento", {}).get("arrivi", []) or []
        # Pre-build arrivo lookup: profile_base → (arrivo_id, data_arrivo)
        arrivo_lookup = {}  # "IPE100" → {"arrivo_id": ..., "data": ...}
        for arrivo in arrivi:
            a_id = arrivo.get("arrivo_id", "")
            a_data_raw = arrivo.get("data_ddt") or arrivo.get("data_arrivo") or ""
            # Format date as dd/mm/yyyy
            a_data = ""
            if a_data_raw:
                try:
                    from datetime import datetime as _dt
                    if "T" in str(a_data_raw):
                        dt_obj = _dt.fromisoformat(str(a_data_raw).replace("Z", "+00:00"))
                    else:
                        dt_obj = _dt.strptime(str(a_data_raw)[:10], "%Y-%m-%d")
                    a_data = dt_obj.strftime("%d/%m/%Y")
                except Exception:
                    a_data = str(a_data_raw)[:10]
            for mat in arrivo.get("materiali", []):
                mat_desc = mat.get("descrizione", "")
                mat_base = _extract_profile_base(mat_desc)
                if mat_base and mat_base not in arrivo_lookup:
                    arrivo_lookup[mat_base] = {
                        "arrivo_id": a_id,
                        "data": a_data,
                        "fornitore": arrivo.get("fornitore_nome", "") or arrivo.get("ddt_fornitore", ""),
                        "numero_ddt": arrivo.get("numero_ddt", "") or arrivo.get("ddt_numero", "") or arrivo.get("ddt_fornitore", ""),
                        "quantita_kg": float(mat.get("quantita", 0) or 0) if (mat.get("unita_misura", "kg") or "kg").lower() == "kg" else None,
                    }

        profili_collegati = 0
        profili_bolla_mancante = 0
        for r in risultati_match:
            dim = r.get("dimensioni", "")
            cert_base = _extract_profile_base(dim)
            matched_arrivo = arrivo_lookup.get(cert_base) if cert_base else None
            if matched_arrivo:
                r["stato_ddt"] = "ok"
                r["ddt_arrivo_id"] = matched_arrivo["arrivo_id"]
                r["ddt_data"] = matched_arrivo["data"]
                r["fornitore_ddt"] = matched_arrivo.get("fornitore", "")
                r["ddt_numero"] = matched_arrivo.get("numero_ddt", "")
                r["peso_ddt_kg"] = matched_arrivo.get("quantita_kg")
                profili_collegati += 1
            else:
                r["stato_ddt"] = "bolla_mancante"
                r["ddt_arrivo_id"] = None
                r["ddt_data"] = None
                profili_bolla_mancante += 1

        logger.info(f"[DDT-CHECK] doc {doc_id}: {profili_collegati} con DDT, {profili_bolla_mancante} senza bolla")

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
        msg_parts = [f"{len(profili)} profili trovati", f"{matched_count} corrispondenti all'OdA"]
        if profili_bolla_mancante:
            msg_parts.append(f"{profili_bolla_mancante} in attesa di bolla")
        await db[COLL].update_one({"commessa_id": cid}, push_event(
            cid, "CERTIFICATO_ANALIZZATO", user,
            " — ".join(msg_parts),
            {"doc_id": doc_id, "risultati_match": risultati_match, "metadata": metadata}
        ))

        return {
            "message": f"Certificato analizzato: {profili_collegati} profili collegati, {profili_bolla_mancante} in attesa di bolla.",
            "metadata": metadata,
            "profili_trovati": len(profili),
            "risultati_match": risultati_match,
            "profili_collegati": profili_collegati,
            "profili_bolla_mancante": profili_bolla_mancante,
            "pending_confirm": True,
        }

    except HTTPException:
        raise
    except ImportError as ie:
        logger.error(f"Certificate parsing import error: {ie}")
        raise HTTPException(500, f"Libreria mancante per analisi certificato: {str(ie)}")
    except Exception as e:
        logger.error(f"Certificate parsing error: {type(e).__name__}: {e}", exc_info=True)
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
    comm = await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])

    # Get stored match results from the document
    doc = await db[DOC_COLL].find_one(
        {"doc_id": doc_id, "commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    risultati_match = doc.get("risultati_match", [])
    if not risultati_match:
        raise HTTPException(400, "Nessun risultato di matching da confermare. Rianalizza il certificato.")

    # Clean up any existing batches from previous imports for this document
    await db.material_batches.delete_many({"source_doc_id": doc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)})
    await db.lotti_cam.delete_many({"source_doc_id": doc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)})
    await db.archivio_certificati.delete_many({"source_doc_id": doc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)})

    # Process only selected profiles
    metadata = doc.get("metadata_estratti") or doc.get("metadata") or {}
    n_cert = metadata.get("numero_certificato", "")
    fornitore = metadata.get("fornitore", "")
    acciaieria = metadata.get("acciaieria", "")
    ente_cert = metadata.get("ente_certificatore", "")

    imported_count = 0
    archived_count = 0

    for i, r in enumerate(risultati_match):
        colata = (r.get("numero_colata") or "").strip()
        dim = (r.get("dimensioni") or "").strip()
        qualita = (r.get("qualita_acciaio") or "").strip()
        peso = r.get("peso_kg", 0)
        target_cid = (r.get("commessa_id") or "").strip()

        # Skip profiles with missing key fields to avoid upsert crash
        if i in data.selected_indices and (not colata or not dim):
            logger.warning(f"[CONFIRM] Skipping profile index {i}: missing colata={colata!r} or dim={dim!r}")
            archived_count += 1
            continue

        if i in data.selected_indices and target_cid and r.get("stato_ddt") != "bolla_mancante":
            # USER SELECTED + DDT OK: create material_batch + CAM lotto
            batch_id = f"bat_{uuid.uuid4().hex[:10]}"
            batch_data = {
                "user_id": user["user_id"], "tenant_id": tenant_match(user),
                "heat_number": colata, "numero_colata": colata,
                "material_type": qualita, "tipo_materiale": qualita,
                "supplier_name": r.get("fornitore_ddt", "") or fornitore, "fornitore": r.get("fornitore_ddt", "") or fornitore,
                "acciaieria": acciaieria, "dimensions": dim,
                "normativa": metadata.get("normativa_riferimento", ""),
                "source_doc_id": doc_id, "commessa_id": target_cid,
                "numero_certificato": n_cert,
                "ddt_numero": r.get("ddt_numero", ""),
                "peso_kg": r.get("peso_ddt_kg") if r.get("peso_ddt_kg") else float(peso or 0),
                "notes": f"Confermato da utente - cert {n_cert}",
            }
            await db.material_batches.update_one(
                {"commessa_id": target_cid, "heat_number": colata, "dimensions": dim},
                {"$set": batch_data, "$setOnInsert": {"batch_id": batch_id, "created_at": ts()}},
                upsert=True,
            )

            # CAM lotto
            metodo = r.get("metodo_produttivo", metadata.get("metodo_produttivo", "forno_elettrico_non_legato"))
            perc = r.get("percentuale_riciclato")
            if perc is None:
                perc = {"forno_elettrico_non_legato": 80, "forno_elettrico_legato": 65, "ciclo_integrale": 10}.get(metodo, 75)
            perc = float(perc)
            soglie = {"forno_elettrico_non_legato": 75, "forno_elettrico_legato": 60, "ciclo_integrale": 12}
            soglia = soglie.get(metodo, 75)

            cam_id = f"cam_{uuid.uuid4().hex[:10]}"
            cam_data = {
                "user_id": user["user_id"], "tenant_id": tenant_match(user),
                "commessa_id": target_cid,
                "descrizione": dim or qualita or "Materiale da certificato",
                "fornitore": fornitore, "numero_colata": colata,
                "peso_kg": r.get("peso_ddt_kg") if r.get("peso_ddt_kg") else float(peso or 0), "qualita_acciaio": qualita,
                "percentuale_riciclato": perc, "metodo_produttivo": metodo,
                "tipo_certificazione": "dichiarazione_produttore",
                "numero_certificazione": n_cert,
                "ente_certificatore": ente_cert,
                "uso_strutturale": True, "soglia_minima_cam": soglia,
                "conforme_cam": perc >= soglia, "source_doc_id": doc_id,
                "note": f"Confermato da utente - {r.get('match_source', '')}",
            }
            await db.lotti_cam.update_one(
                {"commessa_id": target_cid, "numero_colata": colata, "descrizione": dim},
                {"$set": cam_data, "$setOnInsert": {"lotto_id": cam_id, "created_at": ts()}},
                upsert=True,
            )
            imported_count += 1
            logger.info(f"[CONFIRM] Imported profile '{dim}' colata={colata} to commessa {target_cid}")
        elif i in data.selected_indices and r.get("stato_ddt") == "bolla_mancante":
            # USER SELECTED + BOLLA MANCANTE: create material_batch (tracciabilità) + archive
            batch_id = f"bat_{uuid.uuid4().hex[:10]}"
            batch_data_bm = {
                "user_id": user["user_id"], "tenant_id": tenant_match(user),
                "heat_number": colata, "numero_colata": colata,
                "material_type": qualita, "tipo_materiale": qualita,
                "supplier_name": fornitore, "fornitore": fornitore,
                "acciaieria": acciaieria, "dimensions": dim,
                "normativa": metadata.get("normativa_riferimento", ""),
                "source_doc_id": doc_id, "commessa_id": target_cid or cid,
                "numero_certificato": n_cert,
                "peso_kg": float(peso or 0),
                "ddt_presente": False,
                "stato_tracciabilita": "archivio",
                "notes": f"Importato senza DDT - cert {n_cert}",
            }
            await db.material_batches.update_one(
                {"commessa_id": target_cid or cid, "heat_number": colata, "dimensions": dim},
                {"$set": batch_data_bm, "$setOnInsert": {"batch_id": batch_id, "created_at": ts()}},
                upsert=True,
            )
            await db.archivio_certificati.update_one(
                {"heat_number": colata, "source_doc_id": doc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
                {"$set": {
                    "user_id": user["user_id"], "tenant_id": tenant_match(user),
                    "heat_number": colata, "material_type": qualita,
                    "supplier_name": fornitore, "dimensions": dim,
                    "source_doc_id": doc_id, "numero_certificato": n_cert,
                    "peso_kg": float(peso or 0),
                    "note": "Nessun arrivo DDT registrato per questo profilo",
                    "motivo_archivio": "Nessun arrivo DDT registrato per questo profilo",
                    "stato_tracciabilita": "bolla_mancante",
                    "created_at": ts(),
                }},
                upsert=True,
            )
            imported_count += 1
            archived_count += 1
            logger.info(f"[CONFIRM] Imported bolla_mancante profile '{dim}' colata={colata} to commessa {target_cid or cid}")

            # CAM lotto per bolla_mancante
            metodo = r.get("metodo_produttivo", metadata.get("metodo_produttivo", "forno_elettrico_non_legato"))
            perc = r.get("percentuale_riciclato")
            if perc is None:
                perc = {"forno_elettrico_non_legato": 80, "forno_elettrico_legato": 65, "ciclo_integrale": 10}.get(metodo, 75)
            perc = float(perc)
            soglie = {"forno_elettrico_non_legato": 75, "forno_elettrico_legato": 60, "ciclo_integrale": 12}
            soglia = soglie.get(metodo, 75)
            cert_amb = metadata.get("certificazione_ambientale", "")
            ente_cert_bm = metadata.get("ente_certificatore_ambientale", "")
            cert_type = "dichiarazione_produttore"
            if cert_amb and "epd" in cert_amb.lower():
                cert_type = "epd"
            elif cert_amb and "remade" in cert_amb.lower():
                cert_type = "remade_in_italy"
            cam_id_bm = f"cam_{uuid.uuid4().hex[:10]}"
            cam_data_bm = {
                "user_id": user["user_id"], "tenant_id": tenant_match(user),
                "commessa_id": target_cid or cid,
                "descrizione": dim or qualita or "Materiale da certificato",
                "fornitore": fornitore, "numero_colata": colata,
                "peso_kg": float(peso or 0), "qualita_acciaio": qualita,
                "percentuale_riciclato": perc, "metodo_produttivo": metodo,
                "tipo_certificazione": cert_type,
                "numero_certificazione": n_cert,
                "ente_certificatore": ente_cert_bm,
                "uso_strutturale": True, "soglia_minima_cam": soglia,
                "conforme_cam": perc >= soglia, "source_doc_id": doc_id,
                "note": f"Importato senza DDT - cert {n_cert}",
            }
            await db.lotti_cam.update_one(
                {"commessa_id": target_cid or cid, "numero_colata": colata, "descrizione": dim},
                {"$set": cam_data_bm, "$setOnInsert": {"lotto_id": cam_id_bm, "created_at": ts()}},
                upsert=True,
            )
        else:
            # NOT SELECTED or NO MATCH or BOLLA MANCANTE: archive
            is_bolla_mancante = r.get("stato_ddt") == "bolla_mancante"
            note_archivio = (
                "Nessun arrivo DDT registrato per questo profilo" if is_bolla_mancante
                else ("Non selezionato dall'utente" if target_cid else "Nessun match OdA")
            )
            await db.archivio_certificati.update_one(
                {"heat_number": colata, "source_doc_id": doc_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
                {"$set": {
                    "user_id": user["user_id"], "tenant_id": tenant_match(user),
                    "heat_number": colata, "material_type": qualita,
                    "supplier_name": fornitore, "dimensions": dim,
                    "source_doc_id": doc_id, "numero_certificato": n_cert,
                    "peso_kg": float(peso or 0),
                    "note": note_archivio,
                    "motivo_archivio": note_archivio if is_bolla_mancante else None,
                    "stato_tracciabilita": "bolla_mancante" if is_bolla_mancante else None,
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
    # Long compound synonyms first (order matters: longer patterns before shorter)
    t = re.sub(r'\bBARRA\s+FERRO\s+TOND[AO]?\b', 'TONDO', t)
    t = re.sub(r'\bBARRA\s+TOND[AO]?\b', 'TONDO', t)
    t = re.sub(r'\bBARRA\s+FERRO\s+ANGOLARE\b', 'ANGOLARE', t)
    t = re.sub(r'\bTUBO\s+FERRO\s+QUADRO\b', 'TUBOQ', t)
    t = re.sub(r'\bTUBO\s+FERRO\s+RETT\.?\w*\b', 'TUBOR', t)
    t = re.sub(r'\bTUBO\s+QUADRO\b', 'TUBOQ', t)
    t = re.sub(r'\bTUBO\s+RETT\.?\w*\b', 'TUBOR', t)
    t = re.sub(r'\bTRAVE\s+HEB\b', 'HEB', t)
    t = re.sub(r'\bPROFILO\s+HEB\b', 'HEB', t)
    t = re.sub(r'\bTRAVE\s+HEA\b', 'HEA', t)
    t = re.sub(r'\bPROFILO\s+HEA\b', 'HEA', t)
    t = re.sub(r'\bTRAVE\s+IPE\b', 'IPE', t)
    t = re.sub(r'\bPROFILO\s+IPE\b', 'IPE', t)
    t = re.sub(r'\bPROFILO\s+UPN\b', 'UPN', t)
    t = re.sub(r'\bU\s+UPN\b', 'UPN', t)
    t = re.sub(r'\bPROFILO\s+T\b', 'T', t)
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
    full_dim_families = r'(PIATTO|TUBOQ|TUBOR|TUBO|ANGOLARE|L)'
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
        {"user_id": user["user_id"], "tenant_id": tenant_match(user)},
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
                {"heat_number": colata, "commessa_id": target_cid, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
            )
            if not existing_batch:
                batch_id = f"bat_{uuid.uuid4().hex[:10]}"
                await db.material_batches.insert_one({
                    "batch_id": batch_id, "user_id": user["user_id"], "tenant_id": tenant_match(user),
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
                {"numero_colata": colata, "commessa_id": target_cid, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
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
                    "lotto_id": cam_id, "user_id": user["user_id"], "tenant_id": tenant_match(user),
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
                "user_id": user["user_id"], "tenant_id": tenant_match(user),
            })
            if not existing_copy:
                copy_doc = {
                    "doc_id": f"doc_{uuid.uuid4().hex[:10]}",
                    "user_id": user["user_id"], "tenant_id": tenant_match(user),
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
                {"numero_colata": colata, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
                {"$set": {
                    "numero_colata": colata, "user_id": user["user_id"], "tenant_id": tenant_match(user),
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
#  AI OCR: Parse DDT Fornitore
# ══════════════════════════════════════════════════════════════════

@router.post("/{cid}/documenti/{doc_id}/parse-ddt")
async def parse_ddt_fornitore(cid: str, doc_id: str, user: dict = Depends(get_current_user)):
    """Use Claude Sonnet 4 Vision to extract structured data from a supplier DDT.
    Returns extracted metadata + dry-run OdA matching per materiale.
    """
    import os
    import base64 as b64mod
    from io import BytesIO

    LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
    if not LLM_KEY:
        raise HTTPException(500, "Chiave AI non configurata")

    doc = await db[DOC_COLL].find_one({"doc_id": doc_id, "commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user)})
    if not doc:
        raise HTTPException(404, "Documento non trovato")
    if not doc.get("file_base64"):
        raise HTTPException(400, "Documento senza contenuto")

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

        file_b64 = doc["file_base64"]
        content_type = doc.get("content_type", "")

        # PDF → PNG conversion (same logic as parse-certificato)
        if content_type == "application/pdf" or doc.get("nome_file", "").lower().endswith(".pdf"):
            from pdf2image import convert_from_bytes
            pdf_bytes = b64mod.b64decode(file_b64)
            images = convert_from_bytes(pdf_bytes, first_page=1, last_page=3, dpi=300)
            if not images:
                raise HTTPException(400, "Impossibile convertire il PDF in immagine")
            file_contents = []
            for i, img in enumerate(images):
                buf = BytesIO()
                img.save(buf, format='PNG', optimize=True)
                buf.seek(0)
                page_b64 = b64mod.b64encode(buf.read()).decode('utf-8')
                file_contents.append(ImageContent(image_base64=page_b64))
                logger.info(f"DDT PDF page {i+1} → PNG for AI: {doc_id}")
        else:
            file_contents = [ImageContent(image_base64=file_b64)]

        prompt = """Analizza questo DDT (Documento di Trasporto) di un fornitore siderurgico italiano. Estrai TUTTI i campi in JSON strutturato.

IMPORTANTE: nel DDT possono esserci righe "ORDI" o "RIF. VS ORDINE" che separano materiali appartenenti a ordini diversi. Ogni riga ORDI introduce una nuova sezione: tutti i materiali successivi appartengono a quell'ordine fino al prossimo ORDI.

Restituisci JSON con questa struttura ESATTA (senza markdown, senza ```):
{
  "numero_ddt": "765",
  "data_ddt": "2026-02-03",
  "fornitore_nome": "Siderimport 3 Srl",
  "fornitore_partita_iva": "00768560492",
  "totale_peso_kg": 1584.0,
  "riferimenti_ordini": ["N.5 del 02/02/2026", "N.6 del 02/02/2026"],
  "materiali": [
    {
      "codice_articolo": "TRIPE100MT12",
      "descrizione": "TRAVI IPE 100 MT 6",
      "profilo_normalizzato": "IPE 100",
      "quantita": 0.240,
      "unita_misura": "T",
      "riferimento_ordine": "N.5 del 02/02/2026",
      "richiede_certificato": true
    }
  ],
  "num_certificati_allegati": 2
}

REGOLE per profilo_normalizzato:
- "TRAVI IPE 100" → "IPE 100"
- "TRAVI UNP 100" → "UNP 100"
- "TUBOLARE 100X100X3" → "TUB 100X100X3"
- "LAMIERE DEC 1.5X1500X3000" → "LAMIERA 1.5X1500X3000"
- "HEB 120" → "HEB 120"
richiede_certificato: true se il materiale è acciaio strutturale (IPE/HEB/HEA/UNP/piatto/lamiera), false per bulloni/vernici/accessori.

Se un campo non è leggibile, usa null. Rispondi SOLO con il JSON."""

        chat = LlmChat(
            api_key=LLM_KEY,
            session_id=f"ddt-{doc_id}",
            system_message="Sei un tecnico esperto di logistica siderurgica italiana. Estrai con precisione tutti i dati da DDT (Documenti di Trasporto) fornitori. Leggi ogni riga della tabella materiali senza saltarne nessuna."
        ).with_model("anthropic", "claude-sonnet-4-20250514")

        response = await chat.send_message(UserMessage(
            text=prompt,
            file_contents=file_contents,
        ))

        import json as json_mod
        response_text = response if isinstance(response, str) else getattr(response, 'text', str(response))
        response_text = response_text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1] if "\n" in response_text else response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        try:
            metadata = json_mod.loads(response_text)
        except json_mod.JSONDecodeError:
            metadata = {"raw_response": response_text, "parse_error": True}

        # Ensure materiali array
        materiali = metadata.get("materiali", [])
        metadata["materiali"] = materiali

        # Save extracted metadata
        await db[DOC_COLL].update_one(
            {"doc_id": doc_id},
            {"$set": {"metadata_estratti": metadata, "ddt_parsed": True}},
        )

        # ── DRY-RUN: match materiali DDT → OdA della commessa corrente ──
        comm = await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
        ordini = comm.get("approvvigionamento", {}).get("ordini", [])

        # Build OdA lookup: profile_base → ordine_id
        oda_base_lookup = {}  # "IPE100" → { ordine_id, descrizione, fornitore }
        for oda in ordini:
            oda_id = oda.get("ordine_id", "")
            for riga in oda.get("righe", []):
                base = _extract_profile_base(riga.get("descrizione", ""))
                if base and base not in oda_base_lookup:
                    oda_base_lookup[base] = {
                        "ordine_id": oda_id,
                        "descrizione_oda": riga.get("descrizione", ""),
                        "fornitore_oda": oda.get("fornitore_nome", ""),
                        "stato_oda": oda.get("stato", ""),
                    }

        match_results = []
        for mat in materiali:
            profilo_norm = mat.get("profilo_normalizzato", "") or mat.get("descrizione", "")
            cert_base = _extract_profile_base(profilo_norm)

            matched_oda = None
            match_source = "nessuno"

            if cert_base and cert_base in oda_base_lookup:
                matched_oda = oda_base_lookup[cert_base]
                match_source = f"profilo base {cert_base}"

            match_results.append({
                "descrizione": mat.get("descrizione", ""),
                "profilo_normalizzato": profilo_norm,
                "profile_base": cert_base,
                "quantita": mat.get("quantita"),
                "unita_misura": mat.get("unita_misura", ""),
                "riferimento_ordine": mat.get("riferimento_ordine", ""),
                "richiede_certificato": mat.get("richiede_certificato", False),
                "codice_articolo": mat.get("codice_articolo", ""),
                "match_oda": matched_oda,
                "match_source": match_source,
            })

        # Store match results for confirm step
        await db[DOC_COLL].update_one(
            {"doc_id": doc_id},
            {"$set": {"ddt_match_results": match_results, "ddt_pending_confirm": True}},
        )

        matched_count = sum(1 for r in match_results if r["match_oda"])
        await db[COLL].update_one({"commessa_id": cid}, push_event(
            cid, "DDT_ANALIZZATO", user,
            f"DDT {metadata.get('numero_ddt', '?')}: {len(materiali)} materiali, {matched_count} con OdA",
            {"doc_id": doc_id, "numero_ddt": metadata.get("numero_ddt")}
        ))

        return {
            "message": f"DDT analizzato: {len(materiali)} materiali trovati, {matched_count} corrispondono a OdA.",
            "metadata_estratti": metadata,
            "match_results": match_results,
            "doc_id": doc_id,
            "pending_confirm": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DDT parsing error: {e}")
        raise HTTPException(500, f"Errore analisi DDT: {str(e)}")


class ConfirmDDTRequest(BaseModel):
    """Request body for confirming DDT materials to create an arrival."""
    materiali_confermati: List[int] = []  # Indices of materials to import
    crea_arrivo: bool = True


@router.post("/{cid}/documenti/{doc_id}/confirm-ddt")
async def confirm_ddt(cid: str, doc_id: str, data: ConfirmDDTRequest, user: dict = Depends(get_current_user)):
    """
    Step 2 of DDT analysis: User confirms which materials to register.
    Creates an arrival record in the commessa with OdA linking.
    """
    comm = await get_commessa_or_404(cid, user["user_id"], user["tenant_id"])
    await ensure_ops_fields(cid)

    doc = await db[DOC_COLL].find_one(
        {"doc_id": doc_id, "commessa_id": cid, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    metadata = doc.get("metadata_estratti", {})
    match_results = doc.get("ddt_match_results", [])
    if not metadata or not match_results:
        raise HTTPException(400, "DDT non ancora analizzato. Usa prima 'Analizza DDT'.")

    # Build materiali for the arrivo
    materiali_arrivo = []
    oda_ids_to_update = set()
    selected_indices = set(data.materiali_confermati) if data.materiali_confermati else set(range(len(match_results)))

    for i, mr in enumerate(match_results):
        if i not in selected_indices:
            continue

        mat_dict = {
            "descrizione": mr.get("descrizione", ""),
            "quantita": float(mr.get("quantita", 0) or 0),
            "unita_misura": mr.get("unita_misura", "kg"),
            "richiede_cert_31": mr.get("richiede_certificato", False),
            "commessa_id": cid,
            "ordine_id": "",
            "codice_articolo": mr.get("codice_articolo", ""),
        }

        # Link to OdA if matched
        if mr.get("match_oda"):
            oda_id = mr["match_oda"]["ordine_id"]
            mat_dict["ordine_id"] = oda_id
            oda_ids_to_update.add(oda_id)

        materiali_arrivo.append(mat_dict)

    if not materiali_arrivo:
        raise HTTPException(400, "Nessun materiale selezionato.")

    # Create the arrivo record
    arrivo_id = new_id("arr_")
    arrivo = {
        "arrivo_id": arrivo_id,
        "ddt_fornitore": metadata.get("numero_ddt", ""),
        "data_ddt": metadata.get("data_ddt", ts().isoformat()[:10]),
        "fornitore_nome": metadata.get("fornitore_nome", ""),
        "fornitore_id": "",
        "ddt_document_id": doc_id,
        "materiali": materiali_arrivo,
        "ordine_id": "",
        "note": f"Creato da analisi AI DDT - Doc {doc_id}",
        "stato": "da_verificare",
        "data_arrivo": ts().isoformat(),
        "data_verifica": None,
    }

    await db[COLL].update_one(
        {"commessa_id": cid},
        build_update_with_event(
            push_items={"approvvigionamento.arrivi": arrivo},
            tipo="MATERIALE_ARRIVATO", user=user,
            note=f"DDT {metadata.get('numero_ddt', '?')} (AI) — {len(materiali_arrivo)} materiali"
        ),
    )

    # Mark matched OdA as "in_consegna"
    oda_aggiornati = []
    for oda_id in oda_ids_to_update:
        await db[COLL].update_one(
            {"commessa_id": cid},
            {"$set": {"approvvigionamento.ordini.$[elem].stato": "in_consegna"}},
            array_filters=[{"elem.ordine_id": oda_id}],
        )
        oda_aggiornati.append(oda_id)

    # Mark DDT doc as confirmed
    await db[DOC_COLL].update_one(
        {"doc_id": doc_id},
        {"$set": {"ddt_pending_confirm": False, "ddt_arrivo_id": arrivo_id}},
    )

    logger.info(f"[CONFIRM-DDT] doc {doc_id}: arrivo {arrivo_id}, {len(materiali_arrivo)} mat, {len(oda_aggiornati)} OdA aggiornati")
    return {
        "arrivo_id": arrivo_id,
        "materiali_creati": len(materiali_arrivo),
        "oda_aggiornati": oda_aggiornati,
        "message": f"Arrivo creato (DDT {metadata.get('numero_ddt', '?')}): {len(materiali_arrivo)} materiali, {len(oda_aggiornati)} OdA aggiornati",
    }

