"""
Movimenti Bancari — Import CSV, riconciliazione scadenze, matching automatico.
"""
import csv
import io
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/movimenti", tags=["movimenti"])

COLL = "movimenti_bancari"


def new_id():
    return f"mov_{uuid.uuid4().hex[:12]}"


def ts():
    return datetime.now(timezone.utc)


# ─── Models ──────────────────────────────────────────────────────────────────

class RiconciliaRequest(BaseModel):
    scadenza_tipo: str          # "passiva" | "attiva"
    fattura_id: str
    scadenza_idx: Optional[int] = None   # index in scadenze_pagamento array
    importo: Optional[float] = None      # partial amount


# ─── IMPORT CSV ──────────────────────────────────────────────────────────────

@router.post("/import-csv")
async def import_csv(file: UploadFile = File(...), conto: str = Query("Banca MPS"), user: dict = Depends(get_current_user)):
    """Import movimenti da CSV estratto conto. Formato: data;descrizione;dare;avere;saldo (sep ; o ,)."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    raw = (await file.read()).decode("utf-8-sig", errors="replace")

    # Auto-detect separator
    sep = ";" if raw.count(";") > raw.count(",") else ","
    reader = csv.reader(io.StringIO(raw), delimiter=sep)
    rows = list(reader)
    if not rows:
        raise HTTPException(400, "File CSV vuoto")

    # Auto-detect header row
    header = [h.strip().lower() for h in rows[0]]
    data_col = desc_col = dare_col = avere_col = importo_col = None
    for i, h in enumerate(header):
        if h in ("data", "date", "data operazione", "data_operazione", "data valuta"):
            data_col = i
        elif h in ("descrizione", "description", "causale", "descrizione operazione"):
            desc_col = i
        elif h in ("dare", "addebito", "debit", "uscite"):
            dare_col = i
        elif h in ("avere", "accredito", "credit", "entrate"):
            avere_col = i
        elif h in ("importo", "amount", "movimento"):
            importo_col = i

    if data_col is None or desc_col is None:
        raise HTTPException(400, "Colonne 'data' e 'descrizione' non trovate nel CSV. Header trovato: " + str(header))

    imported = 0
    duplicates = 0
    errors = []

    for row_num, row in enumerate(rows[1:], 2):
        if len(row) <= max(data_col, desc_col):
            continue
        data_str = row[data_col].strip()
        descrizione = row[desc_col].strip()
        if not data_str or not descrizione:
            continue

        # Parse date (DD/MM/YYYY or YYYY-MM-DD)
        data_iso = None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
            try:
                data_iso = datetime.strptime(data_str, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue
        if not data_iso:
            errors.append(f"Riga {row_num}: data non valida '{data_str}'")
            continue

        # Parse importo
        importo = 0.0
        if dare_col is not None and avere_col is not None:
            dare_val = _parse_number(row[dare_col]) if dare_col < len(row) else 0
            avere_val = _parse_number(row[avere_col]) if avere_col < len(row) else 0
            if dare_val:
                importo = -abs(dare_val)
            elif avere_val:
                importo = abs(avere_val)
        elif importo_col is not None and importo_col < len(row):
            importo = _parse_number(row[importo_col])
        else:
            errors.append(f"Riga {row_num}: importo non trovato")
            continue

        if importo == 0:
            continue

        segno = "avere" if importo > 0 else "dare"

        # Dedup: same date + description + amount
        exists = await db[COLL].find_one({
            "user_id": uid, "tenant_id": tid, "data": data_iso, "descrizione": descrizione,
            "importo": round(importo, 2),
        })
        if exists:
            duplicates += 1
            continue

        doc = {
            "movimento_id": new_id(),
            "user_id": uid, "tenant_id": tid,
            "data": data_iso,
            "descrizione": descrizione,
            "importo": round(importo, 2),
            "segno": segno,
            "conto": conto,
            "stato_riconciliazione": "non_riconciliato",
            "scadenza_id": None,
            "fattura_id": None,
            "scadenza_tipo": None,
            "scadenza_idx": None,
            "created_at": ts(),
        }
        await db[COLL].insert_one(doc)
        imported += 1

    return {
        "message": f"Importati {imported} movimenti ({duplicates} duplicati ignorati)",
        "imported": imported,
        "duplicates": duplicates,
        "errors": errors[:10],
    }


def _parse_number(s: str) -> float:
    """Parse '1.234,56' or '1234.56' or '-500,00'."""
    s = s.strip().replace(" ", "")
    if not s or s == "-":
        return 0.0
    # Italian format: dots as thousands, comma as decimal
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


# ─── LIST MOVIMENTI ─────────────────────────────────────────────────────────

@router.get("/")
async def list_movimenti(
    data_dal: Optional[str] = Query(None),
    data_al: Optional[str] = Query(None),
    conto: Optional[str] = Query(None),
    stato: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(200),
    user: dict = Depends(get_current_user),
):
    uid = user["user_id"]
    tid = user["tenant_id"]
    filt = {"user_id": uid, "tenant_id": tid}
    if data_dal:
        filt.setdefault("data", {})["$gte"] = data_dal
    if data_al:
        filt.setdefault("data", {})["$lte"] = data_al
    if conto and conto != "__none__":
        filt["conto"] = conto
    if stato and stato != "__none__":
        filt["stato_riconciliazione"] = stato
    if search:
        filt["descrizione"] = {"$regex": search, "$options": "i"}

    total = await db[COLL].count_documents(filt)
    items = await db[COLL].find(filt, {"_id": 0}).sort("data", -1).skip(skip).limit(limit).to_list(limit)

    # KPIs
    all_items = await db[COLL].find({"user_id": uid, "tenant_id": tid}, {"_id": 0, "importo": 1, "segno": 1, "stato_riconciliazione": 1}).to_list(10000)
    non_ric = [m for m in all_items if m.get("stato_riconciliazione") == "non_riconciliato"]
    dare_nr = sum(abs(m["importo"]) for m in non_ric if m.get("segno") == "dare")
    avere_nr = sum(abs(m["importo"]) for m in non_ric if m.get("segno") == "avere")

    # Distinct conti for filter
    conti = await db[COLL].distinct("conto", {"user_id": uid, "tenant_id": tid})

    return {
        "items": items,
        "total": total,
        "kpi": {
            "non_riconciliati": len(non_ric),
            "dare_non_riconciliato": round(dare_nr, 2),
            "avere_non_riconciliato": round(avere_nr, 2),
        },
        "conti": sorted(conti),
    }


# ─── SCADENZE CANDIDATE PER RICONCILIAZIONE ─────────────────────────────────

@router.get("/{movimento_id}/scadenze-candidate")
async def get_scadenze_candidate(movimento_id: str, user: dict = Depends(get_current_user)):
    """Restituisce scadenze aperte con importo simile (±10%) per riconciliazione manuale."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    mov = await db[COLL].find_one({"movimento_id": movimento_id, "user_id": uid, "tenant_id": tid}, {"_id": 0})
    if not mov:
        raise HTTPException(404, "Movimento non trovato")

    importo_abs = abs(mov["importo"])
    margin = importo_abs * 0.10
    low = importo_abs - margin
    high = importo_abs + margin

    candidates = []

    if mov["segno"] == "dare":
        # Uscita → cerco fatture passive con scadenze aperte
        fatture = await db.fatture_ricevute.find(
            {"user_id": uid, "tenant_id": tid, "payment_status": {"$nin": ["pagata"]}},
            {"_id": 0, "fr_id": 1, "numero_documento": 1, "fornitore_nome": 1,
             "totale_documento": 1, "scadenze_pagamento": 1, "data_scadenza_pagamento": 1, "residuo": 1}
        ).to_list(500)
        for f in fatture:
            scadenze = f.get("scadenze_pagamento") or []
            if scadenze:
                for idx, s in enumerate(scadenze):
                    if s.get("pagata"):
                        continue
                    imp = s.get("importo", 0)
                    if low <= imp <= high:
                        candidates.append({
                            "tipo": "passiva",
                            "fattura_id": f["fr_id"],
                            "numero": f.get("numero_documento", ""),
                            "soggetto": f.get("fornitore_nome", ""),
                            "importo": imp,
                            "data_scadenza": s.get("data_scadenza", ""),
                            "scadenza_idx": idx,
                        })
            else:
                residuo = f.get("residuo") or f.get("totale_documento", 0)
                if low <= residuo <= high:
                    candidates.append({
                        "tipo": "passiva",
                        "fattura_id": f["fr_id"],
                        "numero": f.get("numero_documento", ""),
                        "soggetto": f.get("fornitore_nome", ""),
                        "importo": residuo,
                        "data_scadenza": f.get("data_scadenza_pagamento", ""),
                        "scadenza_idx": None,
                    })
    else:
        # Entrata → cerco fatture attive con scadenze aperte
        invoices = await db.invoices.find(
            {"user_id": uid, "tenant_id": tid, "payment_status": {"$nin": ["pagata", "paid"]}},
            {"_id": 0, "invoice_id": 1, "number": 1, "client_name": 1,
             "totals": 1, "scadenze_pagamento": 1, "due_date": 1}
        ).to_list(500)
        for inv in invoices:
            scadenze = inv.get("scadenze_pagamento") or []
            if scadenze:
                for idx, s in enumerate(scadenze):
                    if s.get("pagata"):
                        continue
                    imp = s.get("importo", 0)
                    if low <= imp <= high:
                        candidates.append({
                            "tipo": "attiva",
                            "fattura_id": inv["invoice_id"],
                            "numero": inv.get("number", ""),
                            "soggetto": inv.get("client_name", ""),
                            "importo": imp,
                            "data_scadenza": s.get("data_scadenza", ""),
                            "scadenza_idx": idx,
                        })
            else:
                tot = (inv.get("totals") or {}).get("total_document", 0)
                if low <= tot <= high:
                    candidates.append({
                        "tipo": "attiva",
                        "fattura_id": inv["invoice_id"],
                        "numero": inv.get("number", ""),
                        "soggetto": inv.get("client_name", ""),
                        "importo": tot,
                        "data_scadenza": inv.get("due_date", ""),
                        "scadenza_idx": None,
                    })

    # Sort by importo distance
    candidates.sort(key=lambda c: abs(c["importo"] - importo_abs))
    return {"candidates": candidates[:20], "movimento": mov}


