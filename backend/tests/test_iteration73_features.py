"""
Iteration 73 - Test Scheda Rintracciabilità and New Feature Fields

Features to test:
1. Backend: GET /api/health returns 200
2. Backend: POST /api/preventivi creates preventivo with numero_disegno and ingegnere_disegno fields
3. Backend: PUT /api/preventivi/{id} updates numero_disegno and ingegnere_disegno
4. Backend: POST /api/fpc/batches creates batch with new fields (posizione, n_pezzi, numero_certificato, ddt_numero, disegno_numero)
5. Backend: PUT /api/fpc/batches/{id} updates new fields
6. Backend: GET /api/commesse/{cid}/scheda-rintracciabilita-pdf generates PDF
7. Backend: _extract_profile_base correctly extracts IPE100 from 'Trave IPE 100 in S275 JR' and 'IPE 100X55X4.1'
8. Backend: Smart matching assigns profile to correct commessa based on profile base
9. Backend: Cascade delete removes lotti_cam by colata numbers from metadata
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://inventory-norma.preview.emergentagent.com').rstrip('/')

# Test session token created via mongosh
TEST_SESSION_TOKEN = None
TEST_USER_ID = None
TEST_PREVENTIVO_ID = None
TEST_BATCH_ID = None
TEST_COMMESSA_ID = None


@pytest.fixture(scope="module", autouse=True)
def setup_test_data():
    """Create test user and session via mongosh."""
    global TEST_SESSION_TOKEN, TEST_USER_ID
    
    import subprocess
    timestamp = int(time.time() * 1000)
    
    # Create test user and session
    cmd = f'''mongosh --quiet --eval "
use('test_database');
var userId = 'test-user-iter73-{timestamp}';
var sessionToken = 'test_session_iter73_{timestamp}';
db.users.insertOne({{
  user_id: userId,
  email: 'test.iter73.{timestamp}@example.com',
  name: 'Test User Iter73',
  picture: 'https://via.placeholder.com/150',
  created_at: new Date()
}});
db.user_sessions.insertOne({{
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
}});
print(sessionToken + '|' + userId);
"'''
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    output = result.stdout.strip()
    
    if '|' in output:
        parts = output.split('|')
        TEST_SESSION_TOKEN = parts[0].strip()
        TEST_USER_ID = parts[1].strip()
        print(f"Created test session: {TEST_SESSION_TOKEN}")
    else:
        raise Exception(f"Failed to create test session: {result.stderr}")
    
    yield
    
    # Cleanup
    cleanup_cmd = f'''mongosh --quiet --eval "
use('test_database');
db.users.deleteMany({{email: /test\\.iter73\\./}});
db.user_sessions.deleteMany({{session_token: /test_session_iter73/}});
db.preventivi.deleteMany({{user_id: /test-user-iter73/}});
db.material_batches.deleteMany({{user_id: /test-user-iter73/}});
db.commesse.deleteMany({{user_id: /test-user-iter73/}});
db.lotti_cam.deleteMany({{user_id: /test-user-iter73/}});
db.commessa_documents.deleteMany({{user_id: /test-user-iter73/}});
print('Cleanup complete');
"'''
    subprocess.run(cleanup_cmd, shell=True, capture_output=True, text=True)


@pytest.fixture
def api_client():
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TEST_SESSION_TOKEN}"
    })
    return session


class TestHealthEndpoint:
    """Test health endpoint."""
    
    def test_health_returns_200(self, api_client):
        """GET /api/health returns 200."""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"Health check: {data}")


class TestPreventivoFields:
    """Test numero_disegno and ingegnere_disegno fields on preventivo."""
    
    def test_create_preventivo_with_disegno_fields(self, api_client):
        """POST /api/preventivi creates preventivo with numero_disegno and ingegnere_disegno."""
        global TEST_PREVENTIVO_ID
        
        payload = {
            "subject": "Test Preventivo Iter73",
            "validity_days": 30,
            "lines": [
                {
                    "description": "IPE 200 S275JR",
                    "quantity": 10,
                    "unit": "kg",
                    "unit_price": 1.5,
                    "vat_rate": "22"
                }
            ],
            "numero_disegno": "DIS-2026-001",
            "ingegnere_disegno": "Ing. Mario Rossi"
        }
        
        response = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        TEST_PREVENTIVO_ID = data.get("preventivo_id")
        assert TEST_PREVENTIVO_ID is not None
        
        # Verify the fields are saved
        assert data.get("numero_disegno") == "DIS-2026-001"
        assert data.get("ingegnere_disegno") == "Ing. Mario Rossi"
        print(f"Created preventivo {TEST_PREVENTIVO_ID} with disegno fields")
    
    def test_update_preventivo_disegno_fields(self, api_client):
        """PUT /api/preventivi/{id} updates numero_disegno and ingegnere_disegno."""
        global TEST_PREVENTIVO_ID
        
        if not TEST_PREVENTIVO_ID:
            pytest.skip("No preventivo created")
        
        payload = {
            "numero_disegno": "DIS-2026-002",
            "ingegnere_disegno": "Ing. Luigi Verdi"
        }
        
        response = api_client.put(f"{BASE_URL}/api/preventivi/{TEST_PREVENTIVO_ID}", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("numero_disegno") == "DIS-2026-002"
        assert data.get("ingegnere_disegno") == "Ing. Luigi Verdi"
        print(f"Updated preventivo {TEST_PREVENTIVO_ID} disegno fields")
    
    def test_get_preventivo_has_disegno_fields(self, api_client):
        """GET /api/preventivi/{id} returns disegno fields."""
        global TEST_PREVENTIVO_ID
        
        if not TEST_PREVENTIVO_ID:
            pytest.skip("No preventivo created")
        
        response = api_client.get(f"{BASE_URL}/api/preventivi/{TEST_PREVENTIVO_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("numero_disegno") == "DIS-2026-002"
        assert data.get("ingegnere_disegno") == "Ing. Luigi Verdi"
        print(f"Verified preventivo has disegno fields")


class TestFpcBatchesFields:
    """Test new fields on FPC material batches."""
    
    def test_create_batch_with_new_fields(self, api_client):
        """POST /api/fpc/batches creates batch with posizione, n_pezzi, numero_certificato, ddt_numero."""
        global TEST_BATCH_ID
        
        payload = {
            "supplier_name": "Acciaierie Pittini",
            "material_type": "S275JR",
            "heat_number": "COL-2026-001",
            "dimensions": "IPE 100",
            "posizione": "P01",
            "n_pezzi": 10,
            "numero_certificato": "CERT-2026-001",
            "ddt_numero": "DDT-2026-001",
            "disegno_numero": "DIS-STR-01"
        }
        
        response = api_client.post(f"{BASE_URL}/api/fpc/batches", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        TEST_BATCH_ID = data.get("batch_id")
        assert TEST_BATCH_ID is not None
        
        # Verify new fields are saved
        assert data.get("posizione") == "P01"
        assert data.get("n_pezzi") == 10
        assert data.get("numero_certificato") == "CERT-2026-001"
        assert data.get("ddt_numero") == "DDT-2026-001"
        assert data.get("disegno_numero") == "DIS-STR-01"
        print(f"Created batch {TEST_BATCH_ID} with new fields")
    
    def test_update_batch_new_fields(self, api_client):
        """PUT /api/fpc/batches/{id} updates new fields."""
        global TEST_BATCH_ID
        
        if not TEST_BATCH_ID:
            pytest.skip("No batch created")
        
        payload = {
            "supplier_name": "Acciaierie Pittini",
            "material_type": "S275JR",
            "heat_number": "COL-2026-001",
            "posizione": "P02",
            "n_pezzi": 20,
            "numero_certificato": "CERT-2026-002",
            "ddt_numero": "DDT-2026-002",
            "disegno_numero": "DIS-STR-02"
        }
        
        response = api_client.put(f"{BASE_URL}/api/fpc/batches/{TEST_BATCH_ID}", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "updated"
        print(f"Updated batch {TEST_BATCH_ID}")
    
    def test_get_batch_has_new_fields(self, api_client):
        """GET /api/fpc/batches/{id} returns new fields."""
        global TEST_BATCH_ID
        
        if not TEST_BATCH_ID:
            pytest.skip("No batch created")
        
        response = api_client.get(f"{BASE_URL}/api/fpc/batches/{TEST_BATCH_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("posizione") == "P02"
        assert data.get("n_pezzi") == 20
        assert data.get("numero_certificato") == "CERT-2026-002"
        assert data.get("ddt_numero") == "DDT-2026-002"
        print(f"Verified batch has new fields")


class TestSchedaRintracciabilitaPdf:
    """Test Scheda Rintracciabilità PDF endpoint."""
    
    def test_create_commessa_for_pdf_test(self, api_client):
        """Create commessa with material batches for PDF test."""
        global TEST_COMMESSA_ID, TEST_USER_ID
        
        # Create commessa
        payload = {
            "title": "Test Commessa Iter73 PDF",
            "numero": "COM-ITER73-001",
            "classe_esecuzione": "EXC2"
        }
        
        response = api_client.post(f"{BASE_URL}/api/commesse/", json=payload)
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        TEST_COMMESSA_ID = data.get("commessa_id")
        assert TEST_COMMESSA_ID is not None
        print(f"Created commessa {TEST_COMMESSA_ID}")
        
        # Create material batch linked to commessa
        import subprocess
        timestamp = int(time.time() * 1000)
        cmd = f'''mongosh --quiet --eval "
use('test_database');
db.material_batches.insertOne({{
  batch_id: 'bat_pdf_test_{timestamp}',
  commessa_id: '{TEST_COMMESSA_ID}',
  user_id: '{TEST_USER_ID}',
  supplier_name: 'Acciaierie Test',
  material_type: 'S355J2',
  heat_number: 'COL-PDF-TEST',
  dimensions: 'HEB 200',
  posizione: 'P01',
  n_pezzi: 5,
  numero_certificato: 'CERT-PDF-01',
  ddt_numero: 'DDT-PDF-01',
  created_at: new Date().toISOString()
}});
print('Batch created');
"'''
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(f"Material batch for PDF test: {result.stdout}")
    
    def test_scheda_rintracciabilita_pdf_endpoint(self, api_client):
        """GET /api/commesse/{cid}/scheda-rintracciabilita-pdf generates PDF."""
        global TEST_COMMESSA_ID
        
        if not TEST_COMMESSA_ID:
            pytest.skip("No commessa created")
        
        # Test the correct endpoint /api/commesse/{cid}/scheda-rintracciabilita-pdf
        response = api_client.get(f"{BASE_URL}/api/commesse/{TEST_COMMESSA_ID}/scheda-rintracciabilita-pdf")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get('content-type') == 'application/pdf'
        
        # Verify PDF content
        pdf_content = response.content
        assert len(pdf_content) > 0
        assert pdf_content[:4] == b'%PDF', "Response should be a PDF file"
        print(f"Generated Scheda Rintracciabilità PDF: {len(pdf_content)} bytes")
    
    def test_frontend_url_mismatch(self, api_client):
        """Check if frontend URL /api/commessa-ops/{cid}/scheda-rintracciabilita-pdf exists."""
        global TEST_COMMESSA_ID
        
        if not TEST_COMMESSA_ID:
            pytest.skip("No commessa created")
        
        # This tests the URL the frontend is currently using
        # It should return 404 because the router prefix is /commesse, not /commessa-ops
        response = api_client.get(f"{BASE_URL}/api/commessa-ops/{TEST_COMMESSA_ID}/scheda-rintracciabilita-pdf")
        
        # Document the mismatch - frontend uses /commessa-ops/ but backend has /commesse/
        if response.status_code == 404:
            print("WARNING: Frontend URL mismatch detected!")
            print(f"Frontend uses: /api/commessa-ops/{TEST_COMMESSA_ID}/scheda-rintracciabilita-pdf")
            print(f"Backend has: /api/commesse/{TEST_COMMESSA_ID}/scheda-rintracciabilita-pdf")
        
        # Just record the result, don't fail the test
        print(f"Frontend URL test result: {response.status_code}")


class TestProfileBaseExtraction:
    """Test _extract_profile_base function."""
    
    def test_extract_profile_base_function(self):
        """Test _extract_profile_base extracts base profile correctly."""
        # Import the function
        import sys
        sys.path.insert(0, '/app/backend')
        from routes.commessa_ops import _extract_profile_base
        
        # Test cases from requirements
        test_cases = [
            ("Trave IPE 100 in S275 JR", "IPE100"),
            ("IPE 100X55X4.1", "IPE100"),
            ("IPE 80X4.6X3.8", "IPE80"),
            ("HEB 200 S355 JR", "HEB200"),
            ("Tubo 60x60x3", "TUBO60"),
            ("UPN 120", "UPN120"),
            ("L 50x50x5", "L50"),
            ("HEA 160", "HEA160"),
            ("HEM 300", "HEM300"),
        ]
        
        for input_text, expected_output in test_cases:
            result = _extract_profile_base(input_text)
            assert result == expected_output, f"Failed for '{input_text}': expected '{expected_output}', got '{result}'"
            print(f"✓ _extract_profile_base('{input_text}') = '{result}'")


class TestCascadeDelete:
    """Test cascade delete removes lotti_cam by colata numbers."""
    
    def test_cascade_delete_by_colata(self, api_client):
        """Test that deleting a document cascades to lotti_cam by colata numbers."""
        global TEST_USER_ID, TEST_COMMESSA_ID
        
        if not TEST_COMMESSA_ID:
            pytest.skip("No commessa created")
        
        import subprocess
        timestamp = int(time.time() * 1000)
        doc_id = f"doc_cascade_test_{timestamp}"
        colata_number = f"COLATA-CASCADE-{timestamp}"
        
        # Create a certificate document with metadata containing colata
        cmd = f'''mongosh --quiet --eval "
use('test_database');
db.commessa_documents.insertOne({{
  doc_id: '{doc_id}',
  commessa_id: '{TEST_COMMESSA_ID}',
  user_id: '{TEST_USER_ID}',
  nome_file: 'test_cert.pdf',
  tipo: 'certificato_31',
  content_type: 'application/pdf',
  file_base64: 'dGVzdA==',
  size_bytes: 4,
  metadata_estratti: {{
    fornitore: 'Test Fornitore',
    numero_colata: '{colata_number}',
    profili: [
      {{numero_colata: '{colata_number}', dimensioni: 'IPE 100', qualita_acciaio: 'S275JR'}}
    ]
  }},
  uploaded_at: new Date().toISOString(),
  uploaded_by: 'Test'
}});
db.lotti_cam.insertOne({{
  lotto_id: 'lotto_cascade_{timestamp}',
  commessa_id: '{TEST_COMMESSA_ID}',
  user_id: '{TEST_USER_ID}',
  descrizione: 'IPE 100',
  numero_colata: '{colata_number}',
  qualita_acciaio: 'S275JR',
  source_doc_id: '{doc_id}',
  created_at: new Date().toISOString()
}});
print('Test data created');
"'''
        subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(f"Created test document {doc_id} with colata {colata_number}")
        
        # Verify lotto exists before delete
        check_cmd = f'''mongosh --quiet --eval "
use('test_database');
var count = db.lotti_cam.countDocuments({{numero_colata: '{colata_number}', commessa_id: '{TEST_COMMESSA_ID}'}});
print(count);
"'''
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        count_before = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        assert count_before >= 1, f"Expected at least 1 lotto before delete, got {count_before}"
        print(f"Lotti before delete: {count_before}")
        
        # Delete the document via API
        response = api_client.delete(f"{BASE_URL}/api/commesse/{TEST_COMMESSA_ID}/documenti/{doc_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Delete response: {data}")
        
        # Verify lotto was cascade deleted
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        count_after = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        print(f"Lotti after delete: {count_after}")
        
        # The cascade should have deleted the lotto
        assert count_after < count_before, f"Expected cascade delete to reduce lotti count from {count_before} to less, got {count_after}"
        print("✓ Cascade delete by colata verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
