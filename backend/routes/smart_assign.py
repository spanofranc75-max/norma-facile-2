"""Smart Assign routes — lookup data from registries for FPC/Fascicolo Tecnico auto-fill.
Does NOT alter any commessa data schema. Only provides data for the UI to auto-populate fields."""
from datetime import date
from fastapi import APIRouter, Depends
from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/smart-assign", tags=["smart-assign"])


@router.get("/welders")
async def get_welders_for_assign(user: dict = Depends(get_current_user)):
    """Returns welders with qualification status for Fascicolo Tecnico assignment."""
    today_str = date.today().isoformat()
    threshold_30 = date.today().replace(day=date.today().day)
    from datetime import timedelta
    threshold_str = (date.today() + timedelta(days=30)).isoformat()

    welders = await db.welders.find({"is_active": True}, {"_id": 0}).to_list(200)
    result = []
    for w in welders:
        quals = w.get("qualifications", [])
        valid_quals = []
        has_expired = False
        has_expiring = False

        for q in quals:
            exp = q.get("expiry_date", "")
            if not exp:
                continue
            status = "attivo"
            if exp < today_str:
                status = "scaduto"
                has_expired = True
            elif exp <= threshold_str:
                status = "in_scadenza"
                has_expiring = True

            valid_quals.append({
                "qual_id": q.get("qual_id", ""),
                "standard": q.get("standard", ""),
                "process": q.get("process", ""),
                "expiry_date": exp,
                "status": status,
                "has_file": bool(q.get("safe_filename")),
            })

        overall = "ok"
        if not quals:
            overall = "no_qual"
        elif has_expired and not any(q["status"] == "attivo" for q in valid_quals):
            overall = "expired"
        elif has_expired or has_expiring:
            overall = "warning"

        result.append({
            "welder_id": w["welder_id"],
            "name": w["name"],
            "stamp_id": w.get("stamp_id", ""),
            "role": w.get("role", ""),
            "overall_status": overall,
            "qualifications": valid_quals,
        })

    return {"welders": result}


@router.get("/instruments")
async def get_instruments_for_assign(user: dict = Depends(get_current_user)):
    """Returns instruments with calibration status for Piano Controlli assignment."""
    today_str = date.today().isoformat()
    from datetime import timedelta
    threshold_str = (date.today() + timedelta(days=30)).isoformat()

    instruments = await db.instruments.find(
        {"status": {"$nin": ["fuori_uso"]}},
        {"_id": 0}
    ).to_list(200)

    result = []
    for i in instruments:
        ncd = i.get("next_calibration_date", "")
        cal_status = "ok"
        if ncd:
            if ncd < today_str:
                cal_status = "scaduto"
            elif ncd <= threshold_str:
                cal_status = "in_scadenza"

        result.append({
            "instrument_id": i.get("instrument_id", ""),
            "name": i["name"],
            "serial_number": i.get("serial_number", ""),
            "instrument_type": i.get("instrument_type", ""),
            "next_calibration_date": ncd,
            "calibration_status": cal_status,
        })

    return {"instruments": result}
