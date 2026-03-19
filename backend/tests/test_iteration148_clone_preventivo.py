"""
Test Suite for Iteration 148: Duplica Preventivo (Clone Quote) Feature

Tests the POST /api/preventivi/{prev_id}/clone endpoint:
- Creates a cloned preventivo with new ID, new number (PRV-YYYY-NNNN), status 'bozza'
- Today's date, all lines copied with new line_ids, totals recalculated
- converted_commessa_id null, total_invoiced reset to 0
- Returns 201 with full cloned document
- 404 for non-existent preventivo
"""

import pytest
import requests
import os
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://preventivo-stable.preview.emergentagent.com"


class TestClonePreventivo:
    """Tests for the Clone Preventivo (Duplica) feature"""
    
    @pytest.fixture(scope="class")
    def session_token(self):
        """Create or use test session token"""
        import pymongo
        from datetime import timedelta
        client = pymongo.MongoClient('mongodb://localhost:27017')
        db = client['test_database']
        
        # Create test session - using user_sessions collection with session_token field
        token = f"test_session_clone_{int(time.time()*1000)}"
        user_id = "user_97c773827822"
        
        db.user_sessions.update_one(
            {"session_token": token},
            {"$set": {
                "session_token": token,
                "user_id": user_id,
                "email": "spano.franc75@gmail.com",
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=30)
            }},
            upsert=True
        )
        
        yield token
        
        # Cleanup
        db.user_sessions.delete_one({"session_token": token})
        client.close()
    
    @pytest.fixture(scope="class")
    def api_client(self, session_token):
        """API client with auth cookie"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        session.cookies.set("session_token", session_token)
        return session
    
    @pytest.fixture(scope="class")
    def source_preventivo(self, api_client):
        """Create a source preventivo to clone"""
        payload = {
            "subject": "TEST_Clone_Source - Preventivo da clonare",
            "client_id": None,  # No client for test
            "validity_days": 45,
            "notes": "Questo preventivo verrà clonato",
            "payment_type_label": "Bonifico 30gg",
            "iban": "IT60X0542811101000000123456",
            "banca": "Banca Test",
            "normativa": "EN_1090",
            "classe_esecuzione": "EXC2",
            "giorni_consegna": 30,
            "sconto_globale": 5,
            "acconto": 500,
            "lines": [
                {
                    "description": "Carpenteria metallica strutturale",
                    "codice_articolo": "CARP-001",
                    "quantity": 10,
                    "unit": "kg",
                    "unit_price": 12.50,
                    "sconto_1": 10,
                    "vat_rate": "22"
                },
                {
                    "description": "Lavorazione speciale EN 1090",
                    "codice_articolo": "LAV-002",
                    "quantity": 1,
                    "unit": "corpo",
                    "unit_price": 850.00,
                    "sconto_1": 0,
                    "vat_rate": "22"
                }
            ]
        }
        
        response = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
        assert response.status_code == 201, f"Failed to create source preventivo: {response.text}"
        
        data = response.json()
        yield data
        
        # Cleanup - delete source preventivo
        api_client.delete(f"{BASE_URL}/api/preventivi/{data['preventivo_id']}")
    
    def test_clone_returns_201(self, api_client, source_preventivo):
        """Clone endpoint returns 201 status code"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        # Cleanup the clone
        cloned = response.json()
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
    
    def test_clone_has_new_preventivo_id(self, api_client, source_preventivo):
        """Cloned preventivo has a different preventivo_id"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201
        
        cloned = response.json()
        assert cloned["preventivo_id"] != source_preventivo["preventivo_id"], \
            "Cloned preventivo should have different ID"
        assert cloned["preventivo_id"].startswith("prev_"), \
            f"Cloned ID should start with 'prev_': {cloned['preventivo_id']}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
    
    def test_clone_has_new_number(self, api_client, source_preventivo):
        """Cloned preventivo has a new auto-generated number (PRV-YYYY-NNNN)"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201
        
        cloned = response.json()
        assert cloned["number"] != source_preventivo["number"], \
            "Cloned preventivo should have different number"
        
        year = datetime.now().year
        assert cloned["number"].startswith(f"PRV-{year}-"), \
            f"Cloned number should follow PRV-YYYY-NNNN format: {cloned['number']}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
    
    def test_clone_status_is_bozza(self, api_client, source_preventivo):
        """Cloned preventivo has status 'bozza' regardless of source status"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201
        
        cloned = response.json()
        assert cloned["status"] == "bozza", \
            f"Cloned status should be 'bozza', got: {cloned['status']}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
    
    def test_clone_has_today_date(self, api_client, source_preventivo):
        """Cloned preventivo has today's date in created_at"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201
        
        cloned = response.json()
        today = datetime.now().strftime("%Y-%m-%d")
        created_date = cloned.get("created_at", "")[:10]
        
        assert created_date == today, \
            f"Cloned created_at should be today ({today}), got: {created_date}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
    
    def test_clone_preserves_client_id(self, api_client, source_preventivo):
        """Cloned preventivo preserves source client_id"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201
        
        cloned = response.json()
        assert cloned.get("client_id") == source_preventivo.get("client_id"), \
            "Cloned preventivo should preserve client_id"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
    
    def test_clone_preserves_subject(self, api_client, source_preventivo):
        """Cloned preventivo preserves source subject"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201
        
        cloned = response.json()
        assert cloned.get("subject") == source_preventivo.get("subject"), \
            f"Subject mismatch: expected '{source_preventivo.get('subject')}', got '{cloned.get('subject')}'"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
    
    def test_clone_preserves_normativa(self, api_client, source_preventivo):
        """Cloned preventivo preserves normativa field (EN_1090, EN_13241, etc.)"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201
        
        cloned = response.json()
        assert cloned.get("normativa") == source_preventivo.get("normativa"), \
            f"Normativa mismatch: expected '{source_preventivo.get('normativa')}', got '{cloned.get('normativa')}'"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
    
    def test_clone_preserves_payment_info(self, api_client, source_preventivo):
        """Cloned preventivo preserves payment type, IBAN, banca"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201
        
        cloned = response.json()
        assert cloned.get("payment_type_label") == source_preventivo.get("payment_type_label"), \
            "Payment type label mismatch"
        assert cloned.get("iban") == source_preventivo.get("iban"), \
            "IBAN mismatch"
        assert cloned.get("banca") == source_preventivo.get("banca"), \
            "Banca mismatch"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
    
    def test_clone_preserves_lines_count(self, api_client, source_preventivo):
        """Cloned preventivo has same number of lines"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201
        
        cloned = response.json()
        source_lines = source_preventivo.get("lines", [])
        cloned_lines = cloned.get("lines", [])
        
        assert len(cloned_lines) == len(source_lines), \
            f"Lines count mismatch: expected {len(source_lines)}, got {len(cloned_lines)}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
    
    def test_clone_lines_have_new_line_ids(self, api_client, source_preventivo):
        """Cloned lines have fresh line_ids (not same as source)"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201
        
        cloned = response.json()
        source_line_ids = {line.get("line_id") for line in source_preventivo.get("lines", [])}
        cloned_line_ids = {line.get("line_id") for line in cloned.get("lines", [])}
        
        # No overlap between source and cloned line IDs
        overlap = source_line_ids & cloned_line_ids
        assert len(overlap) == 0, \
            f"Cloned lines should have new line_ids, but found overlap: {overlap}"
        
        # All cloned line IDs should start with 'ln_'
        for line_id in cloned_line_ids:
            assert line_id.startswith("ln_"), \
                f"Cloned line_id should start with 'ln_': {line_id}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
    
    def test_clone_lines_preserve_content(self, api_client, source_preventivo):
        """Cloned lines preserve description, quantity, price, etc."""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201
        
        cloned = response.json()
        source_lines = source_preventivo.get("lines", [])
        cloned_lines = cloned.get("lines", [])
        
        for i, (src, cln) in enumerate(zip(source_lines, cloned_lines)):
            assert cln.get("description") == src.get("description"), \
                f"Line {i} description mismatch"
            assert cln.get("quantity") == src.get("quantity"), \
                f"Line {i} quantity mismatch"
            assert cln.get("unit_price") == src.get("unit_price"), \
                f"Line {i} unit_price mismatch"
            assert cln.get("vat_rate") == src.get("vat_rate"), \
                f"Line {i} vat_rate mismatch"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
    
    def test_clone_recalculates_totals(self, api_client, source_preventivo):
        """Cloned preventivo has totals recalculated"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201
        
        cloned = response.json()
        totals = cloned.get("totals", {})
        
        # Verify totals structure exists and has values
        assert "subtotal" in totals, "totals.subtotal missing"
        assert "total" in totals, "totals.total missing"
        assert totals.get("subtotal", 0) > 0, "totals.subtotal should be > 0"
        assert totals.get("total", 0) > 0, "totals.total should be > 0"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
    
    def test_clone_resets_converted_commessa_id(self, api_client, source_preventivo):
        """Cloned preventivo has converted_commessa_id = None"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201
        
        cloned = response.json()
        assert cloned.get("converted_commessa_id") is None, \
            f"converted_commessa_id should be None, got: {cloned.get('converted_commessa_id')}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
    
    def test_clone_resets_total_invoiced(self, api_client, source_preventivo):
        """Cloned preventivo has total_invoiced = 0"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201
        
        cloned = response.json()
        assert cloned.get("total_invoiced", 0) == 0, \
            f"total_invoiced should be 0, got: {cloned.get('total_invoiced')}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
    
    def test_clone_nonexistent_returns_404(self, api_client):
        """Clone of non-existent preventivo returns 404"""
        fake_id = "prev_nonexistent_12345"
        response = api_client.post(f"{BASE_URL}/api/preventivi/{fake_id}/clone")
        
        assert response.status_code == 404, \
            f"Expected 404 for non-existent preventivo, got: {response.status_code}"
    
    def test_clone_can_be_retrieved(self, api_client, source_preventivo):
        """Cloned preventivo can be retrieved via GET"""
        # Clone
        clone_response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert clone_response.status_code == 201
        
        cloned = clone_response.json()
        cloned_id = cloned["preventivo_id"]
        
        # GET the cloned preventivo
        get_response = api_client.get(f"{BASE_URL}/api/preventivi/{cloned_id}")
        assert get_response.status_code == 200, \
            f"Failed to GET cloned preventivo: {get_response.text}"
        
        fetched = get_response.json()
        assert fetched["preventivo_id"] == cloned_id
        assert fetched["status"] == "bozza"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned_id}")
    
    def test_clone_preserves_notes(self, api_client, source_preventivo):
        """Cloned preventivo preserves notes field"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/{source_preventivo['preventivo_id']}/clone")
        assert response.status_code == 201
        
        cloned = response.json()
        assert cloned.get("notes") == source_preventivo.get("notes"), \
            f"Notes mismatch: expected '{source_preventivo.get('notes')}', got '{cloned.get('notes')}'"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")


