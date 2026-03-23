"""
Norma Facile 2.0 - Main Application Entry Point
CRM/ERP per Fabbri (Metalworkers).
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from core.database import db

logger = logging.getLogger(__name__)

# Import core modules
from core.config import settings
from core.database import close_database

# Import routers
from routes.auth import router as auth_router
from routes.clients import router as clients_router
from routes.invoices import router as invoices_router
from routes.company import router as company_router
from routes.rilievi import router as rilievi_router
from routes.distinta import router as distinta_router
from routes.certificazioni import router as certificazioni_router
from routes.sicurezza import router as sicurezza_router
from routes.dashboard import router as dashboard_router
from routes.catalogo import router as catalogo_router
from routes.verbale_posa import router as verbale_posa_router
from routes.vendor_api import router as vendor_router
from routes.preventivi import router as preventivi_router
from routes.payment_types import router as payment_types_router
from routes.ddt import router as ddt_router
from routes.perizia import router as perizia_router
from routes.articoli import router as articoli_router
from routes.fatture_ricevute import router as fatture_ricevute_router
from routes.sopralluogo import router as sopralluogo_router
from routes.movimenti import router as movimenti_router
from routes.engine import router as engine_router
from routes.commesse import router as commesse_router
from routes.commessa_ops import router as commessa_ops_router
from routes.fpc import router as fpc_router
from routes.cam import router as cam_router
from routes.fascicolo_tecnico import router as fascicolo_tecnico_router
from routes.company_docs import router as company_docs_router
from routes.instruments import router as instruments_router
from routes.welders import router as welders_router
from routes.audits import router as audits_router
from routes.quality_hub import router as quality_hub_router
from routes.smart_assign import router as smart_assign_router
from routes.migrazione import router as migrazione_router
from routes.gate_certification import router as gate_cert_router
from routes.consumables import router as consumables_router
from routes.cost_control import router as cost_control_router
from routes.backup import router as backup_router
from routes.team import router as team_router
from routes.notifications import router as notifications_router
from routes.diario_produzione import router as diario_produzione_router
from routes.qrcode_gen import router as qrcode_router
from routes.db_cleanup import router as cleanup_router
from routes.wps import router as wps_router
from routes.rdp import router as rdp_router
from routes.search import router as search_router
from routes.activity_log import router as activity_log_router
from routes.voci_lavoro import router as voci_lavoro_router
from routes.officina import router as officina_router
from routes.pacco_documenti import router as pacco_documenti_router
from routes.smistatore import router as smistatore_router
from routes.sfridi import router as sfridi_router
from routes.qualita import router as qualita_router
from routes.montaggio import router as montaggio_router
from routes.attrezzature import router as attrezzature_router
from routes.archivio import router as archivio_router
from routes.sicurezza import router as sicurezza_router
from routes.dop_frazionata import router as dop_frazionata_router
from routes.sal_acconti import router as sal_acconti_router
from routes.preventivatore import router as preventivatore_router
from routes.kpi_dashboard import router as kpi_dashboard_router
from routes.calibrazione import router as calibrazione_router
from routes.manuale import router as manuale_router
from routes.riesame_tecnico import router as riesame_router
from routes.registro_saldatura import router as registro_saldatura_router
from routes.controllo_finale import router as controllo_finale_router
from routes.template_111 import router as template_111_router
from routes.report_ispezioni import router as report_ispezioni_router
from routes.scadenziario_manutenzioni import router as scad_manut_router
from routes.verbali_itt import router as verbali_itt_router
from routes.istruttoria import router as istruttoria_router
from routes.validation import router as validation_router
from routes.commesse_normative import router as commesse_normative_router
from routes.cantieri_sicurezza import router as cantieri_sicurezza_router
from routes.pacchetti_documentali import router as pacchetti_documentali_router
from routes.obblighi_commessa import router as obblighi_commessa_router
from routes.committenza import router as committenza_router
from routes.profili_committente import router as profili_committente_router
from routes.notifiche_smart import router as notifiche_smart_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Norma Facile 2.0 starting up...")
    # Start the watchdog scheduler
    from services.notification_scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    # Init object storage
    try:
        from services.object_storage import init_storage
        init_storage()
    except Exception as e:
        logger.warning(f"Object storage init deferred: {e}")
    yield
    # Shutdown
    stop_scheduler()
    await close_database()
    logger.info("Norma Facile 2.0 shutting down...")


# Create FastAPI application
app = FastAPI(
    title="Norma Facile 2.0 - Core Engine",
    description="CRM/ERP per Fabbri - Gestione commesse, fatturazione e certificazioni CE",
    version="2.1.0",
    lifespan=lifespan
)

# Add CORS middleware
_cors_origins = [o.strip() for o in settings.cors_origins.split(',') if o.strip() and o.strip() != '*']
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https://.*\.emergentagent\.com|https://.*\.emergent\.host",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log validation errors in detail for debugging
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    logger.error(f"Validation error on {request.method} {request.url.path}: {errors}")
    field_errors = []
    for err in errors:
        loc = " -> ".join(str(x) for x in err.get("loc", []))
        msg = err.get("msg", "")
        field_errors.append(f"{loc}: {msg}")
    detail = "; ".join(field_errors) if field_errors else "Errore di validazione"
    return JSONResponse(status_code=422, content={"detail": detail})

# Include routers with /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(clients_router, prefix="/api")
app.include_router(invoices_router, prefix="/api")
app.include_router(company_router, prefix="/api")
app.include_router(rilievi_router, prefix="/api")
app.include_router(distinta_router, prefix="/api")
app.include_router(certificazioni_router, prefix="/api")
app.include_router(sicurezza_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(catalogo_router, prefix="/api")
app.include_router(verbale_posa_router, prefix="/api")
app.include_router(vendor_router, prefix="/api")
app.include_router(preventivi_router, prefix="/api")
app.include_router(payment_types_router, prefix="/api")
app.include_router(ddt_router, prefix="/api")
app.include_router(perizia_router, prefix="/api")
app.include_router(articoli_router, prefix="/api")
app.include_router(fatture_ricevute_router, prefix="/api")
app.include_router(engine_router, prefix="/api")
app.include_router(commesse_router, prefix="/api")
app.include_router(commessa_ops_router, prefix="/api")
app.include_router(fpc_router)
app.include_router(cam_router, prefix="/api")
app.include_router(fascicolo_tecnico_router, prefix="/api")
app.include_router(company_docs_router, prefix="/api")
app.include_router(instruments_router, prefix="/api")
app.include_router(welders_router, prefix="/api")
app.include_router(audits_router, prefix="/api")
app.include_router(quality_hub_router, prefix="/api")
app.include_router(smart_assign_router, prefix="/api")
app.include_router(migrazione_router, prefix="/api")
app.include_router(gate_cert_router, prefix="/api")
app.include_router(consumables_router, prefix="/api")
app.include_router(cost_control_router, prefix="/api")
app.include_router(backup_router, prefix="/api")
app.include_router(team_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(diario_produzione_router, prefix="/api")
app.include_router(qrcode_router, prefix="/api")
app.include_router(cleanup_router, prefix="/api")
app.include_router(wps_router, prefix="/api")
app.include_router(rdp_router, prefix="/api")
app.include_router(sopralluogo_router, prefix="/api")
app.include_router(movimenti_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(activity_log_router, prefix="/api")
app.include_router(voci_lavoro_router, prefix="/api")
app.include_router(officina_router, prefix="/api")
app.include_router(pacco_documenti_router, prefix="/api")
app.include_router(smistatore_router, prefix="/api")
app.include_router(sfridi_router, prefix="/api")
app.include_router(qualita_router, prefix="/api")
app.include_router(montaggio_router, prefix="/api")
app.include_router(attrezzature_router, prefix="/api")
app.include_router(archivio_router, prefix="/api")
app.include_router(sicurezza_router, prefix="/api")
app.include_router(dop_frazionata_router, prefix="/api")
app.include_router(sal_acconti_router, prefix="/api")
app.include_router(preventivatore_router, prefix="/api")
app.include_router(kpi_dashboard_router, prefix="/api")
app.include_router(calibrazione_router, prefix="/api")
app.include_router(manuale_router, prefix="/api")
app.include_router(riesame_router, prefix="/api")
app.include_router(registro_saldatura_router, prefix="/api")
app.include_router(controllo_finale_router, prefix="/api")
app.include_router(template_111_router, prefix="/api")
app.include_router(report_ispezioni_router, prefix="/api")
app.include_router(scad_manut_router, prefix="/api")
app.include_router(verbali_itt_router, prefix="/api")
app.include_router(istruttoria_router, prefix="/api")
app.include_router(validation_router, prefix="/api")
app.include_router(commesse_normative_router, prefix="/api")
app.include_router(cantieri_sicurezza_router, prefix="/api")
app.include_router(pacchetti_documentali_router, prefix="/api")
app.include_router(obblighi_commessa_router, prefix="/api")
app.include_router(committenza_router, prefix="/api")
app.include_router(profili_committente_router, prefix="/api")
app.include_router(notifiche_smart_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Startup tasks: migrate existing users to have admin role + create indices."""
    logger.info("Norma Facile 2.0 starting up...")
    # Ensure all existing users without a role get 'admin' (legacy migration)
    await db.users.update_many(
        {"role": {"$exists": False}},
        {"$set": {"role": "admin"}},
    )

    # Indici univoci per modello gerarchico commesse
    try:
        await db.commesse_normative.create_index(
            [("commessa_id", 1), ("normativa", 1), ("user_id", 1)],
            unique=True, name="uq_commessa_normativa"
        )
        await db.emissioni_documentali.create_index(
            [("ramo_id", 1), ("emission_type", 1), ("emission_seq", 1), ("user_id", 1)],
            unique=True, name="uq_emissione"
        )
        await db.emissioni_documentali.create_index(
            [("commessa_id", 1)], name="idx_emissioni_commessa"
        )
        # Indici per Safety Branch
        await db.cantieri_sicurezza.create_index(
            [("user_id", 1), ("cantiere_id", 1)],
            unique=True, name="uq_cantiere_sicurezza"
        )
        await db.cantieri_sicurezza.create_index(
            [("user_id", 1), ("parent_commessa_id", 1)],
            name="idx_cantiere_commessa"
        )
        # Libreria 3 livelli
        await db.lib_fasi_lavoro.create_index(
            [("user_id", 1), ("codice", 1)], unique=True, name="uq_lib_fasi"
        )
        await db.lib_fasi_lavoro.create_index(
            [("user_id", 1), ("categoria", 1)], name="idx_fasi_cat"
        )
        await db.lib_rischi_sicurezza.create_index(
            [("user_id", 1), ("codice", 1)], unique=True, name="uq_lib_rischi"
        )
        await db.lib_rischi_sicurezza.create_index(
            [("user_id", 1), ("categoria", 1), ("sottocategoria", 1)], name="idx_rischi_cat"
        )
        await db.lib_dpi_misure.create_index(
            [("user_id", 1), ("codice", 1)], unique=True, name="uq_lib_dpi"
        )
        await db.lib_dpi_misure.create_index(
            [("user_id", 1), ("tipo", 1)], name="idx_dpi_tipo"
        )
        # Indici Registro Obblighi Commessa
        await db.obblighi_commessa.create_index(
            [("dedupe_key", 1), ("user_id", 1)], unique=True, name="uq_obbligo_dedupe"
        )
        await db.obblighi_commessa.create_index(
            [("commessa_id", 1), ("user_id", 1), ("status", 1)], name="idx_obblighi_commessa"
        )
        await db.obblighi_commessa.create_index(
            [("user_id", 1), ("blocking_level_sort", 1), ("severity_sort", 1)],
            name="idx_obblighi_priority"
        )
        # Indici Verifica Committenza (C1)
        await db.pacchetti_committenza.create_index(
            [("package_id", 1), ("user_id", 1)], unique=True, name="uq_pkg_committenza"
        )
        await db.pacchetti_committenza.create_index(
            [("commessa_id", 1), ("user_id", 1)], name="idx_pkg_commessa"
        )
        await db.analisi_committenza.create_index(
            [("analysis_id", 1), ("user_id", 1)], unique=True, name="uq_analisi_committenza"
        )
        await db.analisi_committenza.create_index(
            [("commessa_id", 1), ("user_id", 1)], name="idx_analisi_commessa"
        )
    except Exception as e:
        logger.warning(f"Index creation (may already exist): {e}")


@app.get("/api/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Benvenuto a Norma Facile 2.0",
        "version": "2.1.0",
        "status": "operativo"
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "service": "Norma Facile 2.0",
        "version": "2.1.0"
    }
