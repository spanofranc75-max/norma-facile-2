"""
Test Suite for Perizia Sinistro (Damage Assessment) Module
Tests all CRUD operations, cost calculation logic, recalculation, and PDF generation.
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

# Use localhost for internal tests (external URL uses same MongoDB)
BASE_URL = "http://localhost:8001"

from pymongo import MongoClient


def create_test_session():
    """Create a test user and session in MongoDB."""
    client = MongoClient("mongodb://localhost:27017")
    db = client["test_database"]
    
    session_token = f"test_perizia_{uuid.uuid4().hex[:12]}"
    user_id = f"user_perizia_{uuid.uuid4().hex[:8]}"
    email = f"{user_id}@test.com"
    
    # Create user in 'users' collection
    db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "email": email,
            "name": "Perizia Test User",
            "picture": "",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True
    )
    
    # Create session in 'user_sessions' collection
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


# Create session at module load
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
    # Cleanup at end
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
    # Cleanup test data
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
# Health Check
# ═══════════════════════════════════════════════════════════════════════════════

class TestPeriziaHealthCheck:
    """Health check for perizie endpoints"""
    
    def test_api_health(self):
        """Test API health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ API health check passed")


# ═══════════════════════════════════════════════════════════════════════════════
# CRUD Operations Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPeriziaCreate:
    """Test perizia creation with auto cost generation"""
    
    def test_create_perizia_strutturale_generates_6_items(self, api_client, cleanup_perizie):
        """POST /api/perizie/ with tipo_danno=strutturale → should generate 6 cost items"""
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Urto veicolo su recinzione acciaio zincato",
            "prezzo_ml_originale": 150.0,
            "coefficiente_maggiorazione": 20,
            "moduli": [
                {"descrizione": "Modulo A", "lunghezza_ml": 3.0, "altezza_m": 2.0, "note": "Piegato"},
                {"descrizione": "Modulo B", "lunghezza_ml": 2.5, "altezza_m": 2.0, "note": "Deformato"}
            ],
            "localizzazione": {
                "indirizzo": "Via Test 123",
                "lat": 41.9028,
                "lng": 12.4964,
                "comune": "Roma",
                "provincia": "RM"
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        # Verify basic fields
        assert "perizia_id" in data
        assert data["number"].startswith("PER-")
        assert data["tipo_danno"] == "strutturale"
        assert data["status"] == "bozza"
        
        # Verify 6 cost items for strutturale
        voci = data.get("voci_costo", [])
        assert len(voci) == 6, f"Strutturale should have 6 items, got {len(voci)}"
        
        codes = [v["codice"] for v in voci]
        assert "A.01" in codes, "Missing A.01 (smontaggio)"
        assert "B.01" in codes, "Missing B.01 (fornitura)"
        assert "C.01" in codes, "Missing C.01 (trasporto)"
        assert "D.01" in codes, "Missing D.01 (installazione)"
        assert "E.01" in codes, "Missing E.01 (oneri normativi)"
        assert "F.01" in codes, "Missing F.01 (smaltimento)"
        
        assert data.get("total_perizia", 0) > 0
        print(f"✓ Created strutturale perizia {data['number']} with 6 items, total: {data['total_perizia']} EUR")
    
    def test_create_perizia_estetico_generates_3_items(self, api_client, cleanup_perizie):
        """POST /api/perizie/ with tipo_danno=estetico → should generate 3 cost items"""
        payload = {
            "tipo_danno": "estetico",
            "descrizione_utente": "TEST_Graffi e abrasioni su verniciatura",
            "prezzo_ml_originale": 100.0,
            "moduli": [{"descrizione": "Pannello", "lunghezza_ml": 4.0, "altezza_m": 1.5, "note": ""}]
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        voci = data.get("voci_costo", [])
        assert len(voci) == 3, f"Estetico should have 3 items, got {len(voci)}"
        
        codes = [v["codice"] for v in voci]
        assert "A.01" in codes
        assert "B.01" in codes, "Missing B.01 (carteggiatura)"
        assert "F.01" in codes
        print(f"✓ Created estetico perizia {data['number']} with 3 items")
    
    def test_create_perizia_automatismi_generates_4_items(self, api_client, cleanup_perizie):
        """POST /api/perizie/ with tipo_danno=automatismi → should generate 4 cost items"""
        payload = {
            "tipo_danno": "automatismi",
            "descrizione_utente": "TEST_Motore automazione cancello danneggiato",
            "prezzo_ml_originale": 200.0,
            "moduli": [{"descrizione": "Cancello", "lunghezza_ml": 5.0, "altezza_m": 2.5, "note": ""}]
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        voci = data.get("voci_costo", [])
        assert len(voci) == 4, f"Automatismi should have 4 items, got {len(voci)}"
        
        codes = [v["codice"] for v in voci]
        assert "A.01" in codes
        assert "B.01" in codes, "Missing B.01 (componenti)"
        assert "B.02" in codes, "Missing B.02 (collaudo EN12453)"
        assert "F.01" in codes
        print(f"✓ Created automatismi perizia {data['number']} with 4 items")


class TestPeriziaList:
    """Test listing and searching perizie"""
    
    def test_list_perizie_returns_items_and_total(self, api_client):
        """GET /api/perizie/ returns items array and total count"""
        response = api_client.get(f"{BASE_URL}/api/perizie/")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        print(f"✓ Listed {data['total']} perizie")
    
    def test_list_perizie_with_search_filter(self, api_client, cleanup_perizie):
        """GET /api/perizie/?search=XXX filters results"""
        # First create a unique one
        unique_desc = f"TEST_UNIQUE_{uuid.uuid4().hex[:8]}"
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": unique_desc,
            "moduli": [{"descrizione": "Test", "lunghezza_ml": 1, "altezza_m": 1, "note": ""}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert create_resp.status_code == 201
        cleanup_perizie.append(create_resp.json()["perizia_id"])
        
        # Search for it
        response = api_client.get(f"{BASE_URL}/api/perizie/?search={unique_desc}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] >= 1
        assert any(unique_desc in item.get("descrizione_utente", "") for item in data["items"])
        print(f"✓ Search filter working, found {data['total']} matching perizie")


class TestPeriziaGetOne:
    """Test getting single perizia"""
    
    def test_get_perizia_returns_all_fields(self, api_client, cleanup_perizie):
        """GET /api/perizie/{id} returns complete perizia with all fields"""
        # Create one
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Get single",
            "prezzo_ml_originale": 120,
            "moduli": [{"descrizione": "Module", "lunghezza_ml": 2.0, "altezza_m": 1.5, "note": ""}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert create_resp.status_code == 201
        perizia_id = create_resp.json()["perizia_id"]
        cleanup_perizie.append(perizia_id)
        
        # Fetch it
        response = api_client.get(f"{BASE_URL}/api/perizie/{perizia_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["perizia_id"] == perizia_id
        assert "number" in data
        assert "tipo_danno" in data
        assert "voci_costo" in data
        assert "total_perizia" in data
        print(f"✓ Got perizia {data['number']} with all fields")
    
    def test_get_perizia_not_found_returns_404(self, api_client):
        """GET /api/perizie/{invalid_id} returns 404"""
        response = api_client.get(f"{BASE_URL}/api/perizie/nonexistent_id_xyz")
        assert response.status_code == 404
        print("✓ 404 returned for non-existent perizia")


class TestPeriziaUpdate:
    """Test updating perizia"""
    
    def test_update_perizia_modifies_fields(self, api_client, cleanup_perizie):
        """PUT /api/perizie/{id} updates fields correctly"""
        # Create
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Original",
            "prezzo_ml_originale": 100,
            "moduli": [{"descrizione": "Orig", "lunghezza_ml": 2, "altezza_m": 1.5, "note": ""}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert create_resp.status_code == 201
        perizia_id = create_resp.json()["perizia_id"]
        cleanup_perizie.append(perizia_id)
        
        # Update
        update_payload = {
            "descrizione_utente": "TEST_Updated",
            "prezzo_ml_originale": 180,
            "notes": "Updated notes"
        }
        response = api_client.put(f"{BASE_URL}/api/perizie/{perizia_id}", json=update_payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["descrizione_utente"] == "TEST_Updated"
        assert data["prezzo_ml_originale"] == 180
        assert data["notes"] == "Updated notes"
        
        # Verify persistence via GET
        get_resp = api_client.get(f"{BASE_URL}/api/perizie/{perizia_id}")
        assert get_resp.json()["descrizione_utente"] == "TEST_Updated"
        print(f"✓ Updated perizia, verified persistence")
    
    def test_update_voci_costo_recalculates_total(self, api_client, cleanup_perizie):
        """PUT /api/perizie/{id} with voci_costo recalculates total_perizia"""
        # Create
        payload = {
            "tipo_danno": "estetico",
            "descrizione_utente": "TEST_Voci update",
            "moduli": [{"descrizione": "M", "lunghezza_ml": 2, "altezza_m": 1, "note": ""}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert create_resp.status_code == 201
        perizia_id = create_resp.json()["perizia_id"]
        cleanup_perizie.append(perizia_id)
        
        # Update with custom cost items
        custom_voci = [
            {"codice": "X.01", "descrizione": "Item 1", "unita": "corpo", "quantita": 1, "prezzo_unitario": 500, "totale": 500},
            {"codice": "X.02", "descrizione": "Item 2", "unita": "ore", "quantita": 5, "prezzo_unitario": 50, "totale": 250}
        ]
        response = api_client.put(f"{BASE_URL}/api/perizie/{perizia_id}", json={"voci_costo": custom_voci})
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["voci_costo"]) == 2
        assert data["total_perizia"] == 750.0
        print(f"✓ Updated cost items, total recalculated to {data['total_perizia']} EUR")


class TestPeriziaDelete:
    """Test deleting perizia"""
    
    def test_delete_perizia_removes_it(self, api_client):
        """DELETE /api/perizie/{id} removes the perizia"""
        # Create one (don't add to cleanup since we're deleting)
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_To delete",
            "moduli": [{"descrizione": "D", "lunghezza_ml": 1, "altezza_m": 1, "note": ""}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert create_resp.status_code == 201
        perizia_id = create_resp.json()["perizia_id"]
        
        # Delete
        response = api_client.delete(f"{BASE_URL}/api/perizie/{perizia_id}")
        assert response.status_code == 200
        assert response.json()["message"] == "Perizia eliminata"
        
        # Verify gone
        get_resp = api_client.get(f"{BASE_URL}/api/perizie/{perizia_id}")
        assert get_resp.status_code == 404
        print(f"✓ Deleted perizia and verified removal")
    
    def test_delete_not_found_returns_404(self, api_client):
        """DELETE /api/perizie/{invalid_id} returns 404"""
        response = api_client.delete(f"{BASE_URL}/api/perizie/nonexistent_xyz")
        assert response.status_code == 404
        print("✓ 404 returned for deleting non-existent perizia")


# ═══════════════════════════════════════════════════════════════════════════════
# Cost Calculation Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCostCalculation:
    """Test cost calculation formulas"""
    
    def test_fornitura_uses_markup_formula(self, api_client, cleanup_perizie):
        """fornitura = prezzo_ml * (1 + coefficiente_maggiorazione/100) * total_ml"""
        prezzo_ml = 150.0
        coeff = 20  # 20%
        ml1, ml2 = 3.0, 2.5
        total_ml = ml1 + ml2  # 5.5
        
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Fornitura calc",
            "prezzo_ml_originale": prezzo_ml,
            "coefficiente_maggiorazione": coeff,
            "moduli": [
                {"descrizione": "A", "lunghezza_ml": ml1, "altezza_m": 2, "note": ""},
                {"descrizione": "B", "lunghezza_ml": ml2, "altezza_m": 2, "note": ""}
            ]
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        # Find B.01 (fornitura)
        fornitura = next((v for v in data["voci_costo"] if v["codice"] == "B.01"), None)
        assert fornitura is not None
        
        expected_unit = prezzo_ml * (1 + coeff / 100)  # 150 * 1.2 = 180
        expected_total = expected_unit * total_ml  # 180 * 5.5 = 990
        
        assert abs(fornitura["prezzo_unitario"] - expected_unit) < 0.01
        assert abs(fornitura["totale"] - expected_total) < 0.01
        print(f"✓ Fornitura calc: {total_ml} ml × {fornitura['prezzo_unitario']} EUR/ml = {fornitura['totale']} EUR")
    
    def test_trasporto_180_when_under_2_5ml(self, api_client, cleanup_perizie):
        """trasporto = 180 EUR when total_ml <= 2.5"""
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Trasporto small",
            "prezzo_ml_originale": 100,
            "moduli": [{"descrizione": "Small", "lunghezza_ml": 2.0, "altezza_m": 1.5, "note": ""}]
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        trasporto = next((v for v in data["voci_costo"] if v["codice"] == "C.01"), None)
        assert trasporto is not None
        assert trasporto["totale"] == 180.0
        print(f"✓ Trasporto for ≤2.5ml = {trasporto['totale']} EUR (expected 180)")
    
    def test_trasporto_350_when_over_2_5ml(self, api_client, cleanup_perizie):
        """trasporto = 350 EUR when total_ml > 2.5"""
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Trasporto large",
            "prezzo_ml_originale": 100,
            "moduli": [{"descrizione": "Large", "lunghezza_ml": 3.0, "altezza_m": 2, "note": ""}]
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        trasporto = next((v for v in data["voci_costo"] if v["codice"] == "C.01"), None)
        assert trasporto is not None
        assert trasporto["totale"] == 350.0
        print(f"✓ Trasporto for >2.5ml = {trasporto['totale']} EUR (expected 350)")


# ═══════════════════════════════════════════════════════════════════════════════
# Recalculation Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPeriziaRecalc:
    """Test cost recalculation endpoint"""
    
    def test_recalc_regenerates_costs(self, api_client, cleanup_perizie):
        """POST /api/perizie/{id}/recalc regenerates cost items from current data"""
        # Create with initial values
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Recalc",
            "prezzo_ml_originale": 100,
            "coefficiente_maggiorazione": 20,
            "moduli": [{"descrizione": "M", "lunghezza_ml": 2, "altezza_m": 1.5, "note": ""}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert create_resp.status_code == 201
        perizia_id = create_resp.json()["perizia_id"]
        cleanup_perizie.append(perizia_id)
        original_total = create_resp.json()["total_perizia"]
        
        # Update modules and price (more material = higher cost)
        update = {
            "prezzo_ml_originale": 200,
            "moduli": [
                {"descrizione": "A", "lunghezza_ml": 4, "altezza_m": 2, "note": ""},
                {"descrizione": "B", "lunghezza_ml": 3, "altezza_m": 2, "note": ""}
            ]
        }
        api_client.put(f"{BASE_URL}/api/perizie/{perizia_id}", json=update)
        
        # Recalc
        response = api_client.post(f"{BASE_URL}/api/perizie/{perizia_id}/recalc")
        assert response.status_code == 200
        
        data = response.json()
        assert "voci_costo" in data
        assert "total_perizia" in data
        assert data["total_perizia"] > original_total, "Recalc should increase total with more material"
        
        # Verify persisted
        get_resp = api_client.get(f"{BASE_URL}/api/perizie/{perizia_id}")
        assert get_resp.json()["total_perizia"] == data["total_perizia"]
        print(f"✓ Recalc changed total from {original_total} to {data['total_perizia']} EUR")
    
    def test_recalc_not_found_returns_404(self, api_client):
        """POST /api/perizie/{invalid}/recalc returns 404"""
        response = api_client.post(f"{BASE_URL}/api/perizie/nonexistent_xyz/recalc")
        assert response.status_code == 404
        print("✓ 404 returned for recalc on non-existent perizia")


# ═══════════════════════════════════════════════════════════════════════════════
# PDF Generation Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPeriziaPDF:
    """Test PDF generation endpoint"""
    
    def test_pdf_returns_valid_document(self, api_client, cleanup_perizie):
        """GET /api/perizie/{id}/pdf returns PDF with correct headers"""
        # Create with full data
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_PDF generation",
            "prezzo_ml_originale": 150,
            "moduli": [{"descrizione": "Module PDF", "lunghezza_ml": 3, "altezza_m": 2, "note": "Test"}],
            "stato_di_fatto": "Stato di fatto test text",
            "nota_tecnica": "Nota tecnica test text"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert create_resp.status_code == 201
        perizia_id = create_resp.json()["perizia_id"]
        cleanup_perizie.append(perizia_id)
        
        # Get PDF
        response = api_client.get(f"{BASE_URL}/api/perizie/{perizia_id}/pdf")
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 100  # PDF should have some content
        
        # Check Content-Disposition header
        content_disp = response.headers.get("content-disposition", "")
        assert "perizia_" in content_disp
        assert ".pdf" in content_disp
        print(f"✓ PDF generated, size: {len(response.content)} bytes")
    
    def test_pdf_not_found_returns_404(self, api_client):
        """GET /api/perizie/{invalid}/pdf returns 404"""
        response = api_client.get(f"{BASE_URL}/api/perizie/nonexistent_xyz/pdf")
        assert response.status_code == 404
        print("✓ 404 returned for PDF on non-existent perizia")


# ═══════════════════════════════════════════════════════════════════════════════
# Authentication Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPeriziaAuth:
    """Test authentication requirements"""
    
    def test_list_requires_auth(self):
        """GET /api/perizie/ without auth returns 401/403/422"""
        response = requests.get(f"{BASE_URL}/api/perizie/")
        assert response.status_code in [401, 403, 422]
        print(f"✓ List requires auth: {response.status_code}")
    
    def test_create_requires_auth(self):
        """POST /api/perizie/ without auth returns 401/403/422"""
        response = requests.post(f"{BASE_URL}/api/perizie/", json={"tipo_danno": "strutturale"})
        assert response.status_code in [401, 403, 422]
        print(f"✓ Create requires auth: {response.status_code}")


# ═══════════════════════════════════════════════════════════════════════════════
# Perizia Number Format Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPeriziaNumber:
    """Test perizia number generation"""
    
    def test_number_format_per_year_seq(self, api_client, cleanup_perizie):
        """Perizia number follows PER-{year}/{seq} format"""
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Number format",
            "moduli": [{"descrizione": "M", "lunghezza_ml": 1, "altezza_m": 1, "note": ""}]
        }
        
        response = api_client.post(f"{BASE_URL}/api/perizie/", json=payload)
        assert response.status_code == 201
        data = response.json()
        cleanup_perizie.append(data["perizia_id"])
        
        number = data["number"]
        current_year = datetime.now().strftime("%Y")
        
        assert number.startswith(f"PER-{current_year}/"), f"Should start with PER-{current_year}/, got {number}"
        
        parts = number.split("/")
        assert len(parts) == 2
        seq = parts[1]
        assert seq.isdigit() and len(seq) == 4, f"Sequence should be 4-digit, got {seq}"
        print(f"✓ Perizia number format correct: {number}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
