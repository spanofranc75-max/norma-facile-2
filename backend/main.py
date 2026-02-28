"""
Norma Facile 2.0 - Main Application Entry Point
CRM/ERP per Fabbri (Metalworkers).
"""
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

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
    yield
    # Shutdown
    await close_database()
    logger.info("Norma Facile 2.0 shutting down...")


# Create FastAPI application
app = FastAPI(
    title="Norma Facile 2.0 - Core Engine",
    description="CRM/ERP per Fabbri - Gestione commesse, fatturazione e certificazioni CE",
    version="2.0.1",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.cors_origins.split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(fpc_router)


@app.get("/api/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Benvenuto a Norma Facile 2.0",
        "version": "2.0.1",
        "status": "operativo"
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "service": "Norma Facile 2.0",
        "version": "2.0.1"
    }
