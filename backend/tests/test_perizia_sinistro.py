"""
Test Suite for Perizia Sinistro (Damage Assessment) Module
Tests all CRUD operations, cost calculation logic, recalculation, and PDF generation.
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestPeriziaSetup:
    """Test setup - create auth token and seed data"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create an authenticated session for testing"""
        # Create a unique test session
        session_id = f"test_session_perizia_{uuid.uuid4().hex[:12]}"
        user_id = f"test_user_perizia_{uuid.uuid4().hex[:8]}"
        
        # Create session directly in MongoDB
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017")
        db = client["test_database"]
        
        # Create user session
        db.sessions.insert_one({
            "session_id": session_id,
            "user_id": user_id,
            "email": f"{user_id}@test.com",
            "name": "Test User Perizia",
            "picture": "",
            "created_at": datetime.utcnow(),
            "expires_at": datetime(2030, 1, 1),
        })
        
        # Return session headers
        headers = {
            "Authorization": f"Bearer {session_id}",
            "Content-Type": "application/json"
        }
        
        yield {"headers": headers, "user_id": user_id, "session_id": session_id, "db": db}
        
        # Cleanup
        db.sessions.delete_many({"user_id": user_id})
        db.perizie.delete_many({"user_id": user_id})
        db.clients.delete_many({"user_id": user_id})
        client.close()


