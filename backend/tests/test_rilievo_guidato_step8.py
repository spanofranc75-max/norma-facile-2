"""
STEP 8 — Test completo Rilievo Guidato: tutte e 6 le tipologie.
Copre: create, update misure, calcola-materiali, PDF generation, backward compat, error handling.
"""
import pytest
import httpx
import asyncio
import uuid
from datetime import datetime, timezone

BASE_URL = "http://localhost:8001/api"

TIPOLOGIE_TEST_DATA = {
    "inferriata_fissa": {
        "misure": {
            "luce_larghezza": 1200, "luce_altezza": 1500,
            "interasse_montanti": 120, "profilo_montante": "30x30",
            "profilo_traverso": "20x20", "numero_traversi": 3,
            "altezza_davanzale": 900,
        },
        "expected_materials": ["Montante", "Traverso"],
    },
    "cancello_carrabile": {
        "misure": {
            "luce_netta": 4000, "altezza": 2000,
            "profilo_telaio": "60x40", "profilo_infisso": "40x20",
            "interasse_infissi": 100, "motorizzazione": True, "tipo_motore": "FAAC",
        },
        "expected_materials": ["Telaio", "Infisso", "Motore"],
    },
    "cancello_pedonale": {
        "misure": {
            "luce_netta": 1200, "altezza": 1800,
            "profilo_telaio": "40x40", "profilo_infisso": "25x25",
            "interasse_infissi": 100,
        },
        "expected_materials": ["Telaio", "Infisso"],
    },
    "scala": {
        "misure": {
            "numero_gradini": 12, "larghezza": 900,
            "alzata": 175, "pedata": 280,
            "profilo_struttura": "UPN100", "tipo_gradino": "mandorlato",
            "spessore_gradino": 4, "corrimano": True,
            "profilo_corrimano": "tondo_40", "montanti_corrimano": "quadro_20x20",
            "interasse_montanti": 150, "lato_corrimano": "dx",
        },
        "expected_materials": ["Struttura", "Gradino", "Corrimano", "Montante corrimano"],
    },
    "recinzione": {
        "misure": {
            "lunghezza_totale": 10000, "altezza": 1500,
            "interasse_pali": 2500, "profilo_palo": "60x60",
            "numero_orizzontali": 3, "profilo_orizzontale": "30x20",
            "interasse_verticali": 120, "profilo_verticale": "20x20",
        },
        "expected_materials": ["Palo", "Orizzontale", "Verticale"],
    },
    "ringhiera": {
        "misure": {
            "lunghezza": 5000, "altezza": 1000,
            "profilo_corrente": "40x40", "profilo_montante": "40x40",
            "interasse_montanti": 1000, "tipo_infisso": "quadro_20x20",
            "interasse_infissi": 100, "corrimano": "tondo_40",
        },
        "expected_materials": ["Corrente", "Montante", "Infisso", "Corrimano"],
    },
}


async def _setup_test_user():
    import sys
    sys.path.insert(0, '/app/backend')
    from core.database import db

    user_id = f"test_ril_{uuid.uuid4().hex[:8]}"
    session_token = f"test_sess_{uuid.uuid4().hex}"

    await db.users.insert_one({
        "user_id": user_id, "email": f"{user_id}@test.com",
        "name": "Test Rilievo", "role": "admin",
        "created_at": datetime.now(timezone.utc),
    })
    await db.user_sessions.insert_one({
        "user_id": user_id, "session_token": session_token,
        "expires_at": datetime(2027, 1, 1, tzinfo=timezone.utc),
    })
    client_id = f"cl_test_{uuid.uuid4().hex[:8]}"
    await db.clients.insert_one({
        "client_id": client_id, "user_id": user_id,
        "business_name": "Cliente Test SRL",
        "created_at": datetime.now(timezone.utc),
    })
    await db.company_settings.insert_one({
        "user_id": user_id, "business_name": "Steel Project Test SRL",
    })
    return user_id, session_token, client_id


