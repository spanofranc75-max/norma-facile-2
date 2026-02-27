"""Application configuration settings."""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')


class Settings(BaseModel):
    """Application settings loaded from environment variables."""
    
    # Database
    mongo_url: str = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name: str = os.environ.get('DB_NAME', 'test_database')
    
    # CORS
    cors_origins: str = os.environ.get('CORS_ORIGINS', '*')
    
    # Auth
    session_expire_days: int = 7
    emergent_auth_url: str = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
    
    # LLM
    emergent_llm_key: str = os.environ.get('EMERGENT_LLM_KEY', '')
    
    class Config:
        env_file = ".env"


settings = Settings()
