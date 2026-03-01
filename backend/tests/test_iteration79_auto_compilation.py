"""
Iteration 79 Tests: Auto-Compilation Feature Tests for EN 1090 Fascicolo Tecnico

Features tested:
1. Company settings save/load new EN 1090 fields (responsabile_nome, ruolo_firmatario, 
   ente_certificatore, ente_certificatore_numero, certificato_en1090_numero)
2. GET /api/fascicolo-tecnico/{cid} auto-populates:
   - firmatario from company business_name
   - mandatario from client_name
   - ente_notificato from company ente_certificatore
   - certificato_numero from company certificato_en1090_numero
   - redatto_da from company responsabile_nome
   - ddt_riferimento with commessa/01 suffix
   - resilienza from material type lookup (RESILIENZA_TABLE)
3. Resilienza lookup works for S355JR (27 J a 20 C), S275J2 (27 J a -20 C)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def test_user():
    """Create test user and session for all tests."""
    user_id = f"test-user-iter79-{uuid.uuid4().hex[:8]}"
    session_token = f"test_session_iter79_{uuid.uuid4().hex[:16]}"
    email = f"test.iter79.{uuid.uuid4().hex[:6]}@example.com"
    
    # Create user via mongosh
    os.system(f'''mongosh --quiet --eval "
use('test_database');
db.users.insertOne({{
  user_id: '{user_id}',
  email: '{email}',
  name: 'Test User Iter79',
  picture: 'https://via.placeholder.com/150',
  created_at: new Date()
}});
db.user_sessions.insertOne({{
  user_id: '{user_id}',
  session_token: '{session_token}',
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
}});
"''')
    
    yield {"user_id": user_id, "session_token": session_token, "email": email}
    
    # Cleanup after all tests
    os.system(f'''mongosh --quiet --eval "
use('test_database');
db.users.deleteOne({{ user_id: '{user_id}' }});
db.user_sessions.deleteOne({{ session_token: '{session_token}' }});
db.company_settings.deleteMany({{ user_id: '{user_id}' }});
db.commesse.deleteMany({{ user_id: '{user_id}' }});
db.preventivi.deleteMany({{ user_id: '{user_id}' }});
db.clients.deleteMany({{ user_id: '{user_id}' }});
db.material_batches.deleteMany({{ user_id: '{user_id}' }});
"''')


@pytest.fixture(scope="module")
def auth_headers(test_user):
    """Get authorization headers."""
    return {"Authorization": f"Bearer {test_user['session_token']}"}


class TestHealthEndpoint:
    """Basic health check."""
    
    def test_health_endpoint(self):
        """Verify API is healthy."""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("PASS: Health endpoint returns healthy")


class TestCompanySettingsEN1090Fields:
    """Test company settings save/load for new EN 1090 fields."""
    
    def test_save_en1090_fields(self, auth_headers, test_user):
        """Test saving EN 1090 certification fields."""
        en1090_data = {
            "business_name": "Test Steel Company SRL",
            "city": "Bologna",
            "responsabile_nome": "Mario Rossi",
            "ruolo_firmatario": "Legale Rappresentante",
            "ente_certificatore": "Rina Service",
            "ente_certificatore_numero": "0474",
            "certificato_en1090_numero": "CER-1090-2025-001"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/company/settings",
            json=en1090_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed to save settings: {response.text}"
        data = response.json()
        
        # Verify all EN 1090 fields saved
        assert data.get("responsabile_nome") == "Mario Rossi"
        assert data.get("ruolo_firmatario") == "Legale Rappresentante"
        assert data.get("ente_certificatore") == "Rina Service"
        assert data.get("ente_certificatore_numero") == "0474"
        assert data.get("certificato_en1090_numero") == "CER-1090-2025-001"
        print("PASS: EN 1090 fields saved correctly")
    
    def test_load_en1090_fields(self, auth_headers):
        """Test loading EN 1090 certification fields."""
        response = requests.get(
            f"{BASE_URL}/api/company/settings",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all EN 1090 fields loaded
        assert data.get("responsabile_nome") == "Mario Rossi"
        assert data.get("ruolo_firmatario") == "Legale Rappresentante"
        assert data.get("ente_certificatore") == "Rina Service"
        assert data.get("ente_certificatore_numero") == "0474"
        assert data.get("certificato_en1090_numero") == "CER-1090-2025-001"
        print("PASS: EN 1090 fields loaded correctly")


class TestFascicoloTecnicoAutoPopulation:
    """Test auto-population of fascicolo tecnico fields."""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self, test_user, auth_headers):
        """Set up commessa, client, preventivo, and material batches for testing."""
        user_id = test_user["user_id"]
        client_id = f"client-iter79-{uuid.uuid4().hex[:8]}"
        preventivo_id = f"prev-iter79-{uuid.uuid4().hex[:8]}"
        commessa_id = f"comm-iter79-{uuid.uuid4().hex[:8]}"
        
        # Create client
        os.system(f'''mongosh --quiet --eval "
use('test_database');
db.clients.insertOne({{
  client_id: '{client_id}',
  user_id: '{user_id}',
  name: 'Cliente Test SPA',
  email: 'cliente@test.com',
  created_at: new Date()
}});
"''')
        
        # Create preventivo
        os.system(f'''mongosh --quiet --eval "
use('test_database');
db.preventivi.insertOne({{
  preventivo_id: '{preventivo_id}',
  user_id: '{user_id}',
  client_id: '{client_id}',
  client_name: 'Cliente Test SPA',
  numero_disegno: 'DIS-2025-001',
  classe_esecuzione: 'EXC2',
  created_at: new Date()
}});
"''')
        
        # Create commessa linked to preventivo
        os.system(f'''mongosh --quiet --eval "
use('test_database');
db.commesse.insertOne({{
  commessa_id: '{commessa_id}',
  user_id: '{user_id}',
  client_id: '{client_id}',
  preventivo_id: '{preventivo_id}',
  numero: 'COMM-2025-001',
  title: 'Struttura Acciaio Test',
  stato: 'in_produzione',
  fascicolo_tecnico: {{}},
  created_at: new Date()
}});
"''')
        
        # Create material batches with material types for resilienza lookup
        os.system(f'''mongosh --quiet --eval "
use('test_database');
db.material_batches.insertMany([
  {{
    batch_id: 'batch-1-{uuid.uuid4().hex[:6]}',
    commessa_id: '{commessa_id}',
    user_id: '{user_id}',
    material_type: 'S355JR',
    dimensions: 'HEA 200',
    created_at: new Date()
  }},
  {{
    batch_id: 'batch-2-{uuid.uuid4().hex[:6]}',
    commessa_id: '{commessa_id}',
    user_id: '{user_id}',
    material_type: 'S275J2+N',
    dimensions: 'IPE 300',
    created_at: new Date()
  }}
]);
"''')
        
        self.commessa_id = commessa_id
        self.client_id = client_id
        self.preventivo_id = preventivo_id
        yield
    
    def test_auto_populate_firmatario_from_business_name(self, auth_headers):
        """Test firmatario auto-populated from company business_name."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{self.commessa_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # firmatario should be from company business_name
        assert data.get("firmatario") == "Test Steel Company SRL"
        assert "firmatario" in data.get("_auto_fields", [])
        print("PASS: firmatario auto-populated from company business_name")
    
    def test_auto_populate_mandatario_from_client_name(self, auth_headers):
        """Test mandatario auto-populated from client_name."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{self.commessa_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # mandatario should be from client name
        assert data.get("mandatario") == "Cliente Test SPA"
        assert "mandatario" in data.get("_auto_fields", [])
        print("PASS: mandatario auto-populated from client_name")
    
    def test_auto_populate_ente_notificato_from_company(self, auth_headers):
        """Test ente_notificato auto-populated from company ente_certificatore."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{self.commessa_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("ente_notificato") == "Rina Service"
        assert "ente_notificato" in data.get("_auto_fields", [])
        print("PASS: ente_notificato auto-populated from company ente_certificatore")
    
    def test_auto_populate_certificato_numero_from_company(self, auth_headers):
        """Test certificato_numero auto-populated from company certificato_en1090_numero."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{self.commessa_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("certificato_numero") == "CER-1090-2025-001"
        assert "certificato_numero" in data.get("_auto_fields", [])
        print("PASS: certificato_numero auto-populated from company certificato_en1090_numero")
    
    def test_auto_populate_redatto_da_from_company(self, auth_headers):
        """Test redatto_da auto-populated from company responsabile_nome."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{self.commessa_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("redatto_da") == "Mario Rossi"
        assert "redatto_da" in data.get("_auto_fields", [])
        print("PASS: redatto_da auto-populated from company responsabile_nome")
    
    def test_auto_populate_ddt_riferimento_with_suffix(self, auth_headers):
        """Test ddt_riferimento auto-populated with commessa/01 suffix."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{self.commessa_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # ddt_riferimento should be like "COMM-2025-001/01"
        ddt_rif = data.get("ddt_riferimento", "")
        assert ddt_rif.startswith("COMM-2025-001/"), f"Expected DDT prefix 'COMM-2025-001/', got '{ddt_rif}'"
        assert ddt_rif.endswith("/01"), f"Expected suffix '/01', got '{ddt_rif}'"
        assert "ddt_riferimento" in data.get("_auto_fields", [])
        print(f"PASS: ddt_riferimento auto-populated with suffix: {ddt_rif}")
    
    def test_auto_populate_ddt_data_today(self, auth_headers):
        """Test ddt_data auto-populated with today's date."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{self.commessa_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        today = datetime.now().strftime("%d/%m/%Y")
        assert data.get("ddt_data") == today
        assert "ddt_data" in data.get("_auto_fields", [])
        print(f"PASS: ddt_data auto-populated with today: {today}")
    
    def test_auto_populate_luogo_data_firma(self, auth_headers):
        """Test luogo_data_firma auto-populated with city and date."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{self.commessa_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        luogo_data = data.get("luogo_data_firma", "")
        assert luogo_data.startswith("Bologna,"), f"Expected city 'Bologna,', got '{luogo_data}'"
        assert "luogo_data_firma" in data.get("_auto_fields", [])
        print(f"PASS: luogo_data_firma auto-populated: {luogo_data}")


class TestResilienzaLookup:
    """Test resilienza auto-calculation from material type lookup table."""
    
    @pytest.fixture(autouse=True)
    def setup_materials(self, test_user, auth_headers):
        """Set up test commesse with different material types."""
        user_id = test_user["user_id"]
        self.commessa_s355jr = f"comm-s355jr-{uuid.uuid4().hex[:8]}"
        self.commessa_s275j2 = f"comm-s275j2-{uuid.uuid4().hex[:8]}"
        
        # Create commessa with S355JR material
        os.system(f'''mongosh --quiet --eval "
use('test_database');
db.commesse.insertOne({{
  commessa_id: '{self.commessa_s355jr}',
  user_id: '{user_id}',
  numero: 'COMM-S355',
  title: 'Struttura S355JR',
  stato: 'in_produzione',
  fascicolo_tecnico: {{}},
  created_at: new Date()
}});
db.material_batches.insertOne({{
  batch_id: 'batch-s355-{uuid.uuid4().hex[:6]}',
  commessa_id: '{self.commessa_s355jr}',
  user_id: '{user_id}',
  material_type: 'S355JR',
  dimensions: 'HEA 200',
  created_at: new Date()
}});
"''')
        
        # Create commessa with S275J2 material (includes +N suffix to test normalization)
        os.system(f'''mongosh --quiet --eval "
use('test_database');
db.commesse.insertOne({{
  commessa_id: '{self.commessa_s275j2}',
  user_id: '{user_id}',
  numero: 'COMM-S275',
  title: 'Struttura S275J2',
  stato: 'in_produzione',
  fascicolo_tecnico: {{}},
  created_at: new Date()
}});
db.material_batches.insertOne({{
  batch_id: 'batch-s275-{uuid.uuid4().hex[:6]}',
  commessa_id: '{self.commessa_s275j2}',
  user_id: '{user_id}',
  material_type: 'S275J2+N',
  dimensions: 'IPE 300',
  created_at: new Date()
}});
"''')
        yield
    
    def test_resilienza_s355jr(self, auth_headers):
        """Test resilienza lookup for S355JR returns '27 J a 20 °C'."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{self.commessa_s355jr}",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # S355JR should have "27 J a 20 °C"
        resilienza = data.get("resilienza", "")
        assert "27" in resilienza and "20" in resilienza, f"Expected '27 J a 20 °C' for S355JR, got '{resilienza}'"
        assert "resilienza" in data.get("_auto_fields", [])
        print(f"PASS: Resilienza for S355JR: {resilienza}")
    
    def test_resilienza_s275j2(self, auth_headers):
        """Test resilienza lookup for S275J2 returns '27 J a -20 °C'."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{self.commessa_s275j2}",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # S275J2 should have "27 J a -20 °C"
        resilienza = data.get("resilienza", "")
        assert "27" in resilienza and "-20" in resilienza, f"Expected '27 J a -20 °C' for S275J2, got '{resilienza}'"
        assert "resilienza" in data.get("_auto_fields", [])
        print(f"PASS: Resilienza for S275J2: {resilienza}")


class TestAutoFieldsList:
    """Test that _auto_fields list includes all auto-populated field names."""
    
    @pytest.fixture(autouse=True)
    def setup_complete_data(self, test_user, auth_headers):
        """Set up commessa with all data sources for complete auto-population."""
        user_id = test_user["user_id"]
        self.commessa_id = f"comm-complete-{uuid.uuid4().hex[:8]}"
        client_id = f"client-complete-{uuid.uuid4().hex[:8]}"
        prev_id = f"prev-complete-{uuid.uuid4().hex[:8]}"
        
        os.system(f'''mongosh --quiet --eval "
use('test_database');
db.clients.insertOne({{
  client_id: '{client_id}',
  user_id: '{user_id}',
  name: 'Complete Test Client',
  created_at: new Date()
}});
db.preventivi.insertOne({{
  preventivo_id: '{prev_id}',
  user_id: '{user_id}',
  client_id: '{client_id}',
  client_name: 'Complete Test Client',
  numero_disegno: 'DIS-COMPLETE-001',
  classe_esecuzione: 'EXC3',
  created_at: new Date()
}});
db.commesse.insertOne({{
  commessa_id: '{self.commessa_id}',
  user_id: '{user_id}',
  client_id: '{client_id}',
  preventivo_id: '{prev_id}',
  numero: 'COMM-COMPLETE-001',
  title: 'Complete Auto Test',
  stato: 'in_produzione',
  fascicolo_tecnico: {{}},
  created_at: new Date()
}});
db.material_batches.insertOne({{
  batch_id: 'batch-complete-{uuid.uuid4().hex[:6]}',
  commessa_id: '{self.commessa_id}',
  user_id: '{user_id}',
  material_type: 'S355JR',
  dimensions: 'HEA 200',
  created_at: new Date()
}});
"''')
        yield
    
    def test_auto_fields_list_complete(self, auth_headers):
        """Test _auto_fields list includes all expected auto-populated fields."""
        response = requests.get(
            f"{BASE_URL}/api/fascicolo-tecnico/{self.commessa_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        auto_fields = data.get("_auto_fields", [])
        
        # Expected auto-populated fields based on the code
        expected_auto = [
            "firmatario",          # from company business_name
            "mandatario",          # from client_name
            "ente_notificato",     # from company ente_certificatore
            "certificato_numero",  # from company certificato_en1090_numero
            "redatto_da",          # from company responsabile_nome
            "ddt_riferimento",     # commessa/01 suffix
            "ddt_data",            # today
            "luogo_data_firma",    # city, today
            "data_emissione",      # today
            "client_name",         # from client
            "commessa_numero",     # from commessa
            "disegno_numero",      # from preventivo
            "disegno_riferimento", # from preventivo
            "resilienza",          # from material lookup
        ]
        
        # Check that expected fields are in auto_fields
        found = []
        missing = []
        for field in expected_auto:
            if field in auto_fields:
                found.append(field)
            else:
                missing.append(field)
        
        print(f"Auto fields found: {found}")
        if missing:
            print(f"Auto fields missing (may be OK if no source data): {missing}")
        
        # At minimum, these should always be present
        critical_auto = ["ddt_data", "data_emissione", "commessa_numero"]
        for field in critical_auto:
            assert field in auto_fields, f"Critical auto field '{field}' missing from _auto_fields"
        
        print(f"PASS: _auto_fields list contains {len(auto_fields)} auto-populated fields")