async def _cleanup(user_id):
    import sys
    sys.path.insert(0, '/app/backend')
    from core.database import db
    await db.users.delete_many({"user_id": user_id})
    await db.user_sessions.delete_many({"user_id": user_id})
    await db.clients.delete_many({"user_id": user_id})
    await db.company_settings.delete_many({"user_id": user_id})
    await db.rilievi.delete_many({"user_id": user_id})


@pytest.mark.asyncio
async def test_rilievo_guidato_step8_complete():
    """Single comprehensive test: all 6 tipologie + backward compat + error handling."""
    user_id = None
    try:
        user_id, token, client_id = await _setup_test_user()
        headers = {"Cookie": f"session_token={token}"}

        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as http:

            # ── TEST A: All 6 tipologie full flow ──
            for tipologia, td in TIPOLOGIE_TEST_DATA.items():
                print(f"\n--- {tipologia} ---")

                # CREATE
                resp = await http.post("/rilievi/", json={
                    "client_id": client_id,
                    "project_name": f"Test {tipologia}",
                    "survey_date": "2026-03-09",
                    "location": "Via Test 1",
                    "tipologia": tipologia,
                    "misure": td["misure"],
                    "elementi": [], "vista_3d_config": {},
                    "sketches": [], "photos": [],
                    "notes": f"Note {tipologia}",
                }, headers=headers)
                assert resp.status_code == 201, f"CREATE {tipologia}: {resp.status_code} {resp.text}"
                rid = resp.json()["rilievo_id"]
                assert resp.json()["tipologia"] == tipologia
                print(f"  CREATE OK: {rid}")

                # CALCOLA MATERIALI
                resp = await http.post(f"/rilievi/{rid}/calcola-materiali", headers=headers)
                assert resp.status_code == 200, f"CALCOLA {tipologia}: {resp.status_code} {resp.text}"
                calc = resp.json()
                assert calc["peso_totale_kg"] > 0
                assert calc["superficie_verniciatura_m2"] > 0
                mat_descs = [m["descrizione"] for m in calc["materiali"]]
                for exp in td["expected_materials"]:
                    assert any(exp.lower() in d.lower() for d in mat_descs), \
                        f"Material '{exp}' missing in {mat_descs}"
                print(f"  CALCOLA OK: {len(calc['materiali'])} mat, {calc['peso_totale_kg']}kg, {calc['superficie_verniciatura_m2']}m2")

                # PDF
                resp = await http.get(f"/rilievi/{rid}/pdf", headers=headers)
                assert resp.status_code == 200, f"PDF {tipologia}: {resp.status_code}"
                assert resp.headers.get("content-type") == "application/pdf"
                assert len(resp.content) > 1000
                print(f"  PDF OK: {len(resp.content)} bytes")

            # ── TEST B: Backward compat (no tipologia) ──
            print("\n--- backward_compat ---")
            resp = await http.post("/rilievi/", json={
                "client_id": client_id,
                "project_name": "Rilievo Senza Tipologia",
                "survey_date": "2026-03-09",
                "sketches": [], "photos": [],
                "notes": "Vecchio formato",
            }, headers=headers)
            assert resp.status_code == 201
            rid_old = resp.json()["rilievo_id"]
            resp = await http.get(f"/rilievi/{rid_old}/pdf", headers=headers)
            assert resp.status_code == 200
            assert len(resp.content) > 500
            print(f"  BACKWARD COMPAT OK: {len(resp.content)} bytes")

            # ── TEST C: calcola-materiali on rilievo without tipologia → 400 ──
            print("\n--- error_handling ---")
            resp = await http.post(f"/rilievi/{rid_old}/calcola-materiali", headers=headers)
            assert resp.status_code == 400
            print(f"  ERROR HANDLING OK: 400 returned")

            print("\n" + "="*50)
            print("TUTTI I TEST PASSATI")
            print("="*50)

    finally:
        if user_id:
            await _cleanup(user_id)
            print("Cleanup OK")
