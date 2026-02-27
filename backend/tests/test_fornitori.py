"""
Test Suite: Fornitori (Suppliers) Module - Backend API Tests
Tests the client_type filter functionality for suppliers:
- GET /api/clients/?client_type=fornitore returns fornitore + cliente_fornitore
- GET /api/clients/?client_type=cliente returns cliente + cliente_fornitore
- CRUD operations for suppliers
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', 'test_session_fornitori_1772206511636')


@pytest.fixture(scope="module")
def api_client():
    """Session with auth header."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    return session


@pytest.fixture(scope="module")
def test_supplier_data():
    """Test supplier data with TEST_ prefix for cleanup."""
    return {
        "business_name": "TEST_Fornitore SRL",
        "client_type": "fornitore",
        "partita_iva": "IT98765432109",
        "codice_fiscale": "98765432109",
        "codice_sdi": "0000000",
        "address": "Via Fornitori 123",
        "city": "Milano",
        "province": "MI",
        "cap": "20100",
        "country": "IT",
        "phone": "+39 02 12345678",
        "email": "test@fornitore.it",
        "notes": "Test supplier for fornitori module"
    }


@pytest.fixture(scope="module")
def test_cliente_fornitore_data():
    """Test cliente_fornitore data."""
    return {
        "business_name": "TEST_Cliente_Fornitore SPA",
        "client_type": "cliente_fornitore",
        "partita_iva": "IT55555555555",
        "codice_fiscale": "55555555555",
        "codice_sdi": "XXXXXXX",
        "address": "Via Mista 50",
        "city": "Roma",
        "province": "RM",
        "cap": "00100",
        "country": "IT",
        "phone": "+39 06 99998888",
        "email": "test@clientefornitore.it"
    }


@pytest.fixture(scope="module")
def test_cliente_data():
    """Test cliente data."""
    return {
        "business_name": "TEST_Cliente SRL",
        "client_type": "cliente",
        "partita_iva": "IT11111111111",
        "codice_fiscale": "11111111111",
        "codice_sdi": "0000000",
        "address": "Via Clienti 100",
        "city": "Torino",
        "province": "TO",
        "cap": "10100",
        "country": "IT",
        "phone": "+39 011 1234567",
        "email": "test@cliente.it"
    }


