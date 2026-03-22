"""
Iteration 237 — Pacchetti Documentali D4+D5 Testing
====================================================
D4: POST /api/pacchetti-documentali/{id}/prepara-invio - Generate email draft + attachments + warnings
D5: POST /api/pacchetti-documentali/{id}/invia - Send email via Resend + log
D5: GET /api/pacchetti-documentali/{id}/invii - Get send history
PATCH /api/pacchetti-documentali/{id} - Update recipient/label

Tests:
- D1-D3 regression (quick sanity checks)
- D4 prepara-invio endpoint
- D5 invia endpoint (with graceful error handling if Resend not configured)
- D5 invii history endpoint
- PATCH update recipient
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "BccyJvnOyrPXRRYy4GfxR5osuF51RWcYWWnUUoHx434"
USER_ID = "user_6988e9b9316c"


@pytest.fixture
def auth_headers():
    """Return headers with Bearer token for authenticated requests."""
    return {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def auth_headers_form():
    """Return headers for form-data requests (no Content-Type, let requests set it)."""
    return {
        "Authorization": f"Bearer {AUTH_TOKEN}"
    }


# ═══════════════════════════════════════════════════════════════
#  D1-D3 REGRESSION TESTS (Quick sanity checks)
# ═══════════════════════════════════════════════════════════════

class TestD1D3Regression:
    """Quick regression tests for D1-D3 features."""
    
    def test_get_tipi_documento(self, auth_headers):
        """GET /api/documenti/tipi should return document types."""
        response = requests.get(f"{BASE_URL}/api/documenti/tipi", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        tipi = response.json()
        assert isinstance(tipi, list), "Response should be a list"
        assert len(tipi) >= 20, f"Expected at least 20 document types, got {len(tipi)}"
        print(f"PASSED: GET /api/documenti/tipi returned {len(tipi)} types")
    
    def test_get_templates(self, auth_headers):
        """GET /api/pacchetti-documentali/templates should return templates."""
        response = requests.get(f"{BASE_URL}/api/pacchetti-documentali/templates", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        templates = response.json()
        assert isinstance(templates, list), "Response should be a list"
        assert len(templates) >= 5, f"Expected at least 5 templates, got {len(templates)}"
        print(f"PASSED: GET /api/pacchetti-documentali/templates returned {len(templates)} templates")
    
    def test_list_pacchetti(self, auth_headers):
        """GET /api/pacchetti-documentali should return packages list."""
        response = requests.get(f"{BASE_URL}/api/pacchetti-documentali", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        pacchetti = response.json()
        assert isinstance(pacchetti, list), "Response should be a list"
        print(f"PASSED: GET /api/pacchetti-documentali returned {len(pacchetti)} packages")


# ═══════════════════════════════════════════════════════════════
#  D4 — PREPARA INVIO TESTS
# ═══════════════════════════════════════════════════════════════

class TestD4PreparaInvio:
    """D4: Test prepara-invio endpoint for email draft generation."""
    
    @pytest.fixture
    def test_package(self, auth_headers):
        """Create a test package for D4/D5 testing."""
        # Create package from QUALIFICA_FORNITORE template (simpler, azienda only)
        create_data = {
            "template_code": "QUALIFICA_FORNITORE",
            "label": f"TEST_D4D5_Package_{datetime.now().strftime('%H%M%S')}"
        }
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali",
            headers=auth_headers,
            json=create_data
        )
        assert response.status_code == 200, f"Failed to create test package: {response.text}"
        pack = response.json()
        print(f"Created test package: {pack['pack_id']}")
        return pack
    
    def test_prepara_invio_returns_email_draft(self, auth_headers, test_package):
        """POST /api/pacchetti-documentali/{id}/prepara-invio should return email draft."""
        pack_id = test_package["pack_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/prepara-invio",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        
        # Verify response structure
        assert "pack_id" in result, "Response should contain pack_id"
        assert "email_draft" in result, "Response should contain email_draft"
        assert "attachments" in result, "Response should contain attachments"
        assert "warnings" in result, "Response should contain warnings"
        assert "pack_status" in result, "Response should contain pack_status"
        assert "summary" in result, "Response should contain summary"
        assert "recipient" in result, "Response should contain recipient"
        
        print(f"PASSED: prepara-invio returned valid structure")
        print(f"  - pack_status: {result['pack_status']}")
        print(f"  - attachments: {len(result['attachments'])}")
        print(f"  - warnings: {len(result['warnings'])}")
    
    def test_prepara_invio_email_draft_structure(self, auth_headers, test_package):
        """Email draft should have subject, body, and attachment info."""
        pack_id = test_package["pack_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/prepara-invio",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        result = response.json()
        email_draft = result.get("email_draft", {})
        
        assert "subject" in email_draft, "email_draft should have subject"
        assert "body" in email_draft, "email_draft should have body"
        assert "attachments_count" in email_draft, "email_draft should have attachments_count"
        assert "attachments_ready" in email_draft, "email_draft should have attachments_ready"
        
        # Subject should contain package label
        assert test_package["label"] in email_draft["subject"] or test_package["template_code"] in email_draft["subject"], \
            f"Subject should contain package label or template code"
        
        print(f"PASSED: email_draft structure is valid")
        print(f"  - subject: {email_draft['subject'][:50]}...")
        print(f"  - attachments_count: {email_draft['attachments_count']}")
    
    def test_prepara_invio_generates_warnings_for_missing_docs(self, auth_headers, test_package):
        """Prepara-invio should generate warnings for missing required documents."""
        pack_id = test_package["pack_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/prepara-invio",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        result = response.json()
        warnings = result.get("warnings", [])
        summary = result.get("summary", {})
        
        # If there are missing required docs, there should be warnings
        if summary.get("missing", 0) > 0:
            assert len(warnings) > 0, "Should have warnings for missing documents"
            # Check warning format
            missing_warnings = [w for w in warnings if "mancante" in w.lower()]
            assert len(missing_warnings) > 0, "Should have 'mancante' warnings"
            print(f"PASSED: {len(missing_warnings)} warnings for missing documents")
        else:
            print(f"PASSED: No missing documents, no warnings expected")
    
    def test_prepara_invio_404_for_invalid_pack(self, auth_headers):
        """Prepara-invio should return 404 for non-existent package."""
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/pack_nonexistent123/prepara-invio",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASSED: prepara-invio returns 404 for invalid pack_id")
    
    def test_prepara_invio_auto_verifies_package(self, auth_headers, test_package):
        """Prepara-invio should auto-verify the package before generating draft."""
        pack_id = test_package["pack_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/prepara-invio",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        result = response.json()
        
        # After prepara-invio, package should have updated summary
        summary = result.get("summary", {})
        assert "total_required" in summary, "Summary should have total_required"
        assert "attached" in summary, "Summary should have attached"
        assert "missing" in summary, "Summary should have missing"
        
        print(f"PASSED: prepara-invio auto-verified package")
        print(f"  - total_required: {summary.get('total_required')}")
        print(f"  - attached: {summary.get('attached')}")
        print(f"  - missing: {summary.get('missing')}")


# ═══════════════════════════════════════════════════════════════
#  D5 — INVIA EMAIL TESTS
# ═══════════════════════════════════════════════════════════════

class TestD5InviaEmail:
    """D5: Test invia endpoint for sending emails."""
    
    @pytest.fixture
    def test_package_for_send(self, auth_headers):
        """Create a test package for send testing."""
        create_data = {
            "template_code": "QUALIFICA_FORNITORE",
            "label": f"TEST_D5_Send_{datetime.now().strftime('%H%M%S')}"
        }
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali",
            headers=auth_headers,
            json=create_data
        )
        assert response.status_code == 200
        pack = response.json()
        
        # Prepare the package first
        requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{pack['pack_id']}/prepara-invio",
            headers=auth_headers
        )
        
        return pack
    
    def test_invia_requires_recipient(self, auth_headers, test_package_for_send):
        """POST /api/pacchetti-documentali/{id}/invia should require recipient."""
        pack_id = test_package_for_send["pack_id"]
        
        # Try to send without recipient
        send_data = {
            "to": [],
            "cc": [],
            "subject": "Test Subject",
            "body": "Test Body"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/invia",
            headers=auth_headers,
            json=send_data
        )
        
        # Should return 400 error for missing recipient
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        result = response.json()
        assert "destinatario" in result.get("detail", "").lower() or "recipient" in result.get("detail", "").lower(), \
            "Error should mention missing recipient"
        print("PASSED: invia returns 400 for missing recipient")
    
    def test_invia_requires_subject(self, auth_headers, test_package_for_send):
        """POST /api/pacchetti-documentali/{id}/invia should require subject."""
        pack_id = test_package_for_send["pack_id"]
        
        send_data = {
            "to": ["test@example.com"],
            "cc": [],
            "subject": "",
            "body": "Test Body"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/invia",
            headers=auth_headers,
            json=send_data
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        result = response.json()
        assert "oggetto" in result.get("detail", "").lower() or "subject" in result.get("detail", "").lower(), \
            "Error should mention missing subject"
        print("PASSED: invia returns 400 for missing subject")
    
    def test_invia_with_valid_data(self, auth_headers, test_package_for_send):
        """POST /api/pacchetti-documentali/{id}/invia with valid data should work or fail gracefully."""
        pack_id = test_package_for_send["pack_id"]
        
        send_data = {
            "to": ["test-recipient@example.com"],
            "cc": ["cc-recipient@example.com"],
            "subject": "Test Email Subject - D5 Testing",
            "body": "This is a test email body for D5 testing.\n\nBest regards,\nTest"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/invia",
            headers=auth_headers,
            json=send_data
        )
        
        # Should return 200 (success or graceful failure)
        # Note: If Resend is not configured, it should still return 200 with success=false
        # or 400 with a clear error message
        if response.status_code == 200:
            result = response.json()
            assert "success" in result, "Response should have success field"
            assert "send_log" in result, "Response should have send_log"
            
            send_log = result.get("send_log", {})
            assert "send_id" in send_log, "send_log should have send_id"
            assert "email_to" in send_log, "send_log should have email_to"
            assert "subject" in send_log, "send_log should have subject"
            assert "status" in send_log, "send_log should have status"
            
            if result["success"]:
                print(f"PASSED: Email sent successfully (send_id: {send_log['send_id']})")
            else:
                print(f"PASSED: Email send logged but failed (expected if Resend not configured)")
                print(f"  - status: {send_log.get('status')}")
        elif response.status_code == 400:
            result = response.json()
            # Check if it's a Resend configuration error (expected)
            detail = result.get("detail", "")
            if "resend" in detail.lower() or "api_key" in detail.lower() or "configurata" in detail.lower():
                print(f"PASSED: Graceful error for Resend not configured: {detail}")
            else:
                pytest.fail(f"Unexpected 400 error: {detail}")
        else:
            pytest.fail(f"Unexpected status code {response.status_code}: {response.text}")
    
    def test_invia_404_for_invalid_pack(self, auth_headers):
        """Invia should return 404 for non-existent package."""
        send_data = {
            "to": ["test@example.com"],
            "subject": "Test",
            "body": "Test"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/pack_nonexistent123/invia",
            headers=auth_headers,
            json=send_data
        )
        assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}"
        print("PASSED: invia returns error for invalid pack_id")


# ═══════════════════════════════════════════════════════════════
#  D5 — INVII HISTORY TESTS
# ═══════════════════════════════════════════════════════════════

class TestD5InviiHistory:
    """D5: Test invii (send history) endpoint."""
    
    def test_get_invii_returns_list(self, auth_headers):
        """GET /api/pacchetti-documentali/{id}/invii should return a list."""
        # First get an existing package
        response = requests.get(f"{BASE_URL}/api/pacchetti-documentali", headers=auth_headers)
        assert response.status_code == 200
        pacchetti = response.json()
        
        if not pacchetti:
            pytest.skip("No packages available for testing")
        
        pack_id = pacchetti[0]["pack_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/invii",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        invii = response.json()
        assert isinstance(invii, list), "Response should be a list"
        print(f"PASSED: GET invii returned {len(invii)} send records")
    
    def test_get_invii_empty_for_new_package(self, auth_headers):
        """New package should have empty send history."""
        # Create a new package
        create_data = {
            "template_code": "QUALIFICA_FORNITORE",
            "label": f"TEST_Invii_Empty_{datetime.now().strftime('%H%M%S')}"
        }
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali",
            headers=auth_headers,
            json=create_data
        )
        assert response.status_code == 200
        pack = response.json()
        
        # Get invii for new package
        response = requests.get(
            f"{BASE_URL}/api/pacchetti-documentali/{pack['pack_id']}/invii",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        invii = response.json()
        assert invii == [], "New package should have empty send history"
        print("PASSED: New package has empty invii history")


# ═══════════════════════════════════════════════════════════════
#  PATCH UPDATE RECIPIENT TESTS
# ═══════════════════════════════════════════════════════════════

class TestPatchUpdatePackage:
    """Test PATCH endpoint for updating package fields."""
    
    @pytest.fixture
    def test_package_for_update(self, auth_headers):
        """Create a test package for update testing."""
        create_data = {
            "template_code": "QUALIFICA_FORNITORE",
            "label": f"TEST_Update_{datetime.now().strftime('%H%M%S')}"
        }
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali",
            headers=auth_headers,
            json=create_data
        )
        assert response.status_code == 200
        return response.json()
    
    def test_patch_update_recipient(self, auth_headers, test_package_for_update):
        """PATCH should update recipient field."""
        pack_id = test_package_for_update["pack_id"]
        
        update_data = {
            "recipient": {
                "to": ["updated@example.com", "another@example.com"],
                "cc": ["cc@example.com"]
            }
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}",
            headers=auth_headers,
            json=update_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result.get("recipient", {}).get("to") == ["updated@example.com", "another@example.com"], \
            "Recipient 'to' should be updated"
        assert result.get("recipient", {}).get("cc") == ["cc@example.com"], \
            "Recipient 'cc' should be updated"
        
        print("PASSED: PATCH updated recipient successfully")
    
    def test_patch_update_label(self, auth_headers, test_package_for_update):
        """PATCH should update label field."""
        pack_id = test_package_for_update["pack_id"]
        new_label = f"Updated_Label_{datetime.now().strftime('%H%M%S')}"
        
        update_data = {"label": new_label}
        
        response = requests.patch(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}",
            headers=auth_headers,
            json=update_data
        )
        assert response.status_code == 200
        
        result = response.json()
        assert result.get("label") == new_label, "Label should be updated"
        
        print(f"PASSED: PATCH updated label to '{new_label}'")
    
    def test_patch_ignores_disallowed_fields(self, auth_headers, test_package_for_update):
        """PATCH should ignore fields not in allowed list."""
        pack_id = test_package_for_update["pack_id"]
        original_status = test_package_for_update.get("status")
        
        update_data = {
            "status": "inviato",  # Should be ignored
            "items": [],  # Should be ignored
            "label": "Allowed_Update"
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}",
            headers=auth_headers,
            json=update_data
        )
        assert response.status_code == 200
        
        result = response.json()
        # Status should NOT be changed (not in allowed fields)
        assert result.get("status") == original_status or result.get("status") == "draft", \
            "Status should not be changed via PATCH"
        # Label should be changed
        assert result.get("label") == "Allowed_Update", "Label should be updated"
        
        print("PASSED: PATCH ignores disallowed fields")
    
    def test_patch_404_for_invalid_pack(self, auth_headers):
        """PATCH should return 404 for non-existent package."""
        response = requests.patch(
            f"{BASE_URL}/api/pacchetti-documentali/pack_nonexistent123",
            headers=auth_headers,
            json={"label": "Test"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASSED: PATCH returns 404 for invalid pack_id")


# ═══════════════════════════════════════════════════════════════
#  GET SINGLE PACKAGE TESTS
# ═══════════════════════════════════════════════════════════════

class TestGetSinglePackage:
    """Test GET single package endpoint."""
    
    def test_get_package_returns_full_data(self, auth_headers):
        """GET /api/pacchetti-documentali/{id} should return full package data."""
        # First get list to find a package
        response = requests.get(f"{BASE_URL}/api/pacchetti-documentali", headers=auth_headers)
        assert response.status_code == 200
        pacchetti = response.json()
        
        if not pacchetti:
            pytest.skip("No packages available for testing")
        
        pack_id = pacchetti[0]["pack_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        pack = response.json()
        
        # Verify structure
        assert "pack_id" in pack, "Should have pack_id"
        assert "user_id" in pack, "Should have user_id"
        assert "template_code" in pack, "Should have template_code"
        assert "label" in pack, "Should have label"
        assert "status" in pack, "Should have status"
        assert "items" in pack, "Should have items"
        assert "summary" in pack, "Should have summary"
        assert "recipient" in pack, "Should have recipient"
        
        print(f"PASSED: GET single package returned full data")
        print(f"  - pack_id: {pack['pack_id']}")
        print(f"  - status: {pack['status']}")
        print(f"  - items count: {len(pack.get('items', []))}")
    
    def test_get_package_404_for_invalid_id(self, auth_headers):
        """GET should return 404 for non-existent package."""
        response = requests.get(
            f"{BASE_URL}/api/pacchetti-documentali/pack_nonexistent123",
            headers=auth_headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASSED: GET returns 404 for invalid pack_id")


# ═══════════════════════════════════════════════════════════════
#  INTEGRATION TEST: FULL D4+D5 FLOW
# ═══════════════════════════════════════════════════════════════

class TestD4D5IntegrationFlow:
    """Integration test for full D4+D5 workflow."""
    
    def test_full_prepare_and_send_flow(self, auth_headers):
        """Test complete flow: create → verify → prepara-invio → update recipient → invia → check invii."""
        
        # Step 1: Create package
        create_data = {
            "template_code": "QUALIFICA_FORNITORE",
            "label": f"TEST_Integration_Flow_{datetime.now().strftime('%H%M%S')}"
        }
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali",
            headers=auth_headers,
            json=create_data
        )
        assert response.status_code == 200, f"Step 1 failed: {response.text}"
        pack = response.json()
        pack_id = pack["pack_id"]
        print(f"Step 1 PASSED: Created package {pack_id}")
        
        # Step 2: Verify package
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/verifica",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Step 2 failed: {response.text}"
        verified = response.json()
        print(f"Step 2 PASSED: Verified package, status={verified.get('status')}")
        
        # Step 3: Prepara invio
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/prepara-invio",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Step 3 failed: {response.text}"
        preview = response.json()
        assert "email_draft" in preview, "Step 3: Should have email_draft"
        print(f"Step 3 PASSED: Prepared email draft with {len(preview.get('attachments', []))} attachments")
        
        # Step 4: Update recipient
        update_data = {
            "recipient": {
                "to": ["integration-test@example.com"],
                "cc": []
            }
        }
        response = requests.patch(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}",
            headers=auth_headers,
            json=update_data
        )
        assert response.status_code == 200, f"Step 4 failed: {response.text}"
        print("Step 4 PASSED: Updated recipient")
        
        # Step 5: Attempt to send (may fail if Resend not configured, but should not crash)
        send_data = {
            "to": ["integration-test@example.com"],
            "cc": [],
            "subject": preview.get("email_draft", {}).get("subject", "Test Subject"),
            "body": preview.get("email_draft", {}).get("body", "Test Body")
        }
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/invia",
            headers=auth_headers,
            json=send_data
        )
        # Accept 200 (success or logged failure) or 400 (Resend not configured)
        assert response.status_code in [200, 400], f"Step 5 failed with unexpected status: {response.status_code}"
        if response.status_code == 200:
            send_result = response.json()
            print(f"Step 5 PASSED: Send attempted, success={send_result.get('success')}")
        else:
            print(f"Step 5 PASSED: Send returned 400 (expected if Resend not configured)")
        
        # Step 6: Check invii history
        response = requests.get(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/invii",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Step 6 failed: {response.text}"
        invii = response.json()
        print(f"Step 6 PASSED: Invii history has {len(invii)} records")
        
        print("\n=== INTEGRATION TEST COMPLETE ===")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
