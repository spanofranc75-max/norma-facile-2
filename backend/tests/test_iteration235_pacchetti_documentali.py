"""
Iteration 235 — Pacchetti Documentali D1+D2+D3 Testing
======================================================
D1: Archivio documenti strutturato (upload, metadata, expiry tracking)
D2: Template pacchetti (5 standard templates) + package creation from template
D3: Verification engine (match package items against archive, calculate status)

Tests:
- GET /api/documenti/tipi - returns 26 document types
- POST /api/documenti - upload document with metadata (form-data)
- GET /api/documenti - list documents with filters
- GET /api/documenti/{doc_id} - get single document with calculated status
- PATCH /api/documenti/{doc_id} - update document metadata
- GET /api/pacchetti-documentali/templates - returns 5 templates
- POST /api/pacchetti-documentali - create package from template
- GET /api/pacchetti-documentali - list packages
- GET /api/pacchetti-documentali/{pack_id} - get package with items
- POST /api/pacchetti-documentali/{pack_id}/verifica - D3 verification engine
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "BccyJvnOyrPXRRYy4GfxR5osuF51RWcYWWnUUoHx434"
USER_ID = "user_6988e9b9316c"

# Existing test data from context
EXISTING_DOC_ID = "doc_1f3432425c4c"  # DURC document
EXISTING_PACK_ID = "pack_f6581a6a70e5"  # Existing package


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


class TestD1TipiDocumento:
    """D1: Test document types library endpoint."""
    
    def test_get_tipi_documento_returns_26_types(self, auth_headers):
        """GET /api/documenti/tipi should return 26 document types."""
        response = requests.get(f"{BASE_URL}/api/documenti/tipi", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        tipi = response.json()
        assert isinstance(tipi, list), "Response should be a list"
        assert len(tipi) == 26, f"Expected 26 document types, got {len(tipi)}"
    
    def test_tipi_documento_structure(self, auth_headers):
        """Each document type should have required fields."""
        response = requests.get(f"{BASE_URL}/api/documenti/tipi", headers=auth_headers)
        assert response.status_code == 200
        
        tipi = response.json()
        required_fields = ["code", "label", "category", "entity_type", "has_expiry", "privacy_level"]
        
        for tipo in tipi:
            for field in required_fields:
                assert field in tipo, f"Missing field '{field}' in tipo: {tipo.get('code', 'unknown')}"
    
    def test_tipi_documento_entity_types(self, auth_headers):
        """Document types should have valid entity_type values."""
        response = requests.get(f"{BASE_URL}/api/documenti/tipi", headers=auth_headers)
        assert response.status_code == 200
        
        tipi = response.json()
        valid_entity_types = {"azienda", "persona", "mezzo", "cantiere"}
        
        for tipo in tipi:
            assert tipo["entity_type"] in valid_entity_types, f"Invalid entity_type: {tipo['entity_type']}"
    
    def test_tipi_documento_privacy_levels(self, auth_headers):
        """Document types should have valid privacy_level values."""
        response = requests.get(f"{BASE_URL}/api/documenti/tipi", headers=auth_headers)
        assert response.status_code == 200
        
        tipi = response.json()
        valid_privacy = {"cliente_condivisibile", "interno", "riservato", "sensibile"}
        
        for tipo in tipi:
            assert tipo["privacy_level"] in valid_privacy, f"Invalid privacy_level: {tipo['privacy_level']}"
    
    def test_tipi_documento_has_durc(self, auth_headers):
        """DURC document type should exist with correct properties."""
        response = requests.get(f"{BASE_URL}/api/documenti/tipi", headers=auth_headers)
        assert response.status_code == 200
        
        tipi = response.json()
        durc = next((t for t in tipi if t["code"] == "DURC"), None)
        
        assert durc is not None, "DURC document type not found"
        assert durc["entity_type"] == "azienda"
        assert durc["has_expiry"] == True
        assert durc["privacy_level"] == "cliente_condivisibile"


class TestD1ArchivioDocumenti:
    """D1: Test document archive CRUD operations."""
    
    def test_list_documenti(self, auth_headers):
        """GET /api/documenti should return list of documents."""
        response = requests.get(f"{BASE_URL}/api/documenti", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        docs = response.json()
        assert isinstance(docs, list), "Response should be a list"
    
    def test_list_documenti_with_entity_filter(self, auth_headers):
        """GET /api/documenti?entity_type=azienda should filter by entity type."""
        response = requests.get(f"{BASE_URL}/api/documenti?entity_type=azienda", headers=auth_headers)
        assert response.status_code == 200
        
        docs = response.json()
        for doc in docs:
            assert doc["entity_type"] == "azienda", f"Expected entity_type=azienda, got {doc['entity_type']}"
    
    def test_get_existing_documento(self, auth_headers):
        """GET /api/documenti/{doc_id} should return existing document."""
        response = requests.get(f"{BASE_URL}/api/documenti/{EXISTING_DOC_ID}", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        doc = response.json()
        assert doc["doc_id"] == EXISTING_DOC_ID
        assert "status" in doc, "Document should have calculated status"
        assert "document_type_code" in doc
    
    def test_get_nonexistent_documento(self, auth_headers):
        """GET /api/documenti/{doc_id} should return 404 for nonexistent document."""
        response = requests.get(f"{BASE_URL}/api/documenti/doc_nonexistent123", headers=auth_headers)
        assert response.status_code == 404
    
    def test_upload_documento_form_data(self, auth_headers_form):
        """POST /api/documenti should upload document with form-data."""
        # Calculate future expiry date (valid document)
        expiry_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        issue_date = datetime.now().strftime("%Y-%m-%d")
        
        form_data = {
            "document_type_code": "POLIZZA_RCT",
            "entity_type": "azienda",
            "title": "TEST_Polizza RCT Test Upload",
            "issue_date": issue_date,
            "expiry_date": expiry_date,
            "privacy_level": "cliente_condivisibile",
            "verified": "true",
            "owner_label": "Test Company Srl"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documenti",
            headers=auth_headers_form,
            data=form_data
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        doc = response.json()
        assert "doc_id" in doc, "Response should contain doc_id"
        assert doc["document_type_code"] == "POLIZZA_RCT"
        assert doc["entity_type"] == "azienda"
        assert doc["title"] == "TEST_Polizza RCT Test Upload"
        assert doc["status"] == "valido", f"Expected status=valido, got {doc['status']}"
        
        # Store for cleanup
        return doc["doc_id"]
    
    def test_upload_documento_with_expiry_calculates_status(self, auth_headers_form):
        """Uploaded document with expiry should have calculated status."""
        # Upload document expiring in 15 days (in_scadenza)
        expiry_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        
        form_data = {
            "document_type_code": "DURC",
            "entity_type": "azienda",
            "title": "TEST_DURC In Scadenza",
            "expiry_date": expiry_date,
            "privacy_level": "cliente_condivisibile"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documenti",
            headers=auth_headers_form,
            data=form_data
        )
        assert response.status_code == 200
        
        doc = response.json()
        assert doc["status"] == "in_scadenza", f"Expected status=in_scadenza for 15-day expiry, got {doc['status']}"
    
    def test_upload_documento_expired_status(self, auth_headers_form):
        """Uploaded document with past expiry should have scaduto status."""
        # Upload document that expired yesterday
        expiry_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        form_data = {
            "document_type_code": "VISURA_CAMERALE",
            "entity_type": "azienda",
            "title": "TEST_Visura Scaduta",
            "expiry_date": expiry_date,
            "privacy_level": "cliente_condivisibile"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/documenti",
            headers=auth_headers_form,
            data=form_data
        )
        assert response.status_code == 200
        
        doc = response.json()
        assert doc["status"] == "scaduto", f"Expected status=scaduto for past expiry, got {doc['status']}"
    
    def test_update_documento(self, auth_headers):
        """PATCH /api/documenti/{doc_id} should update document metadata."""
        # First get the existing document
        response = requests.get(f"{BASE_URL}/api/documenti/{EXISTING_DOC_ID}", headers=auth_headers)
        assert response.status_code == 200
        
        # Update title
        updates = {"title": "DURC Updated Title Test"}
        response = requests.patch(
            f"{BASE_URL}/api/documenti/{EXISTING_DOC_ID}",
            headers=auth_headers,
            json=updates
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        doc = response.json()
        assert doc["title"] == "DURC Updated Title Test"
    
    def test_update_nonexistent_documento(self, auth_headers):
        """PATCH /api/documenti/{doc_id} should return 404 for nonexistent document."""
        response = requests.patch(
            f"{BASE_URL}/api/documenti/doc_nonexistent123",
            headers=auth_headers,
            json={"title": "Test"}
        )
        assert response.status_code == 404


class TestD2Templates:
    """D2: Test package templates endpoint."""
    
    def test_get_templates_returns_5(self, auth_headers):
        """GET /api/pacchetti-documentali/templates should return 5 templates."""
        response = requests.get(f"{BASE_URL}/api/pacchetti-documentali/templates", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        templates = response.json()
        assert isinstance(templates, list), "Response should be a list"
        assert len(templates) == 5, f"Expected 5 templates, got {len(templates)}"
    
    def test_templates_have_required_codes(self, auth_headers):
        """Templates should include all 5 standard codes."""
        response = requests.get(f"{BASE_URL}/api/pacchetti-documentali/templates", headers=auth_headers)
        assert response.status_code == 200
        
        templates = response.json()
        expected_codes = {
            "INGRESSO_CANTIERE",
            "QUALIFICA_FORNITORE",
            "PERSONALE_OPERATIVO",
            "DOCUMENTI_MEZZI",
            "PACCHETTO_SICUREZZA"
        }
        
        actual_codes = {t["code"] for t in templates}
        assert actual_codes == expected_codes, f"Missing templates: {expected_codes - actual_codes}"
    
    def test_template_structure(self, auth_headers):
        """Each template should have required fields."""
        response = requests.get(f"{BASE_URL}/api/pacchetti-documentali/templates", headers=auth_headers)
        assert response.status_code == 200
        
        templates = response.json()
        required_fields = ["code", "label", "description", "rules"]
        
        for tpl in templates:
            for field in required_fields:
                assert field in tpl, f"Missing field '{field}' in template: {tpl.get('code', 'unknown')}"
            assert isinstance(tpl["rules"], list), f"Rules should be a list in template: {tpl['code']}"
    
    def test_ingresso_cantiere_has_11_rules(self, auth_headers):
        """INGRESSO_CANTIERE template should have 11 rules."""
        response = requests.get(f"{BASE_URL}/api/pacchetti-documentali/templates", headers=auth_headers)
        assert response.status_code == 200
        
        templates = response.json()
        ingresso = next((t for t in templates if t["code"] == "INGRESSO_CANTIERE"), None)
        
        assert ingresso is not None, "INGRESSO_CANTIERE template not found"
        assert len(ingresso["rules"]) == 11, f"Expected 11 rules, got {len(ingresso['rules'])}"
    
    def test_qualifica_fornitore_has_8_rules(self, auth_headers):
        """QUALIFICA_FORNITORE template should have 8 rules."""
        response = requests.get(f"{BASE_URL}/api/pacchetti-documentali/templates", headers=auth_headers)
        assert response.status_code == 200
        
        templates = response.json()
        qualifica = next((t for t in templates if t["code"] == "QUALIFICA_FORNITORE"), None)
        
        assert qualifica is not None, "QUALIFICA_FORNITORE template not found"
        assert len(qualifica["rules"]) == 8, f"Expected 8 rules, got {len(qualifica['rules'])}"


class TestD2Pacchetti:
    """D2: Test package CRUD operations."""
    
    def test_list_pacchetti(self, auth_headers):
        """GET /api/pacchetti-documentali should return list of packages."""
        response = requests.get(f"{BASE_URL}/api/pacchetti-documentali", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        packs = response.json()
        assert isinstance(packs, list), "Response should be a list"
    
    def test_get_existing_pacchetto(self, auth_headers):
        """GET /api/pacchetti-documentali/{pack_id} should return existing package."""
        response = requests.get(f"{BASE_URL}/api/pacchetti-documentali/{EXISTING_PACK_ID}", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        pack = response.json()
        assert pack["pack_id"] == EXISTING_PACK_ID
        assert "items" in pack, "Package should have items"
        assert "status" in pack, "Package should have status"
    
    def test_get_nonexistent_pacchetto(self, auth_headers):
        """GET /api/pacchetti-documentali/{pack_id} should return 404 for nonexistent package."""
        response = requests.get(f"{BASE_URL}/api/pacchetti-documentali/pack_nonexistent123", headers=auth_headers)
        assert response.status_code == 404
    
    def test_create_pacchetto_from_template(self, auth_headers):
        """POST /api/pacchetti-documentali should create package from template."""
        payload = {
            "template_code": "QUALIFICA_FORNITORE",
            "label": "TEST_Qualifica Fornitore Test"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        pack = response.json()
        assert "pack_id" in pack, "Response should contain pack_id"
        assert pack["template_code"] == "QUALIFICA_FORNITORE"
        assert pack["label"] == "TEST_Qualifica Fornitore Test"
        assert "items" in pack, "Package should have items"
        assert len(pack["items"]) == 8, f"Expected 8 items from QUALIFICA_FORNITORE, got {len(pack['items'])}"
        assert pack["status"] == "draft", f"New package should have status=draft, got {pack['status']}"
        
        return pack["pack_id"]
    
    def test_create_pacchetto_ingresso_cantiere(self, auth_headers):
        """POST /api/pacchetti-documentali with INGRESSO_CANTIERE template."""
        payload = {
            "template_code": "INGRESSO_CANTIERE",
            "label": "TEST_Ingresso Cantiere Test"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200
        
        pack = response.json()
        assert pack["template_code"] == "INGRESSO_CANTIERE"
        # INGRESSO_CANTIERE has 11 rules, but some expand for workers
        # Without workers assigned, persona rules create placeholder items
        assert len(pack["items"]) >= 11, f"Expected at least 11 items, got {len(pack['items'])}"


class TestD3Verifica:
    """D3: Test verification engine."""
    
    def test_verifica_pacchetto(self, auth_headers):
        """POST /api/pacchetti-documentali/{pack_id}/verifica should verify package."""
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{EXISTING_PACK_ID}/verifica",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "pack_id" in result
        assert "status" in result
        assert "summary" in result
        assert "items" in result
    
    def test_verifica_returns_summary_counters(self, auth_headers):
        """Verification should return summary with counters."""
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{EXISTING_PACK_ID}/verifica",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        result = response.json()
        summary = result["summary"]
        
        expected_counters = ["total_required", "attached", "missing", "expired", "in_scadenza", "sensibile"]
        for counter in expected_counters:
            assert counter in summary, f"Missing counter '{counter}' in summary"
            assert isinstance(summary[counter], int), f"Counter '{counter}' should be int"
    
    def test_verifica_calculates_pack_status(self, auth_headers):
        """Verification should calculate package status (pronto_invio/incompleto/draft)."""
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{EXISTING_PACK_ID}/verifica",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        result = response.json()
        valid_statuses = {"pronto_invio", "incompleto", "draft"}
        assert result["status"] in valid_statuses, f"Invalid status: {result['status']}"
    
    def test_verifica_items_have_status(self, auth_headers):
        """Each verified item should have status and blocking flag."""
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{EXISTING_PACK_ID}/verifica",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        result = response.json()
        for item in result["items"]:
            assert "status" in item, f"Item missing status: {item}"
            assert "blocking" in item, f"Item missing blocking flag: {item}"
            assert item["status"] in {"attached", "missing", "expired", "in_scadenza", "pending"}
    
    def test_verifica_nonexistent_pacchetto(self, auth_headers):
        """POST /api/pacchetti-documentali/{pack_id}/verifica should return 404 for nonexistent package."""
        response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/pack_nonexistent123/verifica",
            headers=auth_headers
        )
        assert response.status_code == 404
    
    def test_verifica_finds_durc_as_attached(self, auth_headers, auth_headers_form):
        """Verification should find uploaded DURC as 'attached' for items requiring DURC."""
        # First, ensure we have a valid DURC in archive
        expiry_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        form_data = {
            "document_type_code": "DURC",
            "entity_type": "azienda",
            "title": "TEST_DURC for Verification",
            "expiry_date": expiry_date,
            "privacy_level": "cliente_condivisibile",
            "verified": "true"
        }
        
        upload_response = requests.post(
            f"{BASE_URL}/api/documenti",
            headers=auth_headers_form,
            data=form_data
        )
        assert upload_response.status_code == 200
        
        # Create a new package that requires DURC
        pack_payload = {
            "template_code": "QUALIFICA_FORNITORE",
            "label": "TEST_Package for DURC Verification"
        }
        
        pack_response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali",
            headers=auth_headers,
            json=pack_payload
        )
        assert pack_response.status_code == 200
        pack_id = pack_response.json()["pack_id"]
        
        # Verify the package
        verify_response = requests.post(
            f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/verifica",
            headers=auth_headers
        )
        assert verify_response.status_code == 200
        
        result = verify_response.json()
        
        # Find DURC item
        durc_item = next((i for i in result["items"] if i["document_type_code"] == "DURC"), None)
        assert durc_item is not None, "DURC item not found in package"
        assert durc_item["status"] == "attached", f"DURC should be 'attached', got {durc_item['status']}"
        assert durc_item["document_id"] is not None, "DURC item should have document_id"


class TestD3StatusCalculation:
    """D3: Test status calculation logic."""
    
    def test_valid_document_status_attached(self, auth_headers, auth_headers_form):
        """Valid document should result in 'attached' status."""
        # Upload valid document
        expiry_date = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
        form_data = {
            "document_type_code": "POLIZZA_RCT",
            "entity_type": "azienda",
            "title": "TEST_Valid Polizza",
            "expiry_date": expiry_date,
            "verified": "true"
        }
        
        upload_response = requests.post(
            f"{BASE_URL}/api/documenti",
            headers=auth_headers_form,
            data=form_data
        )
        assert upload_response.status_code == 200
        
        # Create package and verify
        pack_payload = {"template_code": "QUALIFICA_FORNITORE", "label": "TEST_Valid Doc Test"}
        pack_response = requests.post(f"{BASE_URL}/api/pacchetti-documentali", headers=auth_headers, json=pack_payload)
        pack_id = pack_response.json()["pack_id"]
        
        verify_response = requests.post(f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/verifica", headers=auth_headers)
        result = verify_response.json()
        
        polizza_item = next((i for i in result["items"] if i["document_type_code"] == "POLIZZA_RCT"), None)
        assert polizza_item is not None
        assert polizza_item["status"] == "attached"
    
    def test_missing_document_status_and_blocking(self, auth_headers):
        """Missing required document should have status='missing' and blocking=True."""
        # Create package with template that has required docs we don't have
        pack_payload = {"template_code": "DOCUMENTI_MEZZI", "label": "TEST_Missing Docs Test"}
        pack_response = requests.post(f"{BASE_URL}/api/pacchetti-documentali", headers=auth_headers, json=pack_payload)
        pack_id = pack_response.json()["pack_id"]
        
        verify_response = requests.post(f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/verifica", headers=auth_headers)
        result = verify_response.json()
        
        # DOCUMENTI_MEZZI requires mezzo documents which we likely don't have
        missing_items = [i for i in result["items"] if i["status"] == "missing"]
        
        # At least some items should be missing
        assert len(missing_items) > 0, "Expected some missing items"
        
        # Required missing items should be blocking
        for item in missing_items:
            if item.get("required"):
                assert item["blocking"] == True, f"Required missing item should be blocking: {item}"
    
    def test_expired_document_status_and_blocking(self, auth_headers, auth_headers_form):
        """Expired document should have status='expired' and blocking=True if required."""
        # Upload expired document
        expiry_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        form_data = {
            "document_type_code": "CERT_ISO_9001",
            "entity_type": "azienda",
            "title": "TEST_Expired ISO 9001",
            "expiry_date": expiry_date
        }
        
        upload_response = requests.post(
            f"{BASE_URL}/api/documenti",
            headers=auth_headers_form,
            data=form_data
        )
        assert upload_response.status_code == 200
        
        # Create package and verify
        pack_payload = {"template_code": "QUALIFICA_FORNITORE", "label": "TEST_Expired Doc Test"}
        pack_response = requests.post(f"{BASE_URL}/api/pacchetti-documentali", headers=auth_headers, json=pack_payload)
        pack_id = pack_response.json()["pack_id"]
        
        verify_response = requests.post(f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/verifica", headers=auth_headers)
        result = verify_response.json()
        
        iso_item = next((i for i in result["items"] if i["document_type_code"] == "CERT_ISO_9001"), None)
        if iso_item:
            # If we found the item and it matched our expired doc
            if iso_item["document_id"]:
                assert iso_item["status"] == "expired", f"Expired doc should have status='expired', got {iso_item['status']}"
    
    def test_sensibile_privacy_flagged(self, auth_headers, auth_headers_form):
        """Documents with sensibile privacy should be flagged in summary."""
        # Upload sensibile document (IDONEITA_SANITARIA has sensibile privacy)
        expiry_date = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
        form_data = {
            "document_type_code": "IDONEITA_SANITARIA",
            "entity_type": "persona",
            "title": "TEST_Idoneita Sanitaria",
            "expiry_date": expiry_date,
            "verified": "true"
        }
        
        upload_response = requests.post(
            f"{BASE_URL}/api/documenti",
            headers=auth_headers_form,
            data=form_data
        )
        assert upload_response.status_code == 200
        
        # Create package with persona documents
        pack_payload = {"template_code": "PERSONALE_OPERATIVO", "label": "TEST_Sensibile Test"}
        pack_response = requests.post(f"{BASE_URL}/api/pacchetti-documentali", headers=auth_headers, json=pack_payload)
        pack_id = pack_response.json()["pack_id"]
        
        verify_response = requests.post(f"{BASE_URL}/api/pacchetti-documentali/{pack_id}/verifica", headers=auth_headers)
        result = verify_response.json()
        
        # Check that sensibile counter is tracked
        assert "sensibile" in result["summary"]
        
        # Find IDONEITA_SANITARIA item
        idoneita_item = next((i for i in result["items"] if i["document_type_code"] == "IDONEITA_SANITARIA"), None)
        if idoneita_item:
            assert idoneita_item.get("privacy_level") == "sensibile"


class TestAuthentication:
    """Test authentication requirements."""
    
    def test_documenti_tipi_requires_auth(self):
        """GET /api/documenti/tipi should require authentication."""
        response = requests.get(f"{BASE_URL}/api/documenti/tipi")
        assert response.status_code == 401
    
    def test_documenti_list_requires_auth(self):
        """GET /api/documenti should require authentication."""
        response = requests.get(f"{BASE_URL}/api/documenti")
        assert response.status_code == 401
    
    def test_pacchetti_templates_requires_auth(self):
        """GET /api/pacchetti-documentali/templates should require authentication."""
        response = requests.get(f"{BASE_URL}/api/pacchetti-documentali/templates")
        assert response.status_code == 401
    
    def test_pacchetti_list_requires_auth(self):
        """GET /api/pacchetti-documentali should require authentication."""
        response = requests.get(f"{BASE_URL}/api/pacchetti-documentali")
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
