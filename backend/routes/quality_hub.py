"""Routes for Quality Hub Dashboard — aggregated view of all quality modules."""
from datetime import date, timedelta
from fastapi import APIRouter, Depends
from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/quality-hub", tags=["quality-hub"])


@router.get("/summary")
async def quality_hub_summary(user: dict = Depends(get_current_user)):
    """Aggregated quality status from all 4 modules."""
    today = date.today()
    today_str = today.isoformat()
    threshold_30 = (today + timedelta(days=30)).isoformat()

    # ── Welders ──
    welders_all = await db.welders.find({"user_id": user["user_id"], "tenant_id": user["tenant_id"]}, {"_id": 0, "name": 1, "stamp_id": 1, "qualifications": 1}).to_list(200)
    expiring_patents = []
    expired_patents = []
    for w in welders_all:
        for q in w.get("qualifications", []):
            exp = q.get("expiry_date", "")
            if not exp:
                continue
            if exp < today_str:
                expired_patents.append({
                    "welder_name": w["name"],
                    "stamp_id": w.get("stamp_id", ""),
                    "standard": q.get("standard", ""),
                    "process": q.get("process", ""),
                    "expiry_date": exp,
                    "type": "expired",
                })
            elif exp <= threshold_30:
                expiring_patents.append({
                    "welder_name": w["name"],
                    "stamp_id": w.get("stamp_id", ""),
                    "standard": q.get("standard", ""),
                    "process": q.get("process", ""),
                    "expiry_date": exp,
                    "type": "expiring",
                })

    # ── Instruments ──
    instruments_all = await db.instruments.find({"user_id": user["user_id"], "tenant_id": user["tenant_id"]}, {"_id": 0, "name": 1, "serial_number": 1, "next_calibration_date": 1, "instrument_type": 1, "status": 1}).to_list(200)
    expired_instruments = []
    expiring_instruments = []
    for i in instruments_all:
        if i.get("status") in ("fuori_uso", "in_manutenzione"):
            continue
        ncd = i.get("next_calibration_date", "")
        if not ncd:
            continue
        if ncd < today_str:
            expired_instruments.append({
                "name": i["name"],
                "serial_number": i.get("serial_number", ""),
                "instrument_type": i.get("instrument_type", ""),
                "next_calibration_date": ncd,
                "type": "expired",
            })
        elif ncd <= threshold_30:
            expiring_instruments.append({
                "name": i["name"],
                "serial_number": i.get("serial_number", ""),
                "instrument_type": i.get("instrument_type", ""),
                "next_calibration_date": ncd,
                "type": "expiring",
            })

    # ── NCs ──
    open_ncs = await db.non_conformities.find(
        {"status": {"$ne": "chiusa"}, "user_id": user["user_id"], "tenant_id": user["tenant_id"]}, {"_id": 0, "nc_id": 1, "nc_number": 1, "description": 1, "priority": 1, "status": 1, "date": 1, "source": 1}
    ).sort("priority", 1).to_list(100)
    nc_alerts = []
    for nc in open_ncs:
        days = None
        try:
            days = (today - date.fromisoformat(nc.get("date", ""))).days
        except (ValueError, TypeError):
            pass
        nc_alerts.append({
            "nc_id": nc["nc_id"],
            "nc_number": nc.get("nc_number", ""),
            "description": nc.get("description", ""),
            "priority": nc.get("priority", "media"),
            "status": nc.get("status", "aperta"),
            "date": nc.get("date", ""),
            "source": nc.get("source"),
            "days_open": days,
        })

    # ── Audits ──
    all_audits = await db.audits.find({"user_id": user["user_id"], "tenant_id": user["tenant_id"]}, {"_id": 0, "audit_id": 1, "date": 1, "next_audit_date": 1, "audit_type": 1, "auditor_name": 1, "outcome": 1}).to_list(500)
    next_audit = None
    future_audits = [a for a in all_audits if a.get("next_audit_date") and a["next_audit_date"] >= today_str]
    if future_audits:
        future_audits.sort(key=lambda a: a["next_audit_date"])
        na = future_audits[0]
        next_audit = {
            "date": na["next_audit_date"],
            "audit_type": na.get("audit_type", ""),
            "auditor_name": na.get("auditor_name", ""),
        }

    current_year = today.year
    audits_this_year = sum(1 for a in all_audits if a.get("date", "").startswith(str(current_year)))

    # ── Documents ──
    doc_count = await db.company_docs.count_documents({"user_id": user["user_id"], "tenant_id": user["tenant_id"]})

    # ── Summary counts ──
    total_alerts = len(expired_patents) + len(expiring_patents) + len(expired_instruments) + len(expiring_instruments) + len(nc_alerts)

    return {
        "summary": {
            "total_alerts": total_alerts,
            "welders_total": len(welders_all),
            "patents_expired": len(expired_patents),
            "patents_expiring": len(expiring_patents),
            "instruments_total": len(instruments_all),
            "instruments_expired": len(expired_instruments),
            "instruments_expiring": len(expiring_instruments),
            "nc_open": len(nc_alerts),
            "nc_high_priority": sum(1 for n in nc_alerts if n["priority"] == "alta"),
            "audits_this_year": audits_this_year,
            "documents_total": doc_count,
        },
        "next_audit": next_audit,
        "alerts": {
            "expired_patents": expired_patents,
            "expiring_patents": expiring_patents,
            "expired_instruments": expired_instruments,
            "expiring_instruments": expiring_instruments,
            "open_ncs": nc_alerts,
        },
    }
