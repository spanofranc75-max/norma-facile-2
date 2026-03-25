"""
Archivio Storico — Esportazione massiva per anno o cliente.

Genera uno ZIP con struttura ordinata:
  /{Anno}/{Cliente}/{Numero Commessa}/
    - pacco_documenti.pdf (se generabile)
    - foto_*.jpg
    - certificati_*.pdf
"""
import io
import uuid
import zipfile
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from core.security import get_current_user, tenant_match
from core.database import db

router = APIRouter(prefix="/archivio", tags=["archivio"])
logger = logging.getLogger(__name__)

EXPORT_COLL = "archivio_exports"


class ExportRequest(BaseModel):
    anno: Optional[int] = None
    client_id: Optional[str] = ""


@router.post("/export")
async def export_archivio(data: ExportRequest, user: dict = Depends(get_current_user)):
    """
    Generate a ZIP archive with all documents organized by Year/Client/Commessa.
    Returns the ZIP as a streaming download.
    """
    user_id = user["user_id"]
    tenant_id = user["tenant_id"]
    now = datetime.now(timezone.utc)

    # Build query filter
    query = {"user_id": user_id, "tenant_id": tenant_match(user)}
    if data.anno:
        # Filter commesse created in that year
        start = f"{data.anno}-01-01T00:00:00"
        end = f"{data.anno + 1}-01-01T00:00:00"
        query["created_at"] = {"$gte": start, "$lt": end}
    if data.client_id:
        query["client_id"] = data.client_id

    # Get matching commesse
    commesse = await db.commesse.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)

    if not commesse:
        raise HTTPException(404, "Nessuna commessa trovata con i filtri specificati")

    # Build client name lookup
    client_ids = list(set(c.get("client_id", "") for c in commesse if c.get("client_id")))
    clients = {}
    if client_ids:
        for cid in client_ids:
            cl = await db.clients.find_one({"client_id": cid}, {"_id": 0, "business_name": 1, "name": 1})
            if cl:
                clients[cid] = cl.get("business_name") or cl.get("name", "N/D")

    # Create ZIP in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for commessa in commesse:
            cid = commessa["commessa_id"]
            numero = commessa.get("numero", cid)
            client_name = clients.get(commessa.get("client_id", ""), "Senza_Cliente")
            # Sanitize folder names
            client_name = _sanitize(client_name)
            numero_clean = _sanitize(numero)

            # Determine year
            created = commessa.get("created_at", "")
            try:
                year = str(datetime.fromisoformat(created).year)
            except (ValueError, TypeError):
                year = "Senza_Data"

            base_path = f"{year}/{client_name}/{numero_clean}"

            # Info file
            info_text = (
                f"Commessa: {numero}\n"
                f"Oggetto: {commessa.get('title', commessa.get('oggetto', ''))}\n"
                f"Cliente: {clients.get(commessa.get('client_id', ''), 'N/D')}\n"
                f"Normativa: {commessa.get('normativa_tipo', '')}\n"
                f"Stato: {commessa.get('stato', '')}\n"
                f"Creata: {created[:10] if created else 'N/D'}\n"
            )
            zf.writestr(f"{base_path}/info_commessa.txt", info_text)

            # Documents (photos + certificates)
            docs = await db.commessa_documents.find(
                {"commessa_id": cid},
                {"_id": 0, "doc_id": 1, "nome_file": 1, "tipo": 1, "file_base64": 1, "content_type": 1}
            ).to_list(200)

            for doc in docs:
                file_b64 = doc.get("file_base64", "")
                if not file_b64:
                    continue

                nome = _sanitize(doc.get("nome_file", doc["doc_id"]))
                tipo = doc.get("tipo", "altro")

                # Subfolder by type
                if "foto" in tipo or "image" in doc.get("content_type", ""):
                    subfolder = "Foto"
                elif "certificato" in tipo:
                    subfolder = "Certificati"
                else:
                    subfolder = "Documenti"

                try:
                    import base64
                    content = base64.b64decode(file_b64)
                    zf.writestr(f"{base_path}/{subfolder}/{nome}", content)
                except Exception:
                    pass  # Skip corrupt files

            # Diario entries summary
            diario = await db.diario_produzione.find(
                {"commessa_id": cid}, {"_id": 0, "voce_id": 1, "operatore_nome": 1, "data": 1, "ore_totali": 1}
            ).to_list(200)

            if diario:
                lines = ["Data;Operatore;Voce;Ore"]
                for d in diario:
                    lines.append(f"{d.get('data','')};{d.get('operatore_nome','')};{d.get('voce_id','')};{d.get('ore_totali','')}")
                zf.writestr(f"{base_path}/diario_produzione.csv", "\n".join(lines))

            # Montaggio data
            montaggio = await db.diario_montaggio.find(
                {"commessa_id": cid}, {"_id": 0}
            ).to_list(50)

            if montaggio:
                import json
                montaggio_clean = []
                for m in montaggio:
                    m.pop("firma_cliente_base64", None)  # Don't export raw signature
                    montaggio_clean.append(m)
                zf.writestr(f"{base_path}/diario_montaggio.json", json.dumps(montaggio_clean, indent=2, ensure_ascii=False))

    zip_buffer.seek(0)
    zip_size = zip_buffer.getbuffer().nbytes

    # Log export
    export_id = f"exp_{uuid.uuid4().hex[:10]}"
    await db[EXPORT_COLL].insert_one({
        "export_id": export_id,
        "user_id": user_id, "tenant_id": tenant_match(user),
        "anno": data.anno,
        "client_id": data.client_id or "",
        "num_commesse": len(commesse),
        "size_bytes": zip_size,
        "created_at": now.isoformat(),
    })

    anno_label = str(data.anno) if data.anno else "tutti"
    filename = f"NormaFacile_Archivio_{anno_label}_{now.strftime('%Y%m%d')}.zip"

    logger.info(f"[ARCHIVIO] Export: {export_id} — {len(commesse)} commesse — {zip_size} bytes")

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/exports")
async def list_exports(user: dict = Depends(get_current_user)):
    """List previous exports."""
    exports = await db[EXPORT_COLL].find(
        {"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return {"exports": exports}


@router.get("/stats")
async def get_archivio_stats(user: dict = Depends(get_current_user)):
    """Get archivio stats for the export UI: available years and clients."""
    commesse = await db.commesse.find(
        {"user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "created_at": 1, "client_id": 1}
    ).to_list(1000)

    years = set()
    client_ids = set()
    for c in commesse:
        try:
            y = datetime.fromisoformat(c.get("created_at", "")).year
            years.add(y)
        except (ValueError, TypeError):
            pass
        if c.get("client_id"):
            client_ids.add(c["client_id"])

    # Get client names
    clients = []
    for cid in client_ids:
        cl = await db.clients.find_one({"client_id": cid}, {"_id": 0, "client_id": 1, "business_name": 1, "name": 1})
        if cl:
            clients.append({"client_id": cl["client_id"], "nome": cl.get("business_name") or cl.get("name", "")})

    return {
        "anni": sorted(years, reverse=True),
        "clienti": sorted(clients, key=lambda c: c["nome"]),
        "totale_commesse": len(commesse),
    }


def _sanitize(name: str) -> str:
    """Sanitize a string for use as a filename/folder name."""
    import re
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = name.strip('. ')
    return name[:100] if name else "senza_nome"
