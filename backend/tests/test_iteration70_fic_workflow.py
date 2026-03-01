"""
Test Suite for Iteration 70: Fatture in Cloud Integration, AI Certificate Fallback, SDI Workflow
Tests the FIC credentials, company settings, and AI certificate parsing with fallback logic.
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test data prefix for cleanup
TEST_PREFIX = "TEST_ITER70_"


class TestHealthAndBasics:
    """Basic health check and API availability tests."""

    def test_health_endpoint(self):
        """Test GET /api/health returns healthy status."""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        assert "service" in data
        print(f"Health check passed: {data}")


class TestCompanySettingsFICFields:
    """Test Fatture in Cloud fields in company settings."""

    @pytest.fixture(autouse=True)
    def setup_test_session(self):
        """Create test user and session."""
        self.session_token = f"test_session_iter70_{uuid.uuid4().hex[:12]}"
        self.user_id = f"test-user-iter70-{uuid.uuid4().hex[:12]}"
        
        # Create test user via MongoDB
        import subprocess
        create_user = f'''
        mongosh --quiet --eval "
        use('test_database');
        db.users.insertOne({{
          user_id: '{self.user_id}',
          email: '{TEST_PREFIX}user_{uuid.uuid4().hex[:8]}@test.com',
          name: 'Test User Iter70',
          created_at: new Date()
        }});
        db.user_sessions.insertOne({{
          user_id: '{self.user_id}',
          session_token: '{self.session_token}',
          expires_at: new Date(Date.now() + 7*24*60*60*1000),
          created_at: new Date()
        }});
        "
        '''
        result = subprocess.run(create_user, shell=True, capture_output=True, text=True)
        assert result.returncode == 0, f"Failed to create test user: {result.stderr}"
        
        self.headers = {
            "Authorization": f"Bearer {self.session_token}",
            "Content-Type": "application/json",
        }
        
        yield
        
        # Cleanup
        cleanup = f'''
        mongosh --quiet --eval "
        use('test_database');
        db.users.deleteOne({{user_id: '{self.user_id}'}});
        db.user_sessions.deleteOne({{session_token: '{self.session_token}'}});
        db.company_settings.deleteOne({{user_id: '{self.user_id}'}});
        "
        '''
        subprocess.run(cleanup, shell=True, capture_output=True)

    def test_get_company_settings_unauthenticated(self):
        """Test GET /api/company/settings without auth returns 401."""
        response = requests.get(f"{BASE_URL}/api/company/settings")
        assert response.status_code == 401
        print("Unauthenticated request correctly returned 401")

    def test_get_company_settings_empty(self):
        """Test GET /api/company/settings returns empty settings for new user."""
        response = requests.get(
            f"{BASE_URL}/api/company/settings",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should return empty/default settings
        assert "business_name" in data or data == {} or data.get("business_name") == ""
        print(f"Empty settings returned: {list(data.keys()) if data else 'empty'}")

    def test_put_company_settings_with_fic_fields(self):
        """Test PUT /api/company/settings accepts FIC fields."""
        settings_payload = {
            "business_name": f"{TEST_PREFIX}Test Company",
            "partita_iva": "IT12345678901",
            "codice_fiscale": "12345678901",
            "fic_company_id": "1234567",
            "fic_access_token": "test_fic_token_12345",
            "address": "Via Test 123",
            "city": "Roma",
            "cap": "00100",
            "province": "RM",
        }
        
        response = requests.put(
            f"{BASE_URL}/api/company/settings",
            headers=self.headers,
            json=settings_payload
        )
        
        assert response.status_code == 200, f"Failed to update settings: {response.text}"
        
        # Verify saved data
        get_response = requests.get(
            f"{BASE_URL}/api/company/settings",
            headers=self.headers
        )
        assert get_response.status_code == 200
        saved = get_response.json()
        
        # Verify FIC fields are saved
        assert saved.get("fic_company_id") == "1234567", f"fic_company_id not saved: {saved}"
        assert saved.get("fic_access_token") == "test_fic_token_12345", f"fic_access_token not saved: {saved}"
        assert saved.get("business_name") == f"{TEST_PREFIX}Test Company"
        print(f"FIC fields saved correctly: fic_company_id={saved.get('fic_company_id')}")


class TestInvoiceSDIEndpoints:
    """Test SDI-related invoice endpoints with FIC integration."""

    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Create test user, client, and invoice."""
        self.session_token = f"test_session_sdi70_{uuid.uuid4().hex[:12]}"
        self.user_id = f"test-user-sdi70-{uuid.uuid4().hex[:12]}"
        self.client_id = f"cli_{uuid.uuid4().hex[:12]}"
        self.invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
        
        import subprocess
        create_data = f'''
        mongosh --quiet --eval "
        use('test_database');
        db.users.insertOne({{
          user_id: '{self.user_id}',
          email: '{TEST_PREFIX}sdi_user@test.com',
          name: 'Test SDI User',
          created_at: new Date()
        }});
        db.user_sessions.insertOne({{
          user_id: '{self.user_id}',
          session_token: '{self.session_token}',
          expires_at: new Date(Date.now() + 7*24*60*60*1000),
          created_at: new Date()
        }});
        db.clients.insertOne({{
          client_id: '{self.client_id}',
          user_id: '{self.user_id}',
          business_name: '{TEST_PREFIX}SDI Client',
          partita_iva: 'IT98765432109',
          codice_fiscale: 'RSSMRA80A01H501U',
          codice_sdi: '0000000',
          address: 'Via Cliente 1',
          city: 'Milano',
          cap: '20100',
          province: 'MI',
          created_at: new Date()
        }});
        db.invoices.insertOne({{
          invoice_id: '{self.invoice_id}',
          user_id: '{self.user_id}',
          client_id: '{self.client_id}',
          document_type: 'FT',
          document_number: 'FT-2026/TEST001',
          status: 'emessa',
          issue_date: '2026-01-15',
          totals: {{
            subtotal: 1000,
            total_vat: 220,
            total_document: 1220
          }},
          lines: [{{
            line_id: 'ln_test1',
            description: 'Test Service',
            quantity: 1,
            unit_price: 1000,
            vat_rate: '22',
            line_total: 1000,
            vat_amount: 220
          }}],
          created_at: new Date()
        }});
        "
        '''
        result = subprocess.run(create_data, shell=True, capture_output=True, text=True)
        assert result.returncode == 0, f"Failed to create test data: {result.stderr}"
        
        self.headers = {
            "Authorization": f"Bearer {self.session_token}",
            "Content-Type": "application/json",
        }
        
        yield
        
        # Cleanup
        cleanup = f'''
        mongosh --quiet --eval "
        use('test_database');
        db.users.deleteOne({{user_id: '{self.user_id}'}});
        db.user_sessions.deleteOne({{session_token: '{self.session_token}'}});
        db.clients.deleteOne({{client_id: '{self.client_id}'}});
        db.invoices.deleteOne({{invoice_id: '{self.invoice_id}'}});
        db.company_settings.deleteOne({{user_id: '{self.user_id}'}});
        "
        '''
        subprocess.run(cleanup, shell=True, capture_output=True)

    def test_send_sdi_without_fic_credentials(self):
        """Test POST /api/invoices/{id}/send-sdi returns proper error when FIC credentials missing."""
        # First set up company settings without FIC credentials
        settings_payload = {
            "business_name": f"{TEST_PREFIX}SDI Test Company",
            "partita_iva": "IT12345678901",
        }
        requests.put(
            f"{BASE_URL}/api/company/settings",
            headers=self.headers,
            json=settings_payload
        )
        
        # Try to send to SDI
        response = requests.post(
            f"{BASE_URL}/api/invoices/{self.invoice_id}/send-sdi",
            headers=self.headers
        )
        
        # Should return 400 with clear FIC-related error (not Aruba error)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        error_msg = data.get("detail", "")
        # Should mention Fatture in Cloud, not Aruba
        assert "Fatture in Cloud" in error_msg or "fic" in error_msg.lower() or "credenziali" in error_msg.lower(), \
            f"Error should mention FIC credentials: {error_msg}"
        print(f"SDI send correctly returned FIC credentials error: {error_msg}")

    def test_stato_sdi_without_fic_credentials(self):
        """Test GET /api/invoices/{id}/stato-sdi returns proper error when FIC credentials missing."""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{self.invoice_id}/stato-sdi",
            headers=self.headers
        )
        
        # Should return 400 because document not yet synced with FIC
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        error_msg = data.get("detail", "")
        # Should be clear about the issue (FIC credentials or not synced)
        assert "Cloud" in error_msg or "sincronizzato" in error_msg or "credential" in error_msg.lower(), \
            f"Error should be about FIC: {error_msg}"
        print(f"Stato SDI correctly returned error: {error_msg}")


