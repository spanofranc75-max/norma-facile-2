"""Routes for EN 1090 FPC — Welders, Material Batches, Projects, CE Label, Dossier."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from typing import Optional
import uuid

from core.database import db
from routes.auth import get_current_user
from models.fpc import (
    WelderCreate, MaterialBatchCreate, ProjectCreate,
    DEFAULT_FPC_CONTROLS,
)

router = APIRouter(prefix="/api/fpc", tags=["FPC - EN 1090"])


# ═══════════════════════════════════════════════════════════════
# WELDERS
# ═══════════════════════════════════════════════════════════════

@router.get("/welders")
async def list_welders(user: dict = Depends(get_current_user)):
    cursor = db.welders.find(
        {"user_id": user["user_id"]}, {"_id": 0}
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
        "user_id": user["user_id"],
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
        {"welder_id": welder_id, "user_id": user["user_id"]},
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
    result = await db.welders.delete_one({"welder_id": welder_id, "user_id": user["user_id"]})
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
    query = {"user_id": user["user_id"]}
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
        {"batch_id": batch_id, "user_id": user["user_id"]},
        {"_id": 0, "certificate_base64": 0}
    )
    if not doc:
        raise HTTPException(404, "Lotto non trovato")
    return doc


@router.get("/batches/{batch_id}/certificate")
async def get_batch_certificate(batch_id: str, user: dict = Depends(get_current_user)):
    """Download the 3.1 certificate for a batch."""
    doc = await db.material_batches.find_one(
        {"batch_id": batch_id, "user_id": user["user_id"]},
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
        "user_id": user["user_id"],
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
    }
    if body.certificate_base64 is not None:
        update["certificate_base64"] = body.certificate_base64
        update["certificate_filename"] = body.certificate_filename
        update["has_certificate"] = bool(body.certificate_base64)

    result = await db.material_batches.update_one(
        {"batch_id": batch_id, "user_id": user["user_id"]},
        {"$set": update},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Lotto non trovato")
    return {"status": "updated"}


@router.delete("/batches/{batch_id}")
async def delete_batch(batch_id: str, user: dict = Depends(get_current_user)):
    result = await db.material_batches.delete_one({"batch_id": batch_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(404, "Lotto non trovato")
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
        {"preventivo_id": body.preventivo_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not prev:
        raise HTTPException(404, "Preventivo non trovato")

    # Check no duplicate project
    existing = await db.fpc_projects.find_one(
        {"preventivo_id": body.preventivo_id, "user_id": user["user_id"]},
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
        "user_id": user["user_id"],
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
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1)
    return await cursor.to_list(200)


@router.get("/projects/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    doc = await db.fpc_projects.find_one(
        {"project_id": project_id, "user_id": user["user_id"]},
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
        {"project_id": project_id, "user_id": user["user_id"]},
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
        {"project_id": project_id, "user_id": user["user_id"]},
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
        {"project_id": project_id, "user_id": user["user_id"]},
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
        {"batch_id": batch_id, "user_id": user["user_id"]},
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
        {"project_id": project_id, "user_id": user["user_id"]},
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
        {"project_id": project_id, "user_id": user["user_id"]},
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
        {"project_id": project_id, "user_id": user["user_id"]},
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
        {"project_id": project_id, "user_id": user["user_id"]},
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
        {"project_id": project_id, "user_id": user["user_id"]},
        {"_id": 0, "preventivo_number": 1}
    )
    name_part = (project or {}).get("preventivo_number", project_id).replace("/", "-")
    filename = f"Fascicolo_Tecnico_{name_part}.pdf"

    return StreamingResponse(
        pdf_buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
