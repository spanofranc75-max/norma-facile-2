"""
Demo Mode — Seed script to create realistic demo data.
Creates a demo user with 3 commesse, preventivi, obblighi, and related data.
Run via: POST /api/admin/demo/reset
"""
import uuid
from datetime import datetime, timezone, timedelta

DEMO_USER_ID = "demo_user"
DEMO_EMAIL = "demo@normafacile.it"
NOW = datetime.now(timezone.utc)


def _id(prefix=""):
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def _ts(days_ago=0):
    return (NOW - timedelta(days=days_ago)).isoformat()


DEMO_USER = {
    "user_id": DEMO_USER_ID,
    "email": DEMO_EMAIL,
    "name": "Marco Rossi",
    "picture": "",
    "role": "admin",
    "is_demo": True,
    "created_at": _ts(90),
    "last_login": _ts(0),
}

DEMO_COMPANY = {
    "settings_id": "settings_demo",
    "user_id": DEMO_USER_ID,
    "business_name": "Carpenteria Metallica Rossi S.r.l.",
    "partita_iva": "IT02345678901",
    "codice_fiscale": "IT02345678901",
    "address": "Via dell'Industria 42",
    "cap": "40033",
    "city": "Casalecchio di Reno (BO)",
    "province": "BO",
    "country": "IT",
    "email": "info@carpenteriarossi.it",
    "pec": "carpenteriarossi@pec.it",
    "phone": "+39 051 555 1234",
    "website": "www.carpenteriarossi.it",
    "natura_giuridica": "SRL",
    "regime_fiscale": "RF01",
    "codice_destinatario": "M5UXCR1",
    "responsabile_nome": "Ing. Marco Rossi",
    "ruolo_firmatario": "Legale Rappresentante",
    "certificato_en1090_numero": "1234-CPR-2024-IT",
    "ente_certificatore": "RINA Services S.p.A.",
    "ente_certificatore_numero": "0474",
    "classe_esecuzione_default": "EXC2",
    "bank_accounts": [{
        "account_id": "ba_demo_01",
        "bank_name": "Banca Popolare dell'Emilia Romagna",
        "iban": "IT60X0542402802000000123456",
        "bic_swift": "BPMOIT22XXX",
        "intestatario": "Carpenteria Metallica Rossi S.r.l.",
        "predefinito": True,
    }],
    "condizioni_vendita": "Pagamento a 30 giorni fine mese dalla data fattura.",
    "updated_at": _ts(5),
}

DEMO_CLIENT = {
    "client_id": "cli_demo_main",
    "user_id": DEMO_USER_ID,
    "business_name": "Logistica Emiliana S.p.A.",
    "partita_iva": "IT12345678902",
    "codice_fiscale": "IT12345678902",
    "codice_sdi": "ABC1234",
    "pec": "logistica@pec.it",
    "email": "acquisti@logisticaemiliana.it",
    "phone": "+39 051 444 5678",
    "address": "Via della Logistica 15",
    "cap": "40012",
    "city": "Calderara di Reno (BO)",
    "province": "BO",
    "country": "IT",
    "created_at": _ts(60),
}

DEMO_CLIENT_2 = {
    "client_id": "cli_demo_secondary",
    "user_id": DEMO_USER_ID,
    "business_name": "Condominio Residence Park",
    "partita_iva": "IT98765432100",
    "codice_fiscale": "IT98765432100",
    "codice_sdi": "0000000",
    "email": "admin@residencepark.it",
    "phone": "+39 051 333 9999",
    "address": "Viale dei Giardini 8",
    "cap": "40128",
    "city": "Bologna",
    "province": "BO",
    "country": "IT",
    "created_at": _ts(45),
}

# ─── Main Commessa: Mixed EN 1090 + EN 13241 ──────────────────

