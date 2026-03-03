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
from routes.documents import router as documents_router
from routes.chat import router as chat_router
from routes.clients import router as clients_router
from routes.invoices import router as invoices_router
from routes.company import router as company_router
from routes.rilievi import router as rilievi_router
from routes.distinta import router as distinta_router
from routes.certificazioni import router as certificazioni_router
from routes.sicurezza import router as sicurezza_router
from routes.dashboard import router as dashboard_router
from routes.catalogo import router as catalogo_router
from routes.vendor_api import router as vendor_router
from routes.preventivi import router as preventivi_router
from routes.payment_types import router as payment_types_router
from routes.ddt import router as ddt_router
from routes.perizia import router as perizia_router
from routes.articoli import router as articoli_router
from routes.fatture_ricevute import router as fatture_ricevute_router
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
from routes.qrcode_gen import router as qrcode_router
from routes.db_cleanup import router as cleanup_router

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
    # Return a user-friendly message with details
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
