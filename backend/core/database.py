"""Database connection and utilities."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from .config import settings
import logging

logger = logging.getLogger(__name__)

# MongoDB client initialization
client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongo_url)
db: AsyncIOMotorDatabase = client[settings.db_name]


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance."""
    return db


async def close_database():
    """Close database connection."""
    client.close()
    logger.info("Database connection closed")
