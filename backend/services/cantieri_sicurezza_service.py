"""
Cantieri Sicurezza Service — Safety Branch MVP
================================================
Core logic for:
  - cantieri_sicurezza collection (Safety Site Sheets)
  - libreria_rischi collection (Risk Library)
  - gate_pos (completeness check for POS generation)
  - AI Safety Engine integration
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from core.database import db

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
#  SEED DATA — Libreria Rischi Iniziale
# ═══════════════════════════════════════════════════════════════════

DPI_SEED = [
    {"codice": "DPI-CASCO", "nome": "Casco protettivo", "rif_normativo": "UNI EN 397 - Art 75-77-78 D.Lgs 81/08"},
    {"codice": "DPI-GUANTI-CROSTA", "nome": "Guanti in crosta", "rif_normativo": "UNI EN 388 - Art 75-77-78 D.Lgs 81/08"},
    {"codice": "DPI-GUANTI-CALORE", "nome": "Guanti protezione calore", "rif_normativo": "UNI EN 407 - Art 75-77-78 D.Lgs 81/08"},
    {"codice": "DPI-SCARPE", "nome": "Scarpe antinfortunistiche", "rif_normativo": "UNI EN ISO 20344 - Art 75-77-78 D.Lgs 81/08"},
    {"codice": "DPI-OCCHIALI", "nome": "Occhiali di protezione", "rif_normativo": "UNI EN 166 - Art 75-77-78 D.Lgs 81/08"},
    {"codice": "DPI-SCHERMO-SALD", "nome": "Schermo saldatura", "rif_normativo": "UNI EN 169/175 - Art 75-77-78 D.Lgs 81/08"},
    {"codice": "DPI-CUFFIE", "nome": "Cuffie/tappi auricolari", "rif_normativo": "UNI EN 352 - Art 75-77-78 D.Lgs 81/08"},
    {"codice": "DPI-MASCHERA", "nome": "Maschera antipolvere/filtro", "rif_normativo": "UNI EN 149 - Art 75-77-78 D.Lgs 81/08"},
    {"codice": "DPI-CINTURA", "nome": "Cintura anticaduta", "rif_normativo": "UNI EN 361/362 - Art 75-77-78 D.Lgs 81/08"},
    {"codice": "DPI-TUTA", "nome": "Tuta di protezione", "rif_normativo": "UNI EN 340 - Art 75-77-78 D.Lgs 81/08"},
]

FASI_LAVORO_SEED = [
    {
        "codice": "FL-001",
        "nome": "Taglio e preparazione lamiere/profili",
        "categoria": "carpenteria_metallica",
        "applicabile_a": ["EN_1090", "EN_13241", "GENERICA"],
        "rischi_associati": [
            {"descrizione": "Proiezione di schegge e detriti", "probabilita_default": "Medio Alta", "danno_default": "Notevole", "classe_default": "Grave"},
            {"descrizione": "Rumore", "probabilita_default": "Elevata", "danno_default": "Modesta", "classe_default": "Grave"},
            {"descrizione": "Vibrazioni meccaniche", "probabilita_default": "Medio Alta", "danno_default": "Modesta", "classe_default": "Modesto"},
            {"descrizione": "Tagli e abrasioni", "probabilita_default": "Medio Alta", "danno_default": "Modesta", "classe_default": "Modesto"},
        ],
        "misure_prevenzione": [
            "Utilizzare sempre i DPI previsti",
            "Verificare lo stato degli utensili prima dell'uso",
            "Delimitare l'area di lavoro",
            "Attenersi alle procedure operative specifiche",
        ],
        "dpi_richiesti": ["DPI-OCCHIALI", "DPI-GUANTI-CROSTA", "DPI-SCARPE", "DPI-CUFFIE", "DPI-TUTA"],
        "macchine_tipiche": ["Sega circolare", "Flessibile", "Cesoie"],
    },
    {
        "codice": "FL-002",
        "nome": "Saldatura (MIG/MAG, TIG, Elettrodo)",
        "categoria": "saldatura",
        "applicabile_a": ["EN_1090", "GENERICA"],
        "rischi_associati": [
            {"descrizione": "Radiazioni UV/IR", "probabilita_default": "Elevata", "danno_default": "Notevole", "classe_default": "Gravissimo"},
            {"descrizione": "Fumi di saldatura", "probabilita_default": "Elevata", "danno_default": "Notevole", "classe_default": "Gravissimo"},
            {"descrizione": "Ustioni", "probabilita_default": "Medio Alta", "danno_default": "Modesta", "classe_default": "Modesto"},
            {"descrizione": "Incendio", "probabilita_default": "Medio Bassa", "danno_default": "Ingente", "classe_default": "Grave"},
        ],
        "misure_prevenzione": [
            "Utilizzare schermi e maschere per saldatura omologate",
            "Garantire adeguata ventilazione/aspirazione fumi",
            "Allontanare materiali infiammabili dall'area di saldatura",
            "Predisporre estintore nelle vicinanze",
        ],
        "dpi_richiesti": ["DPI-SCHERMO-SALD", "DPI-GUANTI-CALORE", "DPI-SCARPE", "DPI-MASCHERA", "DPI-TUTA"],
        "macchine_tipiche": ["Saldatrice MIG/MAG", "Saldatrice TIG", "Saldatrice ad elettrodo"],
    },
    {
        "codice": "FL-003",
        "nome": "Montaggio strutture in cantiere",
        "categoria": "montaggio",
        "applicabile_a": ["EN_1090", "GENERICA"],
        "rischi_associati": [
            {"descrizione": "Caduta dall'alto", "probabilita_default": "Medio Alta", "danno_default": "Ingente", "classe_default": "Gravissimo"},
            {"descrizione": "Caduta materiali dall'alto", "probabilita_default": "Medio Alta", "danno_default": "Notevole", "classe_default": "Grave"},
            {"descrizione": "Urti, colpi, impatti", "probabilita_default": "Medio Alta", "danno_default": "Modesta", "classe_default": "Modesto"},
            {"descrizione": "Schiacciamento", "probabilita_default": "Medio Bassa", "danno_default": "Ingente", "classe_default": "Grave"},
        ],
        "misure_prevenzione": [
            "Utilizzare ponteggi e trabattelli regolamentari",
            "Cintura di sicurezza con fune di trattenuta",
            "Delimitare la zona sottostante il montaggio",
            "Imbracatura sicura dei carichi da sollevare",
        ],
        "dpi_richiesti": ["DPI-CASCO", "DPI-CINTURA", "DPI-SCARPE", "DPI-GUANTI-CROSTA"],
        "macchine_tipiche": ["Gru", "Autogrù", "Avvitatore elettrico", "Trapano"],
    },
    {
        "codice": "FL-004",
        "nome": "Movimentazione e trasporto materiali",
        "categoria": "movimentazione",
        "applicabile_a": ["EN_1090", "EN_13241", "GENERICA"],
        "rischi_associati": [
            {"descrizione": "Movimentazione manuale dei carichi", "probabilita_default": "Medio Alta", "danno_default": "Modesta", "classe_default": "Modesto"},
            {"descrizione": "Investimento", "probabilita_default": "Medio Bassa", "danno_default": "Ingente", "classe_default": "Grave"},
            {"descrizione": "Schiacciamento", "probabilita_default": "Medio Bassa", "danno_default": "Notevole", "classe_default": "Modesto"},
        ],
        "misure_prevenzione": [
            "Utilizzare mezzi meccanici per carichi pesanti",
            "Percorsi obbligati e segnalati per mezzi e addetti",
            "Formazione sulla corretta movimentazione dei carichi",
        ],
        "dpi_richiesti": ["DPI-CASCO", "DPI-SCARPE", "DPI-GUANTI-CROSTA"],
        "macchine_tipiche": ["Carrello elevatore", "Carroponte", "Transpallet"],
    },
    {
        "codice": "FL-005",
        "nome": "Verniciatura / Trattamenti superficiali",
        "categoria": "verniciatura",
        "applicabile_a": ["EN_1090", "EN_13241", "GENERICA"],
        "rischi_associati": [
            {"descrizione": "Inalazione solventi/vapori", "probabilita_default": "Elevata", "danno_default": "Notevole", "classe_default": "Gravissimo"},
            {"descrizione": "Contatto cutaneo con sostanze chimiche", "probabilita_default": "Medio Alta", "danno_default": "Modesta", "classe_default": "Modesto"},
            {"descrizione": "Incendio/esplosione", "probabilita_default": "Medio Bassa", "danno_default": "Ingente", "classe_default": "Grave"},
        ],
        "misure_prevenzione": [
            "Garantire ventilazione forzata nell'area di verniciatura",
            "Vietare fiamme libere nella zona",
            "Utilizzare solo quantitativi strettamente necessari",
            "Conservare recipienti chiusi",
        ],
        "dpi_richiesti": ["DPI-MASCHERA", "DPI-GUANTI-CROSTA", "DPI-OCCHIALI", "DPI-TUTA"],
        "macchine_tipiche": ["Pistola a spruzzo", "Compressore"],
    },
    {
        "codice": "FL-006",
        "nome": "Foratura e lavorazione meccanica",
        "categoria": "lavorazione_meccanica",
        "applicabile_a": ["EN_1090", "GENERICA"],
        "rischi_associati": [
            {"descrizione": "Proiezione trucioli", "probabilita_default": "Medio Alta", "danno_default": "Notevole", "classe_default": "Grave"},
            {"descrizione": "Impigliamento", "probabilita_default": "Medio Bassa", "danno_default": "Notevole", "classe_default": "Modesto"},
            {"descrizione": "Rumore", "probabilita_default": "Medio Alta", "danno_default": "Modesta", "classe_default": "Modesto"},
        ],
        "misure_prevenzione": [
            "Verificare protezioni degli organi lavoratori",
            "Non rimuovere dispositivi di sicurezza",
            "Indossare indumenti aderenti, rimuovere anelli e catene",
        ],
        "dpi_richiesti": ["DPI-OCCHIALI", "DPI-GUANTI-CROSTA", "DPI-SCARPE", "DPI-CUFFIE"],
        "macchine_tipiche": ["Trapano a colonna", "Fresatrice", "Trapano elettrico"],
    },
    {
        "codice": "FL-007",
        "nome": "Piegatura e calandratura",
        "categoria": "lavorazione_meccanica",
        "applicabile_a": ["EN_1090", "GENERICA"],
        "rischi_associati": [
            {"descrizione": "Schiacciamento", "probabilita_default": "Medio Alta", "danno_default": "Ingente", "classe_default": "Gravissimo"},
            {"descrizione": "Cesoiamento", "probabilita_default": "Medio Bassa", "danno_default": "Ingente", "classe_default": "Grave"},
            {"descrizione": "Vibrazioni", "probabilita_default": "Medio Bassa", "danno_default": "Modesta", "classe_default": "Accettabile"},
        ],
        "misure_prevenzione": [
            "Verificare il funzionamento dei dispositivi di arresto di emergenza",
            "Non introdurre le mani nella zona operativa",
            "Utilizzare ausili meccanici per il posizionamento dei pezzi",
        ],
        "dpi_richiesti": ["DPI-GUANTI-CROSTA", "DPI-SCARPE", "DPI-OCCHIALI"],
        "macchine_tipiche": ["Pressa piegatrice", "Calandra"],
    },
    {
        "codice": "FL-008",
        "nome": "Consolidamento aperture / cerchiatura",
        "categoria": "edilizia_strutturale",
        "applicabile_a": ["GENERICA"],
        "rischi_associati": [
            {"descrizione": "Rumore", "probabilita_default": "Medio Alta", "danno_default": "Modesta", "classe_default": "Modesto"},
            {"descrizione": "Proiezione di schegge e detriti", "probabilita_default": "Medio Alta", "danno_default": "Notevole", "classe_default": "Grave"},
            {"descrizione": "Vibrazioni meccaniche", "probabilita_default": "Medio Alta", "danno_default": "Notevole", "classe_default": "Grave"},
            {"descrizione": "Movimentazione manuale dei carichi", "probabilita_default": "Medio Alta", "danno_default": "Trascurabile", "classe_default": "Accettabile"},
        ],
        "misure_prevenzione": [
            "Utilizzare sempre i DPI previsti",
            "Vietare la sosta di persone non addette ai lavori",
            "Verificare l'uso costante dei DPI",
        ],
        "dpi_richiesti": ["DPI-CASCO", "DPI-TUTA", "DPI-SCARPE", "DPI-GUANTI-CROSTA", "DPI-OCCHIALI"],
        "macchine_tipiche": ["Attrezzi manuali", "Avvitatori", "Trapani"],
    },
    {
        "codice": "FL-009",
        "nome": "Installazione cancelli/portoni",
        "categoria": "montaggio_en13241",
        "applicabile_a": ["EN_13241"],
        "rischi_associati": [
            {"descrizione": "Caduta dall'alto", "probabilita_default": "Medio Bassa", "danno_default": "Ingente", "classe_default": "Grave"},
            {"descrizione": "Schiacciamento", "probabilita_default": "Medio Alta", "danno_default": "Notevole", "classe_default": "Grave"},
            {"descrizione": "Rischio elettrico", "probabilita_default": "Medio Bassa", "danno_default": "Ingente", "classe_default": "Grave"},
            {"descrizione": "Tagli", "probabilita_default": "Medio Alta", "danno_default": "Modesta", "classe_default": "Modesto"},
        ],
        "misure_prevenzione": [
            "Sezionare l'alimentazione elettrica prima di operare",
            "Utilizzare ponteggi/trabattelli per lavori in quota",
            "Verificare la stabilita dei componenti prima del fissaggio",
        ],
        "dpi_richiesti": ["DPI-CASCO", "DPI-SCARPE", "DPI-GUANTI-CROSTA", "DPI-CINTURA"],
        "macchine_tipiche": ["Avvitatore elettrico", "Trapano", "Flessibile", "Saldatrice"],
    },
    {
        "codice": "FL-010",
        "nome": "Collaudo e messa in esercizio",
        "categoria": "collaudo",
        "applicabile_a": ["EN_13241"],
        "rischi_associati": [
            {"descrizione": "Rischio elettrico", "probabilita_default": "Medio Bassa", "danno_default": "Ingente", "classe_default": "Grave"},
            {"descrizione": "Schiacciamento da parti mobili", "probabilita_default": "Medio Bassa", "danno_default": "Notevole", "classe_default": "Modesto"},
        ],
        "misure_prevenzione": [
            "Verificare che nessuno si trovi nell'area di movimento",
            "Seguire le procedure di collaudo del costruttore",
            "Predisporre barriere durante il test",
        ],
        "dpi_richiesti": ["DPI-SCARPE", "DPI-GUANTI-CROSTA"],
        "macchine_tipiche": ["Strumenti di misura", "Tester elettrici"],
    },
]

MACCHINE_DEFAULT = [
    {"nome": "Avvitatore elettrico", "marcata_ce": True, "verifiche_periodiche": True},
    {"nome": "Flessibile (smerigliatrice)", "marcata_ce": True, "verifiche_periodiche": True},
    {"nome": "Martello demolitore", "marcata_ce": True, "verifiche_periodiche": True},
    {"nome": "Sega circolare", "marcata_ce": True, "verifiche_periodiche": True},
    {"nome": "Trapano elettrico", "marcata_ce": True, "verifiche_periodiche": True},
    {"nome": "Utensili elettrici portatili", "marcata_ce": True, "verifiche_periodiche": True},
    {"nome": "Utensili manuali", "marcata_ce": True, "verifiche_periodiche": True},
    {"nome": "Saldatrice MIG/MAG", "marcata_ce": True, "verifiche_periodiche": True},
]

DPI_CANTIERE_DEFAULT = [
    {"tipo_dpi": "Tuta lavoro", "presente": True},
    {"tipo_dpi": "Scarpe antinfortunistiche", "presente": True},
    {"tipo_dpi": "Guanti", "presente": True},
    {"tipo_dpi": "Occhiali di protezione", "presente": True},
    {"tipo_dpi": "Mascherine antipolvere", "presente": True},
    {"tipo_dpi": "Otoprotettori", "presente": True},
    {"tipo_dpi": "Casco", "presente": True},
    {"tipo_dpi": "Cinture di sicurezza", "presente": True},
]

NUMERI_UTILI_DEFAULT = [
    {"servizio": "Vigili del fuoco", "numero": "115"},
    {"servizio": "Pronto soccorso", "numero": "118"},
    {"servizio": "Carabinieri", "numero": "112"},
    {"servizio": "Commissariato di P.S.", "numero": "113"},
]


# ═══════════════════════════════════════════════════════════════════
#  SEED LIBRERIA RISCHI
# ═══════════════════════════════════════════════════════════════════

async def seed_libreria_rischi(user_id: str):
    """Seed the risk library for a user if empty."""
    count = await db.libreria_rischi.count_documents({"user_id": user_id})
    if count > 0:
        return {"seeded": False, "count": count}

    docs = []
    now = datetime.now(timezone.utc).isoformat()

    # Seed DPI
    for dpi in DPI_SEED:
        docs.append({
            "risk_id": f"risk_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "tipo": "dpi",
            "codice": dpi["codice"],
            "nome": dpi["nome"],
            "rif_normativo": dpi["rif_normativo"],
            "is_default": True,
            "attivo": True,
            "created_at": now,
            "updated_at": now,
        })

    # Seed Fasi di Lavoro
    for fase in FASI_LAVORO_SEED:
        docs.append({
            "risk_id": f"risk_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "tipo": "fase_lavoro",
            "codice": fase["codice"],
            "nome": fase["nome"],
            "categoria": fase["categoria"],
            "applicabile_a": fase["applicabile_a"],
            "rischi_associati": fase["rischi_associati"],
            "misure_prevenzione": fase["misure_prevenzione"],
            "dpi_richiesti": fase["dpi_richiesti"],
            "macchine_tipiche": fase["macchine_tipiche"],
            "is_default": True,
            "attivo": True,
            "created_at": now,
            "updated_at": now,
        })

    if docs:
        await db.libreria_rischi.insert_many(docs)
    return {"seeded": True, "count": len(docs)}


# ═══════════════════════════════════════════════════════════════════
#  CANTIERI SICUREZZA — CRUD
# ═══════════════════════════════════════════════════════════════════

def _new_cantiere_template(cantiere_id: str, user_id: str, commessa_id: Optional[str] = None) -> dict:
    """Return a blank cantiere_sicurezza document with defaults."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "cantiere_id": cantiere_id,
        "user_id": user_id,
        "parent_commessa_id": commessa_id,
        "status": "bozza",
        "revisioni": [{"rev": "00", "motivazione": "Emissione", "data": ""}],
        "dati_cantiere": {
            "attivita_cantiere": "",
            "data_inizio_lavori": "",
            "data_fine_prevista": "",
            "indirizzo_cantiere": "",
            "citta_cantiere": "",
            "provincia_cantiere": "",
        },
        "soggetti_riferimento": {
            "committente": "",
            "responsabile_lavori": "",
            "direttore_lavori": "",
            "progettista": "",
            "csp": "",
            "cse": "",
        },
        "lavoratori_coinvolti": [],
        "turni_lavoro": {
            "mattina": "08:00-13:00",
            "pomeriggio": "14:00-17:00",
            "note": "",
        },
        "subappalti": [],
        "dpi_presenti": list(DPI_CANTIERE_DEFAULT),
        "macchine_attrezzature": list(MACCHINE_DEFAULT),
        "sostanze_chimiche": [],
        "agenti_biologici": [],
        "stoccaggio_materiali": "",
        "servizi_igienici": "",
        "fasi_lavoro_selezionate": [],
        "numeri_utili": list(NUMERI_UTILI_DEFAULT),
        "includi_covid19": False,
        "data_dichiarazione": "",
        "note_aggiuntive": "",
        "gate_pos_status": {
            "completezza_percentuale": 0,
            "campi_mancanti": [],
            "pronto_per_generazione": False,
        },
        "created_at": now,
        "updated_at": now,
    }