class TestCAMReportAuth:
    """Test CAM report endpoint authentication."""

    def test_cam_report_aziendale_requires_auth(self):
        """Test GET /api/cam/report-aziendale returns 401/403 without token."""
        response = requests.get(f"{BASE_URL}/api/cam/report-aziendale")
        assert response.status_code in [401, 403], \
            f"Expected 401/403 for unauthenticated request, got {response.status_code}: {response.text}"
        print(f"CAM report correctly requires auth: {response.status_code}")


class TestCommessaOps:
    """Test commessa operations endpoints."""

    @pytest.fixture(autouse=True)
    def setup_commessa(self):
        """Create test user and commessa."""
        self.session_token = f"test_session_commessa70_{uuid.uuid4().hex[:12]}"
        self.user_id = f"test-user-commessa70-{uuid.uuid4().hex[:12]}"
        self.commessa_id = f"comm_{uuid.uuid4().hex[:12]}"
        
        import subprocess
        create_data = f'''
        mongosh --quiet --eval "
        use('test_database');
        db.users.insertOne({{
          user_id: '{self.user_id}',
          email: '{TEST_PREFIX}commessa_user@test.com',
          name: 'Test Commessa User',
          created_at: new Date()
        }});
        db.user_sessions.insertOne({{
          user_id: '{self.user_id}',
          session_token: '{self.session_token}',
          expires_at: new Date(Date.now() + 7*24*60*60*1000),
          created_at: new Date()
        }});
        db.commesse.insertOne({{
          commessa_id: '{self.commessa_id}',
          user_id: '{self.user_id}',
          numero: '{TEST_PREFIX}001',
          title: 'Test Commessa',
          cliente_nome: 'Test Client',
          normativa: 'EN_1090',
          status: 'in_corso',
          created_at: new Date(),
          updated_at: new Date()
        }});
        "
        '''
        result = subprocess.run(create_data, shell=True, capture_output=True, text=True)
        assert result.returncode == 0, f"Failed to create test data: {result.stderr}"
        
        self.headers = {
            "Authorization": f"Bearer {self.session_token}",
            "Content-Type": "application/json",
        }
        
        yield
        
        # Cleanup
        cleanup = f'''
        mongosh --quiet --eval "
        use('test_database');
        db.users.deleteOne({{user_id: '{self.user_id}'}});
        db.user_sessions.deleteOne({{session_token: '{self.session_token}'}});
        db.commesse.deleteOne({{commessa_id: '{self.commessa_id}'}});
        db.commessa_documents.deleteMany({{commessa_id: '{self.commessa_id}'}});
        db.lotti_cam.deleteMany({{commessa_id: '{self.commessa_id}'}});
        db.material_batches.deleteMany({{commessa_id: '{self.commessa_id}'}});
        "
        '''
        subprocess.run(cleanup, shell=True, capture_output=True)

    def test_get_commessa_ops(self):
        """Test GET /api/commesse/{id}/ops returns proper structure."""
        response = requests.get(
            f"{BASE_URL}/api/commesse/{self.commessa_id}/ops",
            headers=self.headers
        )
        
        # This endpoint may return 200 with ops data or 404 if ops not initialized
        assert response.status_code in [200, 404], \
            f"Expected 200 or 404, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            # Should have ops-related fields
            print(f"Commessa ops returned: {list(data.keys())}")
        else:
            print("Commessa ops endpoint returned 404 (ops not yet initialized)")


