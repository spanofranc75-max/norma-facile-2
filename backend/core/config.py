"""
NormaFacile - Configuration Module
Centralizes all environment variables and configuration settings.
"""
import os
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from functools import lru_cache

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')


class Settings(BaseModel):
    # Database
    mongo_url: str = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name: str = os.environ.get('DB_NAME', 'test_database')

    # Auth
    jwt_secret: str = os.environ.get('JWT_SECRET', '')
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    session_expire_days: int = 7
    emergent_auth_url: str = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

    # CORS
    cors_origins: str = os.environ.get('CORS_ORIGINS', '*')

    @property
    def cors_origins_list(self) -> List[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Domain
    domain_url: str = os.environ.get('DOMAIN_URL', 'https://www.1090normafacile.it')

    # Email (Resend)
    resend_api_key: Optional[str] = os.environ.get('RESEND_API_KEY')
    sender_email: str = os.environ.get('SENDER_EMAIL', 'fatture@steelprojectdesign.it')
    sender_name: str = os.environ.get('SENDER_NAME', 'Steel Project Design Srls')

    # SDI (Aruba / FattureInCloud)
    sdi_api_key: Optional[str] = os.environ.get('SDI_API_KEY')
    sdi_api_secret: Optional[str] = os.environ.get('SDI_API_SECRET')
    sdi_environment: str = os.environ.get('SDI_ENVIRONMENT', 'test')
    fic_access_token: Optional[str] = os.environ.get('FIC_ACCESS_TOKEN')
    fic_company_id: Optional[str] = os.environ.get('FIC_COMPANY_ID')

    # LLM
    emergent_llm_key: str = os.environ.get('EMERGENT_LLM_KEY', '')
    openai_api_key: Optional[str] = os.environ.get('OPENAI_API_KEY')

    # Google OAuth
    google_client_id: Optional[str] = os.environ.get('GOOGLE_CLIENT_ID')
    google_client_secret: Optional[str] = os.environ.get('GOOGLE_CLIENT_SECRET')

    # App
    debug: bool = os.environ.get('DEBUG', 'false').lower() == 'true'
    log_level: str = os.environ.get('LOG_LEVEL', 'INFO')

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