async def crea_cantiere(user_id: str, commessa_id: Optional[str] = None, pre_fill: Optional[dict] = None) -> dict:
    """Create a new cantiere_sicurezza, optionally pre-filled from commessa data."""
    cantiere_id = f"cant_{uuid.uuid4().hex[:12]}"
    doc = _new_cantiere_template(cantiere_id, user_id, commessa_id)

    # Pre-fill from commessa if available
    if commessa_id:
        commessa = await db.commesse.find_one(
            {"commessa_id": commessa_id, "user_id": user_id}, {"_id": 0}
        )
        if commessa:
            doc["dati_cantiere"]["attivita_cantiere"] = commessa.get("description", "")
            doc["soggetti_riferimento"]["committente"] = commessa.get("client_name", "")

    # Pre-fill from company_settings
    company = await db.company_settings.find_one({"user_id": user_id}, {"_id": 0})
    if company:
        # These will be used at DOCX generation time, not stored redundantly
        pass

    # Apply any explicit pre-fill overrides
    if pre_fill:
        for key in ["dati_cantiere", "soggetti_riferimento", "turni_lavoro"]:
            if key in pre_fill and isinstance(pre_fill[key], dict):
                doc[key].update(pre_fill[key])
        for key in ["lavoratori_coinvolti", "subappalti", "sostanze_chimiche"]:
            if key in pre_fill and isinstance(pre_fill[key], list):
                doc[key] = pre_fill[key]

    await db.cantieri_sicurezza.insert_one(doc)
    # Remove _id before returning
    doc.pop("_id", None)

    # Auto-seed libreria rischi for this user
    await seed_libreria_rischi(user_id)

    return doc


