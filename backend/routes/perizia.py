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
from models.perizia import PeriziaCreate, PeriziaUpdate, CODICI_DANNO, CODICI_DANNO_MAP

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
    """Auto-generate cost items based on damage type, modules, AND selected damage codes."""
    tipo = data.get("tipo_danno", "strutturale")
    prezzo_ml = float(data.get("prezzo_ml_originale", 0))
    coeff = float(data.get("coefficiente_maggiorazione", 20))
    moduli = data.get("moduli", [])
    codici = data.get("codici_danno", [])
    total_ml = sum(float(m.get("lunghezza_ml", 0)) for m in moduli)
    costo_orario = 45.0
    voci = []

    # Resolve selected damage codes
    selected_codes = [CODICI_DANNO_MAP[c] for c in codici if c in CODICI_DANNO_MAP]
    has_struttura = any(c["categoria"] == "Struttura" for c in selected_codes)
    has_ancoraggio = any(c["categoria"] == "Ancoraggio" for c in selected_codes)
    has_protezione = any(c["categoria"] == "Protezione" for c in selected_codes)
    has_sicurezza = any(c["categoria"] == "Sicurezza" for c in selected_codes)
    has_automazione = any(c["categoria"] == "Automazione" for c in selected_codes)

    # If no codes selected, fall back to tipo_danno logic
    if not selected_codes:
        has_struttura = tipo == "strutturale"
        has_protezione = tipo in ("strutturale", "estetico")
        has_automazione = tipo == "automatismi"

    # 1. Smontaggio e Messa in Sicurezza (always)
    ore_smontaggio = max(2, total_ml * 0.5)
    norme_cite = ", ".join(sorted(set(c["norma"] for c in selected_codes))) if selected_codes else "EN 1090-2"
    voci.append({
        "codice": "A.01",
        "descrizione": f"Smontaggio elementi danneggiati e messa in sicurezza dell'area. "
                       f"Codici danno rilevati: {', '.join(codici) if codici else 'generico'}. "
                       f"Comprensivo di movimentazione, protezione zone adiacenti e segnaletica provvisoria.",
        "unita": "ore",
        "quantita": round(ore_smontaggio, 1),
        "prezzo_unitario": costo_orario,
        "totale": round(ore_smontaggio * costo_orario, 2),
    })

    # 2. Struttura: S1-DEF, S2-WELD → Sostituzione modulo
    if has_struttura:
        prezzo_maggiorato = prezzo_ml * (1 + coeff / 100)
        struct_codes = [c for c in selected_codes if c["categoria"] == "Struttura"]
        norme_struct = ", ".join(set(c["norma"] for c in struct_codes)) if struct_codes else "EN 1090-2"
        azioni = " ".join(c["azione"] for c in struct_codes) if struct_codes else "Sostituzione integrale del modulo."
        voci.append({
            "codice": "B.01",
            "descrizione": f"Fornitura recinzione/cancello in acciaio zincato a caldo conforme {norme_struct}. "
                           f"{azioni} "
                           f"Produzione fuori serie con maggiorazione {coeff:.0f}% sul prezzo originale di {prezzo_ml:.2f} EUR/ml. "
                           f"Comprensivo di lavorazione, zincatura e verniciatura.",
            "unita": "ml",
            "quantita": round(total_ml, 2),
            "prezzo_unitario": round(prezzo_maggiorato, 2),
            "totale": round(total_ml * prezzo_maggiorato, 2),
        })

    # 3. Ancoraggio: A1-ANCH, A2-CONC → Rifacimento ancoranti
    if has_ancoraggio:
        anch_codes = [c for c in selected_codes if c["categoria"] == "Ancoraggio"]
        has_conc = any(c["codice"] == "A2-CONC" for c in anch_codes)
        desc_anch = "Rifacimento fori e ancorante chimico certificato ETA (ETAG 001). "
        if has_conc:
            desc_anch += "Ripristino cordolo in cemento con malta tixotropica strutturale. "
        desc_anch += "Verifica tenuta meccanica post-installazione."
        ore_anch = max(2, total_ml * 0.4)
        mat_anch = 15.0 * total_ml if total_ml else 80.0
        voci.append({
            "codice": "B.02",
            "descrizione": desc_anch,
            "unita": "corpo",
            "quantita": 1,
            "prezzo_unitario": round(ore_anch * costo_orario + mat_anch, 2),
            "totale": round(ore_anch * costo_orario + mat_anch, 2),
        })

    # 4. Protezione: P1-ZINC → Trattamento anticorrosivo
    if has_protezione and not has_struttura:
        # Only if not already replacing the whole module
        voci.append({
            "codice": "B.03",
            "descrizione": "Ripristino ciclo anticorrosivo conforme ISO 1461 / ISO 12944. "
                           "Carteggiatura manuale, applicazione primer antiruggine bicomponente e "
                           "mano di finitura con smalto poliuretanico colore a campione. "
                           "Compreso mascheratura aree adiacenti.",
            "unita": "mq",
            "quantita": round(total_ml * 1.2, 2),
            "prezzo_unitario": 35.0,
            "totale": round(total_ml * 1.2 * 35.0, 2),
        })

    # 5. Sicurezza: G1-GAP → Riallineamento
    if has_sicurezza:
        voci.append({
            "codice": "B.04",
            "descrizione": "Riallineamento millimetrico elementi e verifica distanze di sicurezza "
                           "anti-cesoiamento conforme EN 13241. Test spazi con calibro certificato. "
                           "Aggiornamento Dichiarazione di Prestazione (DoP).",
            "unita": "corpo",
            "quantita": 1,
            "prezzo_unitario": 220.0,
            "totale": 220.0,
        })

    # 6. Automazione: M1-FORCE → Test forze e sostituzione
    if has_automazione:
        voci.append({
            "codice": "B.05",
            "descrizione": "Fornitura e sostituzione componenti di automazione danneggiati "
                           "(motore, centralina, fotocellule, finecorsa).",
            "unita": "corpo",
            "quantita": 1,
            "prezzo_unitario": round(prezzo_ml * total_ml * 0.5, 2) if prezzo_ml else 450.0,
            "totale": round(prezzo_ml * total_ml * 0.5, 2) if prezzo_ml else 450.0,
        })
        voci.append({
            "codice": "B.06",
            "descrizione": "Verifica e collaudo impianto automazione conforme EN 12453. "
                           "Test forze di impatto con strumento certificato, verifica dispositivi "
                           "di sicurezza e fotocellule. Rilascio certificato di conformita.",
            "unita": "corpo",
            "quantita": 1,
            "prezzo_unitario": 320.0,
            "totale": 320.0,
        })

    # 7. Trasporto (if structural replacement or significant work)
    if has_struttura or total_ml > 2:
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

    # 8. Installazione (if structural replacement)
    if has_struttura:
        ore_install = max(3, total_ml * 0.8)
        voci.append({
            "codice": "D.01",
            "descrizione": "Installazione e fissaggio con ancoranti chimici certificati ETA. "
                           "Comprensivo di ripristino sigillante elastomerico, allineamento e regolazione.",
            "unita": "ore",
            "quantita": round(ore_install, 1),
            "prezzo_unitario": costo_orario,
            "totale": round(ore_install * costo_orario, 2),
        })

    # 9. Oneri Normativi (if any norm-relevant code selected)
    if has_struttura or has_sicurezza:
        norme_list = sorted(set(c["norma"] for c in selected_codes)) if selected_codes else ["EN 1090-2"]
        voci.append({
            "codice": "E.01",
            "descrizione": f"Revisione Fascicolo Tecnico e aggiornamento Dichiarazione di Prestazione (DoP) "
                           f"come richiesto dal Reg. UE 305/2011 e dalle norme {', '.join(norme_list)}. "
                           f"Comprensivo di certificazione e documentazione per conformita CE.",
            "unita": "corpo",
            "quantita": 1,
            "prezzo_unitario": 280.0,
            "totale": 280.0,
        })

    # 10. Smaltimento (always)
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
        "lettera_accompagnamento": data.lettera_accompagnamento,
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
        "nota_tecnica", "lettera_accompagnamento", "notes", "status",
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
