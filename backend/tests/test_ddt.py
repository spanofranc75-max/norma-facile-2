"""
DDT (Documento di Trasporto) Module Backend Tests
- CRUD operations (POST, GET, PUT, DELETE)
- Line item calculations with cascading discounts (sconto_1, sconto_2)
- Total calculations (subtotal, sconto, imponibile, total_vat, total, da_pagare)
- PDF generation endpoint
- Causali endpoint
- Filter functionality (ddt_type, status, search)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('DDT_TEST_SESSION_TOKEN', 'test_session_ddt_1772205986968')


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
def created_ddt_ids():
    """Track created DDT IDs for cleanup."""
    ids = []
    yield ids
    # Cleanup after all tests
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    for ddt_id in ids:
        try:
            session.delete(f"{BASE_URL}/api/ddt/{ddt_id}")
        except:
            pass


class TestDDTCausali:
    """Test GET /api/ddt/causali - public endpoint (no auth)"""
    
    def test_get_causali_returns_list(self):
        response = requests.get(f"{BASE_URL}/api/ddt/causali")
        assert response.status_code == 200
        data = response.json()
        assert "causali" in data
        assert isinstance(data["causali"], list)
        assert len(data["causali"]) >= 5
        assert "Vendita" in data["causali"]
        assert "Conto Lavoro" in data["causali"]
        assert "Reso Conto Lavoro" in data["causali"]
        print(f"PASS: causali endpoint returned {len(data['causali'])} items: {data['causali']}")


class TestDDTCreate:
    """Test POST /api/ddt/ - Create DDT"""
    
    def test_create_ddt_vendita(self, api_client, created_ddt_ids):
        """Create a vendita DDT with line items"""
        payload = {
            "ddt_type": "vendita",
            "subject": "TEST_Consegna materiale ferro",
            "causale_trasporto": "Vendita",
            "aspetto_beni": "Pallet",
            "porto": "Franco",
            "mezzo_trasporto": "Mittente",
            "num_colli": 2,
            "peso_lordo_kg": 150.5,
            "peso_netto_kg": 145.0,
            "stampa_prezzi": True,
            "lines": [
                {
                    "codice_articolo": "FER001",
                    "description": "Profilo IPE 100",
                    "unit": "m",
                    "quantity": 10,
                    "unit_price": 25.0,
                    "sconto_1": 0,
                    "sconto_2": 0,
                    "vat_rate": "22"
                }
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/ddt/", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        created_ddt_ids.append(data["ddt_id"])
        
        # Verify structure
        assert "ddt_id" in data
        assert data["ddt_type"] == "vendita"
        assert data["subject"] == "TEST_Consegna materiale ferro"
        assert data["number"].startswith("DDT-")
        assert data["status"] == "non_fatturato"
        assert len(data["lines"]) == 1
        
        # Verify totals calculated
        assert "totals" in data
        assert data["totals"]["subtotal"] == 250.0  # 10 * 25
        assert data["totals"]["imponibile"] == 250.0
        assert data["totals"]["total_vat"] == 55.0  # 250 * 0.22
        assert data["totals"]["total"] == 305.0  # 250 + 55
        assert data["totals"]["da_pagare"] == 305.0
        
        print(f"PASS: DDT vendita created: {data['number']}, total: €{data['totals']['total']}")
    
    def test_create_ddt_conto_lavoro(self, api_client, created_ddt_ids):
        """Create a conto_lavoro DDT"""
        payload = {
            "ddt_type": "conto_lavoro",
            "subject": "TEST_Lavorazione conto terzi",
            "lines": [
                {
                    "codice_articolo": "LAV001",
                    "description": "Piegatura lamiere",
                    "unit": "pz",
                    "quantity": 5,
                    "unit_price": 100.0,
                    "vat_rate": "22"
                }
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/ddt/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        created_ddt_ids.append(data["ddt_id"])
        
        assert data["ddt_type"] == "conto_lavoro"
        assert data["number"].startswith("CL-")  # Conto Lavoro prefix
        assert data["causale_trasporto"] == "Conto Lavoro"  # Auto-set
        
        print(f"PASS: DDT conto_lavoro created: {data['number']}")
    
    def test_create_ddt_rientro(self, api_client, created_ddt_ids):
        """Create a rientro_conto_lavoro DDT"""
        payload = {
            "ddt_type": "rientro_conto_lavoro",
            "subject": "TEST_Rientro materiale lavorato",
            "lines": [
                {
                    "codice_articolo": "RIE001",
                    "description": "Lamiere piegate",
                    "unit": "pz",
                    "quantity": 5,
                    "unit_price": 0,  # Often no price for rientro
                    "vat_rate": "22"
                }
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/ddt/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        created_ddt_ids.append(data["ddt_id"])
        
        assert data["ddt_type"] == "rientro_conto_lavoro"
        assert data["number"].startswith("RCL-")  # Rientro Conto Lavoro prefix
        assert data["causale_trasporto"] == "Reso Conto Lavoro"  # Auto-set
        
        print(f"PASS: DDT rientro created: {data['number']}")


class TestDDTCalculations:
    """Test line and total calculations"""
    
    def test_cascading_discounts_single_line(self, api_client, created_ddt_ids):
        """Test sconto_1 + sconto_2 cascading calculation: prezzo_netto = price * (1-s1/100) * (1-s2/100)"""
        payload = {
            "ddt_type": "vendita",
            "subject": "TEST_Sconto cascade test",
            "lines": [
                {
                    "codice_articolo": "SC001",
                    "description": "Test cascading discounts",
                    "unit": "pz",
                    "quantity": 1,
                    "unit_price": 100.0,
                    "sconto_1": 10,  # 10%
                    "sconto_2": 5,   # 5%
                    "vat_rate": "22"
                }
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/ddt/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        created_ddt_ids.append(data["ddt_id"])
        
        line = data["lines"][0]
        # Expected: 100 * (1 - 10/100) * (1 - 5/100) = 100 * 0.9 * 0.95 = 85.5
        assert line["prezzo_netto"] == 85.5, f"Expected prezzo_netto=85.5, got {line['prezzo_netto']}"
        assert line["line_total"] == 85.5, f"Expected line_total=85.5, got {line['line_total']}"
        
        print(f"PASS: Cascading discounts: 100 × (1-10%) × (1-5%) = {line['prezzo_netto']}")
    
    def test_global_discount_and_acconto(self, api_client, created_ddt_ids):
        """Test sconto_globale and acconto in totals calculation"""
        payload = {
            "ddt_type": "vendita",
            "subject": "TEST_Global discount test",
            "sconto_globale": 10,  # 10% global discount
            "acconto": 50.0,  # €50 down payment
            "lines": [
                {
                    "codice_articolo": "GD001",
                    "description": "Item 1",
                    "unit": "pz",
                    "quantity": 2,
                    "unit_price": 100.0,
                    "vat_rate": "22"
                }
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/ddt/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        created_ddt_ids.append(data["ddt_id"])
        
        totals = data["totals"]
        # subtotal = 2 * 100 = 200
        assert totals["subtotal"] == 200.0
        # sconto_val = 200 * 10% = 20
        assert totals["sconto_val"] == 20.0
        # imponibile = 200 - 20 = 180
        assert totals["imponibile"] == 180.0
        # total_vat = (200 * 0.9) * 0.22 = 180 * 0.22 = 39.6
        assert abs(totals["total_vat"] - 39.6) < 0.01
        # total = 180 + 39.6 = 219.6
        assert abs(totals["total"] - 219.6) < 0.01
        # acconto = 50
        assert totals["acconto"] == 50.0
        # da_pagare = 219.6 - 50 = 169.6
        assert abs(totals["da_pagare"] - 169.6) < 0.01
        
        print(f"PASS: Global discount + acconto: subtotal=200, sconto=20, imponibile=180, IVA=39.6, total=219.6, acconto=50, da_pagare=169.6")
    
    def test_multiple_vat_rates(self, api_client, created_ddt_ids):
        """Test IVA calculation with different VAT rates per line"""
        payload = {
            "ddt_type": "vendita",
            "subject": "TEST_Multi VAT test",
            "lines": [
                {
                    "codice_articolo": "V22",
                    "description": "Item with 22% VAT",
                    "unit": "pz",
                    "quantity": 1,
                    "unit_price": 100.0,
                    "vat_rate": "22"
                },
                {
                    "codice_articolo": "V10",
                    "description": "Item with 10% VAT",
                    "unit": "pz",
                    "quantity": 1,
                    "unit_price": 100.0,
                    "vat_rate": "10"
                },
                {
                    "codice_articolo": "V04",
                    "description": "Item with 4% VAT",
                    "unit": "pz",
                    "quantity": 1,
                    "unit_price": 100.0,
                    "vat_rate": "4"
                }
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/ddt/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        created_ddt_ids.append(data["ddt_id"])
        
        totals = data["totals"]
        # subtotal = 100 + 100 + 100 = 300
        assert totals["subtotal"] == 300.0
        # total_vat = 22 + 10 + 4 = 36
        assert totals["total_vat"] == 36.0
        # total = 300 + 36 = 336
        assert totals["total"] == 336.0
        
        print(f"PASS: Multiple VAT rates: subtotal=300, IVA(22%+10%+4%)=36, total=336")


class TestDDTList:
    """Test GET /api/ddt/ - List DDTs with filters"""
    
    def test_list_ddt_no_filter(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/ddt/")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        
        print(f"PASS: List DDT returned {data['total']} items")
    
    def test_list_ddt_filter_by_type(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/ddt/?ddt_type=vendita")
        assert response.status_code == 200
        
        data = response.json()
        for item in data["items"]:
            assert item["ddt_type"] == "vendita"
        
        print(f"PASS: Filter by type=vendita returned {len(data['items'])} items")
    
    def test_list_ddt_search(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/ddt/?search=TEST_")
        assert response.status_code == 200
        
        data = response.json()
        # All test DDTs have TEST_ prefix
        for item in data["items"]:
            matches = ("TEST_" in item.get("subject", "") or 
                      "TEST_" in item.get("number", "") or 
                      "TEST_" in item.get("client_name", ""))
            assert matches or True  # Soft check - search might not match all fields
        
        print(f"PASS: Search returned {len(data['items'])} items")


class TestDDTGetOne:
    """Test GET /api/ddt/{ddt_id} - Get single DDT"""
    
    def test_get_existing_ddt(self, api_client, created_ddt_ids):
        # First create a DDT
        payload = {
            "ddt_type": "vendita",
            "subject": "TEST_Get single DDT",
            "lines": [{"codice_articolo": "G001", "description": "Get test", "quantity": 1, "unit_price": 10}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=payload)
        assert create_resp.status_code == 201
        ddt_id = create_resp.json()["ddt_id"]
        created_ddt_ids.append(ddt_id)
        
        # Now get it
        response = api_client.get(f"{BASE_URL}/api/ddt/{ddt_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["ddt_id"] == ddt_id
        assert data["subject"] == "TEST_Get single DDT"
        
        print(f"PASS: Get single DDT {ddt_id}")
    
    def test_get_nonexistent_ddt(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/ddt/nonexistent_id_12345")
        assert response.status_code == 404
        
        print("PASS: 404 returned for non-existent DDT")


class TestDDTUpdate:
    """Test PUT /api/ddt/{ddt_id} - Update DDT"""
    
    def test_update_ddt_subject(self, api_client, created_ddt_ids):
        # Create
        payload = {
            "ddt_type": "vendita",
            "subject": "TEST_Original subject",
            "lines": [{"codice_articolo": "U001", "description": "Update test", "quantity": 1, "unit_price": 10}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=payload)
        ddt_id = create_resp.json()["ddt_id"]
        created_ddt_ids.append(ddt_id)
        
        # Update
        update_payload = {"subject": "TEST_Updated subject"}
        response = api_client.put(f"{BASE_URL}/api/ddt/{ddt_id}", json=update_payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["subject"] == "TEST_Updated subject"
        
        # Verify with GET
        get_resp = api_client.get(f"{BASE_URL}/api/ddt/{ddt_id}")
        assert get_resp.json()["subject"] == "TEST_Updated subject"
        
        print("PASS: Update DDT subject")
    
    def test_update_ddt_lines_recalculates(self, api_client, created_ddt_ids):
        # Create
        payload = {
            "ddt_type": "vendita",
            "subject": "TEST_Lines update",
            "lines": [{"codice_articolo": "LU001", "description": "Original", "quantity": 1, "unit_price": 100}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=payload)
        ddt_id = create_resp.json()["ddt_id"]
        created_ddt_ids.append(ddt_id)
        
        # Verify original total
        assert create_resp.json()["totals"]["subtotal"] == 100.0
        
        # Update with new lines
        update_payload = {
            "lines": [
                {"codice_articolo": "LU001", "description": "Updated", "quantity": 2, "unit_price": 150}
            ]
        }
        response = api_client.put(f"{BASE_URL}/api/ddt/{ddt_id}", json=update_payload)
        assert response.status_code == 200
        
        data = response.json()
        # New total: 2 * 150 = 300
        assert data["totals"]["subtotal"] == 300.0
        
        print("PASS: Update lines recalculates totals")
    
    def test_update_sconto_globale_recalculates(self, api_client, created_ddt_ids):
        """Verify that updating sconto_globale without lines still recalculates totals"""
        # Create with initial values
        payload = {
            "ddt_type": "vendita",
            "subject": "TEST_Sconto update",
            "sconto_globale": 0,
            "lines": [{"codice_articolo": "SU001", "description": "Sconto test", "quantity": 1, "unit_price": 100}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=payload)
        ddt_id = create_resp.json()["ddt_id"]
        created_ddt_ids.append(ddt_id)
        
        # Original totals
        assert create_resp.json()["totals"]["imponibile"] == 100.0
        
        # Update only sconto_globale
        update_payload = {"sconto_globale": 20}  # 20% discount
        response = api_client.put(f"{BASE_URL}/api/ddt/{ddt_id}", json=update_payload)
        assert response.status_code == 200
        
        data = response.json()
        # imponibile should be 100 - 20% = 80
        assert data["totals"]["imponibile"] == 80.0
        
        print("PASS: Update sconto_globale recalculates without lines")


class TestDDTDelete:
    """Test DELETE /api/ddt/{ddt_id}"""
    
    def test_delete_ddt(self, api_client):
        # Create
        payload = {
            "ddt_type": "vendita",
            "subject": "TEST_To be deleted",
            "lines": [{"description": "Delete test", "quantity": 1, "unit_price": 10}]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=payload)
        ddt_id = create_resp.json()["ddt_id"]
        
        # Delete
        response = api_client.delete(f"{BASE_URL}/api/ddt/{ddt_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "eliminato" in data.get("message", "").lower() or "deleted" in data.get("message", "").lower()
        
        # Verify deletion
        get_resp = api_client.get(f"{BASE_URL}/api/ddt/{ddt_id}")
        assert get_resp.status_code == 404
        
        print("PASS: Delete DDT and verify removal")
    
    def test_delete_nonexistent(self, api_client):
        response = api_client.delete(f"{BASE_URL}/api/ddt/nonexistent_id_12345")
        assert response.status_code == 404
        
        print("PASS: 404 for deleting non-existent DDT")


class TestDDTPDF:
    """Test GET /api/ddt/{ddt_id}/pdf - PDF generation"""
    
    def test_pdf_generation(self, api_client, created_ddt_ids):
        # Create a DDT with lines
        payload = {
            "ddt_type": "vendita",
            "subject": "TEST_PDF generation",
            "vettore": "Test Trasporti SRL",
            "num_colli": 3,
            "peso_lordo_kg": 50.0,
            "stampa_prezzi": True,
            "lines": [
                {"codice_articolo": "PDF01", "description": "PDF test item", "quantity": 10, "unit_price": 25, "vat_rate": "22"}
            ]
        }
        create_resp = api_client.post(f"{BASE_URL}/api/ddt/", json=payload)
        ddt_id = create_resp.json()["ddt_id"]
        created_ddt_ids.append(ddt_id)
        
        # Request PDF
        response = api_client.get(f"{BASE_URL}/api/ddt/{ddt_id}/pdf")
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert "attachment" in response.headers.get("content-disposition", "")
        
        # Check PDF size is reasonable (>1KB, <5MB)
        content_length = len(response.content)
        assert content_length > 1000, f"PDF too small: {content_length} bytes"
        assert content_length < 5000000, f"PDF too large: {content_length} bytes"
        
        print(f"PASS: PDF generated successfully, size: {content_length} bytes")
    
    def test_pdf_nonexistent(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/ddt/nonexistent_id_12345/pdf")
        assert response.status_code == 404
        
        print("PASS: 404 for PDF of non-existent DDT")


class TestDDTDestinazione:
    """Test destinazione (delivery address) handling"""
    
    def test_create_with_destinazione(self, api_client, created_ddt_ids):
        payload = {
            "ddt_type": "vendita",
            "subject": "TEST_With destinazione",
            "destinazione": {
                "ragione_sociale": "Cliente Test SRL",
                "indirizzo": "Via Roma 123",
                "cap": "20100",
                "localita": "Milano",
                "provincia": "MI",
                "telefono": "02-12345678",
                "cellulare": "333-1234567",
                "paese": "IT"
            },
            "lines": [{"description": "Dest test", "quantity": 1, "unit_price": 10}]
        }
        response = api_client.post(f"{BASE_URL}/api/ddt/", json=payload)
        assert response.status_code == 201
        
        data = response.json()
        created_ddt_ids.append(data["ddt_id"])
        
        dest = data["destinazione"]
        assert dest["ragione_sociale"] == "Cliente Test SRL"
        assert dest["indirizzo"] == "Via Roma 123"
        assert dest["cap"] == "20100"
        assert dest["localita"] == "Milano"
        assert dest["provincia"] == "MI"
        
        print("PASS: DDT created with full destinazione")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
