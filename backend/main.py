"""
Norma Facile 2.0 - Main Application Entry Point
LegalTech SaaS for Italian legal professionals.
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
    title="Norma Facile 2.0",
    description="Piattaforma LegalTech per professionisti legali italiani",
    version="2.0.0",
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


@app.get("/api/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Benvenuto a Norma Facile 2.0",
        "version": "2.0.0",
        "status": "operativo"
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "service": "Norma Facile 2.0",
        "version": "2.0.0"
    }
