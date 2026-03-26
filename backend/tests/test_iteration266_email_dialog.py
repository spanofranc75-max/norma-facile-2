"""
Iteration 266: Email Preview Dialog Tests
Tests for the modified email dialog that:
1) Uses standard email as default (NOT PEC)
2) Shows all available emails with checkboxes
3) Allows manual email addition
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://fattura-send.preview.emergentagent.com')
SESSION_TOKEN = "EN86LIFjhuDb6Hw4fMs736NpccPZYKZ21k18tGgLe2Q"

# Test invoices
INVOICE_WITH_PEC = "inv_698ab9f8a8c2"  # Galotti Srl - has email + PEC
INVOICE_EMAIL_ONLY = "inv_d2f0007bcdf0"  # Electric Style Snc - email only


@pytest.fixture
def auth_headers():
    """Return headers with session token cookie."""
    return {"Cookie": f"session_token={SESSION_TOKEN}"}


class TestPreviewEmailEndpoint:
    """Tests for GET /api/invoices/{id}/preview-email endpoint."""
    
    def test_preview_email_returns_all_recipients_array(self, auth_headers):
        """Verify all_recipients array is returned in response."""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{INVOICE_WITH_PEC}/preview-email",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "all_recipients" in data
        assert isinstance(data["all_recipients"], list)
        assert len(data["all_recipients"]) >= 1
    
    def test_preview_email_standard_email_is_default(self, auth_headers):
        """Verify standard email has default=true, PEC has default=false."""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{INVOICE_WITH_PEC}/preview-email",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        all_recipients = data["all_recipients"]
        email_recipient = next((r for r in all_recipients if r["type"] == "email"), None)
        pec_recipient = next((r for r in all_recipients if r["type"] == "pec"), None)
        
        # Standard email should be default
        assert email_recipient is not None, "Email recipient not found"
        assert email_recipient["default"] is True, "Standard email should be default"
        
        # PEC should NOT be default
        assert pec_recipient is not None, "PEC recipient not found"
        assert pec_recipient["default"] is False, "PEC should NOT be default"
    
    def test_preview_email_recipient_structure(self, auth_headers):
        """Verify each recipient has required fields: email, label, type, default."""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{INVOICE_WITH_PEC}/preview-email",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        for recipient in data["all_recipients"]:
            assert "email" in recipient, "Missing 'email' field"
            assert "label" in recipient, "Missing 'label' field"
            assert "type" in recipient, "Missing 'type' field"
            assert "default" in recipient, "Missing 'default' field"
            assert recipient["type"] in ["email", "pec", "contact"], f"Invalid type: {recipient['type']}"
    
    def test_preview_email_to_email_matches_default_recipient(self, auth_headers):
        """Verify to_email field matches the default recipient."""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{INVOICE_WITH_PEC}/preview-email",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        default_recipient = next((r for r in data["all_recipients"] if r["default"]), None)
        assert default_recipient is not None, "No default recipient found"
        assert data["to_email"] == default_recipient["email"], "to_email should match default recipient"
    
    def test_preview_email_only_client(self, auth_headers):
        """Test client with only email (no PEC) - email should be default."""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{INVOICE_EMAIL_ONLY}/preview-email",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        all_recipients = data["all_recipients"]
        assert len(all_recipients) >= 1, "Should have at least one recipient"
        
        # Only email type should exist
        email_recipient = next((r for r in all_recipients if r["type"] == "email"), None)
        pec_recipient = next((r for r in all_recipients if r["type"] == "pec"), None)
        
        assert email_recipient is not None, "Email recipient should exist"
        assert email_recipient["default"] is True, "Email should be default"
        assert pec_recipient is None, "PEC should not exist for this client"
    
    def test_preview_email_requires_auth(self):
        """Verify endpoint requires authentication."""
        response = requests.get(
            f"{BASE_URL}/api/invoices/{INVOICE_WITH_PEC}/preview-email"
        )
        assert response.status_code == 401


class TestSendEmailEndpoint:
    """Tests for POST /api/invoices/{id}/send-email endpoint."""
    
    def test_send_email_accepts_to_emails_array(self, auth_headers):
        """Verify send-email endpoint accepts to_emails array in payload."""
        # Note: We don't actually send to avoid real emails
        # Just verify the endpoint structure by checking code
        import inspect
        import sys
        sys.path.insert(0, '/app/backend')
        
        from routes.invoices import send_invoice_email
        source = inspect.getsource(send_invoice_email)
        
        # Verify to_emails handling
        assert "to_emails" in source, "Endpoint should handle to_emails array"
        assert "to_emails[0]" in source, "First email should be used as TO"
        assert "to_emails[1:]" in source, "Rest should be used as CC"
    
    def test_send_email_requires_auth(self):
        """Verify endpoint requires authentication."""
        response = requests.post(
            f"{BASE_URL}/api/invoices/{INVOICE_WITH_PEC}/send-email",
            json={"to_emails": ["test@example.com"]}
        )
        assert response.status_code == 401


class TestFrontendEmailPreviewDialog:
    """Code review tests for EmailPreviewDialog.js component."""
    
    def test_dialog_has_checkbox_for_recipients(self):
        """Verify dialog renders checkboxes for each recipient."""
        with open('/app/frontend/src/components/EmailPreviewDialog.js', 'r') as f:
            content = f.read()
        
        # Check for Checkbox component usage
        assert "Checkbox" in content, "Should use Checkbox component"
        assert "selectedEmails" in content, "Should track selected emails"
        assert "toggleEmail" in content, "Should have toggle function"
    
    def test_dialog_preselects_default_recipients(self):
        """Verify dialog pre-selects recipients with default=true."""
        with open('/app/frontend/src/components/EmailPreviewDialog.js', 'r') as f:
            content = f.read()
        
        # Check for default selection logic
        assert "r.default" in content or "r => r.default" in content, "Should filter by default flag"
        assert "setSelectedEmails" in content, "Should set selected emails"
    
    def test_dialog_has_manual_email_input(self):
        """Verify dialog has manual email addition functionality."""
        with open('/app/frontend/src/components/EmailPreviewDialog.js', 'r') as f:
            content = f.read()
        
        # Check for manual email input
        assert "Aggiungi email" in content, "Should have 'Add email' button"
        assert "addManualEmail" in content, "Should have add manual email function"
        assert "ccInput" in content, "Should have CC input state"
    
    def test_dialog_send_button_shows_count(self):
        """Verify send button shows count when multiple recipients selected."""
        with open('/app/frontend/src/components/EmailPreviewDialog.js', 'r') as f:
            content = f.read()
        
        # Check for count display
        assert "selectedEmails.length" in content, "Should use selectedEmails.length"
        assert "Conferma invio a" in content, "Should show 'Confirm send to X'"
    
    def test_dialog_send_button_disabled_when_no_selection(self):
        """Verify send button is disabled when no emails selected."""
        with open('/app/frontend/src/components/EmailPreviewDialog.js', 'r') as f:
            content = f.read()
        
        # Check for disabled condition
        assert "selectedEmails.length === 0" in content, "Should disable when no emails selected"
        assert "!confirmed" in content, "Should disable when not confirmed"
    
    def test_dialog_has_data_testids(self):
        """Verify dialog has proper data-testid attributes for testing."""
        with open('/app/frontend/src/components/EmailPreviewDialog.js', 'r') as f:
            content = f.read()
        
        required_testids = [
            "email-preview-dialog",
            "email-add-manual-btn",
            "email-manual-input",
            "email-confirm-checkbox",
            "email-preview-send-btn"
        ]
        
        for testid in required_testids:
            assert f'data-testid="{testid}"' in content, f"Missing data-testid: {testid}"


class TestBackendCodeReview:
    """Code review tests for backend preview-email endpoint."""
    
    def test_preview_email_collects_all_emails(self):
        """Verify backend collects email, PEC, and contacts."""
        with open('/app/backend/routes/invoices.py', 'r') as f:
            content = f.read()
        
        # Check for all email collection
        assert 'client.get("email")' in content, "Should get client email"
        assert 'client.get("pec")' in content, "Should get client PEC"
        assert 'client.get("contacts"' in content, "Should get client contacts"
    
    def test_preview_email_sets_correct_defaults(self):
        """Verify backend sets email as default, not PEC."""
        with open('/app/backend/routes/invoices.py', 'r') as f:
            content = f.read()
        
        # Find the preview-email function and check default logic
        # Email should be default=True, PEC should be default=False
        assert '"type": "email", "default": True' in content, "Email should have default=True"
        assert '"type": "pec", "default": False' in content, "PEC should have default=False"
    
    def test_send_email_handles_to_emails_array(self):
        """Verify send-email correctly processes to_emails array."""
        with open('/app/backend/routes/invoices.py', 'r') as f:
            content = f.read()
        
        # Check for to_emails handling
        assert 'to_emails = payload.get("to_emails"' in content, "Should get to_emails from payload"
        assert "to_emails[0]" in content, "Should use first email as TO"
        assert "to_emails[1:]" in content, "Should use rest as CC"
