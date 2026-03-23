"""
Verifica Committenza — API Routes (C1)
========================================
C1.1: Package documenti committenza
C1.2: Analisi AI
C1.3: Review umana
C1.4: Generazione obblighi
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional

from core.security import get_current_user
from core.rate_limiter import limiter
from services.committenza_analysis_service import (
    DOC_CATEGORIES,
    crea_package, get_package, list_packages,
    add_doc_to_package, remove_doc_from_package,
    analizza_committenza, get_analysis, list_analyses,
    review_analysis, approve_analysis,
    genera_obblighi_da_analisi,
)
from services.audit_trail import log_activity

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── Document Categories ───
@router.get("/committenza/categorie")
async def api_get_categories(user: dict = Depends(get_current_user)):
    return DOC_CATEGORIES


# ─── C1.1: Packages ───

@router.post("/committenza/packages")
async def api_crea_package(body: dict, user: dict = Depends(get_current_user)):
    result = await crea_package(
        user["user_id"],
        body.get("commessa_id", ""),
        body.get("title", ""),
        body.get("document_refs", []),
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    await log_activity(user, "create", "committenza_package", result.get("package_id", ""),
                       label=body.get("title", ""),
                       commessa_id=body.get("commessa_id", ""),
                       details={"n_documents": len(body.get("document_refs", []))})
    return result


@router.get("/committenza/packages")
async def api_list_packages(commessa_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    return await list_packages(user["user_id"], commessa_id)


@router.get("/committenza/packages/{package_id}")
async def api_get_package(package_id: str, user: dict = Depends(get_current_user)):
    pkg = await get_package(package_id, user["user_id"])
    if not pkg:
        raise HTTPException(status_code=404, detail="Package non trovato")
    return pkg


@router.post("/committenza/packages/{package_id}/documents")
async def api_add_doc(package_id: str, body: dict, user: dict = Depends(get_current_user)):
    result = await add_doc_to_package(
        package_id, user["user_id"],
        body.get("doc_id", ""),
        body.get("category", "altro"),
    )
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/committenza/packages/{package_id}/documents/{doc_id}")
async def api_remove_doc(package_id: str, doc_id: str, user: dict = Depends(get_current_user)):
    result = await remove_doc_from_package(package_id, user["user_id"], doc_id)
    if not result:
        raise HTTPException(status_code=404, detail="Package non trovato")
    return result


# ─── C1.2: AI Analysis ───

@router.post("/committenza/analizza/{package_id}")
@limiter.limit("10/minute")
async def api_analizza(request: Request, package_id: str, user: dict = Depends(get_current_user)):
    pkg = await get_package(package_id, user["user_id"])
    result = await analizza_committenza(package_id, user["user_id"])
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    await log_activity(user, "ai_precompile", "committenza_analisi", result.get("analysis_id", ""),
                       label=f"Analisi AI committenza",
                       commessa_id=(pkg or {}).get("commessa_id", ""),
                       details={"package_id": package_id,
                                "n_obblighi": len(result.get("extracted_obligations", []) or []),
                                "n_anomalie": len(result.get("anomalies", []) or [])},
                       actor_type="ai")
    return result


@router.get("/committenza/analisi")
async def api_list_analyses(commessa_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    return await list_analyses(user["user_id"], commessa_id)


@router.get("/committenza/analisi/{analysis_id}")
async def api_get_analysis(analysis_id: str, user: dict = Depends(get_current_user)):
    analysis = await get_analysis(analysis_id, user["user_id"])
    if not analysis:
        raise HTTPException(status_code=404, detail="Analisi non trovata")
    return analysis


# ─── C1.3: Human Review ───

@router.patch("/committenza/analisi/{analysis_id}/review")
async def api_review(analysis_id: str, body: dict, user: dict = Depends(get_current_user)):
    result = await review_analysis(analysis_id, user["user_id"], body)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/committenza/analisi/{analysis_id}/approve")
async def api_approve(analysis_id: str, user: dict = Depends(get_current_user)):
    result = await approve_analysis(analysis_id, user["user_id"])
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    await log_activity(user, "approve", "committenza_analisi", analysis_id,
                       label="Analisi approvata",
                       commessa_id=result.get("commessa_id", ""),
                       details={"before_status": "in_review", "after_status": "approved"})
    return result


# ─── C1.4: Generate Obligations ───

@router.post("/committenza/analisi/{analysis_id}/genera-obblighi")
@limiter.limit("10/minute")
async def api_genera_obblighi(request: Request, analysis_id: str, user: dict = Depends(get_current_user)):
    result = await genera_obblighi_da_analisi(analysis_id, user["user_id"])
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    await log_activity(user, "genera_obblighi", "committenza_analisi", analysis_id,
                       label=f"Generati {result.get('created', 0)} obblighi",
                       commessa_id=result.get("commessa_id", ""),
                       details={"created": result.get("created", 0)},
                       actor_type="system")
    return result
