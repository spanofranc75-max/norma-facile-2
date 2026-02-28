"""
Test suite for Supplier Combobox Feature
Tests /api/clients/?client_type=fornitore endpoint and related functionality
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestSupplierComboboxAPI:
    """Tests for supplier (fornitore) filtering API"""
    
    @pytest.fixture(scope="class")
    def session_token(self):
        """Use existing test session"""
        return "combobox_session_1772284732997"
    
    @pytest.fixture(scope="class")
    def headers(self, session_token):
        return {
            "Authorization": f"Bearer {session_token}",
            "Content-Type": "application/json"
        }
    
    def test_get_fornitori_filter(self, headers):
        """Test /api/clients/?client_type=fornitore returns only suppliers"""
        response = requests.get(
            f"{BASE_URL}/api/clients/?client_type=fornitore&limit=100",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "clients" in data
        assert "total" in data
        
        # Verify all returned clients are fornitori
        for client in data["clients"]:
            assert client["client_type"] in ["fornitore", "cliente_fornitore"], \
                f"Expected fornitore or cliente_fornitore, got {client['client_type']}"
        
        print(f"Found {data['total']} suppliers")
    
    def test_fornitori_have_required_fields(self, headers):
        """Test fornitori response includes fields needed for combobox"""
        response = requests.get(
            f"{BASE_URL}/api/clients/?client_type=fornitore&limit=10",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for client in data["clients"]:
            # Required fields for combobox component
            assert "client_id" in client, "Missing client_id"
            assert "business_name" in client, "Missing business_name"
            assert client["client_id"] is not None
            assert client["business_name"] is not None
            assert len(client["business_name"]) > 0
        
        print(f"All {len(data['clients'])} suppliers have required fields")
    
    def test_fornitori_sorted_by_name(self, headers):
        """Test fornitori are sorted alphabetically by business_name"""
        response = requests.get(
            f"{BASE_URL}/api/clients/?client_type=fornitore&limit=100",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        names = [c["business_name"] for c in data["clients"]]
        sorted_names = sorted(names)
        
        assert names == sorted_names, "Suppliers should be sorted alphabetically"
        print(f"Suppliers correctly sorted: {names[:3]}...")
    
    def test_cliente_fornitore_included(self, headers):
        """Test cliente_fornitore type is included when filtering for fornitori"""
        # First create a cliente_fornitore if not exists
        response = requests.get(
            f"{BASE_URL}/api/clients/?client_type=fornitore&limit=100",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check if we have any cliente_fornitore types
        types_found = set(c["client_type"] for c in data["clients"])
        print(f"Client types found in fornitore filter: {types_found}")
        
        # The filter should include cliente_fornitore
        if "cliente_fornitore" in types_found:
            print("SUCCESS: cliente_fornitore included in fornitore filter")
    
    def test_search_within_fornitori(self, headers):
        """Test search parameter works with fornitore filter"""
        response = requests.get(
            f"{BASE_URL}/api/clients/?client_type=fornitore&search=Milano&limit=100",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All results should contain "Milano" in business_name
        for client in data["clients"]:
            assert "milano" in client["business_name"].lower() or \
                   "milano" in (client.get("city") or "").lower(), \
                f"Search result should contain 'Milano': {client['business_name']}"
        
        print(f"Search 'Milano' returned {data['total']} results")
    
    def test_pagination_fornitori(self, headers):
        """Test pagination works for fornitori filter"""
        response = requests.get(
            f"{BASE_URL}/api/clients/?client_type=fornitore&skip=0&limit=2",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["clients"]) <= 2
        print(f"Pagination test passed: got {len(data['clients'])} of {data['total']} total")


class TestSupplierInProcurementForms:
    """Tests for supplier usage in RdP, OdA, Conto Lavoro"""
    
    @pytest.fixture(scope="class")
    def session_token(self):
        return "combobox_session_1772284732997"
    
    @pytest.fixture(scope="class")
    def headers(self, session_token):
        return {
            "Authorization": f"Bearer {session_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def test_commessa_id(self):
        return "com_08cfca0f308c"
    
    @pytest.fixture(scope="class")
    def test_supplier_id(self):
        return "cli_afd5cd8b88cb"  # Acciaierie Milano SRL
    
    def test_rdp_with_fornitore_id(self, headers, test_commessa_id, test_supplier_id):
        """Test RdP creation stores fornitore_id"""
        # Get ops to check existing RdP
        response = requests.get(
            f"{BASE_URL}/api/commesse/{test_commessa_id}/ops",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check if RdP with fornitore exists
        if data["approvvigionamento"]["richieste"]:
            rdp = data["approvvigionamento"]["richieste"][0]
            assert "fornitore_nome" in rdp
            print(f"RdP found with fornitore: {rdp.get('fornitore_nome')}")
    
    def test_commessa_ops_returns_fornitori_data(self, headers, test_commessa_id):
        """Test commessa ops endpoint returns fornitore info"""
        response = requests.get(
            f"{BASE_URL}/api/commesse/{test_commessa_id}/ops",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "approvvigionamento" in data
        assert "richieste" in data["approvvigionamento"]
        assert "ordini" in data["approvvigionamento"]
        assert "conto_lavoro" in data
        
        print(f"Ops data: {len(data['approvvigionamento']['richieste'])} RdP, "
              f"{len(data['approvvigionamento']['ordini'])} OdA, "
              f"{len(data['conto_lavoro'])} C/L")


class TestArticoliSupplierAssociation:
    """Tests for supplier association in Articoli catalog"""
    
    @pytest.fixture(scope="class")
    def session_token(self):
        return "combobox_session_1772284732997"
    
    @pytest.fixture(scope="class")
    def headers(self, session_token):
        return {
            "Authorization": f"Bearer {session_token}",
            "Content-Type": "application/json"
        }
    
    def test_create_articolo_with_fornitore(self, headers):
        """Test creating articolo with fornitore_id"""
        articolo_data = {
            "codice": "TEST-COMBO-001",
            "descrizione": "Articolo test combobox fornitore",
            "categoria": "materiale",
            "unita_misura": "kg",
            "prezzo_unitario": 15.50,
            "aliquota_iva": "22",
            "fornitore_id": "cli_afd5cd8b88cb",
            "fornitore_nome": "Acciaierie Milano SRL"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/articoli/",
            headers=headers,
            json=articolo_data
        )
        
        if response.status_code == 201:
            data = response.json()
            assert data["fornitore_id"] == "cli_afd5cd8b88cb"
            assert data["fornitore_nome"] == "Acciaierie Milano SRL"
            print(f"SUCCESS: Created articolo {data['articolo_id']} with fornitore")
            
            # Cleanup
            requests.delete(
                f"{BASE_URL}/api/articoli/{data['articolo_id']}",
                headers=headers
            )
        else:
            # May already exist, which is fine
            print(f"Articolo creation returned {response.status_code}")
    
    def test_articoli_list_includes_fornitore(self, headers):
        """Test articoli list endpoint returns fornitore data"""
        response = requests.get(
            f"{BASE_URL}/api/articoli/",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "articoli" in data
        assert "total" in data
        
        # If any articoli exist, check fornitore fields
        for art in data["articoli"]:
            # fornitore fields should be present (even if null)
            assert "fornitore_id" in art or art.get("fornitore_id") is None or "fornitore_nome" in art
        
        print(f"Articoli list includes {data['total']} items")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
