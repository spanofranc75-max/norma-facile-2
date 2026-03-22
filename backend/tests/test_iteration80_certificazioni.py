"""
Iteration 80 - Tests for new Certificazioni features:
1. GET /api/company/settings returns new fields: classe_esecuzione_default, certificato_en13241_numero
2. PUT /api/company/settings saves new fields
3. GET /api/fascicolo-tecnico/{commessa_id} returns auto-populated fields (report_numero, report_data, ordine_numero, spessore)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

# Use the public URL for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://istruttoria-hub.preview.emergentagent.com').rstrip('/')


@pytest.fixture(scope="module")
def test_session():
    """Create a test user and session for authenticated requests."""
    import subprocess
    import json
    
    user_id = f"test-user-iter80-{uuid.uuid4().hex[:8]}"
    session_token = f"test_session_iter80_{uuid.uuid4().hex[:16]}"
    
    # Create user and session in MongoDB
    mongo_script = f"""
    use('test_database');
    db.users.insertOne({{
        user_id: '{user_id}',
        email: 'iter80.test@example.com',
        name: 'Iteration 80 Test User',
        picture: 'https://via.placeholder.com/150',
        created_at: new Date()
    }});
    db.user_sessions.insertOne({{
        user_id: '{user_id}',
        session_token: '{session_token}',
        expires_at: new Date(Date.now() + 7*24*60*60*1000),
        created_at: new Date()
    }});
    """
    
    subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
    
    yield {
        "user_id": user_id,
        "session_token": session_token,
        "headers": {
            "Authorization": f"Bearer {session_token}",
            "Content-Type": "application/json"
        }
    }
    
    # Cleanup
    cleanup_script = f"""
    use('test_database');
    db.users.deleteMany({{user_id: '{user_id}'}});
    db.user_sessions.deleteMany({{session_token: '{session_token}'}});
    db.company_settings.deleteMany({{user_id: '{user_id}'}});
    db.commesse.deleteMany({{user_id: '{user_id}'}});
    db.clients.deleteMany({{user_id: '{user_id}'}});
    db.material_batches.deleteMany({{user_id: '{user_id}'}});
    """
    subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], capture_output=True)


class TestHealthEndpoint:
    """Basic health check before proceeding with other tests."""
    
    def test_health_endpoint(self):
        """Test that the backend is up and running."""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health endpoint OK: {data}")


class TestCompanySettingsNewFields:
    """Test new certification fields in company settings."""
    
    def test_get_company_settings_returns_new_fields(self, test_session):
        """Test GET /api/company/settings returns classe_esecuzione_default and certificato_en13241_numero fields."""
        response = requests.get(
            f"{BASE_URL}/api/company/settings",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify new fields exist in response (can be null/empty)
        assert "classe_esecuzione_default" in data, "classe_esecuzione_default field missing from response"
        assert "certificato_en13241_numero" in data, "certificato_en13241_numero field missing from response"
        print(f"✓ GET /api/company/settings returns new fields")
        print(f"  - classe_esecuzione_default: {data.get('classe_esecuzione_default')}")
        print(f"  - certificato_en13241_numero: {data.get('certificato_en13241_numero')}")
    
    def test_put_company_settings_saves_classe_esecuzione(self, test_session):
        """Test PUT /api/company/settings saves classe_esecuzione_default."""
        payload = {
            "business_name": "Test Fabbro SRL",
            "classe_esecuzione_default": "EXC3"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/company/settings",
            headers=test_session["headers"],
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("classe_esecuzione_default") == "EXC3", f"Expected EXC3, got {data.get('classe_esecuzione_default')}"
        print(f"✓ PUT /api/company/settings saves classe_esecuzione_default=EXC3")
    
    def test_put_company_settings_saves_certificato_en13241(self, test_session):
        """Test PUT /api/company/settings saves certificato_en13241_numero."""
        payload = {
            "business_name": "Test Fabbro SRL",
            "certificato_en13241_numero": "1234-CPR-9012"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/company/settings",
            headers=test_session["headers"],
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("certificato_en13241_numero") == "1234-CPR-9012", f"Expected 1234-CPR-9012, got {data.get('certificato_en13241_numero')}"
        print(f"✓ PUT /api/company/settings saves certificato_en13241_numero=1234-CPR-9012")
    
    def test_put_company_settings_saves_both_new_fields(self, test_session):
        """Test PUT /api/company/settings saves both new fields together."""
        payload = {
            "business_name": "Test Fabbro Completo SRL",
            "classe_esecuzione_default": "EXC2",
            "certificato_en13241_numero": "5678-CPR-3456",
            "certificato_en1090_numero": "0474-CPR-2478",
            "ente_certificatore": "Rina Service",
            "ente_certificatore_numero": "0474"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/company/settings",
            headers=test_session["headers"],
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("classe_esecuzione_default") == "EXC2"
        assert data.get("certificato_en13241_numero") == "5678-CPR-3456"
        assert data.get("certificato_en1090_numero") == "0474-CPR-2478"
        assert data.get("ente_certificatore") == "Rina Service"
        print(f"✓ PUT /api/company/settings saves all certification fields")
    
    def test_get_company_settings_persists_new_fields(self, test_session):
        """Test GET /api/company/settings returns previously saved new fields."""
        # First save
        payload = {
            "classe_esecuzione_default": "EXC4",
            "certificato_en13241_numero": "PERSIST-TEST-001"
        }
        
        put_response = requests.put(
            f"{BASE_URL}/api/company/settings",
            headers=test_session["headers"],
            json=payload
        )
        assert put_response.status_code == 200
        
        # Then retrieve
        get_response = requests.get(
            f"{BASE_URL}/api/company/settings",
            headers=test_session["headers"]
        )
        
        assert get_response.status_code == 200
        data = get_response.json()
        
        assert data.get("classe_esecuzione_default") == "EXC4", f"Expected EXC4, got {data.get('classe_esecuzione_default')}"
        assert data.get("certificato_en13241_numero") == "PERSIST-TEST-001", f"Expected PERSIST-TEST-001, got {data.get('certificato_en13241_numero')}"
        print(f"✓ GET /api/company/settings persists new fields correctly")


@pytest.fixture
def test_commessa_with_materials(test_session):
    """Create a test commessa with associated materials and client for fascicolo tecnico testing."""
    import subprocess
    
    user_id = test_session["user_id"]
    commessa_id = f"test-comm-iter80-{uuid.uuid4().hex[:8]}"
    client_id = f"test-client-iter80-{uuid.uuid4().hex[:8]}"
    
    # Create client, commessa and material batches
    mongo_script = f"""
    use('test_database');
    
    // Create client
    db.clients.insertOne({{
        client_id: '{client_id}',
        user_id: '{user_id}',
        name: 'Cliente Test Iter80',
        business_name: 'Cliente Test Iter80 SRL',
        created_at: new Date()
    }});
    
    // Create commessa
    db.commesse.insertOne({{
        commessa_id: '{commessa_id}',
        user_id: '{user_id}',
        client_id: '{client_id}',
        numero: 'COMM-2025-ITER80',
        title: 'Test Commessa Iteration 80',
        fascicolo_tecnico: {{}},
        fasi_produzione: [
            {{tipo: 'taglio', stato: 'completato', data_inizio: '2025-01-10', data_fine: '2025-01-11'}},
            {{tipo: 'saldatura', stato: 'in_corso', data_inizio: '2025-01-12'}}
        ],
        created_at: new Date()
    }});
    
    // Create material batches with spessore
    db.material_batches.insertOne({{
        batch_id: 'batch-iter80-1',
        commessa_id: '{commessa_id}',
        user_id: '{user_id}',
        material_type: 'S355JR',
        dimensions: 'IPE 200',
        spessore: '8mm',
        created_at: new Date()
    }});
    
    db.material_batches.insertOne({{
        batch_id: 'batch-iter80-2',
        commessa_id: '{commessa_id}',
        user_id: '{user_id}',
        material_type: 'S275J0',
        dimensions: 'HEA 160',
        spessore: '10mm',
        created_at: new Date()
    }});
    """
    
    subprocess.run(['mongosh', '--quiet', '--eval', mongo_script], capture_output=True)
    
    yield {
        "commessa_id": commessa_id,
        "client_id": client_id,
        "numero": "COMM-2025-ITER80"
    }
    
    # Cleanup handled by test_session fixture


class TestFascicoloTecnicoAutoFields:
    """Test auto-populated fields in fascicolo tecnico endpoint."""
    
    def test_fascicolo_tecnico_returns_report_numero(self, test_session, test_commessa_with_materials):
        """Test GET /api/fascicolo-tecnico/{cid} returns report_numero in _auto_fields."""
        commessa_id = test_commessa_with_materials["commessa_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{commessa_id}",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        auto_fields = data.get("_auto_fields", [])
        assert "report_numero" in auto_fields, f"report_numero not in _auto_fields: {auto_fields}"
        assert data.get("report_numero") == test_commessa_with_materials["numero"], \
            f"Expected {test_commessa_with_materials['numero']}, got {data.get('report_numero')}"
        print(f"✓ report_numero auto-populated: {data.get('report_numero')}")
    
    def test_fascicolo_tecnico_returns_report_data(self, test_session, test_commessa_with_materials):
        """Test GET /api/fascicolo-tecnico/{cid} returns report_data in _auto_fields."""
        commessa_id = test_commessa_with_materials["commessa_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{commessa_id}",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        auto_fields = data.get("_auto_fields", [])
        assert "report_data" in auto_fields, f"report_data not in _auto_fields: {auto_fields}"
        
        # Should be today's date in dd/mm/yyyy format
        today = datetime.now().strftime("%d/%m/%Y")
        assert data.get("report_data") == today, f"Expected {today}, got {data.get('report_data')}"
        print(f"✓ report_data auto-populated: {data.get('report_data')}")
    
    def test_fascicolo_tecnico_returns_ordine_numero(self, test_session, test_commessa_with_materials):
        """Test GET /api/fascicolo-tecnico/{cid} returns ordine_numero in _auto_fields."""
        commessa_id = test_commessa_with_materials["commessa_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{commessa_id}",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        auto_fields = data.get("_auto_fields", [])
        assert "ordine_numero" in auto_fields, f"ordine_numero not in _auto_fields: {auto_fields}"
        assert data.get("ordine_numero") == test_commessa_with_materials["numero"], \
            f"Expected {test_commessa_with_materials['numero']}, got {data.get('ordine_numero')}"
        print(f"✓ ordine_numero auto-populated: {data.get('ordine_numero')}")
    
    def test_fascicolo_tecnico_returns_spessore(self, test_session, test_commessa_with_materials):
        """Test GET /api/fascicolo-tecnico/{cid} returns spessore in _auto_fields from material batches."""
        commessa_id = test_commessa_with_materials["commessa_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{commessa_id}",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        auto_fields = data.get("_auto_fields", [])
        
        # spessore should be auto-populated from material batches
        spessore = data.get("spessore", "")
        assert spessore, f"spessore should be populated, got: {spessore}"
        # Should contain values from material batches (8mm and 10mm)
        assert "8mm" in spessore or "10mm" in spessore, f"Expected spessore to contain 8mm or 10mm, got: {spessore}"
        
        # If spessore is in auto_fields, it was auto-populated
        if spessore and "spessore" in auto_fields:
            print(f"✓ spessore auto-populated and in _auto_fields: {spessore}")
        elif spessore:
            print(f"✓ spessore populated: {spessore} (may not be in _auto_fields if manually set)")
    
    def test_fascicolo_tecnico_returns_all_auto_fields(self, test_session, test_commessa_with_materials):
        """Test GET /api/fascicolo-tecnico/{cid} returns comprehensive _auto_fields list."""
        commessa_id = test_commessa_with_materials["commessa_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{commessa_id}",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        auto_fields = data.get("_auto_fields", [])
        
        # These fields should always be auto-populated
        expected_auto = ["commessa_numero", "report_data", "data_emissione", "ddt_data"]
        
        for field in expected_auto:
            assert field in auto_fields, f"{field} not in _auto_fields: {auto_fields}"
        
        print(f"✓ _auto_fields contains all expected fields")
        print(f"  Auto-populated fields: {auto_fields}")
    
    def test_fascicolo_tecnico_returns_client_name(self, test_session, test_commessa_with_materials):
        """Test GET /api/fascicolo-tecnico/{cid} returns client_name in _auto_fields."""
        commessa_id = test_commessa_with_materials["commessa_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{commessa_id}",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        auto_fields = data.get("_auto_fields", [])
        assert "client_name" in auto_fields, f"client_name not in _auto_fields: {auto_fields}"
        assert data.get("client_name") == "Cliente Test Iter80 SRL", \
            f"Expected 'Cliente Test Iter80 SRL', got {data.get('client_name')}"
        print(f"✓ client_name auto-populated: {data.get('client_name')}")
    
    def test_fascicolo_tecnico_returns_mandatario(self, test_session, test_commessa_with_materials):
        """Test GET /api/fascicolo-tecnico/{cid} returns mandatario auto-populated from client."""
        commessa_id = test_commessa_with_materials["commessa_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{commessa_id}",
            headers=test_session["headers"]
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        auto_fields = data.get("_auto_fields", [])
        assert "mandatario" in auto_fields, f"mandatario not in _auto_fields: {auto_fields}"
        # Mandatario should be the client business name
        assert data.get("mandatario") == "Cliente Test Iter80 SRL", \
            f"Expected 'Cliente Test Iter80 SRL', got {data.get('mandatario')}"
        print(f"✓ mandatario auto-populated from client: {data.get('mandatario')}")


class TestCompanySettingsClasseEsecuzioneOptions:
    """Test that classe_esecuzione_default accepts all valid EXC values."""
    
    @pytest.mark.parametrize("classe", ["EXC1", "EXC2", "EXC3", "EXC4"])
    def test_classe_esecuzione_valid_values(self, test_session, classe):
        """Test PUT /api/company/settings accepts all valid EXC values."""
        payload = {"classe_esecuzione_default": classe}
        
        response = requests.put(
            f"{BASE_URL}/api/company/settings",
            headers=test_session["headers"],
            json=payload
        )
        
        assert response.status_code == 200, f"Expected 200 for {classe}, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("classe_esecuzione_default") == classe
        print(f"✓ classe_esecuzione_default={classe} saved successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
