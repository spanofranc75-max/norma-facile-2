"""
NormaFacile - Configuration Module
Centralizes all environment variables and configuration settings.
"""
import os
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')


class Settings(BaseSettings):
    # Database
    mongo_url: str = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name: str = os.environ.get('DB_NAME', 'test_database')

    # Auth
    jwt_secret: str = os.environ.get('JWT_SECRET', 'default-secret-change-in-production')
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    session_expire_days: int = 7

    # CORS
    cors_origins: str = os.environ.get('CORS_ORIGINS', '*')

    # Google OAuth
    google_client_id: str = os.environ.get('GOOGLE_CLIENT_ID', '')
    google_client_secret: str = os.environ.get('GOOGLE_CLIENT_SECRET', '')

    # Email
    resend_api_key: str = os.environ.get('RESEND_API_KEY', '')
    sender_email: str = os.environ.get('SENDER_EMAIL', '')
    sender_name: str = os.environ.get('SENDER_NAME', '')

    # FattureInCloud
    fic_access_token: str = os.environ.get('FIC_ACCESS_TOKEN', '')
    fic_company_id: str = os.environ.get('FIC_COMPANY_ID', '')

    # SDI
    sdi_environment: str = os.environ.get('SDI_ENVIRONMENT', 'test')

    # Storage
    object_storage_url: str = os.environ.get('OBJECT_STORAGE_URL', '')

    # Domain
    domain_url: str = os.environ.get('DOMAIN_URL', '')

    @property
    def cors_origins_list(self) -> List[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
