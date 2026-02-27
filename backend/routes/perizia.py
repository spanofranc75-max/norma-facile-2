"""Perizia Sinistro (Damage Assessment) routes — CRUD + AI Analysis + PDF."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import os
import uuid
import logging
from datetime import datetime, timezone
from core.security import get_current_user
from core.database import db
from models.perizia import PeriziaCreate, PeriziaUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/perizie", tags=["perizie"])

COLLECTION = "perizie"
LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

TIPO_DANNO_LABELS = {
    "strutturale": "Danno Strutturale (EN 1090)",
    "estetico": "Danno Estetico",
    "automatismi": "Danno Automatismi (EN 12453)",
}


async def next_perizia_number(user_id: str) -> str:
    year = datetime.now(timezone.utc).strftime("%Y")
    count = await db[COLLECTION].count_documents({"user_id": user_id})
    return f"PER-{year}/{count + 1:04d}"


def calc_voci_costo(data: dict) -> list:
    """Auto-generate cost items based on damage type and modules."""
    tipo = data.get("tipo_danno", "strutturale")
    prezzo_ml = float(data.get("prezzo_ml_originale", 0))
    coeff = float(data.get("coefficiente_maggiorazione", 20))
    moduli = data.get("moduli", [])
    total_ml = sum(float(m.get("lunghezza_ml", 0)) for m in moduli)

    voci = []

    # 1. Smontaggio e Messa in Sicurezza
    ore_smontaggio = max(2, total_ml * 0.5)
    costo_orario = 45.0
    voci.append({
        "codice": "A.01",
        "descrizione": "Smontaggio elementi danneggiati e messa in sicurezza dell'area. "
                       "Comprensivo di movimentazione, protezione zone adiacenti e segnaletica provvisoria.",
        "unita": "ore",
        "quantita": round(ore_smontaggio, 1),
        "prezzo_unitario": costo_orario,
        "totale": round(ore_smontaggio * costo_orario, 2),
    })

    if tipo == "strutturale":
        # 2. Fornitura Materiale (con maggiorazione fuori serie)
        prezzo_maggiorato = prezzo_ml * (1 + coeff / 100)
        voci.append({
            "codice": "B.01",
            "descrizione": f"Fornitura recinzione/cancello in acciaio zincato a caldo conforme EN 1090. "
                           f"Produzione fuori serie di pezzo singolo con maggiorazione {coeff:.0f}% "
                           f"sul prezzo originale di {prezzo_ml:.2f} EUR/ml. "
                           f"Comprensivo di lavorazione, zincatura e verniciatura.",
            "unita": "ml",
            "quantita": round(total_ml, 2),
            "prezzo_unitario": round(prezzo_maggiorato, 2),
            "totale": round(total_ml * prezzo_maggiorato, 2),
        })

        # 3. Trasporto e Logistica
        costo_trasporto = 180.0 if total_ml <= 2.5 else 350.0
        voci.append({
            "codice": "C.01",
            "descrizione": "Trasporto speciale da officina al cantiere e ritorno. "
                           + ("Trasporto fuori sagoma per elementi > 2,5 m con mezzo dedicato." if total_ml > 2.5 else "Trasporto con mezzo standard."),
            "unita": "corpo",
            "quantita": 1,
            "prezzo_unitario": costo_trasporto,
            "totale": costo_trasporto,
        })

        # 4. Installazione e Fissaggio
        ore_install = max(3, total_ml * 0.8)
        voci.append({
            "codice": "D.01",
            "descrizione": "Installazione e fissaggio con ancoranti chimici certificati ETA. "
                           "Comprensivo di ripristino sigillante elastomerico, allineamento e regolazione. "
                           "Verifica di stabilita e planarità a completamento.",
            "unita": "ore",
            "quantita": round(ore_install, 1),
            "prezzo_unitario": costo_orario,
            "totale": round(ore_install * costo_orario, 2),
        })

        # 5. Oneri Normativi
        voci.append({
            "codice": "E.01",
            "descrizione": "Revisione Fascicolo Tecnico della struttura e aggiornamento della "
                           "Dichiarazione di Prestazione (DoP) come richiesto dal Reg. UE 305/2011 "
                           "e dalla norma EN 1090-1. Comprensivo di certificazione del saldatore e "
                           "documentazione per conformita CE.",
            "unita": "corpo",
            "quantita": 1,
            "prezzo_unitario": 280.0,
            "totale": 280.0,
        })

    elif tipo == "estetico":
        # Carteggiatura e verniciatura
        voci.append({
            "codice": "B.01",
            "descrizione": "Carteggiatura manuale delle superfici danneggiate, applicazione primer "
                           "antiruggine bicomponente e mano di finitura con smalto poliuretanico "
                           "colore a campione. Compreso mascheratura aree adiacenti.",
            "unita": "mq",
            "quantita": round(total_ml * 1.2, 2),
            "prezzo_unitario": 35.0,
            "totale": round(total_ml * 1.2 * 35.0, 2),
        })

    elif tipo == "automatismi":
        # Verifica automazione EN 12453
        voci.append({
            "codice": "B.01",
            "descrizione": "Fornitura e sostituzione componenti di automazione danneggiati "
                           "(motore, centralina, fotocellule, finecorsa). Marca e modello da definire in base "
                           "all'impianto esistente.",
            "unita": "corpo",
            "quantita": 1,
            "prezzo_unitario": round(prezzo_ml * total_ml * 0.5, 2) if prezzo_ml else 450.0,
            "totale": round(prezzo_ml * total_ml * 0.5, 2) if prezzo_ml else 450.0,
        })
        voci.append({
            "codice": "B.02",
            "descrizione": "Verifica e collaudo dell'impianto di automazione conforme EN 12453 "
                           "(forze di impatto, dispositivi di sicurezza, fotocellule). "
                           "Rilascio certificato di conformita.",
            "unita": "corpo",
            "quantita": 1,
            "prezzo_unitario": 320.0,
            "totale": 320.0,
        })

    # 6. Smaltimento (always)
    costo_smaltimento = max(120.0, total_ml * 25.0)
    voci.append({
        "codice": "F.01",
        "descrizione": "Trasporto a discarica autorizzata dei materiali rimossi (codice CER 170405 - "
                       "ferro e acciaio). Comprensivo di oneri di conferimento e documentazione "
                       "formulario rifiuti.",
        "unita": "corpo",
        "quantita": 1,
        "prezzo_unitario": round(costo_smaltimento, 2),
        "totale": round(costo_smaltimento, 2),
    })

    return voci


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
        "descrizione_utente": data.descrizione_utente,
        "prezzo_ml_originale": data.prezzo_ml_originale,
        "coefficiente_maggiorazione": data.coefficiente_maggiorazione,
        "moduli": moduli_dicts,
        "foto": data.foto,
        "ai_analysis": data.ai_analysis,
        "stato_di_fatto": data.stato_di_fatto,
        "nota_tecnica": data.nota_tecnica,
        "voci_costo": voci,
        "total_perizia": round(total_perizia, 2),
        "notes": data.notes,
        "status": "bozza",
        "created_at": now,
        "updated_at": now,
    }
    await db[COLLECTION].insert_one(doc)
    created = await db[COLLECTION].find_one({"perizia_id": perizia_id}, {"_id": 0})
    logger.info(f"Perizia created: {perizia_id} ({number})")
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
        "nota_tecnica", "notes", "status",
    ]
    for field in simple_fields:
        val = getattr(data, field, None)
        if val is not None:
            upd[field] = val

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
    return updated


# ── Delete ──

@router.delete("/{perizia_id}")
async def delete_perizia(perizia_id: str, user: dict = Depends(get_current_user)):
    result = await db[COLLECTION].delete_one(
        {"perizia_id": perizia_id, "user_id": user["user_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(404, "Perizia non trovata")
    return {"message": "Perizia eliminata"}


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

    prompt = f"""Sei un perito tecnico specializzato in carpenteria metallica, recinzioni e cancelli.
Analizza le foto allegate di un sinistro (urto da veicolo) su una recinzione/cancello metallico.

CONTESTO:
- Tipo danno classificato: {tipo_label}
- Localizzazione: {indirizzo}
- Descrizione dell'utente: {descrizione or 'Non fornita'}

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
        for photo_b64 in photos[:5]:
            # Remove data URI prefix if present
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
