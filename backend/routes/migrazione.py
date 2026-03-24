"""Migration endpoint — imports data from the old Norma Facile app."""
from fastapi import APIRouter, Depends, HTTPException
from core.security import get_current_user
from core.database import db
import httpx
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/migrazione", tags=["Migrazione"])

EXPORT_URL = "https://audit-stabilize-3.preview.emergentagent.com/api/export/migrazione-completa"


@router.post("/importa")
async def importa_da_vecchia_app(user: dict = Depends(get_current_user)):
    """Fetch all data from old app and import into current DB."""
    uid = user["user_id"]
    now = datetime.now(timezone.utc)
    results = {"anagrafica": 0, "preventivi": 0, "fatture_vendita": 0, "fatture_acquisto": 0, "skipped": 0, "errors": []}

    # 1. Fetch export data
    try:
        headers = {"User-Agent": "1090NormaFacile-Migration/2.1"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(EXPORT_URL, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        raise HTTPException(502, f"Errore connessione vecchia app: {str(e)}")

    # Build client lookup by P.IVA for linking
    piva_to_client_id = {}

    # ── 2. ANAGRAFICA ──
    for a in data.get("anagrafica", []):
        piva = (a.get("partita_iva") or "").strip()
        cf = (a.get("codice_fiscale") or "").strip()
        name = (a.get("business_name") or "").strip()
        if not name:
            continue

        # Check duplicate by P.IVA or name
        dup_filter = {"user_id": uid}
        if piva:
            dup_filter["partita_iva"] = piva
        else:
            dup_filter["business_name"] = name
        existing = await db.clients.find_one(dup_filter, {"_id": 0, "client_id": 1})
        if existing:
            if piva:
                piva_to_client_id[piva] = existing["client_id"]
            results["skipped"] += 1
            continue

        cid = f"cli_{uuid.uuid4().hex[:12]}"
        if piva:
            piva_to_client_id[piva] = cid

        tipo_raw = (a.get("tipo") or "cliente").lower()
        doc = {
            "client_id": cid,
            "user_id": uid,
            "business_name": name,
            "client_type": a.get("client_type", "azienda"),
            "codice_fiscale": cf,
            "partita_iva": piva,
            "codice_sdi": a.get("codice_sdi", ""),
            "pec": a.get("pec") or None,
            "address": a.get("address", ""),
            "cap": a.get("cap", ""),
            "city": a.get("city", ""),
            "province": a.get("province", ""),
            "country": a.get("country", "IT"),
            "phone": a.get("phone", ""),
            "email": a.get("email", ""),
            "notes": a.get("notes", ""),
            "tags": [tipo_raw] if tipo_raw in ("fornitore", "entrambi") else [],
            "created_at": now,
            "updated_at": now,
            "_migrated": True,
        }
        try:
            await db.clients.insert_one(doc)
            results["anagrafica"] += 1
        except Exception as e:
            results["errors"].append(f"Anagrafica {name}: {e}")

    # Rebuild lookup including pre-existing clients
    async for c in db.clients.find({"user_id": uid, "partita_iva": {"$exists": True, "$ne": ""}}, {"_id": 0, "client_id": 1, "partita_iva": 1}):
        piva_to_client_id[c["partita_iva"]] = c["client_id"]

    # ── 3. PREVENTIVI ──
    for p in data.get("preventivi", []):
        num = (p.get("number") or "").strip()
        if not num:
            continue

        existing = await db.preventivi.find_one({"user_id": uid, "number": num}, {"_id": 0, "preventivo_id": 1})
        if existing:
            results["skipped"] += 1
            continue

        # Link client by P.IVA
        client_piva = (p.get("client_partita_iva") or "").strip()
        client_id = piva_to_client_id.get(client_piva, "")

        lines = []
        for l in (p.get("lines") or []):
            lines.append({
                "line_id": f"ln_{uuid.uuid4().hex[:8]}",
                "description": l.get("description", ""),
                "codice_articolo": l.get("codice_articolo", ""),
                "quantity": float(l.get("quantity", 0)),
                "unit": l.get("unit", "pz"),
                "unit_price": float(l.get("unit_price", 0)),
                "prezzo_netto": float(l.get("unit_price", 0)),
                "sconto_1": float(l.get("sconto_1", 0)),
                "sconto_2": float(l.get("sconto_2", 0)),
                "vat_rate": str(l.get("vat_rate", "22")),
                "line_total": float(l.get("unit_price", 0)) * float(l.get("quantity", 0)),
                "notes": l.get("notes", ""),
            })

        totals = p.get("totals", {})
        doc = {
            "preventivo_id": f"prev_{uuid.uuid4().hex[:12]}",
            "user_id": uid,
            "number": num,
            "client_id": client_id,
            "subject": p.get("subject", ""),
            "validity_days": int(p.get("validity_days", 30)),
            "lines": lines,
            "sconto_globale": float(p.get("sconto_globale", 0)),
            "acconto": float(p.get("acconto", 0)),
            "totals": {
                "subtotal": float(totals.get("subtotal", 0)),
                "sconto_globale_value": float(totals.get("sconto_globale_value", 0)),
                "imponibile": float(totals.get("imponibile", 0)),
                "iva": float(totals.get("iva", 0)),
                "total": float(totals.get("total", 0)),
            },
            "notes": p.get("notes", ""),
            "status": p.get("status", "bozza"),
            "payment_type_id": "",
            "payment_type_label": p.get("payment_type", ""),
            "converted_to": None,
            "linked_distinta_id": None,
            "created_at": now,
            "updated_at": now,
            "_migrated": True,
            "_old_date": p.get("date", ""),
        }
        try:
            await db.preventivi.insert_one(doc)
            results["preventivi"] += 1
        except Exception as e:
            results["errors"].append(f"Preventivo {num}: {e}")

    # ── 4. FATTURE VENDITA ──
    for f in data.get("fatture_vendita", []):
        doc_num = (f.get("document_number") or "").strip()
        if not doc_num:
            continue

        issue_date = (f.get("issue_date") or "").strip()
        # Dedup by number + date (same number can exist in different months)
        existing = await db.invoices.find_one(
            {"user_id": uid, "document_number": doc_num, "issue_date": issue_date},
            {"_id": 0, "invoice_id": 1},
        )
        if existing:
            results["skipped"] += 1
            continue

        client_piva = (f.get("client_partita_iva") or "").strip()
        client_id = piva_to_client_id.get(client_piva, "")

        lines = []
        for l in (f.get("lines") or []):
            vr = str(l.get("vat_rate", "22")).replace(".0", "")
            lines.append({
                "line_id": f"line_{uuid.uuid4().hex[:8]}",
                "code": l.get("code", ""),
                "description": l.get("description", ""),
                "quantity": float(l.get("quantity", 0)),
                "unit_price": float(l.get("unit_price", 0)),
                "discount_percent": float(l.get("discount_percent", 0)),
                "vat_rate": vr,
                "line_total": float(l.get("line_total", 0)),
                "vat_amount": float(l.get("vat_amount", 0)),
            })

        totals = f.get("totals", {})
        tax_s = f.get("tax_settings", {})
        doc = {
            "invoice_id": f"inv_{uuid.uuid4().hex[:12]}",
            "user_id": uid,
            "document_type": f.get("document_type", "FT"),
            "document_number": doc_num,
            "client_id": client_id,
            "client_business_name": f.get("client_business_name", ""),
            "issue_date": f.get("issue_date", ""),
            "due_date": f.get("due_date", ""),
            "status": f.get("status", "emessa"),
            "sdi_status": f.get("sdi_status", ""),
            "sdi_id": f.get("sdi_id", ""),
            "payment_method": f.get("payment_method", ""),
            "payment_terms": f.get("payment_terms", ""),
            "lines": lines,
            "totals": {
                "subtotal": float(totals.get("subtotal", 0)),
                "vat_breakdown": totals.get("vat_breakdown", {}),
                "total_vat": float(totals.get("total_vat", 0)),
                "rivalsa_inps": 0.0,
                "cassa": 0.0,
                "ritenuta": 0.0,
                "total_document": float(totals.get("total_document", 0)),
                "total_to_pay": float(totals.get("total_to_pay", 0)),
            },
            "tax_settings": {
                "apply_rivalsa_inps": bool(tax_s.get("apply_rivalsa_inps")),
                "rivalsa_inps_rate": float(tax_s.get("rivalsa_inps_rate", 4.0)),
                "apply_cassa": bool(tax_s.get("apply_cassa")),
                "cassa_type": tax_s.get("cassa_type", ""),
                "cassa_rate": float(tax_s.get("cassa_rate", 4.0)),
                "apply_ritenuta": bool(tax_s.get("apply_ritenuta")),
                "ritenuta_rate": float(tax_s.get("ritenuta_rate", 20.0)),
                "ritenuta_base": tax_s.get("ritenuta_base", "imponibile"),
            },
            "notes": f.get("notes", ""),
            "internal_notes": "",
            "converted_from": None,
            "converted_to": None,
            "created_at": now,
            "updated_at": now,
            "_migrated": True,
            "_linked_preventivo_number": f.get("linked_preventivo_number", ""),
        }
        try:
            await db.invoices.insert_one(doc)
            results["fatture_vendita"] += 1
        except Exception as e:
            results["errors"].append(f"Fattura {doc_num}: {e}")

    # ── 5. FATTURE ACQUISTO ──
    for fa in data.get("fatture_acquisto", []):
        forn_nome = (fa.get("fornitore_nome") or "").strip()
        forn_piva = (fa.get("fornitore_partita_iva") or "").strip()
        num_doc = (fa.get("numero_documento") or "").strip()
        data_doc = (fa.get("data_documento") or "").strip()

        # Dedup: by fornitore + numero + data
        if num_doc and data_doc:
            dup = await db.fatture_ricevute.find_one(
                {"user_id": uid, "numero_documento": num_doc, "data_documento": data_doc, "fornitore_nome": forn_nome},
                {"_id": 0, "fr_id": 1}
            )
        elif forn_nome and fa.get("totale_documento"):
            dup = await db.fatture_ricevute.find_one(
                {"user_id": uid, "fornitore_nome": forn_nome, "totale_documento": fa.get("totale_documento"), "data_ricezione": fa.get("data_ricezione", "")},
                {"_id": 0, "fr_id": 1}
            )
        else:
            dup = None

        if dup:
            results["skipped"] += 1
            continue

        fornitore_id = piva_to_client_id.get(forn_piva, None)

        linee = []
        for i, l in enumerate(fa.get("linee") or []):
            linee.append({
                "numero_linea": l.get("numero_linea", i + 1),
                "codice_articolo": l.get("codice_articolo", ""),
                "descrizione": l.get("descrizione", ""),
                "quantita": float(l.get("quantita", 0)),
                "unita_misura": l.get("unita_misura", "pz"),
                "prezzo_unitario": abs(float(l.get("prezzo_unitario", 0))),
                "sconto_percent": float(l.get("sconto_percent", 0)),
                "aliquota_iva": str(l.get("aliquota_iva", "22")),
                "importo": float(l.get("importo", 0)),
            })

        pagamenti = []
        for pg in (fa.get("pagamenti") or []):
            pagamenti.append({
                "payment_id": f"pay_{uuid.uuid4().hex[:8]}",
                "data": pg.get("data", ""),
                "importo": float(pg.get("importo", 0)),
                "metodo": pg.get("metodo", ""),
                "note": pg.get("note", ""),
            })

        totale_doc = float(fa.get("totale_documento", 0))
        totale_pagato = float(fa.get("totale_pagato", 0))
        residuo = float(fa.get("residuo", totale_doc - totale_pagato))

        ps = fa.get("payment_status", "")
        if not ps:
            ps = "pagata" if residuo <= 0 and totale_doc > 0 else ("parziale" if totale_pagato > 0 else "non_pagata")

        status = fa.get("status", "")
        if not status:
            status = "registrata" if ps == "pagata" else "da_registrare"

        doc = {
            "fr_id": f"fr_{uuid.uuid4().hex[:12]}",
            "user_id": uid,
            "fornitore_id": fornitore_id,
            "fornitore_nome": forn_nome,
            "fornitore_piva": forn_piva,
            "fornitore_cf": fa.get("fornitore_codice_fiscale", ""),
            "tipo_documento": fa.get("tipo_documento", "TD01"),
            "numero_documento": num_doc,
            "data_documento": data_doc,
            "data_ricezione": fa.get("data_ricezione", ""),
            "status": status,
            "sdi_id": fa.get("sdi_id") or None,
            "linee": linee,
            "imponibile": float(fa.get("imponibile", 0)),
            "imposta": float(fa.get("imposta", 0)),
            "totale_documento": totale_doc,
            "modalita_pagamento": fa.get("modalita_pagamento", ""),
            "condizioni_pagamento": fa.get("condizioni_pagamento", ""),
            "data_scadenza_pagamento": fa.get("data_scadenza_pagamento", ""),
            "pagamenti": pagamenti,
            "totale_pagato": totale_pagato,
            "residuo": max(residuo, 0),
            "payment_status": ps,
            "has_xml": False,
            "notes": fa.get("notes", ""),
            "created_at": now,
            "updated_at": now,
            "_migrated": True,
        }
        try:
            await db.fatture_ricevute.insert_one(doc)
            results["fatture_acquisto"] += 1
        except Exception as e:
            results["errors"].append(f"Fatt. acquisto {forn_nome} {num_doc}: {e}")

    return {
        "message": f"Migrazione completata! Importati: {results['anagrafica']} anagrafiche, {results['preventivi']} preventivi, {results['fatture_vendita']} fatture vendita, {results['fatture_acquisto']} fatture acquisto. Saltati {results['skipped']} duplicati.",
        "results": results,
    }


@router.get("/stato")
async def stato_migrazione(user: dict = Depends(get_current_user)):
    """Check how many migrated records exist."""
    uid = user["user_id"]
    return {
        "anagrafica": await db.clients.count_documents({"user_id": uid, "_migrated": True}),
        "preventivi": await db.preventivi.count_documents({"user_id": uid, "_migrated": True}),
        "fatture_vendita": await db.invoices.count_documents({"user_id": uid, "_migrated": True}),
        "fatture_acquisto": await db.fatture_ricevute.count_documents({"user_id": uid, "_migrated": True}),
    }
