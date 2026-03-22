"""Perizia Sinistro (Damage Assessment) routes — CRUD + AI Analysis + PDF."""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse, Response
from typing import Optional
import os
import uuid
import base64
import logging
from datetime import datetime, timezone
from core.security import get_current_user
from core.database import db
from models.perizia import PeriziaCreate, PeriziaUpdate, CODICI_DANNO, CODICI_DANNO_MAP
from services.audit_trail import log_activity
from services.object_storage import upload_photo, get_object

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/perizie", tags=["perizie"])

COLLECTION = "perizie"
LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

TIPO_DANNO_LABELS = {
    "strutturale": "Danno Strutturale (EN 1090)",
    "estetico": "Danno Estetico",
    "automatismi": "Danno Automatismi (EN 12453)",
}


# ── Reference data ──

@router.get("/codici-danno")
async def get_codici_danno():
    """Return the damage codes database for tag selection."""
    return {"codici_danno": CODICI_DANNO}


async def next_perizia_number(user_id: str) -> str:
    year = datetime.now(timezone.utc).strftime("%Y")
    count = await db[COLLECTION].count_documents({"user_id": user_id})
    return f"PER-{year}/{count + 1:04d}"


def calc_voci_costo(data: dict) -> list:
    """Algoritmo "Sinistro Smart" — calcolo commerciale che protegge il margine.

    Formule:
    1. Materiale: PB * lunghezza * 1.20  (ricarico fuori serie pezzo singolo)
    2. Trasporto: €120 se >2.5m, €60 se ≤2.5m
    3. Smontaggio: €40/ml
    4. Montaggio: €50/ml
    5. Certificazioni EN 1090/13241: €150 fisso
    6. Smaltimento: €90 fisso
    + Voci aggiuntive basate sui codici danno selezionati
    """
    tipo = data.get("tipo_danno", "strutturale")
    prezzo_ml = float(data.get("prezzo_ml_originale", 0))
    coeff = float(data.get("coefficiente_maggiorazione", 20))
    moduli = data.get("moduli", [])
    codici = data.get("codici_danno", [])
    total_ml = sum(float(m.get("lunghezza_ml", 0)) for m in moduli)

    voci = []
    selected_codes = [CODICI_DANNO_MAP[c] for c in codici if c in CODICI_DANNO_MAP]
    has_struttura = any(c["categoria"] == "Struttura" for c in selected_codes)
    has_ancoraggio = any(c["categoria"] == "Ancoraggio" for c in selected_codes)
    has_protezione = any(c["categoria"] == "Protezione" for c in selected_codes)
    has_sicurezza = any(c["categoria"] == "Sicurezza" for c in selected_codes)
    has_automazione = any(c["categoria"] == "Automazione" for c in selected_codes)

    if not selected_codes:
        has_struttura = tipo == "strutturale"
        has_protezione = tipo in ("strutturale", "estetico")
        has_automazione = tipo == "automatismi"

    norme_all = sorted(set(c["norma"] for c in selected_codes)) if selected_codes else ["EN 1090-2"]
    codici_str = ", ".join(codici) if codici else "generico"

    # ── 1. FORNITURA MATERIALE (Ricarico Fuori Serie) ──
    if has_struttura and prezzo_ml > 0:
        prezzo_maggiorato = round(prezzo_ml * (1 + coeff / 100), 2)
        tot_materiale = round(prezzo_maggiorato * total_ml, 2)
        voci.append({
            "codice": "MAT.01",
            "categoria_costo": "materiale",
            "descrizione": (
                f"Fornitura recinzione/cancello in acciaio zincato a caldo conforme {', '.join(norme_all)}. "
                f"Produzione fuori serie di pezzo singolo: il settaggio macchine e l'acquisto di piccole "
                f"quantita di materiale comportano una maggiorazione del {coeff:.0f}% sul prezzo originale "
                f"di {prezzo_ml:.2f} EUR/ml. Comprensivo di lavorazione, zincatura a caldo e verniciatura a polvere."
            ),
            "unita": "ml",
            "quantita": round(total_ml, 2),
            "prezzo_unitario": prezzo_maggiorato,
            "totale": tot_materiale,
            "tooltip": (
                f"Un singolo modulo da {total_ml:.1f}m costa di piu (proporzionalmente) rispetto a una commessa "
                f"intera. La produzione richiede il settaggio delle macchine CNC, taglio, saldatura, zincatura "
                f"e verniciatura per un solo pezzo. Il ricarico del {coeff:.0f}% copre questa inefficienza produttiva."
            ),
        })
    elif has_protezione and not has_struttura:
        mq = round(total_ml * 1.2, 2)
        voci.append({
            "codice": "MAT.01",
            "categoria_costo": "materiale",
            "descrizione": (
                "Ripristino ciclo anticorrosivo conforme ISO 1461 / ISO 12944. "
                "Carteggiatura manuale, applicazione primer antiruggine bicomponente e "
                "mano di finitura con smalto poliuretanico colore a campione."
            ),
            "unita": "mq",
            "quantita": mq,
            "prezzo_unitario": 35.0,
            "totale": round(mq * 35.0, 2),
            "tooltip": "La verniciatura in loco non garantisce la stessa durabilita del trattamento industriale. Per la ISO 12944 il ciclo completo (primer + finitura) e' obbligatorio.",
        })

    # ── 2. TRASPORTO E LOGISTICA ──
    if total_ml > 0:
        if total_ml > 2.5:
            costo_trasp = 120.0
            desc_trasp = "Trasporto ingombrante: elemento > 2,5 m richiede mezzo dedicato. Forfettario comprensivo di andata e ritorno."
        else:
            costo_trasp = 60.0
            desc_trasp = "Trasporto standard per elemento <= 2,5 m. Forfettario comprensivo di andata e ritorno."
        voci.append({
            "codice": "TRA.01",
            "categoria_costo": "logistica",
            "descrizione": f"Trasporto da officina al cantiere e ritorno. {desc_trasp}",
            "unita": "corpo",
            "quantita": 1,
            "prezzo_unitario": costo_trasp,
            "totale": costo_trasp,
            "tooltip": "Un modulo da 6 metri non viaggia su un corriere standard. Serve un mezzo con pianale lungo, spesso un autocarro con sponda idraulica.",
        })

    # ── 3. MANODOPERA SMONTAGGIO (€40/ml) ──
    if total_ml > 0:
        costo_smontaggio_ml = 40.0
        tot_smontaggio = round(costo_smontaggio_ml * total_ml, 2)
        voci.append({
            "codice": "MAN.01",
            "categoria_costo": "manodopera",
            "descrizione": (
                f"Smontaggio elementi danneggiati ({codici_str}). "
                f"Comprensivo di taglio/svitatura fissaggi, movimentazione, messa in sicurezza dell'area "
                f"e protezione zone adiacenti."
            ),
            "unita": "ml",
            "quantita": round(total_ml, 2),
            "prezzo_unitario": costo_smontaggio_ml,
            "totale": tot_smontaggio,
            "tooltip": "Lo smontaggio include: taglio dei punti di fissaggio, rimozione con attrezzatura, movimentazione a terra e protezione provvisoria dell'apertura.",
        })

    # ── 4. MANODOPERA MONTAGGIO (€50/ml) ──
    if has_struttura or has_ancoraggio:
        costo_montaggio_ml = 50.0
        tot_montaggio = round(costo_montaggio_ml * total_ml, 2)
        desc_montaggio = "Installazione e fissaggio nuovo elemento"
        if has_ancoraggio:
            desc_montaggio += " con ancoranti chimici certificati ETA (ETAG 001). Rifacimento fori, pulizia sede, iniezione resina e inserimento barra"
        else:
            desc_montaggio += " con ancoranti chimici certificati ETA"
        desc_montaggio += ". Comprensivo di allineamento, regolazione e ripristino sigillante elastomerico."

        has_conc = any(c == "A2-CONC" for c in codici)
        if has_conc:
            desc_montaggio += " Ripristino cordolo in cemento con malta tixotropica strutturale."

        voci.append({
            "codice": "MAN.02",
            "categoria_costo": "manodopera",
            "descrizione": desc_montaggio,
            "unita": "ml",
            "quantita": round(total_ml, 2),
            "prezzo_unitario": costo_montaggio_ml,
            "totale": tot_montaggio,
            "tooltip": "Il montaggio richiede: posizionamento con livella laser, foratura del supporto, iniezione ancorante chimico (tempo di presa 24h), fissaggio definitivo e sigillatura.",
        })

    # ── 5. AUTOMAZIONE (se M1-FORCE) ──
    if has_automazione:
        voci.append({
            "codice": "AUT.01",
            "categoria_costo": "materiale",
            "descrizione": (
                "Fornitura e sostituzione componenti di automazione danneggiati "
                "(motore, centralina, fotocellule, finecorsa). Marca e modello come da impianto esistente."
            ),
            "unita": "corpo", "quantita": 1,
            "prezzo_unitario": round(prezzo_ml * total_ml * 0.5, 2) if prezzo_ml else 450.0,
            "totale": round(prezzo_ml * total_ml * 0.5, 2) if prezzo_ml else 450.0,
            "tooltip": "I componenti di automazione devono essere sostituiti con ricambi originali o compatibili certificati per mantenere la conformita EN 12453.",
        })
        voci.append({
            "codice": "AUT.02",
            "categoria_costo": "normativo",
            "descrizione": (
                "Verifica e collaudo impianto automazione conforme EN 12453. "
                "Test forze di impatto con strumento certificato, verifica dispositivi "
                "di sicurezza e fotocellule. Rilascio certificato di conformita."
            ),
            "unita": "corpo", "quantita": 1,
            "prezzo_unitario": 320.0, "totale": 320.0,
            "tooltip": "Il collaudo delle forze di impatto e' obbligatorio per legge (EN 12453). Senza questo test, il cancello non puo essere rimesso in funzione.",
        })

    # ── 6. SICUREZZA (se G1-GAP) ──
    if has_sicurezza:
        voci.append({
            "codice": "SIC.01",
            "categoria_costo": "normativo",
            "descrizione": (
                "Riallineamento millimetrico elementi e verifica distanze di sicurezza "
                "anti-cesoiamento conforme EN 13241. Test spazi con calibro certificato."
            ),
            "unita": "corpo", "quantita": 1,
            "prezzo_unitario": 180.0, "totale": 180.0,
            "tooltip": "Le distanze tra elementi mobili e fissi sono normate dalla EN 13241 per prevenire il rischio di cesoiamento. Se alterate, vanno ripristinate.",
        })

    # ── 7. ONERI NORMATIVI — Fascicolo Tecnico + DoP (€150 fisso) ──
    if has_struttura or has_sicurezza or has_automazione:
        voci.append({
            "codice": "NOR.01",
            "categoria_costo": "normativo",
            "descrizione": (
                f"Aggiornamento Fascicolo Tecnico e Dichiarazione di Prestazione (DoP) "
                f"come richiesto dal Reg. UE 305/2011 e dalle norme {', '.join(norme_all)}. "
                f"Tempo tecnico per redazione, archiviazione collaudo e documentazione conformita CE."
            ),
            "unita": "corpo", "quantita": 1,
            "prezzo_unitario": 150.0, "totale": 150.0,
            "tooltip": "Molti artigiani dimenticano di farsi pagare la burocrazia. Se sostituisci un pezzo di un cancello certificato EN 13241, DEVI aggiornare i documenti. L'assicurazione e' tenuta a coprire questo costo.",
        })

    # ── 8. SMALTIMENTO (€150 fisso — condizionato) ──
    if data.get("smaltimento", True):
        voci.append({
            "codice": "SMA.01",
            "categoria_costo": "logistica",
            "descrizione": (
                "Smaltimento materiali rimossi presso discarica autorizzata (codice CER 170405 — "
                "ferro e acciaio). Comprensivo di trasporto, oneri di conferimento e compilazione "
                "formulario identificazione rifiuti (FIR)."
            ),
            "unita": "corpo", "quantita": 1,
            "prezzo_unitario": 150.0, "totale": 150.0,
            "tooltip": "Lo smaltimento in discarica autorizzata e' obbligatorio per legge. Il formulario FIR deve essere conservato per 5 anni.",
        })

    # ── 9. MAGGIORAZIONE ACCESSO DIFFICILE (+15% sul subtotale) ──
    if data.get("accesso_difficile", False):
        subtotale_pre = sum(v.get("totale", 0) for v in voci)
        maggiorazione = round(subtotale_pre * 0.15, 2)
        voci.append({
            "codice": "ACC.01",
            "categoria_costo": "logistica",
            "descrizione": (
                "Maggiorazione per accesso cantiere difficoltoso (+15%). "
                "Comprensivo di trasporto speciale, attrezzature aggiuntive e tempo operativo extra."
            ),
            "unita": "corpo", "quantita": 1,
            "prezzo_unitario": maggiorazione, "totale": maggiorazione,
            "tooltip": "L'accesso difficile (strade strette, salite, assenza di area di manovra) richiede mezzi speciali e tempi di lavorazione maggiori.",
        })

    # ── 10. SCONTO DI CORTESIA (% sul totale, dopo maggiorazioni) ──
    sconto_pct = float(data.get("sconto_cortesia", 0))
    if sconto_pct > 0:
        subtotale_post = sum(v.get("totale", 0) for v in voci)
        sconto_val = round(subtotale_post * sconto_pct / 100, 2)
        voci.append({
            "codice": "SCO.01",
            "categoria_costo": "sconto",
            "descrizione": f"Sconto di cortesia ({sconto_pct:.0f}%)",
            "unita": "corpo", "quantita": 1,
            "prezzo_unitario": -sconto_val, "totale": -sconto_val,
            "tooltip": "Sconto commerciale applicato a discrezione del perito.",
        })

    return voci