async def get_cantiere(cantiere_id: str, user_id: str) -> Optional[dict]:
    """Get a single cantiere_sicurezza by ID."""
    doc = await db.cantieri_sicurezza.find_one(
        {"cantiere_id": cantiere_id, "user_id": user_id}, {"_id": 0}
    )
    return doc


async def get_cantieri_by_commessa(commessa_id: str, user_id: str) -> list:
    """Get all cantieri_sicurezza for a commessa."""
    cursor = db.cantieri_sicurezza.find(
        {"parent_commessa_id": commessa_id, "user_id": user_id}, {"_id": 0}
    )
    return await cursor.to_list(length=100)


async def list_cantieri(user_id: str) -> list:
    """List all cantieri_sicurezza for a user."""
    cursor = db.cantieri_sicurezza.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("created_at", -1)
    return await cursor.to_list(length=200)


async def aggiorna_cantiere(cantiere_id: str, user_id: str, updates: dict) -> Optional[dict]:
    """Update a cantiere_sicurezza. Supports partial updates."""
    # Sanitize: remove protected fields
    for key in ["cantiere_id", "user_id", "_id", "created_at"]:
        updates.pop(key, None)

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Recalculate gate after every update
    result = await db.cantieri_sicurezza.find_one_and_update(
        {"cantiere_id": cantiere_id, "user_id": user_id},
        {"$set": updates},
        return_document=True,
    )
    if not result:
        return None

    # Recalculate gate status
    gate = calcola_gate_pos(result)
    await db.cantieri_sicurezza.update_one(
        {"cantiere_id": cantiere_id},
        {"$set": {"gate_pos_status": gate}}
    )
    result["gate_pos_status"] = gate
    result.pop("_id", None)
    return result


