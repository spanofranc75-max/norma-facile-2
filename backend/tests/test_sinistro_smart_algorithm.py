"""
Test Suite for 'Sinistro Smart' Algorithm — Cost Calculation for Perizia Sinistro
Tests the calc_voci_costo function that generates cost items based on damage codes.

Key formula tested:
1. MAT.01: Materiale = prezzo_ml * (1 + coeff/100) * total_ml
2. TRA.01: Trasporto = €120 if >2.5m, €60 if ≤2.5m
3. MAN.01: Smontaggio = €40/ml
4. MAN.02: Montaggio = €50/ml (if structural)
5. AUT.01/02: Automazione (if M1-FORCE)
6. SIC.01: Sicurezza (if G1-GAP)
7. NOR.01: Certificazioni = €150 fisso
8. SMA.01: Smaltimento = €90 fisso
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

# Use public URL for testing
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://production-debug-12.preview.emergentagent.com").rstrip("/")

from pymongo import MongoClient


def create_test_session():
    """Create a test user and session in MongoDB."""
    client = MongoClient("mongodb://localhost:27017")
    db = client["test_database"]
    
    session_token = f"test_sinistro_smart_{uuid.uuid4().hex[:10]}"
    user_id = f"user_smart_{uuid.uuid4().hex[:8]}"
    email = f"{user_id}@test.com"
    
    db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "email": email,
            "name": "Sinistro Smart Test User",
            "picture": "",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True
    )
    
    db.user_sessions.update_one(
        {"session_token": session_token},
        {"$set": {
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": datetime(2030, 1, 1, tzinfo=timezone.utc),
            "created_at": datetime.now(timezone.utc),
        }},
        upsert=True
    )
    
    client.close()
    return session_token, user_id


SESSION_TOKEN, USER_ID = create_test_session()
print(f"Created test session: {SESSION_TOKEN} for user {USER_ID}")


@pytest.fixture(scope="module")
def api_client():
    """Authenticated requests session."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    return session