DEMO_COMMESSA_MAIN = {
    "commessa_id": "com_demo_main",
    "user_id": DEMO_USER_ID,
    "numero": "NF-DEMO-001",
    "title": "Ampliamento area logistica con struttura metallica e cancello carrabile",
    "description": "Fornitura e posa in opera di struttura metallica per copertura area esterna e cancello carrabile motorizzato.",
    "client_id": "cli_demo_main",
    "client_name": "Logistica Emiliana S.p.A.",
    "normativa_tipo": "EN_1090",
    "classe_exc": "EXC2",
    "stato": "in_produzione",
    "status": "lavorazione",
    "priority": "alta",
    "value": 48500.0,
    "importo_totale": 48500.0,
    "peso_totale_kg": 3200,
    "ore_preventivate": 280,
    "riferimento": "OC-2026/0042",
    "moduli": {
        "rilievo_id": None,
        "distinta_id": None,
        "preventivo_id": "prev_demo_main",
        "fpc_project_id": None,
    },
    "cantiere": {
        "indirizzo": "Via della Logistica 15, 40012 Calderara di Reno (BO)",
        "coordinate": "44.5520,11.2780",
    },
    "budget": {"materiali": 18000, "manodopera": 15000, "conto_lavoro": 5000, "totale": 38000},
    "fasi_produzione": [],
    "consegne": [],
    "conto_lavoro": [],
    "approvvigionamento": {"richieste": [], "ordini": [], "arrivi": []},
    "eventi": [
        {"tipo": "COMMESSA_CREATA", "data": _ts(30), "operatore": "Marco Rossi", "note": "Commessa generata da preventivo"},
        {"tipo": "PREVENTIVO_ACCETTATO", "data": _ts(25), "operatore": "Marco Rossi", "note": "Contratto firmato dal cliente"},
        {"tipo": "AVVIO_PRODUZIONE", "data": _ts(15), "operatore": "Marco Rossi", "note": "Materiale arrivato, avvio taglio"},
    ],
    "notes": "Consegna prevista entro 45 giorni dalla firma contratto.",
    "created_at": _ts(30),
    "updated_at": _ts(2),
}

DEMO_VOCI_MAIN = [
    {
        "voce_id": _id("vl_"), "commessa_id": "com_demo_main", "user_id": DEMO_USER_ID,
        "descrizione": "Struttura portante in acciaio S355 per copertura area esterna",
        "normativa_tipo": "EN_1090", "peso_kg": 2400, "valore": 32000,
        "created_at": _ts(30),
    },
    {
        "voce_id": _id("vl_"), "commessa_id": "com_demo_main", "user_id": DEMO_USER_ID,
        "descrizione": "Cancello carrabile motorizzato doppia anta 6m",
        "normativa_tipo": "EN_13241", "peso_kg": 450, "valore": 12500,
        "created_at": _ts(30),
    },
    {
        "voce_id": _id("vl_"), "commessa_id": "com_demo_main", "user_id": DEMO_USER_ID,
        "descrizione": "Accessori e minuteria di fissaggio",
        "normativa_tipo": None, "peso_kg": 350, "valore": 4000,
        "created_at": _ts(30),
    },
]

DEMO_NORMATIVE_MAIN = [
    {
        "ramo_id": "ramo_demo_1090", "commessa_id": "com_demo_main", "user_id": DEMO_USER_ID,
        "normativa": "EN_1090", "classe_esecuzione": "EXC2",
        "created_at": _ts(30),
    },
    {
        "ramo_id": "ramo_demo_13241", "commessa_id": "com_demo_main", "user_id": DEMO_USER_ID,
        "normativa": "EN_13241", "classe_esecuzione": None,
        "created_at": _ts(30),
    },
]

