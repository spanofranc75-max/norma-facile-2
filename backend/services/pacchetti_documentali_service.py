"""
Pacchetti Documentali — Service (D1 + D2 + D3)
================================================
D1: Archivio documenti strutturato
D2: Template pacchetti + creazione pacchetto
D3: Motore verifica presenza/scadenze + matching
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from core.database import db

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  D1 — LIBRERIA TIPI DOCUMENTO (Seed)
# ═══════════════════════════════════════════════════════════════

SEED_TIPI_DOCUMENTO = [
    # Azienda
    {"code": "DURC", "label": "DURC", "category": "legale", "entity_type": "azienda", "has_expiry": True, "validity_days": 120, "privacy_level": "cliente_condivisibile", "default_required_for": ["ingresso_cantiere", "qualifica_fornitore"], "sort_order": 10},
    {"code": "VISURA_CAMERALE", "label": "Visura Camerale", "category": "legale", "entity_type": "azienda", "has_expiry": True, "validity_days": 180, "privacy_level": "cliente_condivisibile", "default_required_for": ["qualifica_fornitore"], "sort_order": 20},
    {"code": "POLIZZA_RCT", "label": "Polizza RCT/RCO", "category": "assicurativa", "entity_type": "azienda", "has_expiry": True, "validity_days": 365, "privacy_level": "cliente_condivisibile", "default_required_for": ["qualifica_fornitore", "ingresso_cantiere"], "sort_order": 30},
    {"code": "CERT_ISO_9001", "label": "Certificazione ISO 9001", "category": "certificazione", "entity_type": "azienda", "has_expiry": True, "validity_days": 1095, "privacy_level": "cliente_condivisibile", "default_required_for": ["qualifica_fornitore"], "sort_order": 40},
    {"code": "CERT_ISO_3834", "label": "Certificazione ISO 3834", "category": "certificazione", "entity_type": "azienda", "has_expiry": True, "validity_days": 1095, "privacy_level": "cliente_condivisibile", "default_required_for": ["qualifica_fornitore"], "sort_order": 41},
    {"code": "CERT_EN_1090", "label": "Certificazione EN 1090", "category": "certificazione", "entity_type": "azienda", "has_expiry": True, "validity_days": 1095, "privacy_level": "cliente_condivisibile", "default_required_for": ["qualifica_fornitore"], "sort_order": 42},
    {"code": "DVR_ESTRATTO", "label": "DVR / Estratto DVR", "category": "sicurezza", "entity_type": "azienda", "has_expiry": False, "validity_days": 0, "privacy_level": "interno", "default_required_for": ["qualifica_fornitore", "sicurezza"], "sort_order": 50},
    {"code": "ORGANIGRAMMA", "label": "Organigramma Sicurezza", "category": "sicurezza", "entity_type": "azienda", "has_expiry": False, "validity_days": 0, "privacy_level": "cliente_condivisibile", "default_required_for": ["qualifica_fornitore"], "sort_order": 55},
    {"code": "DENUNCIA_INAIL", "label": "Denuncia INAIL Cantiere", "category": "legale", "entity_type": "azienda", "has_expiry": False, "validity_days": 0, "privacy_level": "cliente_condivisibile", "default_required_for": ["ingresso_cantiere"], "sort_order": 60},
    # Persona
    {"code": "ATTESTATO_SICUREZZA_BASE", "label": "Attestato Formazione Sicurezza Base", "category": "formazione", "entity_type": "persona", "has_expiry": True, "validity_days": 1825, "privacy_level": "cliente_condivisibile", "default_required_for": ["ingresso_cantiere", "personale_operativo"], "sort_order": 100},
    {"code": "ATTESTATO_SICUREZZA_SPEC", "label": "Attestato Formazione Specifica", "category": "formazione", "entity_type": "persona", "has_expiry": True, "validity_days": 1825, "privacy_level": "cliente_condivisibile", "default_required_for": ["ingresso_cantiere", "personale_operativo"], "sort_order": 101},
    {"code": "ATTESTATO_PRIMO_SOCCORSO", "label": "Attestato Primo Soccorso", "category": "formazione", "entity_type": "persona", "has_expiry": True, "validity_days": 1095, "privacy_level": "cliente_condivisibile", "default_required_for": ["personale_operativo"], "sort_order": 110},
    {"code": "ATTESTATO_ANTINCENDIO", "label": "Attestato Antincendio", "category": "formazione", "entity_type": "persona", "has_expiry": True, "validity_days": 1825, "privacy_level": "cliente_condivisibile", "default_required_for": ["personale_operativo"], "sort_order": 111},
    {"code": "ATTESTATO_PLE", "label": "Attestato PLE (Piattaforme)", "category": "formazione", "entity_type": "persona", "has_expiry": True, "validity_days": 1825, "privacy_level": "cliente_condivisibile", "default_required_for": ["personale_operativo", "mezzi"], "sort_order": 120},
    {"code": "ATTESTATO_GRU", "label": "Attestato Gru / Carroponte", "category": "formazione", "entity_type": "persona", "has_expiry": True, "validity_days": 1825, "privacy_level": "cliente_condivisibile", "default_required_for": ["personale_operativo"], "sort_order": 121},
    {"code": "ATTESTATO_CARRELLO", "label": "Attestato Carrello Elevatore", "category": "formazione", "entity_type": "persona", "has_expiry": True, "validity_days": 1825, "privacy_level": "cliente_condivisibile", "default_required_for": ["personale_operativo"], "sort_order": 122},
    {"code": "ATTESTATO_LAVORI_QUOTA", "label": "Attestato Lavori in Quota", "category": "formazione", "entity_type": "persona", "has_expiry": True, "validity_days": 1825, "privacy_level": "cliente_condivisibile", "default_required_for": ["personale_operativo"], "sort_order": 123},
    {"code": "IDONEITA_SANITARIA", "label": "Idoneita Sanitaria", "category": "sanitaria", "entity_type": "persona", "has_expiry": True, "validity_days": 365, "privacy_level": "sensibile", "default_required_for": ["ingresso_cantiere", "personale_operativo"], "sort_order": 130},
    {"code": "UNILAV", "label": "Comunicazione UNILAV", "category": "contrattuale", "entity_type": "persona", "has_expiry": False, "validity_days": 0, "privacy_level": "riservato", "default_required_for": ["ingresso_cantiere"], "sort_order": 140},
    # Mezzo
    {"code": "LIBRETTO_MEZZO", "label": "Libretto d'Uso e Manutenzione", "category": "attrezzatura", "entity_type": "mezzo", "has_expiry": False, "validity_days": 0, "privacy_level": "cliente_condivisibile", "default_required_for": ["mezzi"], "sort_order": 200},
    {"code": "VERIFICA_PERIODICA", "label": "Verifica Periodica (ASL/INAIL)", "category": "attrezzatura", "entity_type": "mezzo", "has_expiry": True, "validity_days": 730, "privacy_level": "cliente_condivisibile", "default_required_for": ["mezzi", "ingresso_cantiere"], "sort_order": 210},
    {"code": "ASSICURAZIONE_MEZZO", "label": "Assicurazione Mezzo", "category": "assicurativa", "entity_type": "mezzo", "has_expiry": True, "validity_days": 365, "privacy_level": "cliente_condivisibile", "default_required_for": ["mezzi"], "sort_order": 220},
    {"code": "MARCATURA_CE_MEZZO", "label": "Dichiarazione CE / Conformita", "category": "attrezzatura", "entity_type": "mezzo", "has_expiry": False, "validity_days": 0, "privacy_level": "cliente_condivisibile", "default_required_for": ["mezzi"], "sort_order": 230},
    # Cantiere
    {"code": "POS", "label": "Piano Operativo di Sicurezza", "category": "sicurezza", "entity_type": "cantiere", "has_expiry": False, "validity_days": 0, "privacy_level": "cliente_condivisibile", "default_required_for": ["ingresso_cantiere", "sicurezza"], "sort_order": 300},
    {"code": "ELENCO_LAVORATORI", "label": "Elenco Lavoratori Cantiere", "category": "operativo", "entity_type": "cantiere", "has_expiry": False, "validity_days": 0, "privacy_level": "cliente_condivisibile", "default_required_for": ["ingresso_cantiere"], "sort_order": 310},
    {"code": "ELENCO_MEZZI", "label": "Elenco Mezzi / Attrezzature", "category": "operativo", "entity_type": "cantiere", "has_expiry": False, "validity_days": 0, "privacy_level": "cliente_condivisibile", "default_required_for": ["ingresso_cantiere", "mezzi"], "sort_order": 320},
]

SEED_TEMPLATES = [
    {
        "code": "INGRESSO_CANTIERE",
        "label": "Ingresso Cantiere",
        "description": "Pacchetto standard per avvio attivita in cantiere",
        "rules": [
            {"document_type_code": "DURC", "entity_type": "azienda", "required": True},
            {"document_type_code": "VISURA_CAMERALE", "entity_type": "azienda", "required": False},
            {"document_type_code": "POLIZZA_RCT", "entity_type": "azienda", "required": True},
            {"document_type_code": "DENUNCIA_INAIL", "entity_type": "azienda", "required": True},
            {"document_type_code": "DVR_ESTRATTO", "entity_type": "azienda", "required": False},
            {"document_type_code": "POS", "entity_type": "cantiere", "required": True},
            {"document_type_code": "ELENCO_LAVORATORI", "entity_type": "cantiere", "required": True},
            {"document_type_code": "ELENCO_MEZZI", "entity_type": "cantiere", "required": False},
            {"document_type_code": "ATTESTATO_SICUREZZA_BASE", "entity_type": "persona", "required": True, "scope": "all_assigned_workers"},
            {"document_type_code": "IDONEITA_SANITARIA", "entity_type": "persona", "required": True, "scope": "all_assigned_workers"},
            {"document_type_code": "UNILAV", "entity_type": "persona", "required": True, "scope": "all_assigned_workers"},
        ],
    },
    {
        "code": "QUALIFICA_FORNITORE",
        "label": "Qualifica Fornitore",
        "description": "Pacchetto per qualificazione presso grande azienda/ente",
        "rules": [
            {"document_type_code": "DURC", "entity_type": "azienda", "required": True},
            {"document_type_code": "VISURA_CAMERALE", "entity_type": "azienda", "required": True},
            {"document_type_code": "POLIZZA_RCT", "entity_type": "azienda", "required": True},
            {"document_type_code": "CERT_ISO_9001", "entity_type": "azienda", "required": False},
            {"document_type_code": "CERT_ISO_3834", "entity_type": "azienda", "required": False},
            {"document_type_code": "CERT_EN_1090", "entity_type": "azienda", "required": False},
            {"document_type_code": "DVR_ESTRATTO", "entity_type": "azienda", "required": True},
            {"document_type_code": "ORGANIGRAMMA", "entity_type": "azienda", "required": True},
        ],
    },
    {
        "code": "PERSONALE_OPERATIVO",
        "label": "Documenti Personale Operativo",
        "description": "Attestati e idoneita per lavoratori assegnati",
        "rules": [
            {"document_type_code": "ATTESTATO_SICUREZZA_BASE", "entity_type": "persona", "required": True, "scope": "all_assigned_workers"},
            {"document_type_code": "ATTESTATO_SICUREZZA_SPEC", "entity_type": "persona", "required": True, "scope": "all_assigned_workers"},
            {"document_type_code": "ATTESTATO_PRIMO_SOCCORSO", "entity_type": "persona", "required": False, "scope": "all_assigned_workers"},
            {"document_type_code": "ATTESTATO_ANTINCENDIO", "entity_type": "persona", "required": False, "scope": "all_assigned_workers"},
            {"document_type_code": "IDONEITA_SANITARIA", "entity_type": "persona", "required": True, "scope": "all_assigned_workers"},
            {"document_type_code": "ATTESTATO_PLE", "entity_type": "persona", "required": False, "scope": "all_assigned_workers"},
            {"document_type_code": "ATTESTATO_LAVORI_QUOTA", "entity_type": "persona", "required": False, "scope": "all_assigned_workers"},
        ],
    },
    {
        "code": "DOCUMENTI_MEZZI",
        "label": "Documenti Mezzi / Attrezzature",
        "description": "Documentazione per mezzi e attrezzature assegnati",
        "rules": [
            {"document_type_code": "LIBRETTO_MEZZO", "entity_type": "mezzo", "required": True, "scope": "all_assigned_equipment"},
            {"document_type_code": "VERIFICA_PERIODICA", "entity_type": "mezzo", "required": True, "scope": "all_assigned_equipment"},
            {"document_type_code": "ASSICURAZIONE_MEZZO", "entity_type": "mezzo", "required": True, "scope": "all_assigned_equipment"},
            {"document_type_code": "MARCATURA_CE_MEZZO", "entity_type": "mezzo", "required": False, "scope": "all_assigned_equipment"},
        ],
    },
    {
        "code": "PACCHETTO_SICUREZZA",
        "label": "Pacchetto Sicurezza Completo",
        "description": "Documentazione sicurezza completa per cantiere",
        "rules": [
            {"document_type_code": "DVR_ESTRATTO", "entity_type": "azienda", "required": True},
            {"document_type_code": "ORGANIGRAMMA", "entity_type": "azienda", "required": True},
            {"document_type_code": "POS", "entity_type": "cantiere", "required": True},
            {"document_type_code": "ELENCO_LAVORATORI", "entity_type": "cantiere", "required": True},
            {"document_type_code": "ATTESTATO_SICUREZZA_BASE", "entity_type": "persona", "required": True, "scope": "all_assigned_workers"},
            {"document_type_code": "ATTESTATO_SICUREZZA_SPEC", "entity_type": "persona", "required": True, "scope": "all_assigned_workers"},
            {"document_type_code": "IDONEITA_SANITARIA", "entity_type": "persona", "required": True, "scope": "all_assigned_workers"},
        ],
    },
]


async def seed_tipi_documento(user_id: str):
    """Seed document types library if empty."""
    count = await db.lib_tipi_documento.count_documents({"user_id": user_id})
    if count > 0:
        return
    now = datetime.now(timezone.utc).isoformat()
    docs = []
    for t in SEED_TIPI_DOCUMENTO:
        docs.append({**t, "user_id": user_id, "active": True, "created_at": now})
    await db.lib_tipi_documento.insert_many(docs)
    logger.info(f"Seeded {len(docs)} tipi documento for {user_id}")


async def seed_templates(user_id: str):
    """Seed package templates if empty."""
    count = await db.pacchetti_template.count_documents({"user_id": user_id})
    if count > 0:
        return
    now = datetime.now(timezone.utc).isoformat()
    docs = []
    for t in SEED_TEMPLATES:
        docs.append({**t, "user_id": user_id, "active": True, "created_at": now})
    await db.pacchetti_template.insert_many(docs)
    logger.info(f"Seeded {len(docs)} pacchetti template for {user_id}")


# ═══════════════════════════════════════════════════════════════
#  D1 — ARCHIVIO DOCUMENTI
# ═══════════════════════════════════════════════════════════════

def _calc_doc_status(doc: dict) -> str:
    """Calculate document status based on expiry date."""
    expiry = doc.get("expiry_date")
    if not expiry:
        return "valido" if doc.get("verified") else "non_verificato"
    try:
        if isinstance(expiry, str):
            exp_date = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
        else:
            exp_date = expiry
        now = datetime.now(timezone.utc)
        if exp_date.tzinfo is None:
            from datetime import timezone as tz
            exp_date = exp_date.replace(tzinfo=tz.utc)
        if exp_date < now:
            return "scaduto"
        if exp_date < now + timedelta(days=30):
            return "in_scadenza"
        return "valido"
    except (ValueError, TypeError):
        return "non_verificato"


async def upload_documento(user_id: str, data: dict, file_data: bytes = None,
                           filename: str = None, content_type: str = None) -> dict:
    """Upload a document to the archive."""
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    file_info = {}
    if file_data and filename:
        from services.object_storage import put_object
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
        storage_path = f"norma-facile/documenti/{user_id}/{doc_id}.{ext}"
        result = put_object(storage_path, file_data, content_type or "application/octet-stream")
        file_info = {
            "file_id": storage_path,
            "file_name": filename,
            "mime_type": content_type or "application/octet-stream",
            "file_size": result.get("size", len(file_data)),
        }

    doc = {
        "doc_id": doc_id,
        "user_id": user_id,
        "document_type_code": data.get("document_type_code", ""),
        "entity_type": data.get("entity_type", "azienda"),
        "entity_id": data.get("entity_id", ""),
        "owner_label": data.get("owner_label", ""),
        "title": data.get("title", ""),
        "issue_date": data.get("issue_date", ""),
        "expiry_date": data.get("expiry_date", ""),
        "verified": data.get("verified", False),
        "version": data.get("version", 1),
        "privacy_level": data.get("privacy_level", "cliente_condivisibile"),
        "tags": data.get("tags", []),
        "source": data.get("source", "upload_manuale"),
        "notes": data.get("notes", ""),
        **file_info,
        "created_at": now,
        "updated_at": now,
    }
    doc["status"] = _calc_doc_status(doc)

    await db.documenti_archivio.insert_one(doc)
    doc.pop("_id", None)
    return doc


async def list_documenti(user_id: str, entity_type: str = None,
                         entity_id: str = None, document_type_code: str = None,
                         status: str = None) -> list:
    """List documents with filters."""
    query = {"user_id": user_id}
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    if document_type_code:
        query["document_type_code"] = document_type_code
    if status:
        query["status"] = status

    docs = await db.documenti_archivio.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    # Recalculate status for expiry-based docs
    for d in docs:
        d["status"] = _calc_doc_status(d)
    return docs


async def get_documento(doc_id: str, user_id: str) -> Optional[dict]:
    doc = await db.documenti_archivio.find_one(
        {"doc_id": doc_id, "user_id": user_id}, {"_id": 0}
    )
    if doc:
        doc["status"] = _calc_doc_status(doc)
    return doc


async def update_documento(doc_id: str, user_id: str, updates: dict) -> Optional[dict]:
    allowed = {"title", "issue_date", "expiry_date", "verified", "privacy_level",
               "tags", "notes", "owner_label", "entity_id", "entity_type", "document_type_code"}
    filtered = {k: v for k, v in updates.items() if k in allowed and v is not None}
    filtered["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.documenti_archivio.update_one(
        {"doc_id": doc_id, "user_id": user_id}, {"$set": filtered}
    )
    return await get_documento(doc_id, user_id)


# ═══════════════════════════════════════════════════════════════
#  D2 — TEMPLATE & PACCHETTI
# ═══════════════════════════════════════════════════════════════

async def get_templates(user_id: str) -> list:
    await seed_templates(user_id)
    return await db.pacchetti_template.find(
        {"user_id": user_id, "active": True}, {"_id": 0}
    ).to_list(50)


async def crea_pacchetto(user_id: str, data: dict) -> dict:
    """Create a new document package from a template or manual selection."""
    pack_id = f"pack_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    template_code = data.get("template_code")
    items = []

    if template_code:
        # Load template
        tpl = await db.pacchetti_template.find_one(
            {"user_id": user_id, "code": template_code, "active": True}, {"_id": 0}
        )
        if tpl:
            for rule in tpl.get("rules", []):
                scope = rule.get("scope")
                if scope == "all_assigned_workers":
                    # Expand for each worker in cantiere
                    workers = await _get_assigned_workers(user_id, data.get("cantiere_id"))
                    if workers:
                        for w in workers:
                            items.append({
                                "document_type_code": rule["document_type_code"],
                                "entity_type": "persona",
                                "entity_id": w.get("worker_id", ""),
                                "entity_label": w.get("nominativo", ""),
                                "required": rule.get("required", True),
                                "document_id": None,
                                "status": "pending",
                                "blocking": False,
                            })
                    else:
                        items.append({
                            "document_type_code": rule["document_type_code"],
                            "entity_type": "persona",
                            "entity_id": "",
                            "entity_label": "(nessun lavoratore assegnato)",
                            "required": rule.get("required", True),
                            "document_id": None,
                            "status": "pending",
                            "blocking": False,
                        })
                elif scope == "all_assigned_equipment":
                    equip = await _get_assigned_equipment(user_id, data.get("cantiere_id"))
                    if equip:
                        for e in equip:
                            items.append({
                                "document_type_code": rule["document_type_code"],
                                "entity_type": "mezzo",
                                "entity_id": e.get("mezzo_id", ""),
                                "entity_label": e.get("nome", ""),
                                "required": rule.get("required", True),
                                "document_id": None,
                                "status": "pending",
                                "blocking": False,
                            })
                    else:
                        items.append({
                            "document_type_code": rule["document_type_code"],
                            "entity_type": "mezzo",
                            "entity_id": "",
                            "entity_label": "(nessun mezzo assegnato)",
                            "required": rule.get("required", True),
                            "document_id": None,
                            "status": "pending",
                            "blocking": False,
                        })
                else:
                    items.append({
                        "document_type_code": rule["document_type_code"],
                        "entity_type": rule.get("entity_type", "azienda"),
                        "entity_id": data.get("entity_id", ""),
                        "entity_label": "",
                        "required": rule.get("required", True),
                        "document_id": None,
                        "status": "pending",
                        "blocking": False,
                    })

    pack = {
        "pack_id": pack_id,
        "user_id": user_id,
        "commessa_id": data.get("commessa_id", ""),
        "cantiere_id": data.get("cantiere_id", ""),
        "template_code": template_code or "",
        "label": data.get("label", ""),
        "status": "draft",
        "recipient": data.get("recipient", {"to": [], "cc": []}),
        "items": items,
        "summary": {"total_required": 0, "attached": 0, "missing": 0, "expired": 0, "in_scadenza": 0, "sensibile": 0},
        "created_at": now,
        "updated_at": now,
    }

    await db.pacchetti_documentali.insert_one(pack)
    pack.pop("_id", None)
    return pack


async def _get_assigned_workers(user_id: str, cantiere_id: str = None) -> list:
    """Get workers assigned to a cantiere (from cantieri_sicurezza)."""
    if not cantiere_id:
        return []
    cantiere = await db.cantieri_sicurezza.find_one(
        {"cantiere_id": cantiere_id, "user_id": user_id}, {"_id": 0}
    )
    if not cantiere:
        return []
    return cantiere.get("lavoratori_coinvolti", [])


async def _get_assigned_equipment(user_id: str, cantiere_id: str = None) -> list:
    """Get equipment assigned to a cantiere."""
    if not cantiere_id:
        return []
    cantiere = await db.cantieri_sicurezza.find_one(
        {"cantiere_id": cantiere_id, "user_id": user_id}, {"_id": 0}
    )
    if not cantiere:
        return []
    return cantiere.get("macchine_attrezzature", [])


# ═══════════════════════════════════════════════════════════════
#  D3 — MOTORE VERIFICA (matching + status)
# ═══════════════════════════════════════════════════════════════

async def verifica_pacchetto(pack_id: str, user_id: str) -> dict:
    """D3 core: match package items against document archive, calculate status."""
    pack = await db.pacchetti_documentali.find_one(
        {"pack_id": pack_id, "user_id": user_id}, {"_id": 0}
    )
    if not pack:
        return {"error": "Pacchetto non trovato"}

    # Load tipi documento for privacy lookup
    tipi_map = {}
    async for t in db.lib_tipi_documento.find({"user_id": user_id, "active": True}, {"_id": 0}):
        tipi_map[t["code"]] = t

    items = pack.get("items", [])
    counters = {"total_required": 0, "attached": 0, "missing": 0,
                "expired": 0, "in_scadenza": 0, "sensibile": 0}

    for item in items:
        doc_type = item["document_type_code"]
        entity_type = item.get("entity_type", "azienda")
        entity_id = item.get("entity_id", "")
        tipo_def = tipi_map.get(doc_type, {})

        # Build query: find best matching document
        query = {
            "user_id": user_id,
            "document_type_code": doc_type,
        }
        # For azienda, no entity_id filter (company-wide)
        if entity_type != "azienda" and entity_id:
            query["entity_id"] = entity_id

        # Find best document: verified first, most recent, not archived
        candidates = await db.documenti_archivio.find(
            query, {"_id": 0}
        ).sort([("verified", -1), ("created_at", -1)]).to_list(5)

        best = None
        for c in candidates:
            c["status"] = _calc_doc_status(c)
            if c["status"] not in ("sostituito", "archiviato"):
                best = c
                break

        if best:
            item["document_id"] = best["doc_id"]
            item["document_title"] = best.get("title", best.get("file_name", ""))
            status = best["status"]

            if status == "scaduto":
                item["status"] = "expired"
                item["blocking"] = item.get("required", False)
                counters["expired"] += 1
            elif status == "in_scadenza":
                item["status"] = "in_scadenza"
                item["blocking"] = False
                counters["in_scadenza"] += 1
                counters["attached"] += 1
            else:
                item["status"] = "attached"
                item["blocking"] = False
                counters["attached"] += 1
        else:
            item["document_id"] = None
            item["document_title"] = ""
            item["status"] = "missing"
            item["blocking"] = item.get("required", False)
            counters["missing"] += 1

        # Privacy check
        privacy = tipo_def.get("privacy_level", "cliente_condivisibile")
        item["privacy_level"] = privacy
        if privacy == "sensibile":
            counters["sensibile"] += 1

        if item.get("required"):
            counters["total_required"] += 1

    # Determine pack status
    if counters["missing"] == 0 and counters["expired"] == 0:
        pack_status = "pronto_invio"
    elif counters["attached"] > 0:
        pack_status = "incompleto"
    else:
        pack_status = "draft"

    now = datetime.now(timezone.utc).isoformat()
    await db.pacchetti_documentali.update_one(
        {"pack_id": pack_id, "user_id": user_id},
        {"$set": {
            "items": items,
            "summary": counters,
            "status": pack_status,
            "last_verified_at": now,
            "updated_at": now,
        }}
    )

    return {
        "pack_id": pack_id,
        "status": pack_status,
        "summary": counters,
        "items": items,
    }


async def get_pacchetto(pack_id: str, user_id: str) -> Optional[dict]:
    doc = await db.pacchetti_documentali.find_one(
        {"pack_id": pack_id, "user_id": user_id}, {"_id": 0}
    )
    return doc


async def list_pacchetti(user_id: str, commessa_id: str = None) -> list:
    query = {"user_id": user_id}
    if commessa_id:
        query["commessa_id"] = commessa_id
    return await db.pacchetti_documentali.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)


async def get_tipi_documento(user_id: str) -> list:
    await seed_tipi_documento(user_id)
    return await db.lib_tipi_documento.find(
        {"user_id": user_id, "active": True}, {"_id": 0}
    ).sort("sort_order", 1).to_list(100)
