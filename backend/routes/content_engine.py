"""
Content Engine — AI-powered content production system.
M1: Content Sources + Idea Generation
M2: Drafts + Editorial Queue
"""
from fastapi import APIRouter, Depends, HTTPException
from core.database import db
from core.security import get_current_user, tenant_match
from datetime import datetime, timezone
import logging
import uuid
import json
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/content", tags=["content"])

COLL_SOURCES = "content_sources"
COLL_IDEAS = "content_ideas"
COLL_DRAFTS = "content_drafts"
COLL_QUEUE = "content_queue"

FORMATS = ["linkedin_post", "reel_short", "carosello", "case_study"]
QUEUE_STATES = ["idea", "draft", "in_review", "approved", "scheduled", "published", "rejected"]


def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accesso riservato agli admin")


def _now():
    return datetime.now(timezone.utc).isoformat()


# ─── M1: Content Sources ──────────────────────────────────────

@router.get("/sources")
async def list_sources(user: dict = Depends(get_current_user)):
    _require_admin(user)
    cursor = db[COLL_SOURCES].find(
        {"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    ).sort("created_at", -1)
    return await cursor.to_list(100)


@router.get("/sources/{source_id}")
async def get_source(source_id: str, user: dict = Depends(get_current_user)):
    _require_admin(user)
    doc = await db[COLL_SOURCES].find_one(
        {"source_id": source_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Sorgente non trovata")
    return doc


@router.post("/sources")
async def create_source(data: dict, user: dict = Depends(get_current_user)):
    _require_admin(user)
    doc = {
        "source_id": f"src_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "code": data.get("code", ""),
        "title": data.get("title", ""),
        "type": data.get("type", "feature"),
        "category": data.get("category", ""),
        "description": data.get("description", ""),
        "target_audience": data.get("target_audience", []),
        "pain_points": data.get("pain_points", []),
        "value_claim": data.get("value_claim", ""),
        "proof_points": data.get("proof_points", []),
        "demo_route": data.get("demo_route", ""),
        "suggested_formats": data.get("suggested_formats", []),
        "active": True,
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db[COLL_SOURCES].insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/sources/{source_id}")
async def update_source(source_id: str, data: dict, user: dict = Depends(get_current_user)):
    _require_admin(user)
    update = {k: v for k, v in data.items() if k not in ("source_id", "user_id", "_id")}
    update["updated_at"] = _now()
    result = await db[COLL_SOURCES].update_one(
        {"source_id": source_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Sorgente non trovata")
    return await get_source(source_id, user)


@router.delete("/sources/{source_id}")
async def delete_source(source_id: str, user: dict = Depends(get_current_user)):
    _require_admin(user)
    result = await db[COLL_SOURCES].delete_one(
        {"source_id": source_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Sorgente non trovata")
    return {"message": "Sorgente eliminata"}


# ─── M1: Idea Generation ──────────────────────────────────────

@router.post("/sources/{source_id}/generate-ideas")
async def generate_ideas(source_id: str, user: dict = Depends(get_current_user)):
    """Generate content ideas from a source using AI."""
    _require_admin(user)

    source = await db[COLL_SOURCES].find_one(
        {"source_id": source_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    )
    if not source:
        raise HTTPException(status_code=404, detail="Sorgente non trovata")

    ideas = await _ai_generate_ideas(source)

    saved = []
    for idea in ideas:
        doc = {
            "idea_id": f"idea_{uuid.uuid4().hex[:12]}",
            "source_id": source_id,
            "user_id": user["user_id"], "tenant_id": tenant_match(user),
            "format": idea.get("format", "linkedin_post"),
            "hook": idea.get("hook", ""),
            "angle": idea.get("angle", ""),
            "target_audience": idea.get("target_audience", ""),
            "brief": idea.get("brief", ""),
            "status": "generated",
            "created_at": _now(),
        }
        await db[COLL_IDEAS].insert_one(doc)
        doc.pop("_id", None)
        saved.append(doc)

    return {"source": source["title"], "ideas_generated": len(saved), "ideas": saved}


@router.get("/ideas")
async def list_ideas(user: dict = Depends(get_current_user), source_id: str = None):
    _require_admin(user)
    query = {"user_id": user["user_id"], "tenant_id": tenant_match(user)}
    if source_id:
        query["source_id"] = source_id
    cursor = db[COLL_IDEAS].find(query, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(200)


@router.delete("/ideas/{idea_id}")
async def delete_idea(idea_id: str, user: dict = Depends(get_current_user)):
    _require_admin(user)
    result = await db[COLL_IDEAS].delete_one(
        {"idea_id": idea_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Idea non trovata")
    return {"message": "Idea eliminata"}


# ─── M2: Draft Generation ─────────────────────────────────────

@router.post("/ideas/{idea_id}/generate-draft")
async def generate_draft(idea_id: str, user: dict = Depends(get_current_user)):
    """Generate a full content draft from an idea using AI."""
    _require_admin(user)

    idea = await db[COLL_IDEAS].find_one(
        {"idea_id": idea_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    )
    if not idea:
        raise HTTPException(status_code=404, detail="Idea non trovata")

    source = await db[COLL_SOURCES].find_one(
        {"source_id": idea["source_id"], "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    )

    draft_content = await _ai_generate_draft(idea, source)

    doc = {
        "draft_id": f"draft_{uuid.uuid4().hex[:12]}",
        "idea_id": idea_id,
        "source_id": idea.get("source_id"),
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "channel": _format_to_channel(idea.get("format", "")),
        "format": idea.get("format", ""),
        "title": draft_content.get("title", ""),
        "body": draft_content.get("body", ""),
        "cta": draft_content.get("cta", ""),
        "hashtags": draft_content.get("hashtags", []),
        "slides": draft_content.get("slides", []),
        "suggested_asset_type": draft_content.get("suggested_asset_type", ""),
        "suggested_demo_route": source.get("demo_route", "") if source else "",
        "status": "draft",
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db[COLL_DRAFTS].insert_one(doc)
    doc.pop("_id", None)

    # Update idea status
    await db[COLL_IDEAS].update_one(
        {"idea_id": idea_id}, {"$set": {"status": "draft_generated"}}
    )

    return doc


@router.get("/drafts")
async def list_drafts(user: dict = Depends(get_current_user), status: str = None):
    _require_admin(user)
    query = {"user_id": user["user_id"], "tenant_id": tenant_match(user)}
    if status:
        query["status"] = status
    cursor = db[COLL_DRAFTS].find(query, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(200)


@router.get("/drafts/{draft_id}")
async def get_draft(draft_id: str, user: dict = Depends(get_current_user)):
    _require_admin(user)
    doc = await db[COLL_DRAFTS].find_one(
        {"draft_id": draft_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Bozza non trovata")
    return doc


@router.put("/drafts/{draft_id}")
async def update_draft(draft_id: str, data: dict, user: dict = Depends(get_current_user)):
    _require_admin(user)
    update = {k: v for k, v in data.items() if k not in ("draft_id", "user_id", "_id")}
    update["updated_at"] = _now()
    result = await db[COLL_DRAFTS].update_one(
        {"draft_id": draft_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Bozza non trovata")
    return await get_draft(draft_id, user)


@router.delete("/drafts/{draft_id}")
async def delete_draft(draft_id: str, user: dict = Depends(get_current_user)):
    _require_admin(user)
    result = await db[COLL_DRAFTS].delete_one(
        {"draft_id": draft_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bozza non trovata")
    # Also remove from queue
    await db[COLL_QUEUE].delete_many(
        {"draft_id": draft_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
    )
    return {"message": "Bozza eliminata"}


# ─── M2: Editorial Queue ──────────────────────────────────────

@router.post("/queue")
async def add_to_queue(data: dict, user: dict = Depends(get_current_user)):
    _require_admin(user)
    draft_id = data.get("draft_id")
    if not draft_id:
        raise HTTPException(status_code=400, detail="draft_id richiesto")
    draft = await db[COLL_DRAFTS].find_one(
        {"draft_id": draft_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    )
    if not draft:
        raise HTTPException(status_code=404, detail="Bozza non trovata")

    doc = {
        "queue_id": f"q_{uuid.uuid4().hex[:12]}",
        "draft_id": draft_id,
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "channel": data.get("channel", draft.get("channel", "linkedin")),
        "scheduled_for": data.get("scheduled_for"),
        "status": "in_review",
        "approved_by": None,
        "notes": data.get("notes", ""),
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db[COLL_QUEUE].insert_one(doc)
    doc.pop("_id", None)

    # Update draft status
    await db[COLL_DRAFTS].update_one(
        {"draft_id": draft_id}, {"$set": {"status": "queued", "updated_at": _now()}}
    )

    return doc


@router.get("/queue")
async def list_queue(user: dict = Depends(get_current_user), status: str = None, channel: str = None):
    _require_admin(user)
    query = {"user_id": user["user_id"], "tenant_id": tenant_match(user)}
    if status:
        query["status"] = status
    if channel:
        query["channel"] = channel
    cursor = db[COLL_QUEUE].find(query, {"_id": 0}).sort("created_at", -1)
    items = await cursor.to_list(200)

    # Enrich with draft data
    for item in items:
        draft = await db[COLL_DRAFTS].find_one(
            {"draft_id": item.get("draft_id")}, {"_id": 0, "title": 1, "format": 1, "body": 1}
        )
        if draft:
            item["draft_title"] = draft.get("title", "")
            item["draft_format"] = draft.get("format", "")
    return items


@router.put("/queue/{queue_id}")
async def update_queue_item(queue_id: str, data: dict, user: dict = Depends(get_current_user)):
    _require_admin(user)
    update = {k: v for k, v in data.items() if k not in ("queue_id", "user_id", "_id")}
    update["updated_at"] = _now()

    new_status = data.get("status")
    if new_status == "approved":
        update["approved_by"] = user["user_id"]

    result = await db[COLL_QUEUE].update_one(
        {"queue_id": queue_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Elemento coda non trovato")

    doc = await db[COLL_QUEUE].find_one({"queue_id": queue_id}, {"_id": 0})
    return doc


@router.delete("/queue/{queue_id}")
async def remove_from_queue(queue_id: str, user: dict = Depends(get_current_user)):
    _require_admin(user)
    result = await db[COLL_QUEUE].delete_one(
        {"queue_id": queue_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Elemento non trovato")
    return {"message": "Rimosso dalla coda"}


# ─── Stats ─────────────────────────────────────────────────────

@router.get("/stats")
async def content_stats(user: dict = Depends(get_current_user)):
    _require_admin(user)
    uid = user["user_id"]
    tid = user["tenant_id"]
    return {
        "sources": await db[COLL_SOURCES].count_documents({"user_id": uid, "tenant_id": tenant_match(user)}),
        "ideas": await db[COLL_IDEAS].count_documents({"user_id": uid, "tenant_id": tenant_match(user)}),
        "drafts": await db[COLL_DRAFTS].count_documents({"user_id": uid, "tenant_id": tenant_match(user)}),
        "queue_total": await db[COLL_QUEUE].count_documents({"user_id": uid, "tenant_id": tenant_match(user)}),
        "queue_in_review": await db[COLL_QUEUE].count_documents({"user_id": uid, "tenant_id": tenant_match(user), "status": "in_review"}),
        "queue_approved": await db[COLL_QUEUE].count_documents({"user_id": uid, "tenant_id": tenant_match(user), "status": "approved"}),
        "queue_published": await db[COLL_QUEUE].count_documents({"user_id": uid, "tenant_id": tenant_match(user), "status": "published"}),
    }


# ─── AI Functions ──────────────────────────────────────────────

def _format_to_channel(fmt: str) -> str:
    mapping = {
        "linkedin_post": "linkedin",
        "reel_short": "social_video",
        "carosello": "social_carousel",
        "case_study": "blog",
    }
    return mapping.get(fmt, "linkedin")


async def _ai_generate_ideas(source: dict) -> list:
    """Use GPT-4o to generate content ideas from a source."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError:
        logger.warning("emergentintegrations not available")
        return _fallback_ideas(source)

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return _fallback_ideas(source)

    system = """Sei un content strategist B2B che lavora nel settore carpenteria metallica. Conosci bene EN 1090, EN 13241, sicurezza cantiere, uffici tecnici, titolari di officina.

Genera idee contenuto per 1090 Norma Facile — sistema operativo verticale per carpenteria metallica.

STILE OBBLIGATORIO:
- Scrivi come chi lavora davvero nel settore, non come un'agenzia marketing
- Ogni hook deve nominare un problema concreto, non un concetto astratto
- Usa il lessico di officina, cantiere, ufficio tecnico: "commessa", "emissione", "POS", "certificato 3.1", "preposto", "DPI", "fascicolo"
- Niente hype, niente frasi da brochure, niente tono da guru SaaS
- Il prodotto entra come strumento operativo, non come slogan
- Parti dal dolore quotidiano, non dalla feature

ESEMPI DI HOOK BUONI:
- "Il problema non e avere tanti documenti. E non sapere cosa manca davvero per mandare avanti una commessa."
- "Il POS non dovrebbe partire da un vecchio file Word. Dovrebbe partire dalla commessa vera."
- "Una commessa non si blocca all'improvviso. Di solito i segnali c'erano gia, solo che erano sparsi."

ESEMPI DI HOOK DA EVITARE:
- "Trasforma il tuo workflow con la nostra soluzione innovativa"
- "Scopri come l'AI rivoluziona la gestione documentale"
- "Il futuro della carpenteria e qui"

Rispondi SOLO con un JSON array. Ogni elemento ha:
{
  "format": "linkedin_post" | "reel_short" | "carosello" | "case_study",
  "hook": "frase d'apertura che cattura",
  "angle": "pain_point" | "before_after" | "how_to" | "common_mistake" | "insight",
  "target_audience": "titolare" | "ufficio_tecnico" | "sicurezza" | "qualita",
  "brief": "breve descrizione dell'idea in 1-2 frasi"
}

Genera esattamente 7 idee: 3 linkedin_post, 2 reel_short, 1 carosello, 1 case_study."""

    prompt = f"""Sorgente contenuto:
Titolo: {source.get('title', '')}
Tipo: {source.get('type', '')}
Descrizione: {source.get('description', '')}
Pain points: {', '.join(source.get('pain_points', []))}
Valore: {source.get('value_claim', '')}
Prove: {', '.join(source.get('proof_points', []))}
Target: {', '.join(source.get('target_audience', []))}

Genera 7 idee contenuto diverse."""

    chat = LlmChat(
        api_key=api_key,
        session_id=f"content-ideas-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("openai", "gpt-4o")

    try:
        response = await chat.send_message(UserMessage(text=prompt))
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"AI idea generation failed: {e}")
        return _fallback_ideas(source)


async def _ai_generate_draft(idea: dict, source: dict | None) -> dict:
    """Use GPT-4o to generate a full content draft."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError:
        return _fallback_draft(idea)

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return _fallback_draft(idea)

    fmt = idea.get("format", "linkedin_post")

    format_instructions = {
        "linkedin_post": """Scrivi un post LinkedIn (800-1400 caratteri).

STRUTTURA OBBLIGATORIA:
1. HOOK: una frase secca che nomina un problema concreto
2. PROBLEMA: frasi corte, spesso frammenti. Elenchi con trattino. Esempi reali dal settore.
3. TRANSIZIONE: "Per questo in 1090 Norma Facile abbiamo costruito..." — il prodotto entra tardi, dopo il problema
4. COME FUNZIONA: spiegazione operativa, non lista di feature. Il sistema fa X, poi Y, il risultato e Z.
5. VALORE PRATICO: cosa cambia davvero nel lavoro quotidiano. Frase che chiude il cerchio.
6. CTA: breve, conversazionale, tipo "Se vuoi, posso mostrarti..."

STILE:
- Frasi corte, anche frammentate
- Elenchi con trattino e a capo
- Lessico da officina/cantiere: "commessa", "emissione", "POS", "certificato 3.1", "preposto", "DPI"
- Il prodotto e uno strumento operativo, non una "soluzione innovativa"
- Mai sembrare scritto da un'agenzia. Deve sembrare scritto da chi ci lavora
- Bold (**testo**) solo per le frasi chiave, massimo 2-3 nel post

BENCHMARK 1 (Registro Obblighi — tono da seguire):
---
Il problema non e avere tanti documenti. E non sapere cosa manca davvero per mandare avanti una commessa.

Nelle carpenterie il problema raramente e "fare il lavoro".
Il problema e tutto quello che gira intorno alla commessa e che salta fuori troppo tardi.

Un certificato 3.1 che manca.
Un POS non ancora pronto.
Un preposto non assegnato.
Un'emissione bloccata perche manca un controllo.
Un cliente che chiede documenti quando il cantiere deve partire.

Quando queste informazioni stanno sparse tra email, PDF, Word, Excel e memoria delle persone, la commessa va avanti lo stesso — ma senza controllo vero.

Per questo in 1090 Norma Facile abbiamo costruito un Registro Obblighi Commessa.

Non e una lista manuale di task.
E un punto unico che raccoglie automaticamente cio che manca, cio che blocca e cio che richiede attenzione da piu fonti del sistema:
- evidence gate
- POS e sicurezza
- documenti in scadenza
- pacchetti documentali
- istruttoria
- richieste della committenza

Il risultato pratico e semplice:
apri la commessa e vedi subito
- cosa e bloccante
- cosa e da completare
- chi se ne deve occupare
- entro quando

Per chi lavora davvero su commesse EN 1090, cantieri, documenti cliente e sicurezza, questa visibilita cambia molto piu di quanto sembri.

Perche il guadagno non e solo "ordine".
E evitare di scoprire i problemi quando sei gia in ritardo.

CTA: Se vuoi, posso mostrarti come funziona su una commessa demo reale.
---

BENCHMARK 2 (POS dinamico — tono prima/dopo):
---
Il POS non dovrebbe partire da un vecchio file Word. Dovrebbe partire dalla commessa vera.

Chi lavora tra ufficio tecnico e cantiere lo sa bene:
quando arriva il momento di preparare il POS, spesso si riparte da un documento vecchio, si fa "salva con nome" e si comincia a correggere a mano.

Indirizzo cantiere. Committente. Figure coinvolte. Lavori in quota. Saldatura in opera. Autogru. DPI. Allegati.

Il problema non e solo il tempo che si perde.
Il problema e che in quel passaggio si dimentica facilmente qualcosa.

Un preposto non aggiornato. Un rischio lasciato generico. Una lavorazione in quota non confermata bene. Un allegato sicurezza che manca.

Con 1090 Norma Facile abbiamo impostato il POS in modo diverso.

La logica e questa:
- parti dalla commessa
- colleghi la scheda cantiere
- il sistema precompila cio che riesce a dedurre
- attiva rischi, DPI e misure in base alle lavorazioni
- ti lascia solo le conferme ad alto impatto
- genera una bozza POS DOCX da revisionare, non un documento "magico" da firmare al buio

Questo cambia molto il lavoro dell'ufficio tecnico.

Perche il POS smette di essere un file da rincorrere
e diventa una conseguenza ordinata di quello che hai gia capito della commessa.

CTA: Se vuoi, posso farti vedere un esempio reale di POS generato da una commessa demo.
---

BENCHMARK 3 (Dashboard Cantiere — tono executive):
---
Una commessa non si blocca all'improvviso. Di solito i segnali c'erano gia, solo che erano sparsi.

Nelle commesse tecniche il problema non e quasi mai un solo errore grosso.
Sono tanti piccoli segnali che si accumulano:
- un'emissione bloccata
- un POS non pronto
- un documento cliente ancora da mandare
- un attestato in scadenza
- un obbligo aperto che nessuno ha chiuso
- una richiesta del committente rimasta in sospeso

Quando questi segnali stanno in moduli diversi, o peggio ancora fuori dal sistema, il titolare li scopre tardi. Spesso troppo tardi.

Per questo abbiamo costruito una Dashboard Cantiere Multilivello.

Non e solo un cruscotto con numeri.
E una vista che ti permette di leggere la commessa su piu livelli:
- stato generale
- obblighi bloccanti
- rami normativi
- emissioni
- sicurezza e POS
- documenti e richieste del cliente

Il vantaggio vero non e "vedere piu grafici".
E capire in pochi secondi:
- cosa e pronto
- cosa e fermo
- cosa manca
- chi deve muoversi

Per chi gestisce carpenteria, documenti tecnici, cantiere e richieste cliente, questa visibilita vale molto.
Perche riduce una cosa che pesa ogni giorno: lavorare inseguendo problemi gia nati ma ancora invisibili.

CTA: Se vuoi, posso mostrarti come leggiamo una commessa demo in meno di 5 minuti.
---

Scrivi ESATTAMENTE nello stesso stile dei benchmark. Stessa lunghezza, stesse strutture, stesso lessico.""",

        "reel_short": """Scrivi uno script per un video breve (30-60 secondi).
Struttura: HOOK (3 sec) -> PROBLEMA (10 sec) -> DEMO/SOLUZIONE (20 sec) -> CTA (5 sec).
Indica le scene con timestamp e azione visiva.
Tono: sobrio, concreto, da chi ci lavora. Mai sembrare una pubblicita.""",

        "carosello": """Scrivi il testo per un carosello di 5-7 slide.
Slide 1: hook forte che nomina un problema concreto.
Slide 2-4: un problema per slide, con esempio reale (non concetto astratto).
Slide 5-6: come 1090 Norma Facile risolve, in modo operativo.
Slide finale: CTA conversazionale breve.
Formato: array di oggetti {{"title": "", "body": ""}}.
Tono: sobrio, concreto, lessico da cantiere/officina.""",

        "case_study": """Scrivi un caso studio breve (400-600 parole).
Struttura: Contesto -> Sfida concreta -> Cosa fa il sistema -> Risultati (stime prudenziali, mai numeri inventati) -> Cosa cambia.
Usa "stima interna", "caso pilota", range prudenziali.
Mai "ROI garantito" o "riduzione certa del X%".
Il caso deve sembrare scritto da chi ha visto il problema, non da un'agenzia.""",
    }

    system = f"""Sei un copywriter che lavora nel settore carpenteria metallica italiana. Non sei un'agenzia marketing.
Scrivi contenuti per 1090 Norma Facile, sistema operativo verticale per EN 1090, EN 13241, sicurezza cantiere.

REGOLE DI STILE (TASSATIVE):
- Scrivi come chi lavora davvero nel settore, non come un copywriter
- Frasi corte, spesso frammentate. Elenchi con trattino e a capo.
- Il problema viene PRIMA, il prodotto entra DOPO
- Esempi concreti dal settore: certificato 3.1, POS, preposto, DPI, emissione, fascicolo, commessa mista
- Il prodotto e uno strumento operativo, non una "soluzione innovativa"
- Non usare mai: "innovativo", "rivoluzionario", "all-in-one", "game-changer", "ROI garantito"
- CTA breve e conversazionale: "Se vuoi, posso mostrarti..."
- Hashtag specifici del settore: #EN1090 #CarpenteriaMetallica #SicurezzaCantiere

TARGET: titolari officina, uffici tecnici, responsabili qualita e sicurezza.

{format_instructions.get(fmt, format_instructions['linkedin_post'])}

Rispondi SOLO con un JSON:
{{
  "title": "titolo del contenuto",
  "body": "testo completo",
  "cta": "call to action finale",
  "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "slides": [solo per carosello: {{"title": "", "body": ""}}],
  "suggested_asset_type": "screen_recording" | "screenshot" | "infographic" | "video_demo"
}}"""

    source_ctx = ""
    if source:
        source_ctx = f"""
Sorgente: {source.get('title', '')}
Descrizione: {source.get('description', '')}
Pain points: {', '.join(source.get('pain_points', []))}
Valore: {source.get('value_claim', '')}"""

    prompt = f"""Idea contenuto:
Formato: {fmt}
Hook: {idea.get('hook', '')}
Angolo: {idea.get('angle', '')}
Target: {idea.get('target_audience', '')}
Brief: {idea.get('brief', '')}
{source_ctx}

Genera il contenuto completo."""

    chat = LlmChat(
        api_key=api_key,
        session_id=f"content-draft-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("openai", "gpt-4o")

    try:
        response = await chat.send_message(UserMessage(text=prompt))
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"AI draft generation failed: {e}")
        return _fallback_draft(idea)


def _fallback_ideas(source: dict) -> list:
    """Fallback when AI is not available."""
    title = source.get("title", "Feature")
    return [
        {"format": "linkedin_post", "hook": f"Sai cosa succede quando {title} non funziona?", "angle": "pain_point", "target_audience": "titolare", "brief": f"Post su problemi risolti da {title}"},
        {"format": "linkedin_post", "hook": f"Prima: Excel e carta. Dopo: {title}.", "angle": "before_after", "target_audience": "ufficio_tecnico", "brief": "Confronto prima/dopo"},
        {"format": "reel_short", "hook": f"30 secondi per capire {title}", "angle": "how_to", "target_audience": "titolare", "brief": "Demo rapida"},
    ]


def _fallback_draft(idea: dict) -> dict:
    """Fallback draft when AI is not available."""
    return {
        "title": idea.get("hook", "Bozza contenuto"),
        "body": f"Bozza generata per: {idea.get('brief', '')}. [Contenuto da completare manualmente]",
        "cta": "Scopri di piu su 1090 Norma Facile",
        "hashtags": ["#en1090", "#carpenteriametallica", "#normafacile"],
        "slides": [],
        "suggested_asset_type": "screenshot",
    }



# ─── Seed Sources ──────────────────────────────────────────────

@router.post("/seed-sources")
async def seed_content_sources(user: dict = Depends(get_current_user)):
    """Pre-load 10 content sources. Admin only. Upsert by title."""
    _require_admin(user)

    from scripts.content_sources_seed import CONTENT_SOURCES_SEED

    seeded = 0
    updated = 0
    for src in CONTENT_SOURCES_SEED:
        exists = await db[COLL_SOURCES].find_one(
            {"user_id": user["user_id"], "tenant_id": tenant_match(user), "title": src["title"]}
        )
        if exists:
            # Upsert: update existing with new detailed data
            update_data = {k: v for k, v in src.items() if k != "title"}
            update_data["updated_at"] = _now()
            await db[COLL_SOURCES].update_one(
                {"source_id": exists["source_id"]},
                {"$set": update_data}
            )
            updated += 1
        else:
            doc = {
                "source_id": f"src_{uuid.uuid4().hex[:12]}",
                "user_id": user["user_id"], "tenant_id": tenant_match(user),
                **src,
                "active": True,
                "created_at": _now(),
                "updated_at": _now(),
            }
            await db[COLL_SOURCES].insert_one(doc)
            seeded += 1

    total = await db[COLL_SOURCES].count_documents({"user_id": user["user_id"], "tenant_id": tenant_match(user)})
    return {"message": "Seed completato", "seeded": seeded, "updated": updated, "total": total}