# ─── RICONCILIA MANUALE ─────────────────────────────────────────────────────

@router.patch("/{movimento_id}/riconcilia")
async def riconcilia_movimento(movimento_id: str, body: RiconciliaRequest, user: dict = Depends(get_current_user)):
    """Collega un movimento bancario a una scadenza e aggiorna lo stato pagamento."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    mov = await db[COLL].find_one({"movimento_id": movimento_id, "user_id": uid, "tenant_id": tid}, {"_id": 0})
    if not mov:
        raise HTTPException(404, "Movimento non trovato")
    if mov.get("stato_riconciliazione") == "riconciliato":
        raise HTTPException(400, "Movimento già riconciliato")

    today_iso = date.today().isoformat()

    if body.scadenza_tipo == "passiva":
        # Update fattura ricevuta
        fat = await db.fatture_ricevute.find_one({"fr_id": body.fattura_id, "user_id": uid, "tenant_id": tid})
        if not fat:
            raise HTTPException(404, "Fattura passiva non trovata")

        importo_pag = body.importo or abs(mov["importo"])
        scadenze = fat.get("scadenze_pagamento") or []
        if body.scadenza_idx is not None and body.scadenza_idx < len(scadenze):
            scadenze[body.scadenza_idx]["pagata"] = True
            scadenze[body.scadenza_idx]["data_pagamento"] = today_iso
            await db.fatture_ricevute.update_one(
                {"fr_id": body.fattura_id},
                {"$set": {f"scadenze_pagamento.{body.scadenza_idx}.pagata": True,
                          f"scadenze_pagamento.{body.scadenza_idx}.data_pagamento": today_iso}}
            )

        # Update totale_pagato / residuo / payment_status
        tot_doc = fat.get("totale_documento", 0)
        pagato = (fat.get("totale_pagato") or 0) + importo_pag
        residuo = max(0, tot_doc - pagato)
        ps = "pagata" if residuo <= 0.01 else "parziale"
        await db.fatture_ricevute.update_one(
            {"fr_id": body.fattura_id},
            {"$set": {"totale_pagato": round(pagato, 2), "residuo": round(residuo, 2),
                       "payment_status": ps, "data_ultimo_pagamento": today_iso}}
        )

    elif body.scadenza_tipo == "attiva":
        inv = await db.invoices.find_one({"invoice_id": body.fattura_id, "user_id": uid, "tenant_id": tid})
        if not inv:
            raise HTTPException(404, "Fattura attiva non trovata")

        scadenze = inv.get("scadenze_pagamento") or []
        if body.scadenza_idx is not None and body.scadenza_idx < len(scadenze):
            await db.invoices.update_one(
                {"invoice_id": body.fattura_id},
                {"$set": {f"scadenze_pagamento.{body.scadenza_idx}.pagata": True,
                          f"scadenze_pagamento.{body.scadenza_idx}.data_pagamento": today_iso}}
            )

        # Update payment_status
        tot = (inv.get("totals") or {}).get("total_document", 0)
        importo_pag = body.importo or abs(mov["importo"])
        pagato = (inv.get("totale_pagato") or 0) + importo_pag
        residuo = max(0, tot - pagato)
        ps = "pagata" if residuo <= 0.01 else "parziale"
        await db.invoices.update_one(
            {"invoice_id": body.fattura_id},
            {"$set": {"totale_pagato": round(pagato, 2), "residuo": round(residuo, 2),
                       "payment_status": ps}}
        )
    else:
        raise HTTPException(400, "scadenza_tipo deve essere 'passiva' o 'attiva'")

    # Update movimento
    await db[COLL].update_one(
        {"movimento_id": movimento_id},
        {"$set": {
            "stato_riconciliazione": "riconciliato",
            "fattura_id": body.fattura_id,
            "scadenza_tipo": body.scadenza_tipo,
            "scadenza_idx": body.scadenza_idx,
            "data_riconciliazione": today_iso,
        }}
    )

    return {"message": "Movimento riconciliato con successo"}


# ─── AUTO RICONCILIA ─────────────────────────────────────────────────────────

@router.post("/auto-riconcilia")
async def auto_riconcilia(user: dict = Depends(get_current_user)):
    """Matching automatico: importo esatto + fornitore/cliente nella descrizione."""
    uid = user["user_id"]
    tid = user["tenant_id"]
    movimenti = await db[COLL].find(
        {"user_id": uid, "tenant_id": tid, "stato_riconciliazione": "non_riconciliato"},
        {"_id": 0}
    ).to_list(5000)

    matched = 0

    for mov in movimenti:
        importo_abs = abs(mov["importo"])
        desc_lower = (mov.get("descrizione") or "").lower()

        if mov["segno"] == "dare":
            # Match fatture passive per importo esatto
            fatture = await db.fatture_ricevute.find(
                {"user_id": uid, "tenant_id": tid, "payment_status": {"$nin": ["pagata"]}},
                {"_id": 0, "fr_id": 1, "fornitore_nome": 1, "totale_documento": 1,
                 "scadenze_pagamento": 1, "residuo": 1}
            ).to_list(500)

            for f in fatture:
                fornitore = (f.get("fornitore_nome") or "").lower()
                if not fornitore or fornitore not in desc_lower:
                    continue

                scadenze = f.get("scadenze_pagamento") or []
                riconciliato = False
                for idx, s in enumerate(scadenze):
                    if s.get("pagata"):
                        continue
                    if abs(s.get("importo", 0) - importo_abs) < 0.02:
                        body = RiconciliaRequest(scadenza_tipo="passiva", fattura_id=f["fr_id"], scadenza_idx=idx)
                        await riconcilia_movimento(mov["movimento_id"], body, user)
                        matched += 1
                        riconciliato = True
                        break

                if riconciliato:
                    break

                # Fallback: match on total residuo
                residuo = f.get("residuo") or f.get("totale_documento", 0)
                if abs(residuo - importo_abs) < 0.02:
                    body = RiconciliaRequest(scadenza_tipo="passiva", fattura_id=f["fr_id"], importo=importo_abs)
                    await riconcilia_movimento(mov["movimento_id"], body, user)
                    matched += 1
                    break

        else:
            # Match fatture attive per importo esatto
            invoices = await db.invoices.find(
                {"user_id": uid, "tenant_id": tid, "payment_status": {"$nin": ["pagata", "paid"]}},
                {"_id": 0, "invoice_id": 1, "client_name": 1, "totals": 1,
                 "scadenze_pagamento": 1}
            ).to_list(500)

            for inv in invoices:
                client = (inv.get("client_name") or "").lower()
                if not client or client not in desc_lower:
                    continue

                scadenze = inv.get("scadenze_pagamento") or []
                riconciliato = False
                for idx, s in enumerate(scadenze):
                    if s.get("pagata"):
                        continue
                    if abs(s.get("importo", 0) - importo_abs) < 0.02:
                        body = RiconciliaRequest(scadenza_tipo="attiva", fattura_id=inv["invoice_id"], scadenza_idx=idx)
                        await riconcilia_movimento(mov["movimento_id"], body, user)
                        matched += 1
                        riconciliato = True
                        break

                if riconciliato:
                    break

                tot = (inv.get("totals") or {}).get("total_document", 0)
                if abs(tot - importo_abs) < 0.02:
                    body = RiconciliaRequest(scadenza_tipo="attiva", fattura_id=inv["invoice_id"], importo=importo_abs)
                    await riconcilia_movimento(mov["movimento_id"], body, user)
                    matched += 1
                    break

    return {"message": f"Auto-riconciliazione completata: {matched} movimenti abbinati", "matched": matched}
