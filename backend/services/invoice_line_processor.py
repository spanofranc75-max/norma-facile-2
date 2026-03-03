"""Invoice line processing — Smart matching, PMP calculation, row allocation."""
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional
from core.database import db

logger = logging.getLogger(__name__)


async def match_article(user_id: str, descrizione: str, codice_articolo: str = "") -> Optional[dict]:
    """Find best matching article in catalog by code or description."""
    if codice_articolo:
        match = await db.articoli.find_one(
            {"user_id": user_id, "codice": {"$regex": f"^{re.escape(codice_articolo)}$", "$options": "i"}},
            {"_id": 0, "articolo_id": 1, "codice": 1, "descrizione": 1, "prezzo_unitario": 1,
             "giacenza": 1, "prezzo_medio_ponderato": 1}
        )
        if match:
            return match

    if descrizione and len(descrizione) >= 3:
        # Clean description for matching
        clean = re.sub(r'[—–\-]+.*$', '', descrizione).strip()[:40]
        if len(clean) >= 3:
            match = await db.articoli.find_one(
                {"user_id": user_id, "descrizione": {"$regex": re.escape(clean), "$options": "i"}},
                {"_id": 0, "articolo_id": 1, "codice": 1, "descrizione": 1, "prezzo_unitario": 1,
                 "giacenza": 1, "prezzo_medio_ponderato": 1}
            )
            if match:
                return match
    return None


def calc_pmp(current_qty: float, current_pmp: float, new_qty: float, new_price: float) -> float:
    """Calculate weighted average price (Prezzo Medio Ponderato)."""
    if current_qty + new_qty <= 0:
        return new_price
    total_value = (current_qty * current_pmp) + (new_qty * new_price)
    total_qty = current_qty + new_qty
    return round(total_value / total_qty, 4)


async def update_article_inventory(
    articolo_id: str,
    new_qty: float,
    new_price: float,
    fornitore_nome: str = "",
    fr_id: str = "",
) -> dict:
    """Update article with new purchase data: giacenza, PMP, ultimo prezzo."""
    now = datetime.now(timezone.utc)
    art = await db.articoli.find_one({"articolo_id": articolo_id}, {"_id": 0})
    if not art:
        return {}

    old_qty = art.get("giacenza", 0) or 0
    old_pmp = art.get("prezzo_medio_ponderato", art.get("prezzo_unitario", 0)) or 0
    new_pmp = calc_pmp(old_qty, old_pmp, new_qty, new_price)

    update = {
        "giacenza": round(old_qty + new_qty, 4),
        "prezzo_medio_ponderato": new_pmp,
        "ultimo_prezzo_acquisto": round(new_price, 4),
        "prezzo_unitario": round(new_price, 4),
        "updated_at": now,
    }
    if fornitore_nome:
        update["ultimo_fornitore"] = fornitore_nome

    # Append to storico_prezzi
    history_entry = {
        "data": now.isoformat(),
        "prezzo": round(new_price, 4),
        "quantita": new_qty,
        "fornitore": fornitore_nome,
        "fr_id": fr_id,
        "pmp_dopo": new_pmp,
    }

    await db.articoli.update_one(
        {"articolo_id": articolo_id},
        {"$set": update, "$push": {"storico_prezzi": history_entry}}
    )
    logger.info(f"Article {articolo_id}: qty {old_qty}->{round(old_qty + new_qty, 4)}, PMP {old_pmp}->{new_pmp}")
    return {**update, "pmp_precedente": old_pmp, "giacenza_precedente": old_qty}


async def create_article_from_line(
    user_id: str,
    line: dict,
    fornitore_nome: str = "",
    fornitore_id: str = "",
    fr_id: str = "",
) -> dict:
    """Create a new article from an invoice line."""
    now = datetime.now(timezone.utc)
    art_id = f"art_{uuid.uuid4().hex[:12]}"

    doc = {
        "articolo_id": art_id,
        "user_id": user_id,
        "codice": line.get("codice_articolo") or f"AUTO-{art_id[-6:].upper()}",
        "descrizione": line.get("descrizione", "Articolo senza descrizione"),
        "categoria": "materiale",
        "unita_misura": (line.get("unita_misura") or "pz").lower(),
        "prezzo_unitario": round(line.get("prezzo_unitario", 0), 4),
        "aliquota_iva": "22",
        "fornitore_nome": fornitore_nome,
        "fornitore_id": fornitore_id,
        "note": f"Creato da fattura {fr_id}",
        "giacenza": round(line.get("quantita", 0), 4),
        "prezzo_medio_ponderato": round(line.get("prezzo_unitario", 0), 4),
        "ultimo_prezzo_acquisto": round(line.get("prezzo_unitario", 0), 4),
        "ultimo_fornitore": fornitore_nome,
        "storico_prezzi": [{
            "data": now.isoformat(),
            "prezzo": round(line.get("prezzo_unitario", 0), 4),
            "quantita": line.get("quantita", 0),
            "fornitore": fornitore_nome,
            "fr_id": fr_id,
        }],
        "created_at": now,
        "updated_at": now,
    }
    await db.articoli.insert_one(doc)
    logger.info(f"Created article {art_id} from invoice line: {doc['descrizione']}")
    return {"articolo_id": art_id, "codice": doc["codice"], "descrizione": doc["descrizione"]}