# ── Archivio Sinistri (Stats Dashboard) ──

@router.get("/archivio/stats")
async def archivio_stats(user: dict = Depends(get_current_user)):
    """Return aggregated stats for the Archivio Sinistri dashboard."""
    q = {"user_id": user["user_id"]}
    total_count = await db[COLLECTION].count_documents(q)

    if total_count == 0:
        return {
            "total_count": 0,
            "total_amount": 0,
            "avg_amount": 0,
            "by_tipo": {},
            "by_status": {},
            "by_month": [],
            "codici_frequency": [],
        }

    # All perizie (light projection)
    perizie = await db[COLLECTION].find(
        q, {"_id": 0, "total_perizia": 1, "tipo_danno": 1, "status": 1, "created_at": 1, "codici_danno": 1}
    ).to_list(1000)

    total_amount = sum(p.get("total_perizia", 0) for p in perizie)
    avg_amount = total_amount / total_count if total_count else 0

    # By tipo_danno
    by_tipo = {}
    for p in perizie:
        t = p.get("tipo_danno", "altro")
        if t not in by_tipo:
            by_tipo[t] = {"count": 0, "amount": 0}
        by_tipo[t]["count"] += 1
        by_tipo[t]["amount"] += p.get("total_perizia", 0)

    # By status
    by_status = {}
    for p in perizie:
        s = p.get("status", "bozza")
        if s not in by_status:
            by_status[s] = 0
        by_status[s] += 1

    # By month (last 12 months)
    from collections import defaultdict
    monthly = defaultdict(lambda: {"count": 0, "amount": 0})
    for p in perizie:
        ca = p.get("created_at")
        if ca and hasattr(ca, "strftime"):
            key = ca.strftime("%Y-%m")
            monthly[key]["count"] += 1
            monthly[key]["amount"] += p.get("total_perizia", 0)

    by_month = [{"month": k, **v} for k, v in sorted(monthly.items())][-12:]

    # Codici danno frequency
    codici_freq = defaultdict(int)
    for p in perizie:
        for c in p.get("codici_danno", []):
            codici_freq[c] += 1
    codici_frequency = [{"codice": k, "count": v} for k, v in sorted(codici_freq.items(), key=lambda x: -x[1])]

    return {
        "total_count": total_count,
        "total_amount": round(total_amount, 2),
        "avg_amount": round(avg_amount, 2),
        "by_tipo": by_tipo,
        "by_status": by_status,
        "by_month": by_month,
        "codici_frequency": codici_frequency,
    }


