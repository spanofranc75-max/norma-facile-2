"""Routes for EN 1090 FPC — Welders, Material Batches, Projects, CE Label, Dossier."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from typing import Optional
import uuid
import logging

from core.database import db
from routes.auth import get_current_user
from core.security import tenant_match
from models.fpc import (
    WelderCreate, MaterialBatchCreate, ProjectCreate,
    DEFAULT_FPC_CONTROLS,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fpc", tags=["FPC - EN 1090"])


# ═══════════════════════════════════════════════════════════════
# WELDERS
# ═══════════════════════════════════════════════════════════════

@router.get("/welders")
async def list_welders(user: dict = Depends(get_current_user)):
    cursor = db.welders.find(
        {"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    ).sort("name", 1)
    docs = await cursor.to_list(200)
    now = datetime.now(timezone.utc).isoformat()
    for d in docs:
        exp = d.get("license_expiry")
        d["is_expired"] = bool(exp and exp < now[:10])
    return docs


@router.post("/welders")
async def create_welder(body: WelderCreate, user: dict = Depends(get_current_user)):
    doc = {
        "welder_id": f"wld_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "name": body.name,
        "qualification_level": body.qualification_level,
        "license_expiry": body.license_expiry,
        "notes": body.notes or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.welders.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/welders/{welder_id}")
async def update_welder(welder_id: str, body: WelderCreate, user: dict = Depends(get_current_user)):
    result = await db.welders.update_one(
        {"welder_id": welder_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"$set": {
            "name": body.name,
            "qualification_level": body.qualification_level,
            "license_expiry": body.license_expiry,
            "notes": body.notes or "",
        }},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Saldatore non trovato")
    return {"status": "updated"}


@router.delete("/welders/{welder_id}")
async def delete_welder(welder_id: str, user: dict = Depends(get_current_user)):
    result = await db.welders.delete_one({"welder_id": welder_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)})
    if result.deleted_count == 0:
        raise HTTPException(404, "Saldatore non trovato")
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════════
# MATERIAL BATCHES (Tracciabilità Materiali)
# ═══════════════════════════════════════════════════════════════

@router.get("/batches")
async def list_batches(
    commessa_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List material batches, optionally filtered by commessa."""
    query = {"user_id": user["user_id"], "tenant_id": tenant_match(user)}
    if commessa_id:
        query["commessa_id"] = commessa_id
    
    cursor = db.material_batches.find(
        query,
        {"_id": 0, "certificate_base64": 0, "certificato_31_base64": 0}   # Exclude heavy fields
    ).sort("data_registrazione", -1)
    docs = await cursor.to_list(500)
    for d in docs:
        d["has_certificate"] = bool(d.pop("_has_cert", False) or d.get("has_certificate") or d.get("certificato_doc_id"))
    return {"batches": docs}


@router.get("/batches/{batch_id}")
async def get_batch(batch_id: str, user: dict = Depends(get_current_user)):
    doc = await db.material_batches.find_one(
        {"batch_id": batch_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "certificate_base64": 0}
    )
    if not doc:
        raise HTTPException(404, "Lotto non trovato")
    return doc


@router.get("/batches/{batch_id}/certificate")
async def get_batch_certificate(batch_id: str, user: dict = Depends(get_current_user)):
    """Download the 3.1 certificate for a batch."""
    doc = await db.material_batches.find_one(
        {"batch_id": batch_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "certificate_base64": 1, "certificate_filename": 1}
    )
    if not doc or not doc.get("certificate_base64"):
        raise HTTPException(404, "Certificato non trovato")
    return {
        "certificate_base64": doc["certificate_base64"],
        "certificate_filename": doc.get("certificate_filename", "certificato_3_1.pdf"),
    }