DEMO_OBBLIGHI_MAIN = [
    {
        "obbligo_id": _id("ob_"), "commessa_id": "com_demo_main", "user_id": DEMO_USER_ID,
        "dedupe_key": f"com_demo_main|contratto_firmato|contratto",
        "title": "Contratto firmato dal committente",
        "fonte": "contratto", "blocking_level": "hard_block", "severity": "alta",
        "status": "completato", "blocking_level_sort": 0, "severity_sort": 0,
        "created_at": _ts(25),
    },
    {
        "obbligo_id": _id("ob_"), "commessa_id": "com_demo_main", "user_id": DEMO_USER_ID,
        "dedupe_key": f"com_demo_main|certificato_3.1|materiali",
        "title": "Certificato 3.1 materiale base S355",
        "fonte": "materiali", "blocking_level": "hard_block", "severity": "alta",
        "status": "completato", "blocking_level_sort": 0, "severity_sort": 0,
        "created_at": _ts(20),
    },
    {
        "obbligo_id": _id("ob_"), "commessa_id": "com_demo_main", "user_id": DEMO_USER_ID,
        "dedupe_key": f"com_demo_main|qualifica_saldatore|personale",
        "title": "Qualifica saldatore EN ISO 9606-1 processo 135",
        "fonte": "personale", "blocking_level": "hard_block", "severity": "alta",
        "status": "in_progress", "blocking_level_sort": 0, "severity_sort": 0,
        "created_at": _ts(15),
    },
    {
        "obbligo_id": _id("ob_"), "commessa_id": "com_demo_main", "user_id": DEMO_USER_ID,
        "dedupe_key": f"com_demo_main|wps_135|documentazione",
        "title": "WPS procedura di saldatura 135",
        "fonte": "documentazione", "blocking_level": "soft_block", "severity": "media",
        "status": "completato", "blocking_level_sort": 1, "severity_sort": 1,
        "created_at": _ts(18),
    },
    {
        "obbligo_id": _id("ob_"), "commessa_id": "com_demo_main", "user_id": DEMO_USER_ID,
        "dedupe_key": f"com_demo_main|pos_cantiere|sicurezza",
        "title": "Piano Operativo Sicurezza (POS) cantiere",
        "fonte": "sicurezza", "blocking_level": "hard_block", "severity": "alta",
        "status": "in_progress", "blocking_level_sort": 0, "severity_sort": 0,
        "created_at": _ts(12),
    },
    {
        "obbligo_id": _id("ob_"), "commessa_id": "com_demo_main", "user_id": DEMO_USER_ID,
        "dedupe_key": f"com_demo_main|dop_cancello|certificazione",
        "title": "Dichiarazione di Prestazione (DoP) cancello EN 13241",
        "fonte": "certificazione", "blocking_level": "hard_block", "severity": "alta",
        "status": "pending", "blocking_level_sort": 0, "severity_sort": 0,
        "created_at": _ts(10),
    },
    {
        "obbligo_id": _id("ob_"), "commessa_id": "com_demo_main", "user_id": DEMO_USER_ID,
        "dedupe_key": f"com_demo_main|cam_256|normativa",
        "title": "Verifica CAM DM 256/2022 materiali riciclati",
        "fonte": "normativa", "blocking_level": "advisory", "severity": "bassa",
        "status": "pending", "blocking_level_sort": 2, "severity_sort": 2,
        "created_at": _ts(8),
    },
]

# ─── Secondary Commessa: Simple Parapetti ──────────────────

DEMO_COMMESSA_SIMPLE = {
    "commessa_id": "com_demo_simple",
    "user_id": DEMO_USER_ID,
    "numero": "NF-DEMO-002",
    "title": "Parapetti scala esterna condominio",
    "description": "Fornitura e posa in opera parapetti in acciaio zincato per scala esterna.",
    "client_id": "cli_demo_secondary",
    "client_name": "Condominio Residence Park",
    "normativa_tipo": "EN_1090",
    "classe_exc": "EXC1",
    "stato": "bozza",
    "status": "bozza",
    "priority": "media",
    "value": 8500.0,
    "importo_totale": 8500.0,
    "peso_totale_kg": 180,
    "ore_preventivate": 40,
    "riferimento": "",
    "moduli": {"rilievo_id": None, "distinta_id": None, "preventivo_id": "prev_demo_simple", "fpc_project_id": None},
    "cantiere": {},
    "budget": {"materiali": 3000, "manodopera": 3500, "conto_lavoro": 0, "totale": 6500},
    "fasi_produzione": [], "consegne": [], "conto_lavoro": [],
    "approvvigionamento": {"richieste": [], "ordini": [], "arrivi": []},
    "eventi": [
        {"tipo": "COMMESSA_CREATA", "data": _ts(10), "operatore": "Marco Rossi", "note": ""},
    ],
    "notes": "",
    "created_at": _ts(10),
    "updated_at": _ts(10),
}

# ─── Third Commessa: Nearly Complete Cancello ──────────────────

