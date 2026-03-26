"""Tenant-isolated counters for commesse, fatture, DDT, preventivi, etc.

Each counter is scoped to a tenant_id + counter_type + year.
Uses MongoDB atomic find_one_and_update for concurrency safety.
"""
from core.database import db
import logging

logger = logging.getLogger(__name__)

COLLECTION = "tenant_counters"


async def get_next_counter(tenant_id: str, counter_type: str, year: int, prefix: str = "") -> str:
    """Get the next sequential number for a tenant-scoped counter.
    
    Args:
        tenant_id: The tenant identifier
        counter_type: Type of counter (e.g. 'commessa', 'fattura', 'ddt', 'preventivo', 'nota_credito')
        year: The year for the counter
        prefix: Optional prefix for the formatted number (e.g. 'NF', 'FT', 'NC', 'DDT', 'PRV')
    
    Returns:
        Formatted number string, e.g. "NF-2026-000042"
    """
    counter_id = f"{tenant_id}_{counter_type}_{year}"

    result = await db[COLLECTION].find_one_and_update(
        {"counter_id": counter_id},
        {
            "$inc": {"value": 1},
            "$setOnInsert": {
                "tenant_id": tenant_id,
                "counter_type": counter_type,
                "year": year,
            },
        },
        upsert=True,
        return_document=True,
    )

    next_num = result.get("value", 1)

    if prefix:
        return f"{prefix}-{year}-{next_num:06d}"
    return str(next_num)


async def seed_counter(tenant_id: str, counter_type: str, year: int, start_value: int) -> None:
    """Seed a counter to a specific starting value (for migration)."""
    counter_id = f"{tenant_id}_{counter_type}_{year}"

    existing = await db[COLLECTION].find_one({"counter_id": counter_id})
    if existing:
        logger.info(f"Counter {counter_id} already exists at {existing.get('value')}, skipping seed")
        return

    await db[COLLECTION].insert_one({
        "counter_id": counter_id,
        "tenant_id": tenant_id,
        "counter_type": counter_type,
        "year": year,
        "value": start_value,
    })
    logger.info(f"Counter {counter_id} seeded at {start_value}")


async def get_counter_value(tenant_id: str, counter_type: str, year: int) -> int:
    """Get current counter value without incrementing."""
    counter_id = f"{tenant_id}_{counter_type}_{year}"
    doc = await db[COLLECTION].find_one({"counter_id": counter_id}, {"_id": 0})
    return doc.get("value", 0) if doc else 0


async def list_counters(tenant_id: str) -> list:
    """List all counters for a tenant."""
    docs = await db[COLLECTION].find(
        {"tenant_id": tenant_id}, {"_id": 0}
    ).to_list(100)
    return docs