async def elimina_cantiere(cantiere_id: str, user_id: str) -> bool:
    """Delete a cantiere_sicurezza."""
    result = await db.cantieri_sicurezza.delete_one(
        {"cantiere_id": cantiere_id, "user_id": user_id}
    )
    return result.deleted_count > 0


# ═══════════════════════════════════════════════════════════════════
#  LIBRERIA RISCHI — CRUD
# ═══════════════════════════════════════════════════════════════════

async def get_libreria_rischi(user_id: str, tipo: Optional[str] = None) -> list:
    """Get risk library entries for a user, optionally filtered by tipo."""
    query = {"user_id": user_id, "attivo": True}
    if tipo:
        query["tipo"] = tipo
    cursor = db.libreria_rischi.find(query, {"_id": 0}).sort("codice", 1)
    return await cursor.to_list(length=500)


async def get_fasi_per_normativa(user_id: str, normativa: str) -> list:
    """Get work phases applicable to a specific normativa."""
    cursor = db.libreria_rischi.find(
        {
            "user_id": user_id,
            "tipo": "fase_lavoro",
            "attivo": True,
            "applicabile_a": normativa,
        },
        {"_id": 0},
    ).sort("codice", 1)
    return await cursor.to_list(length=100)


# ═══════════════════════════════════════════════════════════════════
#  GATE POS — Completeness Check
# ═══════════════════════════════════════════════════════════════════