# ── List ──

@router.get("/")
async def list_perizie(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    q = {"user_id": user["user_id"]}
    if status:
        q["status"] = status
    if search:
        q["$or"] = [
            {"number": {"$regex": search, "$options": "i"}},
            {"client_name": {"$regex": search, "$options": "i"}},
            {"descrizione_utente": {"$regex": search, "$options": "i"}},
        ]
    total = await db[COLLECTION].count_documents(q)
    items = await db[COLLECTION].find(q, {"_id": 0, "foto": 0}).sort("created_at", -1).to_list(100)
    return {"items": items, "total": total}


# ── Get One ──

@router.get("/{perizia_id}")
async def get_perizia(perizia_id: str, user: dict = Depends(get_current_user)):
    doc = await db[COLLECTION].find_one(
        {"perizia_id": perizia_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Perizia non trovata")
    return doc


# ── Create ──

@router.post("/", status_code=201)
async def create_perizia(data: PeriziaCreate, user: dict = Depends(get_current_user)):
    perizia_id = f"per_{uuid.uuid4().hex[:12]}"
    number = await next_perizia_number(user["user_id"])
    now = datetime.now(timezone.utc)

    client_name = ""
    if data.client_id:
        client = await db.clients.find_one({"client_id": data.client_id}, {"_id": 0, "business_name": 1})
        if client:
            client_name = client["business_name"]

    # Auto-generate cost items if not provided
    moduli_dicts = [m.model_dump() for m in data.moduli]
    voci = [v.model_dump() for v in data.voci_costo] if data.voci_costo else calc_voci_costo({
        "tipo_danno": data.tipo_danno,
        "prezzo_ml_originale": data.prezzo_ml_originale,
        "coefficiente_maggiorazione": data.coefficiente_maggiorazione,
        "moduli": moduli_dicts,
        "codici_danno": data.codici_danno,
        "smaltimento": data.smaltimento,
        "accesso_difficile": data.accesso_difficile,
        "sconto_cortesia": data.sconto_cortesia,
    })

    total_perizia = sum(v.get("totale", 0) for v in voci)

    doc = {
        "perizia_id": perizia_id,
        "user_id": user["user_id"],
        "number": number,
        "client_id": data.client_id,
        "client_name": client_name,
        "localizzazione": data.localizzazione.model_dump() if data.localizzazione else {},
        "tipo_danno": data.tipo_danno,
        "tipo_danno_label": TIPO_DANNO_LABELS.get(data.tipo_danno, ""),
        "codici_danno": data.codici_danno,
        "descrizione_utente": data.descrizione_utente,
        "prezzo_ml_originale": data.prezzo_ml_originale,
        "coefficiente_maggiorazione": data.coefficiente_maggiorazione,
        "moduli": moduli_dicts,
        "foto": data.foto,
        "ai_analysis": data.ai_analysis,
        "stato_di_fatto": data.stato_di_fatto,
        "nota_tecnica": data.nota_tecnica,
        "lettera_accompagnamento": data.lettera_accompagnamento,
        "voci_costo": voci,
        "total_perizia": round(total_perizia, 2),
        "notes": data.notes,
        "status": "bozza",
        "smaltimento": data.smaltimento,
        "accesso_difficile": data.accesso_difficile,
        "sconto_cortesia": data.sconto_cortesia,
        "commessa_id": data.commessa_id,
        "created_at": now,
        "updated_at": now,
    }
    await db[COLLECTION].insert_one(doc)
    created = await db[COLLECTION].find_one({"perizia_id": perizia_id}, {"_id": 0})
    logger.info(f"Perizia created: {perizia_id} ({number})")
    await log_activity(user, "create", "perizia", perizia_id, label=number)
    return created


# ── Update ──

@router.put("/{perizia_id}")
async def update_perizia(perizia_id: str, data: PeriziaUpdate, user: dict = Depends(get_current_user)):
    existing = await db[COLLECTION].find_one(
        {"perizia_id": perizia_id, "user_id": user["user_id"]}
    )
    if not existing:
        raise HTTPException(404, "Perizia non trovata")

    upd = {"updated_at": datetime.now(timezone.utc)}

    simple_fields = [
        "client_id", "tipo_danno", "descrizione_utente", "prezzo_ml_originale",
        "coefficiente_maggiorazione", "ai_analysis", "stato_di_fatto",
        "nota_tecnica", "lettera_accompagnamento", "notes", "status",
        "commessa_id",
    ]
    for field in simple_fields:
        val = getattr(data, field, None)
        if val is not None:
            upd[field] = val

    # Boolean fields — need to check explicitly as False is a valid value
    if data.smaltimento is not None:
        upd["smaltimento"] = data.smaltimento
    if data.accesso_difficile is not None:
        upd["accesso_difficile"] = data.accesso_difficile
    # Float field that can be 0
    if data.sconto_cortesia is not None:
        upd["sconto_cortesia"] = data.sconto_cortesia

    if data.codici_danno is not None:
        upd["codici_danno"] = data.codici_danno

    if data.localizzazione is not None:
        upd["localizzazione"] = data.localizzazione.model_dump()
    if data.moduli is not None:
        upd["moduli"] = [m.model_dump() for m in data.moduli]
    if data.foto is not None:
        upd["foto"] = data.foto
    if data.voci_costo is not None:
        voci = [v.model_dump() for v in data.voci_costo]
        upd["voci_costo"] = voci
        upd["total_perizia"] = round(sum(v.get("totale", 0) for v in voci), 2)

    # Update tipo_danno_label
    if data.tipo_danno:
        upd["tipo_danno_label"] = TIPO_DANNO_LABELS.get(data.tipo_danno, "")

    # Update client name
    cid = data.client_id if data.client_id is not None else existing.get("client_id")
    if cid:
        client = await db.clients.find_one({"client_id": cid}, {"_id": 0, "business_name": 1})
        if client:
            upd["client_name"] = client["business_name"]

    await db[COLLECTION].update_one({"perizia_id": perizia_id}, {"$set": upd})
    updated = await db[COLLECTION].find_one({"perizia_id": perizia_id}, {"_id": 0})
    await log_activity(user, "update", "perizia", perizia_id, label=updated.get("number", ""))
    return updated


# ── Delete ──

@router.delete("/{perizia_id}")
async def delete_perizia(perizia_id: str, user: dict = Depends(get_current_user)):
    result = await db[COLLECTION].delete_one(
        {"perizia_id": perizia_id, "user_id": user["user_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Perizia non trovata")
    await log_activity(user, "delete", "perizia", perizia_id)
    return {"message": "Perizia eliminata"}


# ── Photo Upload (Object Storage) ──

def _upload_perizia_photo(user_id: str, file_data: bytes, filename: str, content_type: str) -> dict:
    """Upload a perizia photo to object storage."""
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    storage_path = f"norma_facile/perizie/{user_id}/{uuid.uuid4()}.{ext}"
    from services.object_storage import put_object
    result = put_object(storage_path, file_data, content_type)
    return {
        "storage_path": result["path"],
        "original_filename": filename,
        "content_type": content_type,
        "size": result.get("size", len(file_data)),
    }


@router.post("/{perizia_id}/upload-foto")
async def upload_foto_perizia(
    perizia_id: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a single photo to object storage and add to perizia."""
    doc = await db[COLLECTION].find_one(
        {"perizia_id": perizia_id, "user_id": user["user_id"]}
    )
    if not doc:
        raise HTTPException(404, "Perizia non trovata")

    current_photos = doc.get("foto", [])
    # Count only object-storage photos (dicts), not legacy base64 strings
    obj_count = sum(1 for p in current_photos if isinstance(p, dict))
    if obj_count >= 5:
        raise HTTPException(400, "Massimo 5 foto per perizia")

    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(400, f"Formato non supportato: {file.content_type}. Usa JPEG, PNG o WebP.")

    file_data = await file.read()
    if len(file_data) > 10 * 1024 * 1024:
        raise HTTPException(400, "File troppo grande (max 10MB)")

    storage_info = _upload_perizia_photo(user["user_id"], file_data, file.filename, file.content_type)
    foto_entry = {
        "foto_id": f"foto_{uuid.uuid4().hex[:8]}",
        **storage_info,
    }

    await db[COLLECTION].update_one(
        {"perizia_id": perizia_id},
        {
            "$push": {"foto": foto_entry},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        },
    )
    return foto_entry


@router.delete("/{perizia_id}/foto/{foto_id}")
async def delete_foto_perizia(perizia_id: str, foto_id: str, user: dict = Depends(get_current_user)):
    """Remove a photo from the perizia (object storage reference)."""
    result = await db[COLLECTION].update_one(
        {"perizia_id": perizia_id, "user_id": user["user_id"]},
        {"$pull": {"foto": {"foto_id": foto_id}}},
    )
    if result.modified_count == 0:
        raise HTTPException(404, "Foto non trovata")
    return {"deleted": True}


@router.get("/foto-proxy/{path:path}")
async def proxy_foto_perizia(path: str, user: dict = Depends(get_current_user)):
    """Proxy a photo from object storage."""
    try:
        data, content_type = get_object(path)
        return Response(content=data, media_type=content_type)
    except Exception as e:
        raise HTTPException(404, f"Foto non trovata: {str(e)[:100]}")


@router.patch("/{perizia_id}/collega-commessa")
async def collega_perizia_a_commessa(
    perizia_id: str,
    payload: dict,
    user: dict = Depends(get_current_user),
):
    """Link a perizia to an existing commessa (bidirectional)."""
    uid = user["user_id"]
    commessa_id = payload.get("commessa_id")
    if not commessa_id:
        raise HTTPException(400, "commessa_id richiesto")

    perizia = await db[COLLECTION].find_one({"perizia_id": perizia_id, "user_id": uid})
    if not perizia:
        raise HTTPException(404, "Perizia non trovata")
    commessa = await db.commesse.find_one({"commessa_id": commessa_id, "user_id": uid})
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    await db[COLLECTION].update_one(
        {"perizia_id": perizia_id},
        {"$set": {"commessa_id": commessa_id}},
    )
    await db.commesse.update_one(
        {"commessa_id": commessa_id},
        {"$set": {"moduli.perizia_id": perizia_id, "linked_perizia_id": perizia_id}},
    )
    await log_activity(user, "update", "perizia", perizia_id,
                       label=perizia.get("number", ""),
                       details={"collegato_a_commessa": commessa.get("numero", commessa_id)})
    return {"message": "Perizia collegata alla commessa", "commessa_id": commessa_id}


# ── AI Photo Analysis ──

@router.post("/{perizia_id}/analyze-photos")
async def analyze_photos(perizia_id: str, user: dict = Depends(get_current_user)):
    """Analyze uploaded photos using GPT-4o vision to detect damage."""
    doc = await db[COLLECTION].find_one(
        {"perizia_id": perizia_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Perizia non trovata")

    photos = doc.get("foto", [])
    if not photos:
        raise HTTPException(422, "Nessuna foto caricata. Caricare almeno una foto del danno.")

    if not LLM_KEY:
        raise HTTPException(500, "Chiave LLM non configurata")

    tipo_danno = doc.get("tipo_danno", "strutturale")
    tipo_label = TIPO_DANNO_LABELS.get(tipo_danno, tipo_danno)
    descrizione = doc.get("descrizione_utente", "")
    localizzazione = doc.get("localizzazione", {})
    indirizzo = localizzazione.get("indirizzo", "non specificato")
    codici = doc.get("codici_danno", [])
    codici_desc = []
    for c in codici:
        cd = CODICI_DANNO_MAP.get(c)
        if cd:
            codici_desc.append(f"[{c}] {cd['label']} ({cd['norma']}): {cd['implicazione']}")
    codici_text = "\n".join(codici_desc) if codici_desc else "Nessun codice danno specifico selezionato."

    prompt = f"""Sei un perito tecnico specializzato in carpenteria metallica, recinzioni e cancelli.
Analizza le foto allegate di un sinistro (urto da veicolo) su una recinzione/cancello metallico.

CONTESTO:
- Tipo danno classificato: {tipo_label}
- Localizzazione: {indirizzo}
- Descrizione dell'utente: {descrizione or 'Non fornita'}
- Codici danno rilevati dall'operatore:
{codici_text}

COMPITO:
1. DESCRIZIONE STATO DI FATTO: Descrivi tecnicamente e in modo asciutto lo stato dei danni visibili. 
   Indica: tipo di struttura, materiale presunto, tipo di deformazione, elementi coinvolti 
   (montanti, traversi, pannelli, cerniere, serratura, automazione se visibile).

2. ANALISI DANNI: Per ogni elemento danneggiato indica:
   - Tipo di danno (deformazione plastica, rottura, distacco, abrasione, ecc.)
   - Gravita stimata (lieve/moderato/grave)
   - Se riparabile o da sostituire

3. NOTA TECNICA: Spiega perche, nel caso di danno strutturale, la sostituzione e' obbligatoria 
   citando la EN 1090 (la raddrizzatura altera le proprieta meccaniche dell'acciaio e della 
   zincatura, invalidando la certificazione originale).

Scrivi in italiano formale, tono professionale e tecnico. Non usare markdown."""

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

        file_contents = []
        for photo in photos[:5]:
            # New format: dict with storage_path (object storage)
            if isinstance(photo, dict) and photo.get("storage_path"):
                try:
                    data, ct = get_object(photo["storage_path"])
                    b64 = base64.b64encode(data).decode("utf-8")
                    file_contents.append(ImageContent(image_base64=b64))
                except Exception as e:
                    logger.warning(f"Failed to load photo from storage: {e}")
            # Legacy format: raw base64 string
            elif isinstance(photo, str) and photo:
                photo_b64 = photo
                if "," in photo_b64:
                    photo_b64 = photo_b64.split(",", 1)[1]
                file_contents.append(ImageContent(image_base64=photo_b64))

        chat = LlmChat(
            api_key=LLM_KEY,
            session_id=f"perizia-{perizia_id}",
            system_message="Sei un perito tecnico esperto in carpenteria metallica, specializzato nella valutazione di danni da sinistro su recinzioni e cancelli. Rispondi sempre in italiano formale e tecnico."
        ).with_model("openai", "gpt-4o")

        response = await chat.send_message(UserMessage(
            text=prompt,
            file_contents=file_contents,
        ))

        # Parse sections from response
        ai_text = response if isinstance(response, str) else str(response)

        # Auto-generate stato_di_fatto and nota_tecnica from AI response
        stato_di_fatto = ""
        nota_tecnica = ""

        # Try to split by sections
        lower = ai_text.lower()
        if "stato di fatto" in lower:
            idx_start = lower.index("stato di fatto")
            # Find next section
            next_sections = ["analisi dann", "nota tecnica"]
            idx_end = len(ai_text)
            for ns in next_sections:
                if ns in lower[idx_start + 20:]:
                    idx_end = lower.index(ns, idx_start + 20)
                    break
            stato_di_fatto = ai_text[idx_start:idx_end].strip()
            # Clean up heading
            for prefix in ["STATO DI FATTO:", "STATO DI FATTO", "DESCRIZIONE STATO DI FATTO:", "DESCRIZIONE STATO DI FATTO", "1.", "1)"]:
                if stato_di_fatto.upper().startswith(prefix.upper()):
                    stato_di_fatto = stato_di_fatto[len(prefix):].strip()

        if "nota tecnica" in lower:
            idx = lower.index("nota tecnica")
            nota_tecnica = ai_text[idx:].strip()
            for prefix in ["NOTA TECNICA:", "NOTA TECNICA", "3.", "3)"]:
                if nota_tecnica.upper().startswith(prefix.upper()):
                    nota_tecnica = nota_tecnica[len(prefix):].strip()

        if not stato_di_fatto:
            stato_di_fatto = ai_text[:len(ai_text) // 2]
        if not nota_tecnica and tipo_danno == "strutturale":
            nota_tecnica = (
                "La raddrizzatura a caldo o a freddo degli elementi in acciaio zincato altera "
                "irreversibilmente le proprieta meccaniche del materiale e compromette lo strato "
                "di zincatura protettiva. Ai sensi della EN 1090-1 e del Regolamento UE 305/2011, "
                "la certificazione CE originale della struttura risulta invalidata. "
                "Si rende pertanto necessaria la sostituzione integrale dei moduli danneggiati."
            )

        await db[COLLECTION].update_one(
            {"perizia_id": perizia_id},
            {"$set": {
                "ai_analysis": ai_text,
                "stato_di_fatto": stato_di_fatto,
                "nota_tecnica": nota_tecnica,
                "updated_at": datetime.now(timezone.utc),
            }}
        )

        logger.info(f"AI photo analysis completed for perizia {perizia_id}")
        return {
            "perizia_id": perizia_id,
            "ai_analysis": ai_text,
            "stato_di_fatto": stato_di_fatto,
            "nota_tecnica": nota_tecnica,
            "status": "analyzed",
        }

    except Exception as e:
        logger.error(f"AI analysis failed for perizia {perizia_id}: {e}")
        raise HTTPException(500, f"Errore nell'analisi AI: {str(e)}")


# ── Genera Lettera di Accompagnamento Tecnica ──

@router.post("/{perizia_id}/genera-lettera")
async def genera_lettera(perizia_id: str, user: dict = Depends(get_current_user)):
    """Generate the formal technical cover letter for the insurance assessor using AI."""
    doc = await db[COLLECTION].find_one(
        {"perizia_id": perizia_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Perizia non trovata")

    # Gather context
    loc = doc.get("localizzazione", {})
    indirizzo = loc.get("indirizzo", "[Indirizzo]")
    comune = loc.get("comune", "")
    provincia = loc.get("provincia", "")
    localita = f"{indirizzo}, {comune} ({provincia})".strip(", ()")

    client_name = doc.get("client_name", "[Nome Cliente]")
    tipo_danno = doc.get("tipo_danno", "strutturale")
    moduli = doc.get("moduli", [])
    total_ml = sum(float(m.get("lunghezza_ml", 0)) for m in moduli)
    total_perizia = doc.get("total_perizia", 0)
    stato_di_fatto = doc.get("stato_di_fatto", "")
    data_sinistro = doc.get("created_at")
    if hasattr(data_sinistro, "strftime"):
        data_sinistro_str = data_sinistro.strftime("%d/%m/%Y")
    else:
        data_sinistro_str = str(data_sinistro)[:10] if data_sinistro else "[Data]"

    # Modules description
    moduli_desc = ", ".join(
        f"1 modulo da {m.get('lunghezza_ml', 0):.1f}ml" for m in moduli
    ) if moduli else "moduli danneggiati"

    # Get company info
    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0})
    co_name = (company or {}).get("company_name", "[Nome Ditta]")
    co_address = (company or {}).get("address", "")
    co_vat = (company or {}).get("vat_number", "")

    if not LLM_KEY:
        # Fallback: generate template without AI
        lettera = _generate_lettera_template(
            localita, data_sinistro_str, moduli_desc, total_ml,
            tipo_danno, total_perizia, co_name, client_name
        )
    else:
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage

            prompt = f"""Sei un responsabile tecnico di una ditta di carpenteria metallica. Devi scrivere una lettera di accompagnamento tecnica formale per un preventivo di ripristino sinistro, da inviare all'ufficio sinistri dell'assicurazione.

DATI PERIZIA:
- Localita sinistro: {localita}
- Data sinistro: {data_sinistro_str}
- Cliente/Proprietario: {client_name}
- Tipo danno: {TIPO_DANNO_LABELS.get(tipo_danno, tipo_danno)}
- Moduli coinvolti: {moduli_desc} (totale {total_ml:.1f} ml)
- Importo perizia: {total_perizia:.2f} EUR
- Stato di fatto: {stato_di_fatto[:500] if stato_di_fatto else 'Danni da urto veicolare'}
- Ditta: {co_name}

STRUTTURA DELLA LETTERA:
1. Oggetto: "Relazione tecnica di ripristino e dichiarazione di conformita (Rif. Sinistro del {data_sinistro_str})"
2. Introduzione: trasmissione computo metrico per ripristino recinzione/cancello in [localita]
3. Qualifica: la ditta e' installatrice/produttrice del manufatto originale
4. Corpo (3 punti tecnici vincolanti):
   a. DECADENZA DELLA MARCATURA CE: L'urto ha alterato le caratteristiche meccaniche. Qualsiasi raddrizzatura o saldatura in opera non certificata comporta decadenza della Marcatura CE e della DoP (EN 1090-2, EN 13241). Come produttori, non possiamo assumerci responsabilita civile e penale sulla stabilita se non tramite sostituzione integrale.
   b. INTEGRITA DEL CICLO ANTICORROSIVO: Frattura protezione superficiale (zincatura/verniciatura a polvere). Per durabilita ISO 12944, necessario ripristino industriale.
   c. SICUREZZA DEI FISSAGGI: Stress meccanico sui tasselli richiede bonifica supporto e nuovo ancoraggio certificato per evitare ribaltamento (carico vento).
5. Chiusura: congruita degli importi necessari a sollevare proprietario e ditta da responsabilita per vizi di conformita post-sinistro.

REGOLE:
- Tono formale, autorevole, tecnico.
- Lingua italiana corretta.
- Cita specificamente le norme: UNI EN 1090-2, UNI EN 13241, ISO 12944.
- NON usare markdown. Scrivi testo semplice con paragrafi.
- Includi spazio per timbro e firma alla fine.
- La lettera deve far capire al perito che tagliare il preventivo significherebbe assumersi responsabilita legali."""

            chat = LlmChat(
                api_key=LLM_KEY,
                session_id=f"perizia-lettera-{perizia_id}",
                system_message="Sei un responsabile tecnico esperto in carpenteria metallica e normative CE. Scrivi lettere formali professionali per periti assicurativi. Rispondi sempre in italiano formale."
            ).with_model("openai", "gpt-4o")

            response = await chat.send_message(UserMessage(text=prompt))
            lettera = response if isinstance(response, str) else str(response)

        except Exception as e:
            logger.error(f"AI letter generation failed: {e}")
            lettera = _generate_lettera_template(
                localita, data_sinistro_str, moduli_desc, total_ml,
                tipo_danno, total_perizia, co_name, client_name
            )

    await db[COLLECTION].update_one(
        {"perizia_id": perizia_id},
        {"$set": {"lettera_accompagnamento": lettera, "updated_at": datetime.now(timezone.utc)}}
    )

    logger.info(f"Lettera accompagnamento generated for perizia {perizia_id}")
    return {"perizia_id": perizia_id, "lettera_accompagnamento": lettera}


def _generate_lettera_template(localita, data_sinistro, moduli_desc, total_ml, tipo_danno, total_perizia, co_name, client_name):
    """Fallback template when AI is not available."""
    return f"""Oggetto: Relazione tecnica di ripristino e dichiarazione di conformita (Rif. Sinistro del {data_sinistro})

Alla cortese attenzione dell'Ufficio Sinistri / Perito incaricato,

In allegato alla presente si trasmette il computo metrico estimativo per il ripristino della recinzione sita in {localita}, danneggiata in data {data_sinistro}.

In qualita di ditta installatrice e produttrice del manufatto originale, si precisa che l'intervento di riparazione e' stato calcolato non secondo criteri puramente estetici, ma nel rigoroso rispetto delle normative cogenti UNI EN 1090-2 (Esecuzione di strutture di acciaio) e UNI EN 13241 (Norma di prodotto per cancelli e recinzioni).

Si evidenziano i seguenti punti tecnici vincolanti:

1. DECADENZA DELLA MARCATURA CE
L'urto ha alterato le caratteristiche meccaniche dei moduli coinvolti ({moduli_desc}, per un totale di {total_ml:.1f} ml). Qualsiasi intervento di raddrizzatura o saldatura in opera non certificato comporterebbe l'immediata decadenza della Marcatura CE originale e della Dichiarazione di Prestazione (DoP). Come produttori, non possiamo assumerci la responsabilita civile e penale sulla stabilita strutturale del manufatto se non tramite la sostituzione integrale degli elementi deformati.

2. INTEGRITA DEL CICLO ANTICORROSIVO
La frattura della protezione superficiale (zincatura a caldo e verniciatura a polvere) espone l'acciaio a fenomeni ossidativi non riparabili con verniciature liquide monocomponenti in loco. Per garantire la durabilita prevista dalla norma ISO 12944, e' necessario il ripristino industriale del componente.

3. SICUREZZA DEI FISSAGGI
Lo stress meccanico subito dai tasselli a seguito dell'impatto richiede la bonifica del supporto e il nuovo ancoraggio certificato, onde evitare il ribaltamento improvviso del modulo in caso di sollecitazioni atmosferiche (carico vento).

L'importo complessivo della perizia ammonta a EUR {total_perizia:.2f}, necessario a sollevare sia la proprieta ({client_name}) che lo scrivente ({co_name}) da responsabilita derivanti da vizi di conformita post-sinistro.

Restiamo a disposizione per ogni chiarimento tecnico.

Distinti saluti,


____________________________
{co_name}
Responsabile Tecnico delle Commesse
[Timbro e Firma]"""


# ── Recalculate Cost Items ──

@router.post("/{perizia_id}/recalc")
async def recalculate_costs(perizia_id: str, user: dict = Depends(get_current_user)):
    """Recalculate cost items based on current perizia data."""
    doc = await db[COLLECTION].find_one(
        {"perizia_id": perizia_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Perizia non trovata")

    voci = calc_voci_costo({
        "tipo_danno": doc.get("tipo_danno", "strutturale"),
        "prezzo_ml_originale": doc.get("prezzo_ml_originale", 0),
        "coefficiente_maggiorazione": doc.get("coefficiente_maggiorazione", 20),
        "moduli": doc.get("moduli", []),
        "codici_danno": doc.get("codici_danno", []),
        "smaltimento": doc.get("smaltimento", True),
        "accesso_difficile": doc.get("accesso_difficile", False),
        "sconto_cortesia": doc.get("sconto_cortesia", 0),
    })
    total_perizia = round(sum(v.get("totale", 0) for v in voci), 2)

    await db[COLLECTION].update_one(
        {"perizia_id": perizia_id},
        {"$set": {"voci_costo": voci, "total_perizia": total_perizia, "updated_at": datetime.now(timezone.utc)}}
    )

    return {"voci_costo": voci, "total_perizia": total_perizia}


# ── PDF ──

@router.get("/{perizia_id}/pdf")
async def get_perizia_pdf(perizia_id: str, user: dict = Depends(get_current_user)):
    doc = await db[COLLECTION].find_one(
        {"perizia_id": perizia_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Perizia non trovata")

    company = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0})

    from services.perizia_pdf_service import generate_perizia_pdf
    pdf_buffer = generate_perizia_pdf(doc, company)
    filename = f"perizia_{doc.get('number', perizia_id).replace('/', '_')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



# ── Ponte Perizia → Preventivatore ──

@router.post("/{perizia_id}/genera-preventivo")
async def genera_preventivo_da_perizia(perizia_id: str, user: dict = Depends(get_current_user)):
    """Ponte Perizia → Preventivatore: trasferisce i dati della perizia in un nuovo preventivo."""
    perizia = await db[COLLECTION].find_one(
        {"perizia_id": perizia_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not perizia:
        raise HTTPException(404, "Perizia non trovata")

    now = datetime.now(timezone.utc)
    year = now.strftime("%Y")
    count = await db.preventivi.count_documents({"user_id": user["user_id"]})
    prev_id = f"prev_{uuid.uuid4().hex[:12]}"
    prev_number = f"PV-{year}-{count + 1:04d}"

    # Build preventivo lines from perizia voci_costo
    voci = perizia.get("voci_costo", [])
    lines = []
    for v in voci:
        totale = v.get("totale", 0)
        qty = v.get("quantita", 1)
        lines.append({
            "line_id": f"l_{uuid.uuid4().hex[:8]}",
            "description": f"[{v.get('codice', '')}] {v.get('descrizione', '')}",
            "quantity": qty,
            "unit": v.get("unita", "corpo"),
            "unit_price": round(v.get("prezzo_unitario", 0), 2),
            "sconto_1": 0,
            "sconto_2": 0,
            "vat_rate": "22",
            "line_total": round(totale, 2),
            "prezzo_netto": round(v.get("prezzo_unitario", 0), 2),
        })

    subtotal = sum(ln.get("line_total", 0) for ln in lines)
    vat = round(subtotal * 0.22, 2)

    # Determine normativa from perizia tipo_danno
    tipo = perizia.get("tipo_danno", "strutturale")
    normativa = "EN_1090" if tipo == "strutturale" else "EN_13241" if tipo == "automatismi" else "NESSUNA"

    # Build subject from perizia info
    moduli = perizia.get("moduli", [])
    total_ml = sum(float(m.get("lunghezza_ml", 0)) for m in moduli)
    subject = f"Ripristino da Perizia {perizia.get('number', '')} — {total_ml:.1f} ml"

    client_name = perizia.get("client_name", "")
    client_id = perizia.get("client_id", "")

    preventivo = {
        "preventivo_id": prev_id,
        "user_id": user["user_id"],
        "number": prev_number,
        "client_id": client_id,
        "client_name": client_name,
        "subject": subject,
        "status": "bozza",
        "lines": lines,
        "totals": {
            "subtotal": round(subtotal, 2),
            "sconto_globale_pct": 0,
            "sconto_val": 0,
            "imponibile": round(subtotal, 2),
            "total_vat": vat,
            "total": round(subtotal + vat, 2),
            "total_document": round(subtotal + vat, 2),
            "acconto": 0,
            "da_pagare": round(subtotal + vat, 2),
            "line_count": len(lines),
        },
        "notes": f"Generato automaticamente da Perizia {perizia.get('number', '')}",
        "normativa": normativa,
        "classe_esecuzione": "EXC2",
        "giorni_consegna": 30,
        "validity_days": 30,
        "perizia_source": {
            "perizia_id": perizia_id,
            "perizia_number": perizia.get("number", ""),
            "tipo_danno": tipo,
            "total_perizia": perizia.get("total_perizia", 0),
        },
        "created_at": now,
        "updated_at": now,
    }

    await db.preventivi.insert_one(preventivo)

    # Link perizia to preventivo
    await db[COLLECTION].update_one(
        {"perizia_id": perizia_id},
        {"$set": {"preventivo_id": prev_id, "preventivo_number": prev_number, "updated_at": now}}
    )

    logger.info(f"Ponte Perizia→Preventivo: {perizia_id} -> {prev_id} ({prev_number})")
    await log_activity(user, "ponte_perizia", "preventivo", prev_id, label=f"Da perizia {perizia.get('number', '')}")

    return {
        "message": f"Preventivo {prev_number} generato da Perizia {perizia.get('number', '')}",
        "preventivo_id": prev_id,
        "preventivo_number": prev_number,
        "totale": round(subtotal + vat, 2),
        "righe": len(lines),
    }
