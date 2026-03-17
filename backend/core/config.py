import os
from typing import List
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    mongo_url: str = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name: str = os.environ.get("DB_NAME", "test_database")
    jwt_secret: str = os.environ.get("JWT_SECRET", "default-secret-change-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    session_expire_days: int = 7
    emergent_auth_url: str = ""
    cors_origins: str = os.environ.get("CORS_ORIGINS", "*")
    google_client_id: str = os.environ.get("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    resend_api_key: str = os.environ.get("RESEND_API_KEY", "")
    sender_email: str = os.environ.get("SENDER_EMAIL", "")
    sender_name: str = os.environ.get("SENDER_NAME", "")
    fic_access_token: str = os.environ.get("FIC_ACCESS_TOKEN", "")
    fic_company_id: str = os.environ.get("FIC_COMPANY_ID", "")
    sdi_environment: str = os.environ.get("SDI_ENVIRONMENT", "test")
    object_storage_url: str = os.environ.get("OBJECT_STORAGE_URL", "")
    domain_url: str = os.environ.get("DOMAIN_URL", "")

    @property
    def cors_origins_list(self) -> List[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