@pytest.fixture(scope="module")
def cleanup_perizie():
    """Track perizia IDs for cleanup at end of module."""
    ids = []
    yield ids
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    for perizia_id in ids:
        try:
            session.delete(f"{BASE_URL}/api/perizie/{perizia_id}")
        except:
            pass
    try:
        client = MongoClient("mongodb://localhost:27017")
        db = client["test_database"]
        db.user_sessions.delete_many({"session_token": SESSION_TOKEN})
        db.perizie.delete_many({"user_id": USER_ID})
        db.users.delete_many({"user_id": USER_ID})
        client.close()
    except:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# API Health & Codici Danno Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAPIHealth:
    """Basic API health checks"""
    
    def test_api_health_endpoint(self):
        """GET /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ API healthy: {data['service']} v{data['version']}")
    
    def test_codici_danno_returns_7_codes(self):
        """GET /api/perizie/codici-danno returns exactly 7 damage codes"""
        response = requests.get(f"{BASE_URL}/api/perizie/codici-danno")
        assert response.status_code == 200
        data = response.json()
        codes = data.get("codici_danno", [])
        assert len(codes) == 7, f"Expected 7 codes, got {len(codes)}"
        
        expected_codes = ["S1-DEF", "S2-WELD", "A1-ANCH", "A2-CONC", "P1-ZINC", "G1-GAP", "M1-FORCE"]
        actual_codes = [c["codice"] for c in codes]
        for ec in expected_codes:
            assert ec in actual_codes, f"Missing code {ec}"
        
        print(f"✓ Codici danno: {', '.join(actual_codes)}")


# ═══════════════════════════════════════════════════════════════════════════════
# Sinistro Smart Algorithm — Cost Item Generation Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSinistroSmartMateriale:
    """Test MAT.01 (Material) cost calculation"""
    
    def test_mat01_calculated_with_markup(self, api_client, cleanup_perizie):
        """MAT.01 totale = prezzo_ml * (1 + coeff/100) * total_ml"""
        prezzo_ml = 170.0
        coeff = 20  # 20% markup
        ml = 6.0
        
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_MAT01 markup calc",
            "prezzo_ml_originale": prezzo_ml,
            "coefficiente_maggiorazione": coeff,
            "moduli": [{"descrizione": "Modulo", "lunghezza_ml": ml, "altezza_m": 1.5, "note": ""}],
            "codici_danno": ["S1-DEF"]  # Structural damage
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201, f"Failed: {response.text}"
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        mat01 = next((v for v in data["voci_costo"] if v["codice"] == "MAT.01"), None)
        assert mat01 is not None, f"MAT.01 missing. Got codes: {[v['codice'] for v in data['voci_costo']]}"
        
        # Expected: 170 * 1.20 * 6 = 1224
        expected_unit = round(prezzo_ml * (1 + coeff / 100), 2)  # 204
        expected_total = round(expected_unit * ml, 2)  # 1224
        
        assert abs(mat01["prezzo_unitario"] - expected_unit) < 0.02, f"Unit price {mat01['prezzo_unitario']} != {expected_unit}"
        assert abs(mat01["totale"] - expected_total) < 0.02, f"Total {mat01['totale']} != {expected_total}"
        
        print(f"✓ MAT.01: {ml} ml × {mat01['prezzo_unitario']} EUR/ml = {mat01['totale']} EUR")


class TestSinistroSmartTrasporto:
    """Test TRA.01 (Transport) cost calculation"""
    
    def test_tra01_120_for_long_elements(self, api_client, cleanup_perizie):
        """TRA.01 = €120 when total_ml > 2.5"""
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_TRA01 long",
            "prezzo_ml_originale": 150,
            "moduli": [{"descrizione": "Long", "lunghezza_ml": 6.0, "altezza_m": 1.5, "note": ""}],
            "codici_danno": ["S1-DEF"]
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        tra01 = next((v for v in data["voci_costo"] if v["codice"] == "TRA.01"), None)
        assert tra01 is not None
        assert tra01["totale"] == 120.0, f"Expected 120, got {tra01['totale']}"
        print(f"✓ TRA.01 for >2.5m: {tra01['totale']} EUR")
    
    def test_tra01_60_for_short_elements(self, api_client, cleanup_perizie):
        """TRA.01 = €60 when total_ml <= 2.5"""
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_TRA01 short",
            "prezzo_ml_originale": 150,
            "moduli": [{"descrizione": "Short", "lunghezza_ml": 2.0, "altezza_m": 1.5, "note": ""}],
            "codici_danno": ["S1-DEF"]
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        tra01 = next((v for v in data["voci_costo"] if v["codice"] == "TRA.01"), None)
        assert tra01 is not None
        assert tra01["totale"] == 60.0, f"Expected 60, got {tra01['totale']}"
        print(f"✓ TRA.01 for ≤2.5m: {tra01['totale']} EUR")


class TestSinistroSmartManodopera:
    """Test MAN.01 (Smontaggio) and MAN.02 (Montaggio) costs"""
    
    def test_man01_smontaggio_40_per_ml(self, api_client, cleanup_perizie):
        """MAN.01 = €40/ml for dismantling"""
        ml = 5.0
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_MAN01",
            "prezzo_ml_originale": 150,
            "moduli": [{"descrizione": "M", "lunghezza_ml": ml, "altezza_m": 1.5, "note": ""}],
            "codici_danno": ["S1-DEF"]
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        man01 = next((v for v in data["voci_costo"] if v["codice"] == "MAN.01"), None)
        assert man01 is not None
        expected_total = ml * 40.0  # €40/ml
        assert abs(man01["totale"] - expected_total) < 0.01
        print(f"✓ MAN.01 Smontaggio: {ml} ml × €40 = {man01['totale']} EUR")
    
    def test_man02_montaggio_50_per_ml(self, api_client, cleanup_perizie):
        """MAN.02 = €50/ml for installation (structural codes)"""
        ml = 5.0
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_MAN02",
            "prezzo_ml_originale": 150,
            "moduli": [{"descrizione": "M", "lunghezza_ml": ml, "altezza_m": 1.5, "note": ""}],
            "codici_danno": ["S1-DEF"]  # Triggers MAN.02
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        man02 = next((v for v in data["voci_costo"] if v["codice"] == "MAN.02"), None)
        assert man02 is not None, f"MAN.02 missing. Got: {[v['codice'] for v in data['voci_costo']]}"
        expected_total = ml * 50.0  # €50/ml
        assert abs(man02["totale"] - expected_total) < 0.01
        print(f"✓ MAN.02 Montaggio: {ml} ml × €50 = {man02['totale']} EUR")


class TestSinistroSmartAutomazione:
    """Test AUT.01 and AUT.02 for automation damage (M1-FORCE)"""
    
    def test_aut_items_generated_for_m1_force(self, api_client, cleanup_perizie):
        """codici_danno=['M1-FORCE'] → generates AUT.01 + AUT.02"""
        payload = {
            "tipo_danno": "automatismi",
            "descrizione_utente": "TEST_AUT M1-FORCE",
            "prezzo_ml_originale": 200,
            "moduli": [{"descrizione": "Cancello", "lunghezza_ml": 4.0, "altezza_m": 2.0, "note": ""}],
            "codici_danno": ["M1-FORCE"]
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        codes = [v["codice"] for v in data["voci_costo"]]
        assert "AUT.01" in codes, f"AUT.01 missing. Got: {codes}"
        assert "AUT.02" in codes, f"AUT.02 missing. Got: {codes}"
        
        aut02 = next(v for v in data["voci_costo"] if v["codice"] == "AUT.02")
        assert aut02["totale"] == 320.0  # Collaudo EN 12453 = €320 fixed
        print(f"✓ Automazione: AUT.01 + AUT.02 (collaudo €{aut02['totale']})")


class TestSinistroSmartSicurezza:
    """Test SIC.01 for safety damage (G1-GAP)"""
    
    def test_sic01_generated_for_g1_gap(self, api_client, cleanup_perizie):
        """codici_danno=['G1-GAP'] → generates SIC.01 at €180"""
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_SIC G1-GAP",
            "prezzo_ml_originale": 150,
            "moduli": [{"descrizione": "M", "lunghezza_ml": 3.0, "altezza_m": 1.5, "note": ""}],
            "codici_danno": ["G1-GAP"]
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        sic01 = next((v for v in data["voci_costo"] if v["codice"] == "SIC.01"), None)
        assert sic01 is not None, f"SIC.01 missing. Got: {[v['codice'] for v in data['voci_costo']]}"
        assert sic01["totale"] == 180.0
        print(f"✓ SIC.01 Sicurezza: {sic01['totale']} EUR")


class TestSinistroSmartNormativo:
    """Test NOR.01 (Certifications) cost"""
    
    def test_nor01_generated_for_structural(self, api_client, cleanup_perizie):
        """Structural damage → NOR.01 = €150 fixed"""
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_NOR structural",
            "prezzo_ml_originale": 150,
            "moduli": [{"descrizione": "M", "lunghezza_ml": 3.0, "altezza_m": 1.5, "note": ""}],
            "codici_danno": ["S1-DEF"]
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        nor01 = next((v for v in data["voci_costo"] if v["codice"] == "NOR.01"), None)
        assert nor01 is not None
        assert nor01["totale"] == 150.0
        print(f"✓ NOR.01 Certificazioni: {nor01['totale']} EUR")


class TestSinistroSmartSmaltimento:
    """Test SMA.01 (Disposal) cost"""
    
    def test_sma01_always_90_fixed(self, api_client, cleanup_perizie):
        """SMA.01 = €90 fixed for all perizie"""
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_SMA disposal",
            "prezzo_ml_originale": 150,
            "moduli": [{"descrizione": "M", "lunghezza_ml": 3.0, "altezza_m": 1.5, "note": ""}],
            "codici_danno": ["S1-DEF"]
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        sma01 = next((v for v in data["voci_costo"] if v["codice"] == "SMA.01"), None)
        assert sma01 is not None
        assert sma01["totale"] == 90.0
        print(f"✓ SMA.01 Smaltimento: {sma01['totale']} EUR")


# ═══════════════════════════════════════════════════════════════════════════════
# Recalculation Endpoint Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecalcEndpoint:
    """Test POST /api/perizie/{id}/recalc"""
    
    def test_recalc_updates_costs_after_module_change(self, api_client, cleanup_perizie):
        """Recalc regenerates costs when modules change"""
        # Create with 3ml module
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Recalc flow",
            "prezzo_ml_originale": 170,
            "coefficiente_maggiorazione": 20,
            "moduli": [{"descrizione": "Orig", "lunghezza_ml": 3.0, "altezza_m": 1.5, "note": ""}],
            "codici_danno": ["S1-DEF"]
        }
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        perizia_id = data["perizia_id"]
        cleanup_perizie.append(perizia_id)
        original_total = data["total_perizia"]
        
        # Update to 6ml module (double material)
        update = {
            "moduli": [{"descrizione": "Bigger", "lunghezza_ml": 6.0, "altezza_m": 2.0, "note": ""}]
        }
        api_client.put(f"{BASE_URL}/api/perizie/{perizia_id}", json=update)
        
        # Recalculate
        recalc_resp = api_client.post(f"{BASE_URL}/api/perizie/{perizia_id}/recalc")
        assert recalc_resp.status_code == 200
        recalc_data = recalc_resp.json()
        
        new_total = recalc_data["total_perizia"]
        assert new_total > original_total, f"New total {new_total} should be > original {original_total}"
        
        # Verify persistence
        get_resp = api_client.get(f"{BASE_URL}/api/perizie/{perizia_id}")
        assert get_resp.json()["total_perizia"] == new_total
        
        print(f"✓ Recalc: {original_total} → {new_total} EUR (module 3ml → 6ml)")
    
    def test_recalc_updates_costs_after_code_change(self, api_client, cleanup_perizie):
        """Recalc regenerates costs when damage codes change"""
        # Create with S1-DEF only
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Recalc codes",
            "prezzo_ml_originale": 150,
            "moduli": [{"descrizione": "M", "lunghezza_ml": 4.0, "altezza_m": 1.5, "note": ""}],
            "codici_danno": ["S1-DEF"]
        }
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        perizia_id = data["perizia_id"]
        cleanup_perizie.append(perizia_id)
        original_codes = [v["codice"] for v in data["voci_costo"]]
        
        # Add G1-GAP (should add SIC.01)
        api_client.put(f"{BASE_URL}/api/perizie/{perizia_id}", json={"codici_danno": ["S1-DEF", "G1-GAP"]})
        
        # Recalc
        recalc_resp = api_client.post(f"{BASE_URL}/api/perizie/{perizia_id}/recalc")
        assert recalc_resp.status_code == 200
        new_codes = [v["codice"] for v in recalc_resp.json()["voci_costo"]]
        
        assert "SIC.01" in new_codes, f"SIC.01 should be added. Got: {new_codes}"
        print(f"✓ Recalc added SIC.01 for G1-GAP: {original_codes} → {new_codes}")


# ═══════════════════════════════════════════════════════════════════════════════
# PDF Generation Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDFGeneration:
    """Test GET /api/perizie/{id}/pdf"""
    
    def test_pdf_returns_valid_document(self, api_client, cleanup_perizie):
        """PDF endpoint returns valid PDF content"""
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_PDF gen",
            "prezzo_ml_originale": 170,
            "moduli": [{"descrizione": "M", "lunghezza_ml": 4.0, "altezza_m": 1.5, "note": ""}],
            "codici_danno": ["S1-DEF", "P1-ZINC"],
            "stato_di_fatto": "Recinzione danneggiata da urto veicolare",
            "nota_tecnica": "Sostituzione obbligatoria per EN 1090-2"
        }
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        perizia_id = data["perizia_id"]
        cleanup_perizie.append(perizia_id)
        
        # Get PDF
        pdf_resp = api_client.get(f"{BASE_URL}/api/perizie/{perizia_id}/pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers.get("content-type") == "application/pdf"
        assert len(pdf_resp.content) > 1000, "PDF should have substantial content"
        
        content_disp = pdf_resp.headers.get("content-disposition", "")
        assert "perizia_" in content_disp
        print(f"✓ PDF generated: {len(pdf_resp.content)} bytes")


# ═══════════════════════════════════════════════════════════════════════════════
# Archivio Stats Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestArchivioStats:
    """Test GET /api/perizie/archivio/stats"""
    
    def test_archivio_stats_returns_aggregated_data(self, api_client, cleanup_perizie):
        """Stats endpoint returns total_count, total_amount, by_tipo, etc."""
        # Create a perizia first
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Stats",
            "prezzo_ml_originale": 170,
            "moduli": [{"descrizione": "M", "lunghezza_ml": 4.0, "altezza_m": 1.5, "note": ""}],
            "codici_danno": ["S1-DEF"]
        }
        api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        cleanup_perizie.append(response.json()["perizia_id"])
        
        # Get stats
        stats_resp = api_client.get(f"{BASE_URL}/api/perizie/archivio/stats")
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        
        assert "total_count" in stats
        assert "total_amount" in stats
        assert "avg_amount" in stats
        assert "by_tipo" in stats
        assert "by_status" in stats
        assert "codici_frequency" in stats
        
        assert stats["total_count"] >= 1
        print(f"✓ Archivio stats: {stats['total_count']} perizie, €{stats['total_amount']} total")


# ═══════════════════════════════════════════════════════════════════════════════
# Full Workflow Integration Test
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullWorkflow:
    """End-to-end test of Sinistro Smart workflow"""
    
    def test_complete_perizia_workflow(self, api_client, cleanup_perizie):
        """Create → Get → Update → Recalc → PDF flow"""
        # Step 1: Create
        create_payload = {
            "localizzazione": {
                "indirizzo": "Via Roma 123",
                "lat": 41.9028,
                "lng": 12.4964,
                "comune": "Roma",
                "provincia": "RM"
            },
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Full workflow - urto veicolo su recinzione",
            "prezzo_ml_originale": 170,
            "coefficiente_maggiorazione": 20,
            "moduli": [
                {"descrizione": "Modulo A", "lunghezza_ml": 3.0, "altezza_m": 1.5, "note": "Deformato"},
                {"descrizione": "Modulo B", "lunghezza_ml": 3.0, "altezza_m": 1.5, "note": "Piegato"}
            ],
            "codici_danno": ["S1-DEF", "P1-ZINC"]
        }
        
        create_resp = api_client.post(f"{BASE_URL}/api/perizie/", json=create_payload)
        assert create_resp.status_code == 201
        data = create_resp.json()
        perizia_id = data["perizia_id"]
        cleanup_perizie.append(perizia_id)
        
        assert data["number"].startswith("PER-")
        assert len(data["voci_costo"]) >= 5  # Should have MAT, TRA, MAN, NOR, SMA
        initial_total = data["total_perizia"]
        print(f"✓ Created {data['number']}, total: €{initial_total}")
        
        # Step 2: Get and verify all fields
        get_resp = api_client.get(f"{BASE_URL}/api/perizie/{perizia_id}")
        assert get_resp.status_code == 200
        fetched = get_resp.json()
        assert fetched["localizzazione"]["indirizzo"] == "Via Roma 123"
        assert len(fetched["codici_danno"]) == 2
        print(f"✓ Verified all fields persisted")
        
        # Step 3: Update - add G1-GAP code
        update_resp = api_client.put(f"{BASE_URL}/api/perizie/{perizia_id}", json={
            "codici_danno": ["S1-DEF", "P1-ZINC", "G1-GAP"],
            "stato_di_fatto": "Recinzione con deformazione plastica e protezione compromessa",
            "nota_tecnica": "Necessaria sostituzione integrale per EN 1090-2"
        })
        assert update_resp.status_code == 200
        print(f"✓ Updated with G1-GAP and technical notes")
        
        # Step 4: Recalculate
        recalc_resp = api_client.post(f"{BASE_URL}/api/perizie/{perizia_id}/recalc")
        assert recalc_resp.status_code == 200
        recalc_data = recalc_resp.json()
        
        new_codes = [v["codice"] for v in recalc_data["voci_costo"]]
        assert "SIC.01" in new_codes, "G1-GAP should add SIC.01"
        new_total = recalc_data["total_perizia"]
        assert new_total > initial_total, "Adding SIC.01 should increase total"
        print(f"✓ Recalculated: €{initial_total} → €{new_total}")
        
        # Step 5: Generate PDF
        pdf_resp = api_client.get(f"{BASE_URL}/api/perizie/{perizia_id}/pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers.get("content-type") == "application/pdf"
        print(f"✓ PDF generated: {len(pdf_resp.content)} bytes")
        
        # Final verification
        final = api_client.get(f"{BASE_URL}/api/perizie/{perizia_id}").json()
        assert final["total_perizia"] == new_total
        assert "SIC.01" in [v["codice"] for v in final["voci_costo"]]
        
        print(f"\n✅ Full workflow complete: {final['number']}")
        print(f"   Total: €{final['total_perizia']}")
        print(f"   Codes: {final['codici_danno']}")
        print(f"   Cost items: {[v['codice'] for v in final['voci_costo']]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
