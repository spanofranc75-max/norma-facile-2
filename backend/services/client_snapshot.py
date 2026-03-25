"""Client snapshot service — creates immutable snapshots of client data for documents.

When a document is created or updated, call `build_snapshot(client_id)` to get
a frozen copy of the client's anagrafica at that point in time.
Documents should store this as `client_snapshot` and use it for display/PDF/email.
"""
from core.database import db

# Fields to include in the snapshot
SNAPSHOT_FIELDS = [
    "client_id", "business_name", "partita_iva", "codice_fiscale",
    "codice_sdi", "pec", "email", "address", "cap", "city",
    "province", "country", "phone", "cellulare",
    "persona_fisica", "titolo", "cognome", "nome",
    "payment_type_id", "payment_type_label", "iban", "banca",
]


async def build_snapshot(client_id: str) -> dict:
    """Fetch current client data and return a snapshot dict.
    Returns empty dict if client not found.
    """
    if not client_id:
        return {}
    client = await db.clients.find_one({"client_id": client_id}, {"_id": 0})
    if not client:
        return {}
    return {k: client.get(k) for k in SNAPSHOT_FIELDS}


def snapshot_from_doc(doc: dict) -> dict:
    """Extract snapshot fields from an existing document's inline fields (for migration)."""
    return {k: doc.get(k) for k in SNAPSHOT_FIELDS if doc.get(k) is not None}
