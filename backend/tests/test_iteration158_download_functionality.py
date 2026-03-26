"""
Iteration 158 - Download Functionality Tests
Tests for verifying file download endpoints (PDF, XML, Backup) work correctly
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://fatture-v2.preview.emergentagent.com').rstrip('/')

# Test session token and user ID created for this test run
TEST_SESSION_TOKEN = "test_session_1772904459711"
TEST_USER_ID = "test-user-1772904459711"
TEST_INVOICE_ID = "inv_7f9b4517f772"
TEST_CLIENT_ID = "cli_592d6ab29c62"


@pytest.fixture
def authenticated_session():
    """Create a requests session with authentication cookie."""
    session = requests.Session()
    session.cookies.set('session_token', TEST_SESSION_TOKEN)
    session.headers.update({'Content-Type': 'application/json'})
    return session


class TestAuthEndpoints:
    """Basic authentication verification."""
    
    def test_auth_me_returns_user(self, authenticated_session):
        """Test /api/auth/me returns user data with valid session."""
        response = authenticated_session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == TEST_USER_ID
        assert "email" in data
        print(f"✓ Auth endpoint returned user: {data['email']}")


class TestInvoiceListEndpoints:
    """Test invoice listing endpoint."""
    
    def test_get_invoices_list(self, authenticated_session):
        """Test /api/invoices/ returns invoice list."""
        response = authenticated_session.get(f"{BASE_URL}/api/invoices/")
        assert response.status_code == 200
        data = response.json()
        assert "invoices" in data
        assert "total" in data
        assert data["total"] >= 1, "Expected at least 1 test invoice"
        print(f"✓ Found {data['total']} invoices")


class TestPDFDownloadEndpoint:
    """Test PDF download functionality."""
    
    def test_pdf_download_returns_200(self, authenticated_session):
        """Test /api/invoices/{id}/pdf returns PDF with 200 status."""
        response = authenticated_session.get(
            f"{BASE_URL}/api/invoices/{TEST_INVOICE_ID}/pdf",
            stream=True
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "application/pdf" in response.headers.get("Content-Type", "")
        
        # Verify it's a valid PDF by checking magic bytes
        content = response.content
        assert content[:4] == b'%PDF', "Response does not start with PDF magic bytes"
        assert len(content) > 1000, f"PDF seems too small: {len(content)} bytes"
        print(f"✓ PDF download successful: {len(content)} bytes")
    
    def test_pdf_download_nonexistent_invoice_returns_404(self, authenticated_session):
        """Test PDF download returns 404 for non-existent invoice."""
        response = authenticated_session.get(
            f"{BASE_URL}/api/invoices/inv_nonexistent123/pdf"
        )
        assert response.status_code == 404
        print("✓ Non-existent invoice correctly returns 404")


class TestXMLDownloadEndpoint:
    """Test XML (FatturaPA) download functionality."""
    
    def test_xml_download_returns_200(self, authenticated_session):
        """Test /api/invoices/{id}/xml returns XML with 200 status."""
        response = authenticated_session.get(
            f"{BASE_URL}/api/invoices/{TEST_INVOICE_ID}/xml"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "application/xml" in response.headers.get("Content-Type", "")
        
        # Verify it's valid XML
        content = response.text
        assert content.startswith("<?xml"), "Response does not start with XML declaration"
        assert "FatturaElettronica" in content, "Response does not contain FatturaElettronica"
        print(f"✓ XML download successful: {len(content)} chars")
    
    def test_xml_download_nonexistent_invoice_returns_404(self, authenticated_session):
        """Test XML download returns 404 for non-existent invoice."""
        response = authenticated_session.get(
            f"{BASE_URL}/api/invoices/inv_nonexistent123/xml"
        )
        assert response.status_code == 404
        print("✓ Non-existent invoice correctly returns 404")


class TestBackupExportEndpoint:
    """Test backup export functionality."""
    
    def test_backup_export_returns_200(self, authenticated_session):
        """Test /api/admin/backup/export returns JSON backup with 200 status."""
        response = authenticated_session.get(f"{BASE_URL}/api/admin/backup/export")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "application/json" in response.headers.get("Content-Type", "")
        
        # Verify backup structure
        data = response.json()
        assert "metadata" in data
        assert "data" in data
        assert "stats" in data
        assert data["metadata"]["app"] == "Norma Facile 2.0"
        assert data["metadata"]["version"] == "2.0"
        print(f"✓ Backup export successful: {data['metadata']['total_records']} records")
    
    def test_backup_last_returns_info(self, authenticated_session):
        """Test /api/admin/backup/last returns last backup info."""
        response = authenticated_session.get(f"{BASE_URL}/api/admin/backup/last")
        assert response.status_code == 200
        data = response.json()
        assert "last_backup" in data
        if data["last_backup"]:
            assert "date" in data["last_backup"]
            print(f"✓ Last backup: {data['last_backup']['date']}")
        else:
            print("✓ No previous backup (expected for new test user)")
    
    def test_backup_stats_returns_counts(self, authenticated_session):
        """Test /api/admin/backup/stats returns collection counts."""
        response = authenticated_session.get(f"{BASE_URL}/api/admin/backup/stats")
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert "total" in data
        print(f"✓ Backup stats: {data['total']} total records")


class TestCompanySettingsEndpoint:
    """Test company settings (required for XML export)."""
    
    def test_company_settings_get(self, authenticated_session):
        """Test /api/company/settings returns company data."""
        response = authenticated_session.get(f"{BASE_URL}/api/company/settings")
        assert response.status_code == 200
        data = response.json()
        assert "business_name" in data
        assert "partita_iva" in data
        print(f"✓ Company settings: {data.get('business_name', 'N/A')}")


class TestFrontendCodePattern:
    """Verify the download code pattern in frontend files."""
    
    def test_invoices_page_uses_correct_download_pattern(self):
        """Verify InvoicesPage.js uses document.createElement instead of window.top."""
        with open('/app/frontend/src/pages/InvoicesPage.js', 'r') as f:
            content = f.read()
        
        # Check correct pattern is used
        assert "document.createElement('a')" in content, "Missing document.createElement('a')"
        assert "document.body.appendChild(a)" in content, "Missing document.body.appendChild(a)"
        
        # Check that window.top is NOT used for downloads
        assert "window.top.document" not in content, "Found window.top.document - should not be used in iframe"
        
        print("✓ InvoicesPage.js uses correct download pattern")
    
    def test_settings_page_uses_correct_download_pattern(self):
        """Verify SettingsPage.js uses document.createElement instead of window.top."""
        with open('/app/frontend/src/pages/SettingsPage.js', 'r') as f:
            content = f.read()
        
        # Check correct pattern is used
        assert "document.createElement('a')" in content, "Missing document.createElement('a')"
        assert "document.body.appendChild(a)" in content, "Missing document.body.appendChild(a)"
        
        # Check that window.top is NOT used for downloads
        assert "window.top.document" not in content, "Found window.top.document - should not be used in iframe"
        
        # Check for the comment indicating the fix
        assert "USA document corrente" in content or "NON window.top" in content, "Missing fix comment"
        
        print("✓ SettingsPage.js uses correct download pattern")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
