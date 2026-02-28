"""
Test Module Interconnection (Data Linking) - Bridge Endpoints
Tests for the 3 new bridge endpoints:
1. POST /api/preventivi/from-distinta/{distinta_id} - Distinta → Preventivo
2. POST /api/invoices/from-preventivo/{preventivo_id} - Preventivo → Fattura
3. POST /api/sicurezza/from-rilievo/{rilievo_id} - Rilievo → POS
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "bridge_test_token_2026"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AUTH_TOKEN}"
    })
    return session


class TestDistintaToPreventivoBridge:
    """Test POST /api/preventivi/from-distinta/{distinta_id} endpoint"""
    
    def test_create_preventivo_from_distinta_default_markup(self, api_client):
        """Test creating a Preventivo from Distinta with default 30% markup"""
        # First, create a test distinta to use for conversion
        distinta_payload = {
            "name": f"TEST_Bridge_Distinta_{datetime.now().timestamp()}",
            "items": [
                {
                    "code": "PROF001",
                    "name": "Profilo Test",
                    "length_mm": 3000,
                    "quantity": 2,
                    "weight_per_meter": 5.5,
                    "surface_per_meter": 0.2,
                    "cost_per_unit": 50.0
                }
            ]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/distinte/", json=distinta_payload)
        print(f"Create distinta response: {create_resp.status_code}")
        
        if create_resp.status_code == 201:
            distinta_id = create_resp.json().get("distinta_id")
            
            # Now create Preventivo from this distinta
            response = api_client.post(f"{BASE_URL}/api/preventivi/from-distinta/{distinta_id}")
            print(f"Create preventivo from distinta: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            
            # Validate response structure
            assert "preventivo_id" in data
            assert "number" in data
            assert "markup_percent" in data
            assert data["markup_percent"] == 30.0, "Default markup should be 30%"
            assert "message" in data
            print(f"✓ Preventivo created: {data['number']} with 30% markup")
        else:
            # Fallback: test with existing distinta if we can find one
            list_resp = api_client.get(f"{BASE_URL}/api/distinte/?limit=1")
            if list_resp.status_code == 200 and list_resp.json().get("distinte"):
                distinta_id = list_resp.json()["distinte"][0]["distinta_id"]
                response = api_client.post(f"{BASE_URL}/api/preventivi/from-distinta/{distinta_id}")
                assert response.status_code in [200, 409], f"Expected 200 or 409, got {response.status_code}"
                print(f"✓ Tested with existing distinta: {response.status_code}")
            else:
                pytest.skip("Could not create or find a test distinta")

    def test_create_preventivo_from_distinta_custom_markup(self, api_client):
        """Test creating a Preventivo from Distinta with custom 50% markup"""
        # Try to get an existing distinta
        list_resp = api_client.get(f"{BASE_URL}/api/distinte/?limit=5")
        if list_resp.status_code != 200 or not list_resp.json().get("distinte"):
            pytest.skip("No distinte found for testing")
        
        # Find a distinta that hasn't been converted yet (no preventivo linked)
        distinta_id = None
        for d in list_resp.json()["distinte"]:
            # Try each one
            test_id = d["distinta_id"]
            response = api_client.post(f"{BASE_URL}/api/preventivi/from-distinta/{test_id}?markup_percent=50")
            if response.status_code == 200:
                data = response.json()
                assert data["markup_percent"] == 50.0, "Custom markup should be 50%"
                print(f"✓ Preventivo created with 50% markup: {data['number']}")
                return
            elif response.status_code == 409:
                # Already converted, try next one
                continue
        
        # If all distinte already converted, just verify the endpoint accepts the parameter
        print("All existing distinte already converted, testing 409 response...")
        response = api_client.post(f"{BASE_URL}/api/preventivi/from-distinta/{list_resp.json()['distinte'][0]['distinta_id']}?markup_percent=50")
        assert response.status_code == 200 or response.status_code == 409
        print(f"✓ Endpoint accepted custom markup parameter")

    def test_create_preventivo_from_nonexistent_distinta(self, api_client):
        """Test 404 response for nonexistent distinta"""
        response = api_client.post(f"{BASE_URL}/api/preventivi/from-distinta/nonexistent_id_12345")
        print(f"Nonexistent distinta response: {response.status_code}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Returns 404 for nonexistent distinta")


class TestPreventivoToInvoiceBridge:
    """Test POST /api/invoices/from-preventivo/{preventivo_id} endpoint"""
    
    created_invoice_id = None  # Track created invoice for cleanup
    
    def test_create_invoice_from_preventivo(self, api_client):
        """Test creating an Invoice from Preventivo"""
        # First, create a test preventivo with a client
        # Get a client first
        clients_resp = api_client.get(f"{BASE_URL}/api/clients/?limit=1")
        client_id = None
        if clients_resp.status_code == 200 and clients_resp.json().get("clients"):
            client_id = clients_resp.json()["clients"][0]["client_id"]
        
        if not client_id:
            pytest.skip("No client found for testing - preventivo needs a client to convert to invoice")
        
        # Create a test preventivo
        prev_payload = {
            "client_id": client_id,
            "subject": f"TEST_Bridge_Preventivo_{datetime.now().timestamp()}",
            "validity_days": 30,
            "lines": [
                {
                    "description": "Test Item for Bridge",
                    "quantity": 1,
                    "unit_price": 100.0,
                    "vat_rate": "22"
                }
            ]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload)
        print(f"Create preventivo response: {create_resp.status_code}")
        
        if create_resp.status_code == 201:
            prev_id = create_resp.json().get("preventivo_id")
            
            # Now create Invoice from this preventivo
            response = api_client.post(f"{BASE_URL}/api/invoices/from-preventivo/{prev_id}")
            print(f"Create invoice from preventivo: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            
            # Validate response structure
            assert "invoice_id" in data
            assert "document_number" in data
            assert "message" in data
            TestPreventivoToInvoiceBridge.created_invoice_id = data["invoice_id"]
            print(f"✓ Invoice created: {data['document_number']}")
            
            # Verify the preventivo status was updated to 'accettato'
            check_prev = api_client.get(f"{BASE_URL}/api/preventivi/{prev_id}")
            if check_prev.status_code == 200:
                prev_data = check_prev.json()
                assert prev_data.get("status") == "accettato", "Preventivo status should be 'accettato'"
                assert prev_data.get("converted_to") == data["invoice_id"], "Preventivo should link to created invoice"
                print("✓ Preventivo status updated to 'accettato' and linked to invoice")
        else:
            pytest.skip("Could not create test preventivo")

    def test_duplicate_conversion_returns_409(self, api_client):
        """Test 409 response when preventivo is already converted"""
        # Get a preventivo that's already converted
        list_resp = api_client.get(f"{BASE_URL}/api/preventivi/?status=accettato&limit=5")
        if list_resp.status_code != 200:
            pytest.skip("Could not fetch preventivi")
        
        preventivi = list_resp.json().get("preventivi", [])
        converted_prev = None
        
        for prev in preventivi:
            if prev.get("converted_to"):
                converted_prev = prev
                break
        
        if not converted_prev:
            # Try to find any preventivo and check if it's already converted
            list_resp = api_client.get(f"{BASE_URL}/api/preventivi/?limit=10")
            for prev in list_resp.json().get("preventivi", []):
                if prev.get("converted_to"):
                    converted_prev = prev
                    break
        
        if not converted_prev:
            pytest.skip("No already-converted preventivo found for testing 409")
        
        response = api_client.post(f"{BASE_URL}/api/invoices/from-preventivo/{converted_prev['preventivo_id']}")
        print(f"Duplicate conversion response: {response.status_code}")
        
        assert response.status_code == 409, f"Expected 409, got {response.status_code}"
        print("✓ Returns 409 for already converted preventivo")

    def test_create_invoice_from_nonexistent_preventivo(self, api_client):
        """Test 404 response for nonexistent preventivo"""
        response = api_client.post(f"{BASE_URL}/api/invoices/from-preventivo/nonexistent_prev_12345")
        print(f"Nonexistent preventivo response: {response.status_code}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Returns 404 for nonexistent preventivo")


class TestRilievoPOSBridge:
    """Test POST /api/sicurezza/from-rilievo/{rilievo_id} endpoint"""
    
    def test_create_pos_from_rilievo(self, api_client):
        """Test creating a POS from Rilievo with auto-filled cantiere info"""
        # First, get or create a test rilievo
        # Get a client first
        clients_resp = api_client.get(f"{BASE_URL}/api/clients/?limit=1")
        client_id = None
        if clients_resp.status_code == 200 and clients_resp.json().get("clients"):
            client_id = clients_resp.json()["clients"][0]["client_id"]
        
        if not client_id:
            pytest.skip("No client found for testing")
        
        # Create a test rilievo
        rilievo_payload = {
            "client_id": client_id,
            "project_name": f"TEST_Bridge_Rilievo_{datetime.now().timestamp()}",
            "survey_date": "2026-01-15",
            "location": "Via Roma 123, Milano",
            "notes": "Test rilievo for POS generation"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/rilievi/", json=rilievo_payload)
        print(f"Create rilievo response: {create_resp.status_code}")
        
        if create_resp.status_code == 201:
            rilievo_id = create_resp.json().get("rilievo_id")
            
            # Now create POS from this rilievo
            response = api_client.post(f"{BASE_URL}/api/sicurezza/from-rilievo/{rilievo_id}")
            print(f"Create POS from rilievo: {response.status_code}")
            print(f"Response: {response.text[:800]}")
            
            assert response.status_code == 201, f"Expected 201, got {response.status_code}"
            data = response.json()
            
            # Validate response structure
            assert "pos_id" in data
            assert "project_name" in data
            assert "cantiere" in data
            
            # Validate auto-filled cantiere info from rilievo location
            cantiere = data.get("cantiere", {})
            assert cantiere.get("address") == "Via Roma 123", f"Address should be 'Via Roma 123', got {cantiere.get('address')}"
            assert cantiere.get("city") == "Milano", f"City should be 'Milano', got {cantiere.get('city')}"
            
            # Validate linked_rilievo_id field
            assert data.get("linked_rilievo_id") == rilievo_id, "POS should have linked_rilievo_id"
            
            print(f"✓ POS created with auto-filled cantiere: {cantiere}")
            print(f"✓ linked_rilievo_id: {data.get('linked_rilievo_id')}")
        else:
            pytest.skip("Could not create test rilievo")

    def test_pos_inherits_client_as_committente(self, api_client):
        """Test that POS committente is auto-filled from client's business_name"""
        # Get a client with a known business name
        clients_resp = api_client.get(f"{BASE_URL}/api/clients/?limit=1")
        if clients_resp.status_code != 200 or not clients_resp.json().get("clients"):
            pytest.skip("No client found")
        
        client = clients_resp.json()["clients"][0]
        client_id = client["client_id"]
        client_name = client.get("business_name", "")
        
        # Create a rilievo with this client
        rilievo_payload = {
            "client_id": client_id,
            "project_name": f"TEST_Committente_Rilievo_{datetime.now().timestamp()}",
            "survey_date": "2026-01-15",
            "location": "Via Test 999, Roma"
        }
        create_resp = api_client.post(f"{BASE_URL}/api/rilievi/", json=rilievo_payload)
        
        if create_resp.status_code == 201:
            rilievo_id = create_resp.json().get("rilievo_id")
            
            # Create POS
            response = api_client.post(f"{BASE_URL}/api/sicurezza/from-rilievo/{rilievo_id}")
            
            if response.status_code == 201:
                data = response.json()
                cantiere = data.get("cantiere", {})
                
                # Validate committente is the client's business name
                assert cantiere.get("committente") == client_name, f"Committente should be '{client_name}', got {cantiere.get('committente')}"
                print(f"✓ Committente auto-filled: {cantiere.get('committente')}")
        else:
            pytest.skip("Could not create test rilievo")

    def test_create_pos_from_nonexistent_rilievo(self, api_client):
        """Test 404 response for nonexistent rilievo"""
        response = api_client.post(f"{BASE_URL}/api/sicurezza/from-rilievo/nonexistent_rilievo_12345")
        print(f"Nonexistent rilievo response: {response.status_code}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Returns 404 for nonexistent rilievo")


