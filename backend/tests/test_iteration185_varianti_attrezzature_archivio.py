"""
Iteration 185: Test Varianti (Montaggio), Attrezzature (Scadenzario), Archivio Storico

Features:
1. Modulo Varianti - variant notes with mandatory photos in Assembly Diary
2. Scadenzario Attrezzature - calibration schedule for welding machines and torque wrenches
3. Archivio Storico - mass export by year/client generating organized ZIP

Endpoints tested:
- POST /api/montaggio/variante (public - worker access)
- GET /api/montaggio/varianti/{commessa_id} (public - worker access)
- POST /api/attrezzature (requires auth)
- GET /api/attrezzature (requires auth)
- PATCH /api/attrezzature/{attr_id} (requires auth)
- DELETE /api/attrezzature/{attr_id} (requires auth)
- GET /api/attrezzature/check-taratura (requires auth)
- POST /api/archivio/export (requires auth)
- GET /api/archivio/stats (requires auth)
- GET /api/archivio/exports (requires auth)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test commessa from previous iterations
TEST_COMMESSA_ID = "com_2b99b2db8681"
TEST_OPERATOR_ID = "op_ahmed"
TEST_OPERATOR_NAME = "Ahmed"


class TestVariantiMontaggio:
    """Test variant notes endpoints (public - no auth required)"""

    def test_create_variante_success(self):
        """POST /api/montaggio/variante - creates variant with mandatory photo"""
        # First, we need a foto_doc_id - simulate one
        fake_foto_doc_id = f"doc_{uuid.uuid4().hex[:10]}"
        
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "voce_id": "",
            "operatore_id": TEST_OPERATOR_ID,
            "operatore_nome": TEST_OPERATOR_NAME,
            "descrizione": "Test variante - modifica posizione ancoraggio",
            "foto_doc_id": fake_foto_doc_id
        }
        
        response = requests.post(f"{BASE_URL}/api/montaggio/variante", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "variante_id" in data
        assert data["descrizione"] == "Test variante - modifica posizione ancoraggio"
        assert data["foto_doc_id"] == fake_foto_doc_id
        assert data["operatore_nome"] == TEST_OPERATOR_NAME
        print(f"✓ Created variante: {data['variante_id']}")

    def test_create_variante_missing_foto_returns_400(self):
        """POST /api/montaggio/variante - returns 400 if foto_doc_id is empty"""
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "voce_id": "",
            "operatore_id": TEST_OPERATOR_ID,
            "operatore_nome": TEST_OPERATOR_NAME,
            "descrizione": "Test variante senza foto",
            "foto_doc_id": ""  # Empty - should fail
        }
        
        response = requests.post(f"{BASE_URL}/api/montaggio/variante", json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "Foto obbligatoria" in response.text
        print("✓ Correctly returns 400 when foto_doc_id is empty")

    def test_create_variante_missing_descrizione_returns_400(self):
        """POST /api/montaggio/variante - returns 400 if descrizione is empty/whitespace"""
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "voce_id": "",
            "operatore_id": TEST_OPERATOR_ID,
            "operatore_nome": TEST_OPERATOR_NAME,
            "descrizione": "   ",  # Whitespace only - should fail
            "foto_doc_id": f"doc_{uuid.uuid4().hex[:10]}"
        }
        
        response = requests.post(f"{BASE_URL}/api/montaggio/variante", json=payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "Descrizione obbligatoria" in response.text
        print("✓ Correctly returns 400 when descrizione is whitespace")

    def test_list_varianti(self):
        """GET /api/montaggio/varianti/{commessa_id} - lists variant notes"""
        response = requests.get(f"{BASE_URL}/api/montaggio/varianti/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "varianti" in data
        assert "count" in data
        assert isinstance(data["varianti"], list)
        print(f"✓ Listed {data['count']} varianti for commessa {TEST_COMMESSA_ID}")


class TestAttrezzatureAuth:
    """Test attrezzature endpoints require authentication"""

    def test_create_attrezzatura_requires_auth(self):
        """POST /api/attrezzature - returns 401 without auth"""
        payload = {
            "tipo": "chiave_dinamometrica",
            "modello": "Test Chiave",
            "numero_serie": "SN-12345",
            "marca": "TestBrand",
            "data_taratura": "2025-01-15",
            "prossima_taratura": "2026-01-15",
            "note": "Test note"
        }
        
        response = requests.post(f"{BASE_URL}/api/attrezzature", json=payload)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ POST /api/attrezzature correctly returns 401 without auth")

    def test_list_attrezzature_requires_auth(self):
        """GET /api/attrezzature - returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/attrezzature")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ GET /api/attrezzature correctly returns 401 without auth")

    def test_update_attrezzatura_requires_auth(self):
        """PATCH /api/attrezzature/{attr_id} - returns 401 without auth"""
        response = requests.patch(
            f"{BASE_URL}/api/attrezzature/attr_test123",
            json={"modello": "Updated Model"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ PATCH /api/attrezzature/{attr_id} correctly returns 401 without auth")

    def test_delete_attrezzatura_requires_auth(self):
        """DELETE /api/attrezzature/{attr_id} - returns 401 without auth"""
        response = requests.delete(f"{BASE_URL}/api/attrezzature/attr_test123")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ DELETE /api/attrezzature/{attr_id} correctly returns 401 without auth")

    def test_check_taratura_requires_auth(self):
        """GET /api/attrezzature/check-taratura - returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/attrezzature/check-taratura")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ GET /api/attrezzature/check-taratura correctly returns 401 without auth")


class TestArchivioStoricoAuth:
    """Test archivio storico endpoints require authentication"""

    def test_export_archivio_requires_auth(self):
        """POST /api/archivio/export - returns 401 without auth"""
        payload = {"anno": 2026}
        response = requests.post(f"{BASE_URL}/api/archivio/export", json=payload)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ POST /api/archivio/export correctly returns 401 without auth")

    def test_archivio_stats_requires_auth(self):
        """GET /api/archivio/stats - returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/archivio/stats")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ GET /api/archivio/stats correctly returns 401 without auth")

    def test_archivio_exports_requires_auth(self):
        """GET /api/archivio/exports - returns 401 without auth"""
        response = requests.get(f"{BASE_URL}/api/archivio/exports")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✓ GET /api/archivio/exports correctly returns 401 without auth")


class TestEndpointStructure:
    """Test that endpoints exist and have correct structure"""

    def test_variante_endpoint_exists(self):
        """Verify /api/montaggio/variante endpoint exists"""
        # Send invalid data to check endpoint exists (not 404)
        response = requests.post(f"{BASE_URL}/api/montaggio/variante", json={})
        assert response.status_code != 404, "Endpoint /api/montaggio/variante not found"
        print("✓ /api/montaggio/variante endpoint exists")

    def test_varianti_list_endpoint_exists(self):
        """Verify /api/montaggio/varianti/{commessa_id} endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/montaggio/varianti/test_commessa")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ /api/montaggio/varianti/{commessa_id} endpoint exists")

    def test_attrezzature_endpoint_exists(self):
        """Verify /api/attrezzature endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/attrezzature")
        # Should be 401 (auth required), not 404
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/attrezzature endpoint exists")

    def test_archivio_export_endpoint_exists(self):
        """Verify /api/archivio/export endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/archivio/export", json={})
        # Should be 401 (auth required), not 404
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/archivio/export endpoint exists")

    def test_archivio_stats_endpoint_exists(self):
        """Verify /api/archivio/stats endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/archivio/stats")
        # Should be 401 (auth required), not 404
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/archivio/stats endpoint exists")


class TestVariantiValidation:
    """Test variante validation rules"""

    def test_variante_with_voce_id(self):
        """POST /api/montaggio/variante - works with voce_id filter"""
        fake_foto_doc_id = f"doc_{uuid.uuid4().hex[:10]}"
        
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "voce_id": "voce_test_123",
            "operatore_id": TEST_OPERATOR_ID,
            "operatore_nome": TEST_OPERATOR_NAME,
            "descrizione": "Variante per voce specifica",
            "foto_doc_id": fake_foto_doc_id
        }
        
        response = requests.post(f"{BASE_URL}/api/montaggio/variante", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["voce_id"] == "voce_test_123"
        print(f"✓ Created variante with voce_id: {data['variante_id']}")

    def test_list_varianti_with_voce_filter(self):
        """GET /api/montaggio/varianti/{commessa_id}?voce_id=... - filters by voce"""
        response = requests.get(
            f"{BASE_URL}/api/montaggio/varianti/{TEST_COMMESSA_ID}",
            params={"voce_id": "voce_test_123"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "varianti" in data
        # All returned varianti should have the specified voce_id
        for v in data["varianti"]:
            assert v["voce_id"] == "voce_test_123"
        print(f"✓ Filtered varianti by voce_id: {data['count']} results")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