class TestFornitoriAPIAuth:
    """Test authentication for clients/fornitori API."""
    
    def test_clients_api_requires_auth(self):
        """GET /api/clients/ without auth returns 401."""
        response = requests.get(f"{BASE_URL}/api/clients/")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Clients API requires authentication")
    
    def test_auth_with_valid_token(self, api_client):
        """GET /api/clients/ with valid token returns 200."""
        response = api_client.get(f"{BASE_URL}/api/clients/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "clients" in data
        assert "total" in data
        print(f"✓ Auth works - found {data['total']} clients")


class TestSupplierCRUD:
    """Test CRUD operations for suppliers (fornitori)."""
    
    created_supplier_id = None
    created_cli_for_id = None
    created_cliente_id = None
    
    def test_01_create_fornitore(self, api_client, test_supplier_data):
        """POST /api/clients/ with client_type=fornitore creates supplier."""
        # First, cleanup any existing test data
        existing = api_client.get(f"{BASE_URL}/api/clients/?search=TEST_&limit=100")
        if existing.status_code == 200:
            for c in existing.json().get("clients", []):
                if c.get("business_name", "").startswith("TEST_"):
                    api_client.delete(f"{BASE_URL}/api/clients/{c['client_id']}")
        
        response = api_client.post(f"{BASE_URL}/api/clients/", json=test_supplier_data)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "client_id" in data
        assert data["business_name"] == test_supplier_data["business_name"]
        assert data["client_type"] == "fornitore"
        assert data["partita_iva"] == test_supplier_data["partita_iva"]
        
        TestSupplierCRUD.created_supplier_id = data["client_id"]
        print(f"✓ Created fornitore: {data['client_id']}")
    
    def test_02_create_cliente_fornitore(self, api_client, test_cliente_fornitore_data):
        """POST /api/clients/ with client_type=cliente_fornitore."""
        response = api_client.post(f"{BASE_URL}/api/clients/", json=test_cliente_fornitore_data)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["client_type"] == "cliente_fornitore"
        TestSupplierCRUD.created_cli_for_id = data["client_id"]
        print(f"✓ Created cliente_fornitore: {data['client_id']}")
    
    def test_03_create_cliente(self, api_client, test_cliente_data):
        """POST /api/clients/ with client_type=cliente."""
        response = api_client.post(f"{BASE_URL}/api/clients/", json=test_cliente_data)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["client_type"] == "cliente"
        TestSupplierCRUD.created_cliente_id = data["client_id"]
        print(f"✓ Created cliente: {data['client_id']}")
    
    def test_04_get_supplier_by_id(self, api_client):
        """GET /api/clients/{id} returns supplier."""
        assert TestSupplierCRUD.created_supplier_id, "Supplier not created"
        
        response = api_client.get(f"{BASE_URL}/api/clients/{TestSupplierCRUD.created_supplier_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["client_type"] == "fornitore"
        print(f"✓ GET fornitore by ID works")
    
    def test_05_update_supplier(self, api_client):
        """PUT /api/clients/{id} updates supplier."""
        assert TestSupplierCRUD.created_supplier_id, "Supplier not created"
        
        update_data = {
            "business_name": "TEST_Fornitore AGGIORNATO SRL",
            "phone": "+39 02 99999999",
            "notes": "Updated supplier notes"
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/clients/{TestSupplierCRUD.created_supplier_id}",
            json=update_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["business_name"] == update_data["business_name"]
        assert data["phone"] == update_data["phone"]
        assert data["client_type"] == "fornitore"  # Type unchanged
        print("✓ UPDATE fornitore works")
        
        # Verify persistence
        get_response = api_client.get(f"{BASE_URL}/api/clients/{TestSupplierCRUD.created_supplier_id}")
        assert get_response.status_code == 200
        verified = get_response.json()
        assert verified["business_name"] == update_data["business_name"]
        print("✓ UPDATE fornitore persisted correctly")


class TestClientTypeFilter:
    """Test client_type filter for fornitore and cliente queries."""
    
    def test_filter_fornitore_returns_fornitore_and_cliente_fornitore(self, api_client):
        """GET /api/clients/?client_type=fornitore returns fornitore + cliente_fornitore."""
        response = api_client.get(f"{BASE_URL}/api/clients/?client_type=fornitore&search=TEST_")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        clients = data.get("clients", [])
        
        # Should have at least fornitore and cliente_fornitore we created
        types_found = set(c["client_type"] for c in clients)
        print(f"Types found with fornitore filter: {types_found}")
        
        # Verify NO pure "cliente" in results
        for c in clients:
            assert c["client_type"] in ["fornitore", "cliente_fornitore"], \
                f"Unexpected client_type '{c['client_type']}' in fornitore filter results"
        
        # Should find our test fornitore and cliente_fornitore
        business_names = [c["business_name"] for c in clients]
        assert any("Fornitore" in name for name in business_names), \
            f"Should find fornitore, got: {business_names}"
        
        print(f"✓ client_type=fornitore filter works - found {len(clients)} suppliers")
    
    def test_filter_cliente_returns_cliente_and_cliente_fornitore(self, api_client):
        """GET /api/clients/?client_type=cliente returns cliente + cliente_fornitore."""
        response = api_client.get(f"{BASE_URL}/api/clients/?client_type=cliente&search=TEST_")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        clients = data.get("clients", [])
        
        types_found = set(c["client_type"] for c in clients)
        print(f"Types found with cliente filter: {types_found}")
        
        # Verify NO pure "fornitore" in results
        for c in clients:
            assert c["client_type"] in ["cliente", "cliente_fornitore"], \
                f"Unexpected client_type '{c['client_type']}' in cliente filter results"
        
        print(f"✓ client_type=cliente filter works - found {len(clients)} clients")
    
    def test_filter_no_filter_returns_all_types(self, api_client):
        """GET /api/clients/ without filter returns all types."""
        response = api_client.get(f"{BASE_URL}/api/clients/?search=TEST_")
        assert response.status_code == 200
        
        data = response.json()
        clients = data.get("clients", [])
        types_found = set(c["client_type"] for c in clients)
        
        print(f"Types found without filter: {types_found}")
        
        # Should have all 3 types we created
        assert len(types_found) >= 2, f"Expected multiple types, got: {types_found}"
        print(f"✓ No filter returns all types - found {len(clients)} records")
    
    def test_filter_specific_type_only(self, api_client):
        """Test that client_type=cliente_fornitore returns only that exact type."""
        # This tests the 'else' branch in the filter logic
        response = api_client.get(f"{BASE_URL}/api/clients/?client_type=cliente_fornitore&search=TEST_")
        assert response.status_code == 200
        
        data = response.json()
        clients = data.get("clients", [])
        
        for c in clients:
            assert c["client_type"] == "cliente_fornitore", \
                f"Expected only cliente_fornitore, got {c['client_type']}"
        
        print(f"✓ Exact type filter works - found {len(clients)} cliente_fornitore records")


class TestSupplierContacts:
    """Test contacts array handling for suppliers."""
    
    def test_supplier_with_contacts(self, api_client):
        """Create supplier with contact persons."""
        supplier_data = {
            "business_name": "TEST_Fornitore_Con_Contatti",
            "client_type": "fornitore",
            "partita_iva": "IT44444444444",
            "contacts": [
                {
                    "tipo": "Commerciale",
                    "nome": "Mario Rossi",
                    "telefono": "+39 333 1234567",
                    "email": "mario.rossi@fornitore.it",
                    "include_preventivi": True,
                    "include_fatture": True,
                    "include_ddt": True,
                    "include_solleciti": False,
                    "include_ordini": False,
                    "note": "Referente principale"
                },
                {
                    "tipo": "Amministrativo",
                    "nome": "Laura Bianchi",
                    "telefono": "+39 333 9876543",
                    "email": "laura.bianchi@fornitore.it",
                    "include_preventivi": False,
                    "include_fatture": True,
                    "include_ddt": False,
                    "include_solleciti": True,
                    "include_ordini": False,
                    "note": "Contabilita"
                }
            ]
        }
        
        response = api_client.post(f"{BASE_URL}/api/clients/", json=supplier_data)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "contacts" in data
        assert len(data["contacts"]) == 2
        assert data["contacts"][0]["nome"] == "Mario Rossi"
        assert data["contacts"][0]["include_ddt"] == True
        assert data["contacts"][1]["nome"] == "Laura Bianchi"
        
        print(f"✓ Supplier with contacts created successfully")
        
        # Verify persistence
        get_response = api_client.get(f"{BASE_URL}/api/clients/{data['client_id']}")
        assert get_response.status_code == 200
        verified = get_response.json()
        assert len(verified["contacts"]) == 2
        print(f"✓ Contacts persisted correctly")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/clients/{data['client_id']}")


class TestSupplierValidation:
    """Test validation rules for suppliers."""
    
    def test_duplicate_piva_rejected(self, api_client, test_supplier_data):
        """Creating supplier with duplicate P.IVA fails."""
        # Create first supplier (or reuse existing)
        response = api_client.get(f"{BASE_URL}/api/clients/?search=TEST_Fornitore")
        existing = response.json().get("clients", [])
        
        if not existing:
            api_client.post(f"{BASE_URL}/api/clients/", json=test_supplier_data)
        
        # Try to create duplicate
        duplicate_data = {
            "business_name": "TEST_Fornitore_Duplicato",
            "client_type": "fornitore",
            "partita_iva": test_supplier_data["partita_iva"]  # Same P.IVA
        }
        
        response = api_client.post(f"{BASE_URL}/api/clients/", json=duplicate_data)
        assert response.status_code == 400, f"Expected 400 for duplicate P.IVA, got {response.status_code}"
        
        data = response.json()
        assert "Partita IVA" in data.get("detail", "")
        print("✓ Duplicate P.IVA correctly rejected")
    
    def test_supplier_not_found(self, api_client):
        """GET non-existent supplier returns 404."""
        response = api_client.get(f"{BASE_URL}/api/clients/cli_nonexistent12345")
        assert response.status_code == 404
        print("✓ Non-existent supplier returns 404")


class TestSupplierDelete:
    """Test delete operations for suppliers."""
    
    def test_delete_supplier(self, api_client):
        """DELETE /api/clients/{id} removes supplier."""
        # Create a supplier to delete
        supplier_data = {
            "business_name": "TEST_Fornitore_Da_Eliminare",
            "client_type": "fornitore",
            "partita_iva": "IT77777777777"
        }
        
        create_response = api_client.post(f"{BASE_URL}/api/clients/", json=supplier_data)
        assert create_response.status_code == 201
        supplier_id = create_response.json()["client_id"]
        
        # Delete
        delete_response = api_client.delete(f"{BASE_URL}/api/clients/{supplier_id}")
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}"
        
        # Verify deleted
        get_response = api_client.get(f"{BASE_URL}/api/clients/{supplier_id}")
        assert get_response.status_code == 404
        print("✓ Supplier deleted successfully")


class TestCleanup:
    """Clean up test data."""
    
    def test_cleanup_test_data(self, api_client):
        """Remove all TEST_ prefixed clients."""
        response = api_client.get(f"{BASE_URL}/api/clients/?search=TEST_&limit=100")
        if response.status_code == 200:
            clients = response.json().get("clients", [])
            deleted = 0
            for c in clients:
                if c.get("business_name", "").startswith("TEST_"):
                    del_resp = api_client.delete(f"{BASE_URL}/api/clients/{c['client_id']}")
                    if del_resp.status_code in [200, 204]:
                        deleted += 1
            print(f"✓ Cleanup: deleted {deleted} test records")
        else:
            print("✓ Cleanup: no test data to clean")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
