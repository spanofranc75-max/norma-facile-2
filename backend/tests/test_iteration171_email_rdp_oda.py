"""
Iteration 171 — Bug P0 Fix Testing: RdP and OdA Email Sending
Tests the following endpoints:
- POST /api/commesse/{cid}/approvvigionamento/richieste/{rdp_id}/send-email (200 with real email)
- POST same with CC payload (200 with CC)
- POST same with fornitore without email (400 error)
- POST /api/commesse/{cid}/approvvigionamento/ordini/{ordine_id}/send-email (200)
- GET /api/commesse/{cid}/approvvigionamento/richieste/{rdp_id}/pdf (PDF generation)
- GET /api/commesse/{cid}/approvvigionamento/richieste/{rdp_id}/preview-email (email preview)

Credentials used:
- Session: test-session-rdp-email-test
- Commessa: com_e8c4810ad476 (NF-2026-000001)
- Fornitore with email (pec): cli_a8a39751d3d1 (pec=azienda@pec.it)
- Fornitore without email: cli_df1bb73d9b6d (BERTOLINI SIDERURGICA SRL)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Existing test credentials
SESSION_TOKEN = "test-session-rdp-email-test"
COMMESSA_ID = "com_e8c4810ad476"
FORNITORE_WITH_EMAIL_ID = "cli_a8a39751d3d1"    # has pec=azienda@pec.it
FORNITORE_WITH_EMAIL_NAME = "Acciaio Service"
FORNITORE_NO_EMAIL_ID = "cli_df1bb73d9b6d"       # no email
FORNITORE_NO_EMAIL_NAME = "BERTOLINI SIDERURGICA SRL"

AUTH_HEADERS = {
    "Authorization": f"Bearer {SESSION_TOKEN}",
    "Content-Type": "application/json",
}


# ─────────────────────────────────────────────────────────────────
# Fixtures: Create fresh RdP / OdA per test class
# ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="class")
def fresh_rdp_with_email():
    """Create a new RdP linked to a supplier that has an email (pec)."""
    headers = AUTH_HEADERS.copy()
    payload = {
        "fornitore_nome": FORNITORE_WITH_EMAIL_NAME,
        "fornitore_id": FORNITORE_WITH_EMAIL_ID,
        "righe": [
            {"descrizione": "Trave IPE 200 S275JR", "quantita": 500, "unita_misura": "kg", "richiede_cert_31": True},
            {"descrizione": "Lamiera 10mm S275", "quantita": 200, "unita_misura": "kg", "richiede_cert_31": False},
        ],
        "note": "Test email invio — iterazione 171",
    }
    response = requests.post(
        f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/richieste",
        json=payload, headers=headers
    )
    assert response.status_code == 200, f"Setup RdP creation failed: {response.text}"
    data = response.json()
    return data["rdp"]["rdp_id"]


@pytest.fixture(scope="class")
def fresh_rdp_no_email():
    """Create a new RdP linked to a supplier that has NO email."""
    headers = AUTH_HEADERS.copy()
    payload = {
        "fornitore_nome": FORNITORE_NO_EMAIL_NAME,
        "fornitore_id": FORNITORE_NO_EMAIL_ID,
        "righe": [
            {"descrizione": "Piatto 30x100 S235", "quantita": 50, "unita_misura": "kg"},
        ],
        "note": "Test no-email supplier",
    }
    response = requests.post(
        f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/richieste",
        json=payload, headers=headers
    )
    assert response.status_code == 200, f"Setup RdP (no email) creation failed: {response.text}"
    data = response.json()
    return data["rdp"]["rdp_id"]


@pytest.fixture(scope="class")
def fresh_oda_with_email():
    """Create a new OdA linked to a supplier that has an email."""
    headers = AUTH_HEADERS.copy()
    payload = {
        "fornitore_nome": FORNITORE_WITH_EMAIL_NAME,
        "fornitore_id": FORNITORE_WITH_EMAIL_ID,
        "righe": [
            {"descrizione": "Trave HEA 200 S355", "quantita": 300, "unita_misura": "kg",
             "prezzo_unitario": 1.50, "richiede_cert_31": True},
            {"descrizione": "Dado M16 8.8", "quantita": 200, "unita_misura": "pz",
             "prezzo_unitario": 0.30},
        ],
        "note": "Test OdA email invio — iterazione 171",
    }
    response = requests.post(
        f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/ordini",
        json=payload, headers=headers
    )
    assert response.status_code == 200, f"Setup OdA creation failed: {response.text}"
    data = response.json()
    return data["ordine"]["ordine_id"]


# ─────────────────────────────────────────────────────────────────
# 1. RdP PDF Generation
# ─────────────────────────────────────────────────────────────────

class TestRdpPdf:
    """GET /api/commesse/{cid}/approvvigionamento/richieste/{rdp_id}/pdf"""

    def test_rdp_pdf_returns_valid_pdf(self, fresh_rdp_with_email):
        """PDF endpoint returns 200 with a valid PDF binary."""
        response = requests.get(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/richieste/{fresh_rdp_with_email}/pdf",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
        )
        assert response.status_code == 200, f"PDF endpoint failed: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf", \
            f"Expected application/pdf, got {response.headers.get('Content-Type')}"
        assert response.content[:4] == b"%PDF", "Response bytes do not start with %PDF magic"
        assert len(response.content) > 1000, "PDF is suspiciously small"
        print(f"✓ RdP PDF generated: {len(response.content)} bytes")

    def test_rdp_pdf_content_disposition(self, fresh_rdp_with_email):
        """PDF Content-Disposition header should be inline."""
        response = requests.get(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/richieste/{fresh_rdp_with_email}/pdf",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
        )
        assert response.status_code == 200
        disposition = response.headers.get("Content-Disposition", "")
        assert "inline" in disposition, f"Expected inline, got: {disposition}"
        print(f"✓ Content-Disposition: {disposition}")

    def test_rdp_pdf_not_found(self):
        """Non-existent RdP returns 404."""
        response = requests.get(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/richieste/rdp_nonexistent/pdf",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent RdP PDF returns 404")


# ─────────────────────────────────────────────────────────────────
# 2. RdP Email Preview
# ─────────────────────────────────────────────────────────────────

class TestRdpPreviewEmail:
    """GET /api/commesse/{cid}/approvvigionamento/richieste/{rdp_id}/preview-email"""

    def test_preview_returns_expected_fields(self, fresh_rdp_with_email):
        """Preview endpoint returns to_email, subject, html_body and attachment info."""
        response = requests.get(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/richieste/{fresh_rdp_with_email}/preview-email",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
        )
        assert response.status_code == 200, f"Preview failed: {response.text}"
        data = response.json()

        # Verify required fields
        assert "to_email" in data, "Missing to_email"
        assert "subject" in data, "Missing subject"
        assert "html_body" in data, "Missing html_body"
        assert "has_attachment" in data, "Missing has_attachment"
        assert "attachment_name" in data, "Missing attachment_name"

        # Verify to_email is populated (supplier has pec=azienda@pec.it)
        assert data["to_email"], "to_email should not be empty"
        assert "@" in data["to_email"], "to_email should be a valid email"

        # Verify subject contains relevant info
        assert data["subject"], "subject should not be empty"

        # Verify HTML body is present
        assert len(data["html_body"]) > 50, "html_body too short"

        # Verify PDF attachment
        assert data["has_attachment"] is True, "should have attachment"
        assert data["attachment_name"].endswith(".pdf"), "attachment should be PDF"

        print(f"✓ Preview: to={data['to_email']}, subject={data['subject'][:50]}")

    def test_preview_to_name_populated(self, fresh_rdp_with_email):
        """Preview should include fornitore name in to_name."""
        response = requests.get(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/richieste/{fresh_rdp_with_email}/preview-email",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("to_name"), "to_name should not be empty"
        print(f"✓ to_name: {data['to_name']}")


# ─────────────────────────────────────────────────────────────────
# 3. RdP Send Email
# ─────────────────────────────────────────────────────────────────

class TestRdpSendEmail:
    """POST /api/commesse/{cid}/approvvigionamento/richieste/{rdp_id}/send-email"""

    def test_send_rdp_email_success(self, fresh_rdp_with_email):
        """Send email for RdP with valid supplier email — must return 200."""
        response = requests.post(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/richieste/{fresh_rdp_with_email}/send-email",
            headers=AUTH_HEADERS,
            json={},
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "message" in data, "Response missing 'message'"
        assert "to" in data, "Response missing 'to'"
        assert "@" in data["to"], f"'to' should be an email: {data['to']}"
        print(f"✓ RdP email sent to: {data['to']}")

    def test_send_rdp_email_email_sent_flag(self, fresh_rdp_with_email):
        """After sending, RdP.email_sent should be True and email_sent_to populated."""
        # Send email first
        send_resp = requests.post(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/richieste/{fresh_rdp_with_email}/send-email",
            headers=AUTH_HEADERS,
            json={},
        )
        assert send_resp.status_code == 200, f"Send failed: {send_resp.text}"

        # Check ops data
        ops_resp = requests.get(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/ops",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
        )
        assert ops_resp.status_code == 200, f"Ops fetch failed: {ops_resp.text}"
        ops = ops_resp.json()
        rdp_list = ops.get("approvvigionamento", {}).get("richieste", [])
        rdp = next((r for r in rdp_list if r.get("rdp_id") == fresh_rdp_with_email), None)
        assert rdp is not None, "RdP not found in ops data"
        assert rdp.get("email_sent") is True, f"email_sent should be True, got {rdp.get('email_sent')}"
        assert rdp.get("email_sent_to"), "email_sent_to should be set"
        assert rdp.get("email_sent_at"), "email_sent_at should be set"
        print(f"✓ email_sent=True, to={rdp['email_sent_to']}")

    def test_send_rdp_email_with_cc(self, fresh_rdp_with_email):
        """Send email with CC list — must return 200 and accept cc payload."""
        payload = {
            "cc": ["cc-test@example.com", "altro-cc@example.com"]
        }
        response = requests.post(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/richieste/{fresh_rdp_with_email}/send-email",
            headers=AUTH_HEADERS,
            json=payload,
        )
        assert response.status_code == 200, (
            f"Expected 200 with CC, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "message" in data
        assert "to" in data
        print(f"✓ RdP email with CC sent: {data['message']}")

    def test_send_rdp_email_no_email_supplier(self, fresh_rdp_no_email):
        """Send email for RdP with supplier that has no email — must return 400."""
        response = requests.post(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/richieste/{fresh_rdp_no_email}/send-email",
            headers=AUTH_HEADERS,
            json={},
        )
        assert response.status_code == 400, (
            f"Expected 400 for no email supplier, got {response.status_code}: {response.text}"
        )
        data = response.json()
        error_msg = data.get("detail", "")
        assert error_msg, "Should have error detail"
        # Check for italian error message
        assert any(word in error_msg.lower() for word in ["email", "indirizzo"]), \
            f"Error message should mention email: {error_msg}"
        print(f"✓ Correctly returns 400: {error_msg}")

    def test_send_rdp_nonexistent(self):
        """Non-existent RdP returns 404."""
        response = requests.post(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/richieste/rdp_fake999/send-email",
            headers=AUTH_HEADERS,
            json={},
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent RdP send-email returns 404")

    def test_send_rdp_email_custom_subject_body(self, fresh_rdp_with_email):
        """Send with custom_subject and custom_body uses send_email_with_attachment path."""
        payload = {
            "custom_subject": "Test Soggetto Personalizzato — RdP Test",
            "custom_body": "Gentile fornitore,\n\nIn allegato la nostra richiesta di preventivo personalizzata.\n\nSaluti.",
        }
        response = requests.post(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/richieste/{fresh_rdp_with_email}/send-email",
            headers=AUTH_HEADERS,
            json=payload,
        )
        assert response.status_code == 200, (
            f"Expected 200 with custom body, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "to" in data
        print(f"✓ RdP email with custom subject/body sent to {data['to']}")


# ─────────────────────────────────────────────────────────────────
# 4. OdA Send Email
# ─────────────────────────────────────────────────────────────────

class TestOdaSendEmail:
    """POST /api/commesse/{cid}/approvvigionamento/ordini/{ordine_id}/send-email"""

    def test_send_oda_email_success(self, fresh_oda_with_email):
        """Send email for OdA with valid supplier email — must return 200."""
        response = requests.post(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/ordini/{fresh_oda_with_email}/send-email",
            headers=AUTH_HEADERS,
            json={},
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "message" in data, "Response missing 'message'"
        assert "to" in data, "Response missing 'to'"
        assert "@" in data["to"], f"'to' should be an email: {data['to']}"
        print(f"✓ OdA email sent to: {data['to']}")

    def test_send_oda_email_sent_flag(self, fresh_oda_with_email):
        """After sending, OdA.email_sent should be True."""
        # Send email
        send_resp = requests.post(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/ordini/{fresh_oda_with_email}/send-email",
            headers=AUTH_HEADERS,
            json={},
        )
        assert send_resp.status_code == 200, f"Send failed: {send_resp.text}"

        # Check ops data
        ops_resp = requests.get(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/ops",
            headers={"Authorization": f"Bearer {SESSION_TOKEN}"},
        )
        assert ops_resp.status_code == 200
        ops = ops_resp.json()
        ordini_list = ops.get("approvvigionamento", {}).get("ordini", [])
        oda = next((o for o in ordini_list if o.get("ordine_id") == fresh_oda_with_email), None)
        assert oda is not None, "OdA not found in ops data"
        assert oda.get("email_sent") is True, f"email_sent should be True, got {oda.get('email_sent')}"
        assert oda.get("email_sent_to"), "email_sent_to should be set"
        print(f"✓ OdA email_sent=True, to={oda['email_sent_to']}")

    def test_send_oda_email_with_cc(self, fresh_oda_with_email):
        """Send OdA email with CC list — must return 200."""
        payload = {
            "cc": ["buyer@azienda.it"]
        }
        response = requests.post(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/ordini/{fresh_oda_with_email}/send-email",
            headers=AUTH_HEADERS,
            json=payload,
        )
        assert response.status_code == 200, (
            f"Expected 200 with CC, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "to" in data
        print(f"✓ OdA email with CC sent: {data['message']}")

    def test_send_oda_nonexistent(self):
        """Non-existent OdA returns 404."""
        response = requests.post(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/ordini/oda_fake999/send-email",
            headers=AUTH_HEADERS,
            json={},
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent OdA send-email returns 404")

    def test_send_oda_email_custom_body(self, fresh_oda_with_email):
        """Send OdA with custom_subject/custom_body — uses generic send path."""
        payload = {
            "custom_subject": "Conferma Ordine — Test Iterazione 171",
            "custom_body": "In allegato il nostro ordine di acquisto. Si prega di confermare.",
        }
        response = requests.post(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/ordini/{fresh_oda_with_email}/send-email",
            headers=AUTH_HEADERS,
            json=payload,
        )
        assert response.status_code == 200, (
            f"Expected 200 with custom body, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "to" in data
        print(f"✓ OdA email with custom body sent to {data['to']}")


# ─────────────────────────────────────────────────────────────────
# 5. Authentication checks
# ─────────────────────────────────────────────────────────────────

class TestAuth:
    """Verify endpoints reject requests without valid auth."""

    def test_rdp_pdf_requires_auth(self):
        """PDF endpoint should require authentication."""
        response = requests.get(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/richieste/rdp_test/pdf"
        )
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ PDF endpoint requires auth: {response.status_code}")

    def test_send_rdp_requires_auth(self):
        """Send email endpoint should require authentication."""
        response = requests.post(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/richieste/rdp_test/send-email",
            json={},
        )
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Send-email endpoint requires auth: {response.status_code}")

    def test_send_oda_requires_auth(self):
        """Send OdA email endpoint should require authentication."""
        response = requests.post(
            f"{BASE_URL}/api/commesse/{COMMESSA_ID}/approvvigionamento/ordini/oda_test/send-email",
            json={},
        )
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ OdA send-email endpoint requires auth: {response.status_code}")