class TestClonePreventivoEdgeCases:
    """Edge cases for clone feature"""
    
    @pytest.fixture(scope="class")
    def session_token(self):
        """Create test session"""
        import pymongo
        from datetime import timedelta
        client = pymongo.MongoClient('mongodb://localhost:27017')
        db = client['test_database']
        
        token = f"test_session_clone_edge_{int(time.time()*1000)}"
        user_id = "user_97c773827822"
        
        db.user_sessions.update_one(
            {"session_token": token},
            {"$set": {
                "session_token": token,
                "user_id": user_id,
                "email": "spano.franc75@gmail.com",
                "created_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(days=30)
            }},
            upsert=True
        )
        
        yield token
        
        db.user_sessions.delete_one({"session_token": token})
        client.close()
    
    @pytest.fixture(scope="class")
    def api_client(self, session_token):
        """API client with auth"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        session.cookies.set("session_token", session_token)
        return session
    
    def test_clone_accepted_preventivo_becomes_bozza(self, api_client):
        """Clone of 'accettato' preventivo still becomes 'bozza'"""
        # Create and accept a preventivo
        payload = {
            "subject": "TEST_Clone_Accepted",
            "lines": [{"description": "Test line", "quantity": 1, "unit_price": 100, "vat_rate": "22"}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
        assert create_resp.status_code == 201
        source = create_resp.json()
        
        # Change status to accettato
        api_client.put(f"{BASE_URL}/api/preventivi/{source['preventivo_id']}", json={"status": "accettato"})
        
        # Clone it
        clone_resp = api_client.post(f"{BASE_URL}/api/preventivi/{source['preventivo_id']}/clone")
        assert clone_resp.status_code == 201
        
        cloned = clone_resp.json()
        assert cloned["status"] == "bozza", \
            "Cloned preventivo from 'accettato' should be 'bozza'"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
        api_client.delete(f"{BASE_URL}/api/preventivi/{source['preventivo_id']}")
    
    def test_clone_empty_lines_preventivo(self, api_client):
        """Clone of preventivo with empty lines still works"""
        # Create with minimal data (empty lines)
        payload = {
            "subject": "TEST_Clone_Empty_Lines",
            "lines": []
        }
        create_resp = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
        assert create_resp.status_code == 201
        source = create_resp.json()
        
        # Clone it
        clone_resp = api_client.post(f"{BASE_URL}/api/preventivi/{source['preventivo_id']}/clone")
        assert clone_resp.status_code == 201
        
        cloned = clone_resp.json()
        assert len(cloned.get("lines", [])) == 0, "Cloned empty lines should still be empty"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{cloned['preventivo_id']}")
        api_client.delete(f"{BASE_URL}/api/preventivi/{source['preventivo_id']}")