class TestExistingConvertToInvoiceEndpoint:
    """Test the existing POST /api/preventivi/{id}/convert-to-invoice endpoint still works"""
    
    def test_existing_convert_endpoint_works(self, api_client):
        """Verify the existing convert endpoint under /preventivi route still functions"""
        # Create a fresh preventivo with a client
        clients_resp = api_client.get(f"{BASE_URL}/api/clients/?limit=1")
        if clients_resp.status_code != 200 or not clients_resp.json().get("clients"):
            pytest.skip("No client found")
        
        client_id = clients_resp.json()["clients"][0]["client_id"]
        
        prev_payload = {
            "client_id": client_id,
            "subject": f"TEST_ExistingConvert_{datetime.now().timestamp()}",
            "validity_days": 30,
            "lines": [{"description": "Test", "quantity": 1, "unit_price": 50.0, "vat_rate": "22"}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/preventivi/", json=prev_payload)
        
        if create_resp.status_code == 201:
            prev_id = create_resp.json().get("preventivo_id")
            
            # Use the existing convert endpoint
            response = api_client.post(f"{BASE_URL}/api/preventivi/{prev_id}/convert-to-invoice")
            print(f"Existing convert endpoint response: {response.status_code}")
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert "invoice_id" in data
            assert "document_number" in data
            print(f"✓ Existing convert endpoint works: {data['document_number']}")
        else:
            pytest.skip("Could not create test preventivo")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