@router.post("/batches")
async def create_batch(body: MaterialBatchCreate, user: dict = Depends(get_current_user)):
    doc = {
        "batch_id": f"bat_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "commessa_id": body.commessa_id or "",  # Link to commessa for traceability
        "supplier_name": body.supplier_name,
        "material_type": body.material_type,
        "heat_number": body.heat_number,
        "certificate_base64": body.certificate_base64,
        "certificate_filename": body.certificate_filename,
        "has_certificate": bool(body.certificate_base64),
        "notes": body.notes or "",
        "received_date": body.received_date,
        "dimensions": body.dimensions,
        "posizione": body.posizione,
        "n_pezzi": body.n_pezzi,
        "numero_certificato": body.numero_certificato,
        "ddt_numero": body.ddt_numero,
        "disegno_numero": body.disegno_numero,
        # CAM fields
        "peso_kg": body.peso_kg or 0,
        "percentuale_riciclato": body.percentuale_riciclato,
        "metodo_produttivo": body.metodo_produttivo,
        "distanza_trasporto_km": body.distanza_trasporto_km,
        "certificazione_epd": body.certificazione_epd,
        "ente_certificatore_epd": body.ente_certificatore_epd,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.material_batches.insert_one(doc)
    doc.pop("_id", None)
    doc.pop("certificate_base64", None)
    return doc


@router.put("/batches/{batch_id}")
async def update_batch(batch_id: str, body: MaterialBatchCreate, user: dict = Depends(get_current_user)):
    update = {
        "supplier_name": body.supplier_name,
        "material_type": body.material_type,
        "heat_number": body.heat_number,
        "notes": body.notes or "",
        "received_date": body.received_date,
        "dimensions": body.dimensions,
        "posizione": body.posizione,
        "n_pezzi": body.n_pezzi,
        "numero_certificato": body.numero_certificato,
        "ddt_numero": body.ddt_numero,
        "disegno_numero": body.disegno_numero,
        # CAM fields
        "peso_kg": body.peso_kg or 0,
        "percentuale_riciclato": body.percentuale_riciclato,
        "metodo_produttivo": body.metodo_produttivo,
        "distanza_trasporto_km": body.distanza_trasporto_km,
        "certificazione_epd": body.certificazione_epd,
        "ente_certificatore_epd": body.ente_certificatore_epd,
    }
    if body.commessa_id is not None:
        update["commessa_id"] = body.commessa_id
    if body.certificate_base64 is not None:
        update["certificate_base64"] = body.certificate_base64
        update["certificate_filename"] = body.certificate_filename
        update["has_certificate"] = bool(body.certificate_base64)

    result = await db.material_batches.update_one(
        {"batch_id": batch_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"$set": update},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Lotto non trovato")
    return {"status": "updated"}


@router.delete("/batches/{batch_id}")
async def delete_batch(batch_id: str, user: dict = Depends(get_current_user)):
    # Find the batch first to get colata/commessa for cascade delete
    batch = await db.material_batches.find_one(
        {"batch_id": batch_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "heat_number": 1, "commessa_id": 1}
    )
    result = await db.material_batches.delete_one({"batch_id": batch_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)})
    if result.deleted_count == 0:
        raise HTTPException(404, "Lotto non trovato")
    
    # Cascade: delete linked CAM lotto (same colata + commessa)
    if batch and batch.get("heat_number") and batch.get("commessa_id"):
        cam_del = await db.lotti_cam.delete_many({
            "numero_colata": batch["heat_number"],
            "commessa_id": batch["commessa_id"],
            "user_id": user["user_id"], "tenant_id": tenant_match(user),
        })
        if cam_del.deleted_count > 0:
            logger.info(f"Cascade: deleted {cam_del.deleted_count} CAM lotti for batch {batch_id}")
    
    return {"status": "deleted"}


# ═══════════════════════════════════════════════════════════════
# FPC PROJECTS
# ═══════════════════════════════════════════════════════════════

@router.post("/projects")
async def create_project(body: ProjectCreate, user: dict = Depends(get_current_user)):
    """Convert a preventivo to an FPC project. Requires execution class."""
    if body.execution_class not in ("EXC1", "EXC2", "EXC3", "EXC4"):
        raise HTTPException(400, "Classe di esecuzione non valida (EXC1-EXC4)")

    prev = await db.preventivi.find_one(
        {"preventivo_id": body.preventivo_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not prev:
        raise HTTPException(404, "Preventivo non trovato")

    # Check no duplicate project
    existing = await db.fpc_projects.find_one(
        {"preventivo_id": body.preventivo_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "project_id": 1}
    )
    if existing:
        raise HTTPException(409, f"Progetto già esistente: {existing['project_id']}")

    # Get client name
    client_name = ""
    if prev.get("client_id"):
        cl = await db.clients.find_one({"client_id": prev["client_id"]}, {"_id": 0, "business_name": 1})
        client_name = cl.get("business_name", "") if cl else ""

    project = {
        "project_id": f"prj_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"], "tenant_id": tenant_match(user),
        "preventivo_id": body.preventivo_id,
        "preventivo_number": prev.get("number", ""),
        "client_id": prev.get("client_id", ""),
        "client_name": client_name,
        "subject": prev.get("subject", "") or prev.get("riferimento", "") or "",
        "status": "in_progress",
        "fpc_data": {
            "execution_class": body.execution_class,
            "wps_id": None,
            "welder_id": None,
            "welder_name": None,
            "material_batches": [],
            "controls": [dict(c) for c in DEFAULT_FPC_CONTROLS],
            "ce_label_generated": False,
            "ce_label_generated_at": None,
        },
        "lines": prev.get("lines", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": None,
    }
    await db.fpc_projects.insert_one(project)
    project.pop("_id", None)
    return project


@router.get("/projects")
async def list_projects(user: dict = Depends(get_current_user)):
    cursor = db.fpc_projects.find(
        {"user_id": user["user_id"], "tenant_id": tenant_match(user)}, {"_id": 0}
    ).sort("created_at", -1)
    return await cursor.to_list(200)


@router.get("/projects/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    doc = await db.fpc_projects.find_one(
        {"project_id": project_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(404, "Progetto non trovato")

    # Enrich with welder expiry info
    fpc = doc.get("fpc_data", {})
    if fpc.get("welder_id"):
        welder = await db.welders.find_one(
            {"welder_id": fpc["welder_id"]}, {"_id": 0}
        )
        if welder:
            now = datetime.now(timezone.utc).isoformat()[:10]
            exp = welder.get("license_expiry")
            doc["welder_expired"] = bool(exp and exp < now)
    return doc


@router.put("/projects/{project_id}/fpc")
async def update_project_fpc(project_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Update FPC data fields (welder, WPS, controls, batches)."""
    project = await db.fpc_projects.find_one(
        {"project_id": project_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not project:
        raise HTTPException(404, "Progetto non trovato")

    fpc = project.get("fpc_data", {})
    allowed = {"wps_id", "welder_id", "welder_name", "material_batches", "controls", "execution_class"}
    for key in allowed:
        if key in body:
            fpc[key] = body[key]

    # If welder_id set, check expiry and warn
    warning = None
    if fpc.get("welder_id"):
        welder = await db.welders.find_one(
            {"welder_id": fpc["welder_id"]}, {"_id": 0}
        )
        if welder:
            fpc["welder_name"] = welder.get("name", "")
            exp = welder.get("license_expiry")
            now_str = datetime.now(timezone.utc).isoformat()[:10]
            if exp and exp < now_str:
                warning = f"ATTENZIONE: Qualifica saldatore {welder['name']} scaduta il {exp}"

    await db.fpc_projects.update_one(
        {"project_id": project_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"$set": {
            "fpc_data": fpc,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    result = {"status": "updated", "fpc_data": fpc}
    if warning:
        result["warning"] = warning
    return result


@router.post("/projects/{project_id}/assign-batch")
async def assign_batch_to_line(project_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Assign a material batch to a project line item: {line_index, batch_id}."""
    project = await db.fpc_projects.find_one(
        {"project_id": project_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not project:
        raise HTTPException(404, "Progetto non trovato")

    line_index = body.get("line_index")
    batch_id = body.get("batch_id")
    if line_index is None or batch_id is None:
        raise HTTPException(400, "line_index e batch_id sono obbligatori")

    lines = project.get("lines", [])
    if line_index < 0 or line_index >= len(lines):
        raise HTTPException(400, "Indice riga non valido")

    # Verify batch exists
    batch = await db.material_batches.find_one(
        {"batch_id": batch_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "batch_id": 1, "heat_number": 1, "material_type": 1}
    )
    if not batch:
        raise HTTPException(404, "Lotto non trovato")

    lines[line_index]["batch_id"] = batch_id
    lines[line_index]["heat_number"] = batch.get("heat_number", "")
    lines[line_index]["material_type"] = batch.get("material_type", "")

    # Also add batch_id to fpc_data.material_batches if not there
    fpc = project.get("fpc_data", {})
    batches = fpc.get("material_batches", [])
    if batch_id not in batches:
        batches.append(batch_id)
        fpc["material_batches"] = batches

    await db.fpc_projects.update_one(
        {"project_id": project_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"$set": {
            "lines": lines,
            "fpc_data": fpc,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"status": "assigned", "line_index": line_index, "batch_id": batch_id}


# ═══════════════════════════════════════════════════════════════
# CE LABEL VALIDATION & GENERATION
# ═══════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/ce-check")
async def check_ce_readiness(project_id: str, user: dict = Depends(get_current_user)):
    """Check if all FPC requirements are met for CE label generation."""
    project = await db.fpc_projects.find_one(
        {"project_id": project_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not project:
        raise HTTPException(404, "Progetto non trovato")

    fpc = project.get("fpc_data", {})
    lines = project.get("lines", [])
    blockers = []

    # 1. Execution class set
    if not fpc.get("execution_class"):
        blockers.append("Classe di esecuzione non selezionata")

    # 2. Welder assigned
    if not fpc.get("welder_id"):
        blockers.append("Saldatore non assegnato")
    else:
        welder = await db.welders.find_one(
            {"welder_id": fpc["welder_id"]}, {"_id": 0}
        )
        if welder:
            exp = welder.get("license_expiry")
            now_str = datetime.now(timezone.utc).isoformat()[:10]
            if exp and exp < now_str:
                blockers.append(f"Qualifica saldatore scaduta ({exp})")

    # 3. All lines linked to a batch
    unlinked = [i + 1 for i, ln in enumerate(lines) if not ln.get("batch_id")]
    if unlinked:
        blockers.append(f"Righe senza lotto materiale: {', '.join(map(str, unlinked))}")

    # 4. All controls checked
    unchecked = [c["label"] for c in fpc.get("controls", []) if not c.get("checked")]
    if unchecked:
        blockers.append(f"Controlli non completati: {', '.join(unchecked)}")

    # 5. WPS assigned
    if not fpc.get("wps_id"):
        blockers.append("WPS (procedura di saldatura) non assegnata")

    return {
        "ready": len(blockers) == 0,
        "blockers": blockers,
        "project_id": project_id,
    }


@router.post("/projects/{project_id}/generate-ce")
async def generate_ce_label(project_id: str, user: dict = Depends(get_current_user)):
    """Generate the CE label if all checks pass."""
    # Run check first
    project = await db.fpc_projects.find_one(
        {"project_id": project_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0}
    )
    if not project:
        raise HTTPException(404, "Progetto non trovato")

    fpc = project.get("fpc_data", {})
    lines = project.get("lines", [])

    # Validate
    if not fpc.get("welder_id"):
        raise HTTPException(400, "Saldatore non assegnato")
    unlinked = [i for i, ln in enumerate(lines) if not ln.get("batch_id")]
    if unlinked:
        raise HTTPException(400, "Tutti i materiali devono essere collegati a un lotto")
    unchecked = [c for c in fpc.get("controls", []) if not c.get("checked")]
    if unchecked:
        raise HTTPException(400, "Tutti i controlli devono essere completati")

    now = datetime.now(timezone.utc).isoformat()
    fpc["ce_label_generated"] = True
    fpc["ce_label_generated_at"] = now

    await db.fpc_projects.update_one(
        {"project_id": project_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"$set": {
            "fpc_data": fpc,
            "status": "completed",
            "updated_at": now,
        }},
    )

    return {
        "status": "ce_generated",
        "ce_label_generated_at": now,
        "project_id": project_id,
        "execution_class": fpc.get("execution_class"),
    }


# ═══════════════════════════════════════════════════════════════
# TECHNICAL DOSSIER
# ═══════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/dossier")
async def download_dossier(project_id: str, user: dict = Depends(get_current_user)):
    """Generate and download the complete Technical Dossier (Fascicolo Tecnico)."""
    from services.dossier_generator import generate_dossier

    try:
        pdf_buf = await generate_dossier(project_id, user["user_id"])
    except ValueError as e:
        raise HTTPException(404, str(e))

    # Build filename
    project = await db.fpc_projects.find_one(
        {"project_id": project_id, "user_id": user["user_id"], "tenant_id": tenant_match(user)},
        {"_id": 0, "preventivo_number": 1}
    )
    name_part = (project or {}).get("preventivo_number", project_id).replace("/", "-")
    filename = f"Fascicolo_Tecnico_{name_part}.pdf"

    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



# ═══════════════════════════════════════════════════════════════
# LINK DDT → LOTTI FPC (Auto-associazione colata)
# ═══════════════════════════════════════════════════════════════

@router.post("/batches/link-ddt/{commessa_id}")
async def link_ddt_to_batches(commessa_id: str, user: dict = Depends(get_current_user)):
    """
    Cerca DDT di carico e associa automaticamente le righe ai lotti FPC
    basandosi sulla corrispondenza tra descrizione/colata del DDT e i batch.
    Aggiorna i batch con il riferimento DDT di origine.
    """
    uid = user["user_id"]
    tid = user["tenant_id"]

    # Load commessa
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": uid, "tenant_id": tid}, {"_id": 0, "commessa_id": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    # Load material batches for this commessa (unified collection)
    batches = await db.material_batches.find(
        {"commessa_id": commessa_id, "user_id": uid, "tenant_id": tid}, {"_id": 0, "certificate_base64": 0}
    ).to_list(200)
    if not batches:
        return {"message": "Nessun lotto FPC per questa commessa", "links": [], "totale": 0}

    # Load all DDT (carico = with lines that could be incoming materials)
    ddt_docs = await db.ddt_documents.find(
        {"user_id": uid, "tenant_id": tid}, {"_id": 0, "ddt_id": 1, "number": 1, "client_name": 1, "lines": 1, "subject": 1}
    ).to_list(500)

    links = []
    for batch in batches:
        heat = (batch.get("heat_number") or "").strip().upper()
        desc = (batch.get("description") or "").strip().upper()
        profile = desc.split(" ")[0] if desc else ""  # e.g. "HEB" from "HEB 120..."

        if not heat and not profile:
            continue

        for ddt in ddt_docs:
            for line in (ddt.get("lines") or []):
                line_desc = (line.get("description") or "").upper()
                line_colata = (line.get("colata") or line.get("heat_number") or "").upper()

                match = False
                match_type = ""

                # Match by heat number (strongest match)
                if heat and line_colata and heat in line_colata:
                    match = True
                    match_type = "colata"
                # Match by profile description
                elif profile and profile in line_desc:
                    match = True
                    match_type = "profilo"

                if match:
                    # Update batch with DDT reference (unified material_batches)
                    await db.material_batches.update_one(
                        {"batch_id": batch["batch_id"]},
                        {"$set": {
                            "ddt_origin": ddt["ddt_id"],
                            "ddt_number": ddt.get("number", ""),
                            "ddt_fornitore": ddt.get("client_name", ""),
                            "linked_at": datetime.now(timezone.utc).isoformat(),
                        }}
                    )
                    links.append({
                        "batch_id": batch["batch_id"],
                        "batch_desc": batch.get("description", ""),
                        "heat_number": heat,
                        "ddt_id": ddt["ddt_id"],
                        "ddt_number": ddt.get("number", ""),
                        "fornitore": ddt.get("client_name", ""),
                        "match_type": match_type,
                    })
                    break  # One DDT match per batch is enough
            if links and links[-1]["batch_id"] == batch["batch_id"]:
                break  # Already matched this batch

    return {
        "message": f"{len(links)} lotti collegati a DDT",
        "links": links,
        "totale": len(links),
        "batches_totali": len(batches),
    }


@router.get("/batches/rintracciabilita/{commessa_id}")
async def scheda_rintracciabilita(commessa_id: str, user: dict = Depends(get_current_user)):
    """
    Scheda Rintracciabilita Materiali auto-compilata.
    Per ogni lotto FPC mostra: materiale, colata, cert 3.1, DDT di origine, posizione disegno.
    """
    uid = user["user_id"]
    tid = user["tenant_id"]

    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": uid, "tenant_id": tid},
        {"_id": 0, "commessa_id": 1, "numero": 1, "title": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    batches = await db.material_batches.find(
        {"commessa_id": commessa_id, "user_id": uid, "tenant_id": tid},
        {"_id": 0, "certificate_base64": 0, "certificato_31_base64": 0}
    ).sort("created_at", 1).to_list(200)

    righe = []
    for b in batches:
        righe.append({
            "batch_id": b["batch_id"],
            "descrizione": b.get("dimensions", b.get("description", b.get("material_type", ""))),
            "materiale": b.get("material_type", b.get("tipo_materiale", "")),
            "colata": b.get("heat_number", b.get("numero_colata", "")),
            "certificato_31": b.get("numero_certificato", b.get("certificate_31", "")),
            "fornitore": b.get("supplier_name", b.get("fornitore", "")),
            "ddt_numero": b.get("ddt_numero", ""),
            "ddt_id": b.get("ddt_origin", ""),
            "quantita": b.get("quantity", b.get("n_pezzi", "")),
            "posizione_dwg": b.get("posizione", b.get("posizione_dwg", "")),
            "linked": bool(b.get("ddt_origin") or b.get("ddt_numero")),
            "peso_kg": b.get("peso_kg"),
            "percentuale_riciclato": b.get("percentuale_riciclato"),
            "metodo_produttivo": b.get("metodo_produttivo"),
            "distanza_trasporto_km": b.get("distanza_trasporto_km"),
        })

    return {
        "commessa_id": commessa_id,
        "numero": commessa.get("numero", ""),
        "title": commessa.get("title", ""),
        "righe": righe,
        "totale": len(righe),
        "collegati": sum(1 for r in righe if r["linked"]),
    }



@router.get("/batches/verifica-coerenza/{commessa_id}")
async def verifica_coerenza_rintracciabilita(commessa_id: str, user: dict = Depends(get_current_user)):
    """
    Confronta material_batches con DDT per segnalare discrepanze:
    - Colate non corrispondenti
    - Pesi/quantita mismatch
    - Descrizioni diverse (es. HEB 120 vs Piatto 100x10)
    - Certificati 3.1 mancanti
    """
    uid = user["user_id"]
    tid = user["tenant_id"]
    commessa = await db.commesse.find_one(
        {"commessa_id": commessa_id, "user_id": uid, "tenant_id": tid},
        {"_id": 0, "commessa_id": 1, "numero": 1}
    )
    if not commessa:
        raise HTTPException(404, "Commessa non trovata")

    # Load material batches
    batches = await db.material_batches.find(
        {"commessa_id": commessa_id, "user_id": uid, "tenant_id": tid},
        {"_id": 0, "certificate_base64": 0, "certificato_31_base64": 0}
    ).to_list(200)

    # Load DDTs related to this commessa
    ddts = await db.ddt_documents.find(
        {"user_id": uid, "tenant_id": tid, "commessa_id": commessa_id},
        {"_id": 0}
    ).to_list(100)
    # Also check DDTs not explicitly linked but referenced in batches
    ddt_ids_from_batches = set()
    for b in batches:
        did = b.get("ddt_origin", "")
        if did:
            ddt_ids_from_batches.add(did)
    if ddt_ids_from_batches:
        extra_ddts = await db.ddt_documents.find(
            {"ddt_id": {"$in": list(ddt_ids_from_batches)}, "user_id": uid, "tenant_id": tid},
            {"_id": 0}
        ).to_list(100)
        existing_ids = {d.get("ddt_id") for d in ddts}
        for ed in extra_ddts:
            if ed.get("ddt_id") not in existing_ids:
                ddts.append(ed)

    # Build DDT lookup by ddt_id
    ddt_map = {d.get("ddt_id", ""): d for d in ddts}

    discrepanze = []
    conformi = 0
    senza_cert = 0
    senza_colata = 0

    for b in batches:
        batch_id = b.get("batch_id", "")
        desc_batch = (b.get("dimensions") or b.get("description") or b.get("material_type") or "").strip()
        colata_batch = (b.get("heat_number") or b.get("numero_colata") or "").strip()
        cert = (b.get("numero_certificato") or b.get("certificate_31") or "").strip()
        ddt_origin = b.get("ddt_origin", "")
        ddt_numero = b.get("ddt_numero", "")

        issues = []

        # Check 1: Colata presente
        if not colata_batch:
            issues.append({
                "tipo": "colata_mancante",
                "gravita": "critica",
                "messaggio": "Numero di colata mancante — rintracciabilita non garantita",
            })
            senza_colata += 1

        # Check 2: Certificato 3.1 presente
        if not cert and not b.get("has_certificate"):
            issues.append({
                "tipo": "certificato_mancante",
                "gravita": "critica",
                "messaggio": "Certificato 3.1 mancante — richiesto da EN 10204",
            })
            senza_cert += 1

        # Check 3: Cross-reference con DDT
        if ddt_origin and ddt_origin in ddt_map:
            ddt_doc = ddt_map[ddt_origin]
            ddt_lines = ddt_doc.get("lines", ddt_doc.get("righe", []))

            # Check descrizione match
            for line in ddt_lines:
                line_desc = (line.get("description") or line.get("descrizione") or "").strip()
                if line_desc and desc_batch:
                    # Fuzzy match: check if main keyword is present
                    batch_words = set(desc_batch.upper().split())
                    line_words = set(line_desc.upper().split())
                    common = batch_words & line_words
                    if len(common) == 0 and len(batch_words) > 1:
                        issues.append({
                            "tipo": "descrizione_mismatch",
                            "gravita": "attenzione",
                            "messaggio": f"Descrizione lotto \"{desc_batch}\" diversa da DDT \"{line_desc}\"",
                        })
                        break

                # Check peso/quantita
                line_qty = line.get("quantity") or line.get("quantita") or ""
                batch_qty = b.get("quantity") or b.get("n_pezzi") or ""
                if line_qty and batch_qty:
                    try:
                        lq = float(str(line_qty).replace(",", ".").split()[0])
                        bq = float(str(batch_qty).replace(",", ".").split()[0])
                        if abs(lq - bq) > 0.01 * max(lq, bq):  # >1% difference
                            issues.append({
                                "tipo": "quantita_mismatch",
                                "gravita": "attenzione",
                                "messaggio": f"Quantita lotto ({batch_qty}) diversa da DDT ({line_qty})",
                            })
                    except (ValueError, IndexError):
                        pass

                # Check colata nel DDT
                line_colata = (line.get("heat_number") or line.get("colata") or "").strip()
                if colata_batch and line_colata and colata_batch.upper() != line_colata.upper():
                    issues.append({
                        "tipo": "colata_mismatch",
                        "gravita": "critica",
                        "messaggio": f"Colata lotto ({colata_batch}) non corrisponde a DDT ({line_colata})",
                    })
                    break
        elif not ddt_origin and not ddt_numero:
            issues.append({
                "tipo": "ddt_non_collegato",
                "gravita": "attenzione",
                "messaggio": "Lotto non collegato a nessun DDT — origine materiale non tracciata",
            })

        if not issues:
            conformi += 1

        discrepanze.append({
            "batch_id": batch_id,
            "descrizione": desc_batch,
            "colata": colata_batch,
            "certificato_31": cert,
            "fornitore": b.get("supplier_name", b.get("fornitore", "")),
            "ddt_numero": ddt_numero,
            "conforme": len(issues) == 0,
            "issues": issues,
        })

    n_totale = len(batches)
    n_critici = sum(1 for d in discrepanze if any(i["gravita"] == "critica" for i in d["issues"]))
    n_attenzione = sum(1 for d in discrepanze if any(i["gravita"] == "attenzione" for i in d["issues"]) and not any(i["gravita"] == "critica" for i in d["issues"]))

    return {
        "commessa_id": commessa_id,
        "numero": commessa.get("numero", ""),
        "eseguito_il": datetime.now(timezone.utc).isoformat(),
        "lotti": discrepanze,
        "riepilogo": {
            "totale": n_totale,
            "conformi": conformi,
            "critici": n_critici,
            "attenzione": n_attenzione,
            "senza_colata": senza_colata,
            "senza_certificato": senza_cert,
            "pct_conforme": round(conformi / n_totale * 100) if n_totale else 0,
        },
    }
