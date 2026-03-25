"""Migration: Backfill tenant_id='default' across ALL data collections.

Run once to add the multi-tenant foundation.
Safe to run multiple times (idempotent — only updates docs missing tenant_id).

Usage:
    python -m migrations.add_tenant_id
"""
import asyncio
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

# All data collections that need tenant_id backfill
DATA_COLLECTIONS = [
    "users",
    "user_sessions",
    "clients",
    "commesse",
    "preventivi",
    "invoices",
    "fatture_ricevute",
    "ddt",
    "perizie",
    "rilievi",
    "articoli",
    "payment_types",
    "company_settings",
    "company_docs",
    "distinte",
    "certificazioni",
    "sicurezza_docs",
    "catalogo",
    "verbali_posa",
    "vendor_keys",
    "fpc_projects",
    "lotti_cam",
    "cam_results",
    "cam_documents",
    "fascicolo_tecnico",
    "instruments",
    "welders",
    "audits",
    "non_conformities",
    "quality_scores",
    "smart_assignments",
    "gate_certifications",
    "consumables",
    "cost_entries",
    "backup_jobs",
    "team_invites",
    "notifications",
    "diario_produzione",
    "wps_records",
    "rdp_records",
    "sopralluoghi",
    "movimenti",
    "activity_log",
    "voci_lavoro",
    "officina_stati",
    "pacco_documenti",
    "sfridi",
    "qualita_records",
    "montaggio_records",
    "attrezzature",
    "documenti_archivio",
    "archivio_certificati",
    "dop_frazionate",
    "sal_acconti",
    "preventivatore_analisi",
    "kpi_snapshots",
    "calibrazioni",
    "manuale_capitoli",
    "riesami_tecnici",
    "registro_saldatura",
    "controllo_finale",
    "template_111_records",
    "report_ispezioni",
    "scadenziario_manutenzioni",
    "verbali_itt",
    "istruttorie",
    "validazioni_p1",
    "commesse_normative",
    "emissioni_documentali",
    "cantieri_sicurezza",
    "lib_fasi_lavoro",
    "lib_rischi_sicurezza",
    "lib_dpi_misure",
    "pacchetti_documentali",
    "obblighi_commessa",
    "pacchetti_committenza",
    "analisi_committenza",
    "profili_committente",
    "notifiche_smart",
    "onboarding_progress",
    "data_integrity_reports",
    "demo_sessions",
    "content_sources",
    "content_articles",
    "pos_documents",
    "componenti",
    "ddt_counter",
    "download_tokens",
]


async def migrate():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # 1. Ensure default tenant exists
    existing = await db.tenants.find_one({"tenant_id": "default"})
    if not existing:
        from datetime import datetime, timezone
        await db.tenants.insert_one({
            "tenant_id": "default",
            "nome_azienda": "Default Tenant",
            "email_admin": "",
            "piano": "pro",
            "attivo": True,
            "creato_il": datetime.now(timezone.utc).isoformat(),
            "impostazioni": {}
        })
        logger.info("Created default tenant")

    # 2. Backfill tenant_id on all data collections
    total_updated = 0
    for coll_name in DATA_COLLECTIONS:
        try:
            result = await db[coll_name].update_many(
                {"tenant_id": {"$exists": False}},
                {"$set": {"tenant_id": "default"}}
            )
            if result.modified_count > 0:
                logger.info(f"  {coll_name}: backfilled {result.modified_count} docs")
                total_updated += result.modified_count
        except Exception as e:
            logger.warning(f"  {coll_name}: skipped ({e})")

    logger.info(f"Migration complete. Total documents updated: {total_updated}")

    # 3. Create tenant_id indexes on high-traffic collections
    index_collections = [
        "clients", "commesse", "preventivi", "invoices", "fatture_ricevute",
        "ddt", "perizie", "rilievi", "articoli", "company_settings",
        "voci_lavoro", "audits", "non_conformities",
    ]
    for coll_name in index_collections:
        try:
            await db[coll_name].create_index(
                [("tenant_id", 1), ("user_id", 1)],
                name=f"idx_{coll_name}_tenant_user"
            )
        except Exception as e:
            logger.warning(f"  Index {coll_name}: {e}")

    logger.info("Tenant indexes created")
    client.close()


if __name__ == "__main__":
    asyncio.run(migrate())