CAMPI_OBBLIGATORI = [
    ("dati_cantiere.indirizzo_cantiere", "Indirizzo cantiere"),
    ("dati_cantiere.citta_cantiere", "Citta cantiere"),
    ("dati_cantiere.data_inizio_lavori", "Data inizio lavori"),
    ("soggetti_riferimento.committente", "Committente"),
    ("lavoratori_coinvolti", "Almeno un lavoratore"),
    ("fasi_lavoro_selezionate", "Almeno una fase di lavoro"),
]

CAMPI_OPZIONALI = [
    ("dati_cantiere.data_fine_prevista", "Data fine prevista"),
    ("dati_cantiere.attivita_cantiere", "Attivita cantiere"),
    ("soggetti_riferimento.direttore_lavori", "Direttore lavori"),
    ("soggetti_riferimento.cse", "Coordinatore sicurezza esecuzione"),
    ("data_dichiarazione", "Data dichiarazione"),
]


def _get_nested(doc: dict, path: str):
    """Get a nested value from a dict using dot notation."""
    keys = path.split(".")
    val = doc
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            return None
    return val


def calcola_gate_pos(cantiere: dict) -> dict:
    """Calculate POS gate status — checks completeness."""
    campi_mancanti = []
    total_checks = len(CAMPI_OBBLIGATORI) + len(CAMPI_OPZIONALI)
    passed = 0

    for path, label in CAMPI_OBBLIGATORI:
        val = _get_nested(cantiere, path)
        if isinstance(val, list):
            if len(val) > 0:
                passed += 1
            else:
                campi_mancanti.append(label)
        elif val:
            passed += 1
        else:
            campi_mancanti.append(label)

    for path, label in CAMPI_OPZIONALI:
        val = _get_nested(cantiere, path)
        if isinstance(val, list) and len(val) > 0:
            passed += 1
        elif val:
            passed += 1

    pct = round((passed / total_checks) * 100) if total_checks > 0 else 0
    # Must have ALL obbligatori for generation
    pronto = len(campi_mancanti) == 0

    return {
        "completezza_percentuale": pct,
        "campi_mancanti": campi_mancanti,
        "pronto_per_generazione": pronto,
    }
