"""Commessa Operations — Thin wrapper that includes all sub-modules.

Sub-modules:
  - approvvigionamento.py  (Procurement: RdP, OdA, Arrivi)
  - produzione_ops.py      (Production phases)
  - conto_lavoro.py        (Subcontracting)
  - documenti_ops.py       (Document repository + AI parsing)
  - consegne_ops.py        (Deliveries, ops data, traceability, warehouse)

This file exists for backward compatibility with main.py and tests.
"""
from fastapi import APIRouter

from routes.approvvigionamento import router as approv_router
from routes.produzione_ops import router as prod_router
from routes.conto_lavoro import router as cl_router
from routes.documenti_ops import router as doc_router
from routes.consegne_ops import router as cons_router

router = APIRouter(prefix="/commesse", tags=["commessa-ops"])
router.include_router(approv_router)
router.include_router(prod_router)
router.include_router(cl_router)
router.include_router(doc_router)
router.include_router(cons_router)

# Re-export for backward compatibility (used by tests)
from routes.documenti_ops import _extract_profile_base, _normalize_profilo
from routes.commessa_ops_common import get_commessa_or_404, ensure_ops_fields
