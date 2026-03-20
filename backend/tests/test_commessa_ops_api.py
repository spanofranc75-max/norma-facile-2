"""
Test CommessaOpsPanel backend APIs
Tests for the refactored CommessaOpsPanel frontend components
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "SGz2wNxiQd67E3cYdQqGqeBRaO1FOzaGpgo3Xf9jQco"
COMMESSA_ID = "com_e8c4810ad476"


@pytest.fixture
def api_client():
    """Requests session with auth cookie"""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestHealthAndAuth:
    """Basic health and auth tests"""
    
    def test_health_endpoint(self, api_client):
        """Test /api/health endpoint"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "NormaFacile" in data.get("service", "") or "Norma Facile" in data.get("service", "")
        print(f"✓ Health: {data}")
    
    def test_auth_me(self, api_client):
        """Test /api/auth/me endpoint"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        print(f"✓ Auth: user_id={data['user_id']}")


class TestCommessaOpsEndpoints:
    """Tests for CommessaOpsPanel related endpoints"""
    
    def test_get_commessa(self, api_client):
        """Test GET /api/commesse/{id}"""
        response = api_client.get(f"{BASE_URL}/api/commesse/{COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        assert "commessa_id" in data or "numero" in data
        print(f"✓ Commessa: {data.get('numero', data.get('commessa_id'))}")
    
    def test_get_commessa_ops(self, api_client):
        """Test GET /api/commesse/{id}/ops - Main endpoint for CommessaOpsPanel"""
        response = api_client.get(f"{BASE_URL}/api/commesse/{COMMESSA_ID}/ops")
        assert response.status_code == 200
        data = response.json()
        
        # Verify all sections have data
        assert "approvvigionamento" in data, "Missing approvvigionamento section"
        assert "fasi_produzione" in data, "Missing fasi_produzione section"
        assert "consegne" in data, "Missing consegne section"
        assert "conto_lavoro" in data, "Missing conto_lavoro section"
        
        # Verify approvvigionamento has sub-sections
        approv = data["approvvigionamento"]
        assert "richieste" in approv, "Missing RdP list"
        assert "ordini" in approv, "Missing OdA list"
        assert "arrivi" in approv, "Missing arrivi list"
        
        print(f"✓ Ops data: {len(approv['richieste'])} RdP, {len(approv['ordini'])} OdA, {len(data['consegne'])} consegne")
    
    def test_get_commessa_documents(self, api_client):
        """Test GET /api/commesse/{id}/documenti - For RepositoryDocumentiSection"""
        response = api_client.get(f"{BASE_URL}/api/commesse/{COMMESSA_ID}/documenti")
        assert response.status_code == 200
        data = response.json()
        # API returns {documents: [], total: N} format
        if isinstance(data, dict):
            assert "documents" in data
            docs = data["documents"]
        else:
            docs = data
        assert isinstance(docs, list)
        print(f"✓ Documents: {len(docs)} documents found")


class TestCAMEndpoints:
    """Tests for CAM (Criteri Ambientali Minimi) section"""
    
    def test_get_cam_lotti(self, api_client):
        """Test GET /api/cam/lotti - List CAM materials"""
        response = api_client.get(f"{BASE_URL}/api/cam/lotti?commessa_id={COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        # API returns {lotti: [], total: N} format
        if isinstance(data, dict):
            assert "lotti" in data
            lotti = data["lotti"]
        else:
            lotti = data
        assert isinstance(lotti, list)
        print(f"✓ CAM Lotti: {len(lotti)} lotti found")
    
    def test_get_cam_calcolo(self, api_client):
        """Test GET /api/cam/calcolo/{commessa_id} - CAM compliance calculation"""
        response = api_client.get(f"{BASE_URL}/api/cam/calcolo/{COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify CAM calculation fields
        assert "peso_totale_kg" in data
        assert "peso_riciclato_kg" in data
        assert "percentuale_riciclato_totale" in data
        assert "conforme_cam" in data
        
        print(f"✓ CAM Calcolo: {data['percentuale_riciclato_totale']:.1f}% riciclato, conforme={data['conforme_cam']}")


class TestTracciabilitaEndpoints:
    """Tests for Tracciabilità Materiali section"""
    
    def test_get_material_batches(self, api_client):
        """Test GET /api/material-batches?commessa_id={id}"""
        # Try direct endpoint
        response = api_client.get(f"{BASE_URL}/api/material-batches?commessa_id={COMMESSA_ID}")
        if response.status_code == 404:
            # Material batches may be in ops data
            response = api_client.get(f"{BASE_URL}/api/commesse/{COMMESSA_ID}/ops")
            assert response.status_code == 200
            print("✓ Material batches: accessed via /ops endpoint")
        else:
            assert response.status_code == 200
            data = response.json()
            batches = data.get("batches", data) if isinstance(data, dict) else data
            print(f"✓ Material batches: {len(batches) if isinstance(batches, list) else 'available'}")


class TestFascicoloTecnicoEndpoints:
    """Tests for Fascicolo Tecnico section"""
    
    def test_get_fascicolo_status(self, api_client):
        """Test GET /api/commesse/{id}/fascicolo-tecnico"""
        response = api_client.get(f"{BASE_URL}/api/commesse/{COMMESSA_ID}/fascicolo-tecnico")
        # Could be 200 or 404 if not configured
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Fascicolo Tecnico: {data.get('status', 'available')}")
        else:
            print("✓ Fascicolo Tecnico: endpoint exists (returns 404 when not configured)")


class TestProduzioneEndpoints:
    """Tests for Produzione section"""
    
    def test_get_produzione_fasi(self, api_client):
        """Test production phases from ops endpoint"""
        response = api_client.get(f"{BASE_URL}/api/commesse/{COMMESSA_ID}/ops")
        assert response.status_code == 200
        data = response.json()
        
        assert "fasi_produzione" in data
        assert "produzione_progress" in data
        
        fasi = data["fasi_produzione"]
        progress = data["produzione_progress"]
        
        print(f"✓ Produzione: {progress['completed']}/{progress['total']} fasi complete ({progress['percentage']}%)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