DEMO_COMMESSA_COMPLETE = {
    "commessa_id": "com_demo_complete",
    "user_id": DEMO_USER_ID,
    "numero": "NF-DEMO-003",
    "title": "Cancello pedonale automatico ingresso uffici",
    "description": "Cancello pedonale motorizzato con sistema di controllo accessi.",
    "client_id": "cli_demo_main",
    "client_name": "Logistica Emiliana S.p.A.",
    "normativa_tipo": "EN_13241",
    "classe_exc": None,
    "stato": "firmato",
    "status": "lavorazione",
    "priority": "bassa",
    "value": 6200.0,
    "importo_totale": 6200.0,
    "peso_totale_kg": 120,
    "ore_preventivate": 24,
    "riferimento": "OC-2026/0038",
    "moduli": {"rilievo_id": None, "distinta_id": None, "preventivo_id": "prev_demo_complete", "fpc_project_id": None},
    "cantiere": {"indirizzo": "Via della Logistica 15, 40012 Calderara di Reno (BO)"},
    "budget": {"materiali": 2500, "manodopera": 2000, "conto_lavoro": 500, "totale": 5000},
    "fasi_produzione": [], "consegne": [], "conto_lavoro": [],
    "approvvigionamento": {"richieste": [], "ordini": [], "arrivi": []},
    "eventi": [
        {"tipo": "COMMESSA_CREATA", "data": _ts(45), "operatore": "Marco Rossi", "note": ""},
        {"tipo": "PREVENTIVO_ACCETTATO", "data": _ts(40), "operatore": "Marco Rossi", "note": ""},
        {"tipo": "AVVIO_PRODUZIONE", "data": _ts(30), "operatore": "Marco Rossi", "note": ""},
        {"tipo": "PRODUZIONE_COMPLETATA", "data": _ts(5), "operatore": "Luca Bianchi", "note": "Cancello assemblato e verniciato"},
    ],
    "notes": "Pronto per consegna e posa.",
    "created_at": _ts(45),
    "updated_at": _ts(5),
}

# ─── Preventivi ──────────────────

DEMO_PREVENTIVI = [
    {
        "prev_id": "prev_demo_main", "preventivo_id": "prev_demo_main",
        "user_id": DEMO_USER_ID, "number": "PRV-DEMO-001",
        "client_id": "cli_demo_main", "status": "accettato",
        "normativa": "EN_1090",
        "subject": "Struttura metallica + cancello carrabile area logistica",
        "lines": [
            {"line_id": "ln_d1", "description": "Struttura portante in acciaio S355 JR per copertura area esterna - EXC2", "qty": 1, "unit": "corpo", "unit_price": 32000, "subtotal": 32000},
            {"line_id": "ln_d2", "description": "Cancello carrabile motorizzato doppia anta L=6000mm EN 13241", "qty": 1, "unit": "corpo", "unit_price": 12500, "subtotal": 12500},
            {"line_id": "ln_d3", "description": "Accessori, minuteria e opere accessorie", "qty": 1, "unit": "corpo", "unit_price": 4000, "subtotal": 4000},
        ],
        "totals": {"subtotal": 48500, "sconto_globale_pct": 0, "sconto_val": 0, "imponibile": 48500, "iva": 10670, "totale": 59170},
        "validity_days": 30,
        "created_at": _ts(35), "updated_at": _ts(25),
    },
    {
        "prev_id": "prev_demo_simple", "preventivo_id": "prev_demo_simple",
        "user_id": DEMO_USER_ID, "number": "PRV-DEMO-002",
        "client_id": "cli_demo_secondary", "status": "inviato",
        "normativa": "EN_1090",
        "subject": "Parapetti scala esterna condominio",
        "lines": [
            {"line_id": "ln_s1", "description": "Parapetti in acciaio zincato a caldo h=1100mm - EXC1", "qty": 12, "unit": "ml", "unit_price": 650, "subtotal": 7800},
            {"line_id": "ln_s2", "description": "Posa in opera e fissaggio", "qty": 1, "unit": "corpo", "unit_price": 700, "subtotal": 700},
        ],
        "totals": {"subtotal": 8500, "sconto_globale_pct": 0, "sconto_val": 0, "imponibile": 8500, "iva": 1870, "totale": 10370},
        "validity_days": 30,
        "created_at": _ts(12), "updated_at": _ts(10),
    },
    {
        "prev_id": "prev_demo_complete", "preventivo_id": "prev_demo_complete",
        "user_id": DEMO_USER_ID, "number": "PRV-DEMO-003",
        "client_id": "cli_demo_main", "status": "accettato",
        "normativa": "EN_13241",
        "subject": "Cancello pedonale automatico",
        "lines": [
            {"line_id": "ln_c1", "description": "Cancello pedonale automatizzato anta singola L=1200mm EN 13241", "qty": 1, "unit": "corpo", "unit_price": 5200, "subtotal": 5200},
            {"line_id": "ln_c2", "description": "Sistema controllo accessi e posa", "qty": 1, "unit": "corpo", "unit_price": 1000, "subtotal": 1000},
        ],
        "totals": {"subtotal": 6200, "sconto_globale_pct": 0, "sconto_val": 0, "imponibile": 6200, "iva": 1364, "totale": 7564},
        "validity_days": 30,
        "created_at": _ts(50), "updated_at": _ts(40),
    },
]

