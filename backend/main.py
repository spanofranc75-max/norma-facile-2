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

# Import routers - with error logging
import sys as _sys
import importlib as _importlib

def _safe_import(module_path):
    try:
        m = _importlib.import_module(module_path)
        return m.router
    except Exception as e:
        print(f"FATAL IMPORT ERROR: {module_path} -> {e}", file=_sys.stderr, flush=True)
        raise

auth_router = _safe_import("routes.auth")
documents_router = _safe_import("routes.documents")
chat_router = _safe_import("routes.chat")
clients_router = _safe_import("routes.clients")
invoices_router = _safe_import("routes.invoices")
company_router = _safe_import("routes.company")
rilievi_router = _safe_import("routes.rilievi")
distinta_router = _safe_import("routes.distinta")
certificazioni_router = _safe_import("routes.certificazioni")
sicurezza_router = _safe_import("routes.sicurezza")
dashboard_router = _safe_import("routes.dashboard")
catalogo_router = _safe_import("routes.catalogo")
vendor_router = _safe_import("routes.vendor_api")
preventivi_router = _safe_import("routes.preventivi")
payment_types_router = _safe_import("routes.payment_types")
ddt_router = _safe_import("routes.ddt")
perizia_router = _safe_import("routes.perizia")
articoli_router = _safe_import("routes.articoli")
fatture_ricevute_router = _safe_import("routes.fatture_ricevute")
sopralluogo_router = _safe_import("routes.sopralluogo")
movimenti_router = _safe_import("routes.movimenti")
engine_router = _safe_import("routes.engine")
commesse_router = _safe_import("routes.commesse")
commessa_ops_router = _safe_import("routes.commessa_ops")
fpc_router = _safe_import("routes.fpc")
cam_router = _safe_import("routes.cam")
fascicolo_tecnico_router = _safe_import("routes.fascicolo_tecnico")
company_docs_router = _safe_import("routes.company_docs")
instruments_router = _safe_import("routes.instruments")
welders_router = _safe_import("routes.welders")
audits_router = _safe_import("routes.audits")
quality_hub_router = _safe_import("routes.quality_hub")
smart_assign_router = _safe_import("routes.smart_assign")
migrazione_router = _safe_import("routes.migrazione")
gate_cert_router = _safe_import("routes.gate_certification")
consumables_router = _safe_import("routes.consumables")
cost_control_router = _safe_import("routes.cost_control")
backup_router = _safe_import("routes.backup")
team_router = _safe_import("routes.team")
notifications_router = _safe_import("routes.notifications")
qrcode_router = _safe_import("routes.qrcode_gen")
cleanup_router = _safe_import("routes.db_cleanup")
wps_router = _safe_import("routes.wps")
rdp_router = _safe_import("routes.rdp")
search_router = _safe_import("routes.search")
activity_log_router = _safe_import("routes.activity_log")
personale_router = _safe_import("routes.personale")
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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https://.*\.emergentagent\.com|https://.*\.emergent\.host|https://.*\.netlify\.app",
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
app.include_router(documents_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(clients_router, prefix="/api")
app.include_router(invoices_router, prefix="/api")
app.include_router(company_router, prefix="/api")
app.include_router(rilievi_router, prefix="/api")
app.include_router(distinta_router, prefix="/api")
app.include_router(certificazioni_router, prefix="/api")
app.include_router(sicurezza_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(catalogo_router, prefix="/api")
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
app.include_router(qrcode_router, prefix="/api")
app.include_router(cleanup_router, prefix="/api")
app.include_router(wps_router, prefix="/api")
app.include_router(rdp_router, prefix="/api")
app.include_router(sopralluogo_router, prefix="/api")
app.include_router(movimenti_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(activity_log_router, prefix="/api")
app.include_router(personale_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Startup tasks: migrate existing users to have admin role."""
    logger.info("Norma Facile 2.0 starting up...")
    # Ensure all existing users without a role get 'admin' (legacy migration)
    await db.users.update_many(
        {"role": {"$exists": False}},
        {"$set": {"role": "admin"}},
    )


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