class TestAICertificateFallbackLogic:
    """Test the AI certificate parsing fallback logic.
    
    This tests the bug fix where unmatched profiles should be assigned to 
    the current commessa instead of being archived.
    """

    @pytest.fixture(autouse=True)
    def setup_for_certificate_test(self):
        """Create test user, commessa, and document for certificate testing."""
        self.session_token = f"test_session_cert70_{uuid.uuid4().hex[:12]}"
        self.user_id = f"test-user-cert70-{uuid.uuid4().hex[:12]}"
        self.commessa_id = f"comm_cert_{uuid.uuid4().hex[:12]}"
        self.doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        
        import subprocess
        import base64
        
        # Create a simple test image (1x1 white pixel PNG)
        test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        create_data = f'''
        mongosh --quiet --eval "
        use('test_database');
        db.users.insertOne({{
          user_id: '{self.user_id}',
          email: '{TEST_PREFIX}cert_user@test.com',
          name: 'Test Cert User',
          created_at: new Date()
        }});
        db.user_sessions.insertOne({{
          user_id: '{self.user_id}',
          session_token: '{self.session_token}',
          expires_at: new Date(Date.now() + 7*24*60*60*1000),
          created_at: new Date()
        }});
        db.commesse.insertOne({{
          commessa_id: '{self.commessa_id}',
          user_id: '{self.user_id}',
          numero: '{TEST_PREFIX}CERT001',
          title: 'Test Commessa for Certificate',
          cliente_nome: 'Test Client',
          normativa: 'EN_1090',
          status: 'in_corso',
          approvvigionamento: {{
            richieste: [],
            ordini: [],
            arrivi: []
          }},
          created_at: new Date(),
          updated_at: new Date()
        }});
        db.commessa_documents.insertOne({{
          doc_id: '{self.doc_id}',
          commessa_id: '{self.commessa_id}',
          user_id: '{self.user_id}',
          nome_file: 'test_certificate.png',
          tipo: 'certificato_31',
          content_type: 'image/png',
          file_base64: '{test_image_b64}',
          size_bytes: 67,
          uploaded_at: new Date().toISOString()
        }});
        "
        '''
        result = subprocess.run(create_data, shell=True, capture_output=True, text=True)
        assert result.returncode == 0, f"Failed to create test data: {result.stderr}"
        
        self.headers = {
            "Authorization": f"Bearer {self.session_token}",
            "Content-Type": "application/json",
        }
        
        yield
        
        # Cleanup
        cleanup = f'''
        mongosh --quiet --eval "
        use('test_database');
        db.users.deleteOne({{user_id: '{self.user_id}'}});
        db.user_sessions.deleteOne({{session_token: '{self.session_token}'}});
        db.commesse.deleteOne({{commessa_id: '{self.commessa_id}'}});
        db.commessa_documents.deleteMany({{commessa_id: '{self.commessa_id}'}});
        db.lotti_cam.deleteMany({{commessa_id: '{self.commessa_id}'}});
        db.material_batches.deleteMany({{commessa_id: '{self.commessa_id}'}});
        db.archivio_certificati.deleteMany({{user_id: '{self.user_id}'}});
        "
        '''
        subprocess.run(cleanup, shell=True, capture_output=True)

    def test_fallback_logic_code_review(self):
        """Verify the fallback logic exists in commessa_ops.py code.
        
        This is a code review test - we verify the fix is in place by checking
        that the fallback logic assigns to current_commessa_id when no match found.
        """
        import subprocess
        
        # Check if the fallback code exists
        check_code = '''
        grep -A5 "FALLBACK: If no match found" /app/backend/routes/commessa_ops.py
        '''
        result = subprocess.run(check_code, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "Fallback code comment not found"
        assert "current_commessa_id" in result.stdout, "Fallback should assign to current_commessa_id"
        assert "matched_commessa_id = current_commessa_id" in result.stdout, \
            "Fallback assignment not found"
        print(f"Fallback logic verified in code:\n{result.stdout}")

    def test_match_profili_function_exists(self):
        """Verify _match_profili_to_commesse function exists and has correct signature."""
        import subprocess
        
        check_function = '''
        grep -n "_match_profili_to_commesse" /app/backend/routes/commessa_ops.py | head -5
        '''
        result = subprocess.run(check_function, shell=True, capture_output=True, text=True)
        
        assert result.returncode == 0, "Function not found"
        assert "_match_profili_to_commesse" in result.stdout
        print(f"Function found at:\n{result.stdout}")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