# ─── Cantiere Sicurezza ──────────────────

DEMO_CANTIERE = {
    "cantiere_id": "cant_demo_main",
    "user_id": DEMO_USER_ID,
    "parent_commessa_id": "com_demo_main",
    "denominazione": "Cantiere Logistica Emiliana - Area esterna",
    "indirizzo": "Via della Logistica 15, 40012 Calderara di Reno (BO)",
    "committente": "Logistica Emiliana S.p.A.",
    "responsabile_lavori": "Ing. Paolo Verdi",
    "cse": "Geom. Anna Neri",
    "preposto": "Luca Bianchi",
    "soggetti": [
        {"ruolo": "Committente", "nome": "Logistica Emiliana S.p.A.", "riferimento": "Dott. Franco Mori"},
        {"ruolo": "Direttore Lavori", "nome": "Ing. Paolo Verdi", "telefono": "+39 051 222 3333"},
        {"ruolo": "CSE", "nome": "Geom. Anna Neri", "telefono": "+39 051 444 5555"},
        {"ruolo": "Preposto", "nome": "Luca Bianchi", "qualifica": "Caposquadra"},
    ],
    "rischi_specifici": ["Lavoro in quota", "Movimentazione carichi", "Saldatura in cantiere"],
    "dpi_richiesti": ["Casco", "Scarpe antinfortunistiche", "Imbragatura", "Guanti"],
    "created_at": _ts(15),
}

# ─── Activity Log ──────────────────

DEMO_ACTIVITIES = [
    {"activity_id": _id("act_"), "user_id": DEMO_USER_ID, "action": "create", "entity_type": "preventivo", "entity_id": "prev_demo_main", "timestamp": _ts(35), "details": {"number": "PRV-DEMO-001"}},
    {"activity_id": _id("act_"), "user_id": DEMO_USER_ID, "action": "status_change", "entity_type": "preventivo", "entity_id": "prev_demo_main", "timestamp": _ts(25), "details": {"from": "inviato", "to": "accettato"}},
    {"activity_id": _id("act_"), "user_id": DEMO_USER_ID, "action": "create", "entity_type": "commessa", "entity_id": "com_demo_main", "timestamp": _ts(30), "details": {"numero": "NF-DEMO-001"}},
    {"activity_id": _id("act_"), "user_id": DEMO_USER_ID, "action": "generate_docx", "entity_type": "cantiere_sicurezza", "entity_id": "cant_demo_main", "timestamp": _ts(10), "details": {"type": "POS"}},
    {"activity_id": _id("act_"), "user_id": DEMO_USER_ID, "action": "create", "entity_type": "commessa", "entity_id": "com_demo_complete", "timestamp": _ts(45), "details": {"numero": "NF-DEMO-003"}},
]


def get_all_demo_collections():
    """Return dict of collection_name -> list of documents to seed."""
    return {
        "users": [DEMO_USER],
        "company_settings": [DEMO_COMPANY],
        "clients": [DEMO_CLIENT, DEMO_CLIENT_2],
        "commesse": [DEMO_COMMESSA_MAIN, DEMO_COMMESSA_SIMPLE, DEMO_COMMESSA_COMPLETE],
        "voci_lavoro": DEMO_VOCI_MAIN,
        "commesse_normative": DEMO_NORMATIVE_MAIN,
        "obblighi_commessa": DEMO_OBBLIGHI_MAIN,
        "preventivi": DEMO_PREVENTIVI,
        "cantieri_sicurezza": [DEMO_CANTIERE],
        "activity_log": DEMO_ACTIVITIES,
    }