class TestPeriziaHealthCheck:
    """Health check for perizie endpoints"""
    
    def test_api_health(self):
        """Test API health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("API health check passed")


class TestPeriziaCRUD(TestPeriziaSetup):
    """Test CRUD operations for Perizia Sinistro"""
    
    # ── CREATE Tests ──
    
    def test_create_perizia_strutturale_auto_cost(self, auth_session):
        """Test creating a structural damage perizia - should auto-generate 6 cost items"""
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Urto da veicolo su recinzione in acciaio zincato",
            "prezzo_ml_originale": 150.0,
            "coefficiente_maggiorazione": 20,
            "moduli": [
                {"descrizione": "Modulo A", "lunghezza_ml": 3.0, "altezza_m": 2.0, "note": "Pannello piegato"},
                {"descrizione": "Modulo B", "lunghezza_ml": 2.5, "altezza_m": 2.0, "note": "Montante deformato"}
            ],
            "localizzazione": {
                "indirizzo": "Via Test 123",
                "lat": 41.9028,
                "lng": 12.4964,
                "comune": "Roma",
                "provincia": "RM"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/perizie/",
            json=payload,
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify perizia was created
        assert "perizia_id" in data
        assert data["number"].startswith("PER-")
        assert data["tipo_danno"] == "strutturale"
        assert data["status"] == "bozza"
        
        # Verify auto-generated cost items for strutturale (6 items)
        voci = data.get("voci_costo", [])
        assert len(voci) == 6, f"Expected 6 cost items for strutturale, got {len(voci)}"
        
        # Check cost item codes
        codes = [v["codice"] for v in voci]
        assert "A.01" in codes, "Missing A.01 (smontaggio)"
        assert "B.01" in codes, "Missing B.01 (fornitura)"
        assert "C.01" in codes, "Missing C.01 (trasporto)"
        assert "D.01" in codes, "Missing D.01 (installazione)"
        assert "E.01" in codes, "Missing E.01 (oneri normativi)"
        assert "F.01" in codes, "Missing F.01 (smaltimento)"
        
        # Verify total is calculated
        assert data.get("total_perizia", 0) > 0
        
        print(f"Created strutturale perizia {data['number']} with {len(voci)} cost items, total: {data['total_perizia']} EUR")
        
        # Store for cleanup
        auth_session["test_perizia_id"] = data["perizia_id"]
        return data
    
    def test_create_perizia_estetico_auto_cost(self, auth_session):
        """Test creating an aesthetic damage perizia - should auto-generate cost items"""
        payload = {
            "tipo_danno": "estetico",
            "descrizione_utente": "TEST_Graffi e abrasioni su verniciatura",
            "prezzo_ml_originale": 100.0,
            "coefficiente_maggiorazione": 10,
            "moduli": [
                {"descrizione": "Pannello graffiato", "lunghezza_ml": 4.0, "altezza_m": 1.5, "note": ""}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/perizie/",
            json=payload,
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify estetico cost items (3 items: A.01 smontaggio, B.01 carteggiatura, F.01 smaltimento)
        voci = data.get("voci_costo", [])
        assert len(voci) == 3, f"Expected 3 cost items for estetico, got {len(voci)}"
        
        codes = [v["codice"] for v in voci]
        assert "A.01" in codes, "Missing A.01"
        assert "B.01" in codes, "Missing B.01 (carteggiatura)"
        assert "F.01" in codes, "Missing F.01"
        
        print(f"Created estetico perizia {data['number']} with {len(voci)} cost items")
        return data
    
    def test_create_perizia_automatismi_auto_cost(self, auth_session):
        """Test creating an automation damage perizia - should auto-generate cost items"""
        payload = {
            "tipo_danno": "automatismi",
            "descrizione_utente": "TEST_Motore automazione cancello danneggiato",
            "prezzo_ml_originale": 200.0,
            "coefficiente_maggiorazione": 15,
            "moduli": [
                {"descrizione": "Cancello motorizzato", "lunghezza_ml": 5.0, "altezza_m": 2.5, "note": "Motore bloccato"}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/perizie/",
            json=payload,
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify automatismi cost items (4 items: A.01 smontaggio, B.01 componenti, B.02 collaudo, F.01 smaltimento)
        voci = data.get("voci_costo", [])
        assert len(voci) == 4, f"Expected 4 cost items for automatismi, got {len(voci)}"
        
        codes = [v["codice"] for v in voci]
        assert "A.01" in codes
        assert "B.01" in codes, "Missing B.01 (componenti)"
        assert "B.02" in codes, "Missing B.02 (collaudo EN12453)"
        assert "F.01" in codes
        
        print(f"Created automatismi perizia {data['number']} with {len(voci)} cost items")
        return data
    
    # ── GET/LIST Tests ──
    
    def test_list_perizie(self, auth_session):
        """Test listing all perizie"""
        response = requests.get(
            f"{BASE_URL}/api/perizie/",
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 0
        print(f"Listed {data['total']} perizie")
    
    def test_list_perizie_with_search(self, auth_session):
        """Test searching perizie"""
        response = requests.get(
            f"{BASE_URL}/api/perizie/?search=TEST_",
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        print(f"Search found {data['total']} perizie matching 'TEST_'")
    
    def test_get_single_perizia(self, auth_session):
        """Test getting a single perizia by ID"""
        # First create one
        create_payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Single fetch test",
            "prezzo_ml_originale": 120.0,
            "moduli": [{"descrizione": "Test module", "lunghezza_ml": 2.0, "altezza_m": 1.5, "note": ""}]
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/perizie/",
            json=create_payload,
            headers=auth_session["headers"]
        )
        assert create_resp.status_code == 201
        perizia_id = create_resp.json()["perizia_id"]
        
        # Now fetch it
        response = requests.get(
            f"{BASE_URL}/api/perizie/{perizia_id}",
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["perizia_id"] == perizia_id
        assert data["descrizione_utente"] == "TEST_Single fetch test"
        print(f"Successfully fetched perizia {data['number']}")
    
    def test_get_perizia_not_found(self, auth_session):
        """Test 404 for non-existent perizia"""
        response = requests.get(
            f"{BASE_URL}/api/perizie/nonexistent_id_12345",
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 404
        print("404 returned for non-existent perizia")
    
    # ── UPDATE Tests ──
    
    def test_update_perizia(self, auth_session):
        """Test updating a perizia"""
        # Create one first
        create_payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Original description",
            "prezzo_ml_originale": 100.0,
            "moduli": [{"descrizione": "Original module", "lunghezza_ml": 2.0, "altezza_m": 1.5, "note": ""}]
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/perizie/",
            json=create_payload,
            headers=auth_session["headers"]
        )
        assert create_resp.status_code == 201
        perizia_id = create_resp.json()["perizia_id"]
        
        # Update it
        update_payload = {
            "descrizione_utente": "TEST_Updated description",
            "prezzo_ml_originale": 180.0,
            "notes": "Updated notes from test"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/perizie/{perizia_id}",
            json=update_payload,
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["descrizione_utente"] == "TEST_Updated description"
        assert data["prezzo_ml_originale"] == 180.0
        assert data["notes"] == "Updated notes from test"
        print(f"Successfully updated perizia {data['number']}")
        
        # Verify GET returns updated data
        get_resp = requests.get(
            f"{BASE_URL}/api/perizie/{perizia_id}",
            headers=auth_session["headers"]
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["descrizione_utente"] == "TEST_Updated description"
    
    def test_update_perizia_voci_costo(self, auth_session):
        """Test updating cost items and total recalculation"""
        # Create one first
        create_payload = {
            "tipo_danno": "estetico",
            "descrizione_utente": "TEST_Cost update test",
            "moduli": [{"descrizione": "Module", "lunghezza_ml": 3.0, "altezza_m": 1.5, "note": ""}]
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/perizie/",
            json=create_payload,
            headers=auth_session["headers"]
        )
        assert create_resp.status_code == 201
        perizia_id = create_resp.json()["perizia_id"]
        original_total = create_resp.json()["total_perizia"]
        
        # Update with custom voci_costo
        custom_voci = [
            {"codice": "X.01", "descrizione": "Custom item 1", "unita": "corpo", "quantita": 1, "prezzo_unitario": 500, "totale": 500},
            {"codice": "X.02", "descrizione": "Custom item 2", "unita": "ore", "quantita": 5, "prezzo_unitario": 50, "totale": 250}
        ]
        
        update_payload = {"voci_costo": custom_voci}
        
        response = requests.put(
            f"{BASE_URL}/api/perizie/{perizia_id}",
            json=update_payload,
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["voci_costo"]) == 2
        assert data["total_perizia"] == 750.0  # 500 + 250
        print(f"Cost items updated, new total: {data['total_perizia']} EUR (was {original_total})")
    
    # ── DELETE Tests ──
    
    def test_delete_perizia(self, auth_session):
        """Test deleting a perizia"""
        # Create one first
        create_payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_To be deleted",
            "moduli": [{"descrizione": "Delete me", "lunghezza_ml": 1.0, "altezza_m": 1.0, "note": ""}]
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/perizie/",
            json=create_payload,
            headers=auth_session["headers"]
        )
        assert create_resp.status_code == 201
        perizia_id = create_resp.json()["perizia_id"]
        
        # Delete it
        response = requests.delete(
            f"{BASE_URL}/api/perizie/{perizia_id}",
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Perizia eliminata"
        print(f"Successfully deleted perizia {perizia_id}")
        
        # Verify it's gone
        get_resp = requests.get(
            f"{BASE_URL}/api/perizie/{perizia_id}",
            headers=auth_session["headers"]
        )
        assert get_resp.status_code == 404
    
    def test_delete_perizia_not_found(self, auth_session):
        """Test 404 for deleting non-existent perizia"""
        response = requests.delete(
            f"{BASE_URL}/api/perizie/nonexistent_id_12345",
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 404
        print("404 returned for deleting non-existent perizia")


class TestPeriziaCostCalculation(TestPeriziaSetup):
    """Test cost calculation logic"""
    
    def test_fornitura_calculation_with_markup(self, auth_session):
        """Test: fornitura = prezzo_ml * (1 + coefficiente_maggiorazione/100) * total_ml"""
        prezzo_ml = 150.0
        coeff = 20  # 20% markup
        total_ml = 5.5  # Sum of modules
        
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Fornitura calculation",
            "prezzo_ml_originale": prezzo_ml,
            "coefficiente_maggiorazione": coeff,
            "moduli": [
                {"descrizione": "Mod A", "lunghezza_ml": 3.0, "altezza_m": 2.0, "note": ""},
                {"descrizione": "Mod B", "lunghezza_ml": 2.5, "altezza_m": 2.0, "note": ""}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/perizie/",
            json=payload,
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Find B.01 (fornitura) item
        fornitura = next((v for v in data["voci_costo"] if v["codice"] == "B.01"), None)
        assert fornitura is not None, "B.01 (fornitura) not found"
        
        # Expected calculation: prezzo_ml * (1 + coeff/100) * total_ml
        expected_unit = prezzo_ml * (1 + coeff / 100)  # 150 * 1.20 = 180
        expected_total = expected_unit * total_ml  # 180 * 5.5 = 990
        
        assert fornitura["quantita"] == total_ml, f"Expected qty {total_ml}, got {fornitura['quantita']}"
        assert abs(fornitura["prezzo_unitario"] - expected_unit) < 0.01, f"Expected unit price {expected_unit}, got {fornitura['prezzo_unitario']}"
        assert abs(fornitura["totale"] - expected_total) < 0.01, f"Expected total {expected_total}, got {fornitura['totale']}"
        
        print(f"Fornitura calculation correct: {fornitura['quantita']} ml × {fornitura['prezzo_unitario']} EUR/ml = {fornitura['totale']} EUR")
    
    def test_trasporto_under_2_5ml(self, auth_session):
        """Test trasporto = 180 EUR when ml <= 2.5"""
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Trasporto small",
            "prezzo_ml_originale": 100.0,
            "moduli": [
                {"descrizione": "Small module", "lunghezza_ml": 2.0, "altezza_m": 1.5, "note": ""}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/perizie/",
            json=payload,
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Find C.01 (trasporto) item
        trasporto = next((v for v in data["voci_costo"] if v["codice"] == "C.01"), None)
        assert trasporto is not None
        assert trasporto["totale"] == 180.0, f"Expected trasporto 180 EUR for <=2.5ml, got {trasporto['totale']}"
        
        print(f"Trasporto for <=2.5ml: {trasporto['totale']} EUR (expected 180)")
    
    def test_trasporto_over_2_5ml(self, auth_session):
        """Test trasporto = 350 EUR when ml > 2.5"""
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Trasporto large",
            "prezzo_ml_originale": 100.0,
            "moduli": [
                {"descrizione": "Large module", "lunghezza_ml": 3.0, "altezza_m": 2.0, "note": ""}
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/perizie/",
            json=payload,
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Find C.01 (trasporto) item
        trasporto = next((v for v in data["voci_costo"] if v["codice"] == "C.01"), None)
        assert trasporto is not None
        assert trasporto["totale"] == 350.0, f"Expected trasporto 350 EUR for >2.5ml, got {trasporto['totale']}"
        
        print(f"Trasporto for >2.5ml: {trasporto['totale']} EUR (expected 350)")


class TestPeriziaRecalc(TestPeriziaSetup):
    """Test cost recalculation endpoint"""
    
    def test_recalculate_costs(self, auth_session):
        """Test POST /api/perizie/{id}/recalc recalculates cost items"""
        # Create perizia with initial values
        create_payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Recalc test",
            "prezzo_ml_originale": 100.0,
            "coefficiente_maggiorazione": 20,
            "moduli": [{"descrizione": "Module", "lunghezza_ml": 2.0, "altezza_m": 1.5, "note": ""}]
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/perizie/",
            json=create_payload,
            headers=auth_session["headers"]
        )
        assert create_resp.status_code == 201
        perizia_id = create_resp.json()["perizia_id"]
        original_total = create_resp.json()["total_perizia"]
        
        # Update modules and price (but NOT voci_costo directly)
        update_payload = {
            "prezzo_ml_originale": 200.0,
            "moduli": [
                {"descrizione": "Module A", "lunghezza_ml": 4.0, "altezza_m": 2.0, "note": ""},
                {"descrizione": "Module B", "lunghezza_ml": 3.0, "altezza_m": 2.0, "note": ""}
            ]
        }
        
        requests.put(
            f"{BASE_URL}/api/perizie/{perizia_id}",
            json=update_payload,
            headers=auth_session["headers"]
        )
        
        # Now call recalc
        response = requests.post(
            f"{BASE_URL}/api/perizie/{perizia_id}/recalc",
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "voci_costo" in data
        assert "total_perizia" in data
        assert data["total_perizia"] != original_total, "Recalc should change total with new values"
        
        print(f"Recalc changed total from {original_total} to {data['total_perizia']} EUR")
        
        # Verify persistence
        get_resp = requests.get(
            f"{BASE_URL}/api/perizie/{perizia_id}",
            headers=auth_session["headers"]
        )
        assert get_resp.json()["total_perizia"] == data["total_perizia"]
    
    def test_recalc_not_found(self, auth_session):
        """Test 404 for recalc on non-existent perizia"""
        response = requests.post(
            f"{BASE_URL}/api/perizie/nonexistent_id_12345/recalc",
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 404
        print("404 returned for recalc on non-existent perizia")


class TestPeriziaPDF(TestPeriziaSetup):
    """Test PDF generation"""
    
    def test_pdf_generation(self, auth_session):
        """Test GET /api/perizie/{id}/pdf returns a PDF"""
        # Create perizia
        create_payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_PDF generation test",
            "prezzo_ml_originale": 150.0,
            "moduli": [{"descrizione": "Module for PDF", "lunghezza_ml": 3.0, "altezza_m": 2.0, "note": "Test note"}],
            "stato_di_fatto": "Test stato di fatto for PDF",
            "nota_tecnica": "Test nota tecnica for PDF"
        }
        
        create_resp = requests.post(
            f"{BASE_URL}/api/perizie/",
            json=create_payload,
            headers=auth_session["headers"]
        )
        assert create_resp.status_code == 201
        perizia_id = create_resp.json()["perizia_id"]
        
        # Get PDF
        response = requests.get(
            f"{BASE_URL}/api/perizie/{perizia_id}/pdf",
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 0
        
        # Check filename in Content-Disposition header
        content_disp = response.headers.get("content-disposition", "")
        assert "perizia_" in content_disp
        assert ".pdf" in content_disp
        
        print(f"PDF generated successfully, size: {len(response.content)} bytes")
    
    def test_pdf_not_found(self, auth_session):
        """Test 404 for PDF on non-existent perizia"""
        response = requests.get(
            f"{BASE_URL}/api/perizie/nonexistent_id_12345/pdf",
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 404
        print("404 returned for PDF on non-existent perizia")


class TestPeriziaAuth:
    """Test authentication requirements"""
    
    def test_list_requires_auth(self):
        """Test listing perizie requires authentication"""
        response = requests.get(f"{BASE_URL}/api/perizie/")
        assert response.status_code in [401, 403, 422]
        print(f"List perizie requires auth: {response.status_code}")
    
    def test_create_requires_auth(self):
        """Test creating perizia requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/perizie/",
            json={"tipo_danno": "strutturale", "descrizione_utente": "Unauthorized test"}
        )
        assert response.status_code in [401, 403, 422]
        print(f"Create perizia requires auth: {response.status_code}")


class TestPeriziaNumber(TestPeriziaSetup):
    """Test perizia number generation"""
    
    def test_perizia_number_format(self, auth_session):
        """Test perizia number follows PER-{year}/{seq} format"""
        payload = {
            "tipo_danno": "strutturale",
            "descrizione_utente": "TEST_Number format test",
            "moduli": [{"descrizione": "Module", "lunghezza_ml": 1.0, "altezza_m": 1.0, "note": ""}]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/perizie/",
            json=payload,
            headers=auth_session["headers"]
        )
        
        assert response.status_code == 201
        data = response.json()
        
        number = data["number"]
        current_year = datetime.now().strftime("%Y")
        
        assert number.startswith(f"PER-{current_year}/"), f"Number should start with PER-{current_year}/, got {number}"
        
        # Check sequence part is a 4-digit padded number
        parts = number.split("/")
        assert len(parts) == 2
        seq = parts[1]
        assert seq.isdigit() and len(seq) == 4, f"Sequence should be 4-digit number, got {seq}"
        
        print(f"Perizia number format correct: {number}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
