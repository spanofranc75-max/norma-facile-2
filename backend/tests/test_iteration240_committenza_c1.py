"""
Iteration 240 — C1: Verifica Committenza Module Testing
========================================================
Tests for the new Verifica Committenza module that analyzes client-received documents
via AI, extracts obligations/anomalies/mismatches, allows human review, and generates
obligations in the Registro Obblighi.

Phases:
- C1.1: Package creation (referencing existing archive docs)
- C1.2: AI analysis (GPT-4o) - may fail without LLM key
- C1.3: Human review (confirm/reject items)
- C1.4: Generate obligations from approved snapshot

Collections:
- pacchetti_committenza: analysis packages
- analisi_committenza: AI analysis results + human review
- obblighi_commessa: generated obligations (with dedupe_key)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session from previous iteration
TEST_SESSION_TOKEN = "BccyJvnOyrPXRRYy4GfxR5osuF51RWcYWWnUUoHx434"
TEST_USER_ID = "user_6988e9b9316c"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TEST_SESSION_TOKEN}"
    })
    session.cookies.set("session_token", TEST_SESSION_TOKEN)
    return session


@pytest.fixture(scope="module")
def test_commessa(api_client):
    """Create a test commessa for C1 testing."""
    commessa_data = {
        "title": f"TEST_C1_Commessa_{uuid.uuid4().hex[:8]}",
        "client_name": "Test Client C1",
        "description": "Test commessa for Verifica Committenza",
        "normativa_tipo": "EN_1090",
        "classe_exc": "EXC2",
        "value": 50000
    }
    # Note: trailing slash required to avoid 307 redirect
    response = api_client.post(f"{BASE_URL}/api/commesse/", json=commessa_data)
    assert response.status_code in [200, 201], f"Failed to create commessa: {response.text}"
    commessa = response.json()
    assert "commessa_id" in commessa, f"No commessa_id in response: {commessa}"
    yield commessa
    # Cleanup
    try:
        api_client.delete(f"{BASE_URL}/api/commesse/{commessa['commessa_id']}")
    except:
        pass


@pytest.fixture(scope="module")
def test_archive_doc(api_client, test_commessa):
    """Create a test document in the archive for C1 testing using Form data."""
    # Use Form data for document upload (not JSON)
    form_data = {
        "title": f"TEST_C1_Contratto_{uuid.uuid4().hex[:8]}",
        "document_type_code": "CONTRATTO",
        "entity_type": "commessa",
        "entity_id": test_commessa["commessa_id"],
        "notes": "Test contract document for C1 analysis"
    }
    # Remove Content-Type header for form data
    headers = {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}
    response = requests.post(
        f"{BASE_URL}/api/documenti",
        data=form_data,
        headers=headers,
        cookies={"session_token": TEST_SESSION_TOKEN}
    )
    if response.status_code not in [200, 201]:
        pytest.skip(f"Could not create archive doc: {response.text}")
    doc = response.json()
    yield doc
    # Cleanup
    try:
        api_client.delete(f"{BASE_URL}/api/documenti/{doc['doc_id']}")
    except:
        pass


class TestC1Categories:
    """Test document categories endpoint."""
    
    def test_get_categories(self, api_client):
        """GET /api/committenza/categorie - returns document categories."""
        response = api_client.get(f"{BASE_URL}/api/committenza/categorie")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        categories = response.json()
        assert isinstance(categories, list)
        assert len(categories) > 0
        
        # Check expected categories exist
        codes = [c["code"] for c in categories]
        assert "contratto" in codes
        assert "capitolato" in codes
        assert "psc_duvri" in codes
        assert "allegato_sicurezza" in codes
        
        # Check structure
        for cat in categories:
            assert "code" in cat
            assert "label" in cat
        
        print(f"PASSED: GET /api/committenza/categorie - {len(categories)} categories returned")


class TestC1Packages:
    """Test C1.1: Package CRUD operations."""
    
    def test_create_package(self, api_client, test_commessa):
        """POST /api/committenza/packages - create analysis package."""
        package_data = {
            "commessa_id": test_commessa["commessa_id"],
            "title": f"TEST_C1_Package_{uuid.uuid4().hex[:8]}",
            "document_refs": []
        }
        response = api_client.post(f"{BASE_URL}/api/committenza/packages", json=package_data)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        pkg = response.json()
        assert "package_id" in pkg
        assert pkg["commessa_id"] == test_commessa["commessa_id"]
        assert pkg["status"] == "uploaded"
        assert "document_refs" in pkg
        assert "created_at" in pkg
        
        print(f"PASSED: POST /api/committenza/packages - created {pkg['package_id']}")
    
    def test_create_package_invalid_commessa(self, api_client):
        """POST /api/committenza/packages - fails with invalid commessa."""
        package_data = {
            "commessa_id": "invalid_commessa_id",
            "title": "Should Fail"
        }
        response = api_client.post(f"{BASE_URL}/api/committenza/packages", json=package_data)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("PASSED: POST /api/committenza/packages - correctly rejects invalid commessa")
    
    def test_list_packages(self, api_client, test_commessa):
        """GET /api/committenza/packages - list packages with filter."""
        # Create a package first
        package_data = {
            "commessa_id": test_commessa["commessa_id"],
            "title": f"TEST_C1_ListPkg_{uuid.uuid4().hex[:8]}"
        }
        api_client.post(f"{BASE_URL}/api/committenza/packages", json=package_data)
        
        # List all packages
        response = api_client.get(f"{BASE_URL}/api/committenza/packages")
        assert response.status_code == 200
        packages = response.json()
        assert isinstance(packages, list)
        
        # List with commessa_id filter
        response = api_client.get(f"{BASE_URL}/api/committenza/packages?commessa_id={test_commessa['commessa_id']}")
        assert response.status_code == 200
        filtered = response.json()
        assert all(p["commessa_id"] == test_commessa["commessa_id"] for p in filtered)
        
        print(f"PASSED: GET /api/committenza/packages - {len(packages)} total, {len(filtered)} filtered")
    
    def test_get_single_package(self, api_client, test_commessa):
        """GET /api/committenza/packages/{id} - get single package."""
        # Create a package first
        package_data = {
            "commessa_id": test_commessa["commessa_id"],
            "title": f"TEST_C1_GetPkg_{uuid.uuid4().hex[:8]}"
        }
        response = api_client.post(f"{BASE_URL}/api/committenza/packages", json=package_data)
        pkg = response.json()
        
        response = api_client.get(f"{BASE_URL}/api/committenza/packages/{pkg['package_id']}")
        assert response.status_code == 200
        
        fetched = response.json()
        assert fetched["package_id"] == pkg["package_id"]
        assert fetched["commessa_id"] == test_commessa["commessa_id"]
        
        print(f"PASSED: GET /api/committenza/packages/{pkg['package_id']}")
    
    def test_get_package_not_found(self, api_client):
        """GET /api/committenza/packages/{id} - returns 404 for invalid ID."""
        response = api_client.get(f"{BASE_URL}/api/committenza/packages/invalid_pkg_id")
        assert response.status_code == 404
        print("PASSED: GET /api/committenza/packages/invalid - returns 404")


class TestC1PackageDocuments:
    """Test adding/removing documents from packages."""
    
    def test_add_document_to_package(self, api_client, test_commessa, test_archive_doc):
        """POST /api/committenza/packages/{id}/documents - add archive doc."""
        # Create package
        pkg_data = {
            "commessa_id": test_commessa["commessa_id"],
            "title": f"TEST_C1_DocPkg_{uuid.uuid4().hex[:8]}"
        }
        response = api_client.post(f"{BASE_URL}/api/committenza/packages", json=pkg_data)
        assert response.status_code == 200
        pkg = response.json()
        
        # Add document
        add_data = {
            "doc_id": test_archive_doc["doc_id"],
            "category": "contratto"
        }
        response = api_client.post(
            f"{BASE_URL}/api/committenza/packages/{pkg['package_id']}/documents",
            json=add_data
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        updated_pkg = response.json()
        assert len(updated_pkg["document_refs"]) == 1
        assert updated_pkg["document_refs"][0]["doc_id"] == test_archive_doc["doc_id"]
        assert updated_pkg["document_refs"][0]["category"] == "contratto"
        
        print(f"PASSED: POST /api/committenza/packages/{pkg['package_id']}/documents")
        return pkg
    
    def test_add_duplicate_document(self, api_client, test_commessa, test_archive_doc):
        """POST /api/committenza/packages/{id}/documents - rejects duplicate."""
        # Create package and add doc
        pkg_data = {
            "commessa_id": test_commessa["commessa_id"],
            "title": f"TEST_C1_DupPkg_{uuid.uuid4().hex[:8]}"
        }
        response = api_client.post(f"{BASE_URL}/api/committenza/packages", json=pkg_data)
        pkg = response.json()
        
        # Add document first time
        add_data = {"doc_id": test_archive_doc["doc_id"], "category": "contratto"}
        api_client.post(f"{BASE_URL}/api/committenza/packages/{pkg['package_id']}/documents", json=add_data)
        
        # Try to add same document again
        response = api_client.post(
            f"{BASE_URL}/api/committenza/packages/{pkg['package_id']}/documents",
            json=add_data
        )
        assert response.status_code == 400
        assert "gia presente" in response.json().get("detail", "").lower()
        
        print("PASSED: Duplicate document correctly rejected")
    
    def test_remove_document_from_package(self, api_client, test_commessa, test_archive_doc):
        """DELETE /api/committenza/packages/{id}/documents/{doc_id} - remove doc."""
        # Create package and add doc
        pkg_data = {
            "commessa_id": test_commessa["commessa_id"],
            "title": f"TEST_C1_RemPkg_{uuid.uuid4().hex[:8]}"
        }
        response = api_client.post(f"{BASE_URL}/api/committenza/packages", json=pkg_data)
        pkg = response.json()
        
        # Add document
        add_data = {"doc_id": test_archive_doc["doc_id"], "category": "contratto"}
        api_client.post(f"{BASE_URL}/api/committenza/packages/{pkg['package_id']}/documents", json=add_data)
        
        # Remove document
        response = api_client.delete(
            f"{BASE_URL}/api/committenza/packages/{pkg['package_id']}/documents/{test_archive_doc['doc_id']}"
        )
        assert response.status_code == 200
        
        updated_pkg = response.json()
        assert len(updated_pkg["document_refs"]) == 0
        
        print(f"PASSED: DELETE /api/committenza/packages/{pkg['package_id']}/documents/{test_archive_doc['doc_id']}")


class TestC1AIAnalysis:
    """Test C1.2: AI Analysis endpoint."""
    
    def test_analyze_empty_package(self, api_client, test_commessa):
        """POST /api/committenza/analizza/{id} - fails with empty package."""
        # Create empty package
        pkg_data = {
            "commessa_id": test_commessa["commessa_id"],
            "title": f"TEST_C1_EmptyPkg_{uuid.uuid4().hex[:8]}"
        }
        response = api_client.post(f"{BASE_URL}/api/committenza/packages", json=pkg_data)
        pkg = response.json()
        
        # Try to analyze
        response = api_client.post(f"{BASE_URL}/api/committenza/analizza/{pkg['package_id']}")
        assert response.status_code == 400
        assert "nessun documento" in response.json().get("detail", "").lower()
        
        print("PASSED: POST /api/committenza/analizza - correctly rejects empty package")
    
    def test_analyze_package_llm_error_handling(self, api_client, test_commessa, test_archive_doc):
        """POST /api/committenza/analizza/{id} - handles LLM errors gracefully."""
        # Create package with document
        pkg_data = {
            "commessa_id": test_commessa["commessa_id"],
            "title": f"TEST_C1_AnalyzePkg_{uuid.uuid4().hex[:8]}"
        }
        response = api_client.post(f"{BASE_URL}/api/committenza/packages", json=pkg_data)
        pkg = response.json()
        
        # Add document
        add_data = {"doc_id": test_archive_doc["doc_id"], "category": "contratto"}
        api_client.post(f"{BASE_URL}/api/committenza/packages/{pkg['package_id']}/documents", json=add_data)
        
        # Try to analyze - may fail if no LLM key, but should return proper error
        response = api_client.post(f"{BASE_URL}/api/committenza/analizza/{pkg['package_id']}")
        
        # Either succeeds (200) or returns proper error (400)
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 400:
            detail = response.json().get("detail", "")
            # Should be a meaningful error about LLM/API key
            assert any(x in detail.lower() for x in ["api key", "llm", "ai", "configurata", "errore"])
            print(f"PASSED: POST /api/committenza/analizza - LLM error handled: {detail}")
        else:
            analysis = response.json()
            assert "analysis_id" in analysis
            print(f"PASSED: POST /api/committenza/analizza - Analysis created: {analysis['analysis_id']}")


class TestC1AnalysisCRUD:
    """Test analysis list/get endpoints."""
    
    def test_list_analyses(self, api_client, test_commessa):
        """GET /api/committenza/analisi - list analyses."""
        response = api_client.get(f"{BASE_URL}/api/committenza/analisi")
        assert response.status_code == 200
        analyses = response.json()
        assert isinstance(analyses, list)
        
        # Test with filter
        response = api_client.get(f"{BASE_URL}/api/committenza/analisi?commessa_id={test_commessa['commessa_id']}")
        assert response.status_code == 200
        
        print(f"PASSED: GET /api/committenza/analisi - {len(analyses)} analyses")
    
    def test_get_analysis_not_found(self, api_client):
        """GET /api/committenza/analisi/{id} - returns 404 for invalid ID."""
        response = api_client.get(f"{BASE_URL}/api/committenza/analisi/invalid_analysis_id")
        assert response.status_code == 404
        print("PASSED: GET /api/committenza/analisi/invalid - returns 404")


class TestC1ReviewApproveGenerateViaAPI:
    """Test C1.3 and C1.4: Review, Approve, and Generate Obligations.
    
    Uses a helper endpoint to seed test data via API instead of direct MongoDB.
    """
    
    @pytest.fixture
    def seeded_analysis_via_api(self, api_client, test_commessa, test_archive_doc):
        """Create a package, add doc, and try to analyze. If analysis fails, skip tests."""
        # Create package
        pkg_data = {
            "commessa_id": test_commessa["commessa_id"],
            "title": f"TEST_C1_ReviewPkg_{uuid.uuid4().hex[:8]}"
        }
        response = api_client.post(f"{BASE_URL}/api/committenza/packages", json=pkg_data)
        assert response.status_code == 200
        pkg = response.json()
        
        # Add document
        add_data = {"doc_id": test_archive_doc["doc_id"], "category": "contratto"}
        api_client.post(f"{BASE_URL}/api/committenza/packages/{pkg['package_id']}/documents", json=add_data)
        
        # Try to analyze
        response = api_client.post(f"{BASE_URL}/api/committenza/analizza/{pkg['package_id']}")
        
        if response.status_code != 200:
            pytest.skip(f"AI analysis not available: {response.json().get('detail', 'Unknown error')}")
        
        analysis = response.json()
        yield analysis
    
    def test_review_analysis(self, api_client, seeded_analysis_via_api):
        """PATCH /api/committenza/analisi/{id}/review - save human review."""
        analysis = seeded_analysis_via_api
        
        # Build review data based on what's in the analysis
        obligations_review = [
            {"code": o["code"], "confirmed": True, "note": "Test confirmed"}
            for o in analysis.get("extracted_obligations", [])[:2]  # Confirm first 2
        ]
        anomalies_review = [
            {"code": a["code"], "confirmed": True, "note": ""}
            for a in analysis.get("anomalies", [])[:1]
        ]
        mismatches_review = [
            {"code": m["code"], "confirmed": True, "note": ""}
            for m in analysis.get("mismatches", [])[:1]
        ]
        questions_answers = [
            {"qid": q["qid"], "answer": "Test answer"}
            for q in analysis.get("open_questions", [])[:1]
        ]
        
        review_data = {
            "obligations_review": obligations_review,
            "anomalies_review": anomalies_review,
            "mismatches_review": mismatches_review,
            "questions_answers": questions_answers
        }
        
        response = api_client.patch(
            f"{BASE_URL}/api/committenza/analisi/{analysis['analysis_id']}/review",
            json=review_data
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        updated = response.json()
        assert updated["status"] == "in_review"
        assert updated["human_review"]["review_status"] == "reviewed"
        
        print(f"PASSED: PATCH /api/committenza/analisi/{analysis['analysis_id']}/review")
    
    def test_approve_analysis(self, api_client, seeded_analysis_via_api):
        """POST /api/committenza/analisi/{id}/approve - approve and create snapshot."""
        analysis = seeded_analysis_via_api
        
        # First review to confirm items
        obligations_review = [
            {"code": o["code"], "confirmed": True, "note": ""}
            for o in analysis.get("extracted_obligations", [])
        ]
        review_data = {
            "obligations_review": obligations_review,
            "anomalies_review": [],
            "mismatches_review": [],
            "questions_answers": []
        }
        api_client.patch(
            f"{BASE_URL}/api/committenza/analisi/{analysis['analysis_id']}/review",
            json=review_data
        )
        
        # Now approve
        response = api_client.post(f"{BASE_URL}/api/committenza/analisi/{analysis['analysis_id']}/approve")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        approved = response.json()
        assert approved["status"] == "approved"
        assert approved["official_snapshot"] is not None
        
        print(f"PASSED: POST /api/committenza/analisi/{analysis['analysis_id']}/approve")
    
    def test_generate_obblighi(self, api_client, seeded_analysis_via_api):
        """POST /api/committenza/analisi/{id}/genera-obblighi - generate obligations."""
        analysis = seeded_analysis_via_api
        
        # Review and approve first
        obligations_review = [
            {"code": o["code"], "confirmed": True, "note": ""}
            for o in analysis.get("extracted_obligations", [])
        ]
        api_client.patch(
            f"{BASE_URL}/api/committenza/analisi/{analysis['analysis_id']}/review",
            json={"obligations_review": obligations_review, "anomalies_review": [], "mismatches_review": [], "questions_answers": []}
        )
        api_client.post(f"{BASE_URL}/api/committenza/analisi/{analysis['analysis_id']}/approve")
        
        # Generate obligations
        response = api_client.post(
            f"{BASE_URL}/api/committenza/analisi/{analysis['analysis_id']}/genera-obblighi"
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        result = response.json()
        assert "created" in result
        assert "updated" in result
        
        print(f"PASSED: POST /api/committenza/analisi/{analysis['analysis_id']}/genera-obblighi - created {result['created']}")
    
    def test_generate_obblighi_deduplication(self, api_client, seeded_analysis_via_api):
        """POST /api/committenza/analisi/{id}/genera-obblighi - deduplication works."""
        analysis = seeded_analysis_via_api
        
        # Review and approve first
        obligations_review = [
            {"code": o["code"], "confirmed": True, "note": ""}
            for o in analysis.get("extracted_obligations", [])
        ]
        api_client.patch(
            f"{BASE_URL}/api/committenza/analisi/{analysis['analysis_id']}/review",
            json={"obligations_review": obligations_review, "anomalies_review": [], "mismatches_review": [], "questions_answers": []}
        )
        api_client.post(f"{BASE_URL}/api/committenza/analisi/{analysis['analysis_id']}/approve")
        
        # First call
        response1 = api_client.post(
            f"{BASE_URL}/api/committenza/analisi/{analysis['analysis_id']}/genera-obblighi"
        )
        assert response1.status_code == 200
        result1 = response1.json()
        
        # Second call - should not create duplicates
        response2 = api_client.post(
            f"{BASE_URL}/api/committenza/analisi/{analysis['analysis_id']}/genera-obblighi"
        )
        assert response2.status_code == 200
        result2 = response2.json()
        
        # Second call should create 0 new (all deduplicated)
        assert result2["created"] == 0, f"Expected 0 created on second call, got {result2['created']}"
        
        print(f"PASSED: Deduplication works - first call: {result1['created']} created, second call: {result2['created']} created")


class TestC1ErrorHandling:
    """Test error handling for various edge cases."""
    
    def test_generate_obblighi_not_approved(self, api_client, test_commessa, test_archive_doc):
        """POST /api/committenza/analisi/{id}/genera-obblighi - fails if not approved."""
        # Create package with document
        pkg_data = {
            "commessa_id": test_commessa["commessa_id"],
            "title": f"TEST_C1_NotApproved_{uuid.uuid4().hex[:8]}"
        }
        response = api_client.post(f"{BASE_URL}/api/committenza/packages", json=pkg_data)
        pkg = response.json()
        
        # Add document
        add_data = {"doc_id": test_archive_doc["doc_id"], "category": "contratto"}
        api_client.post(f"{BASE_URL}/api/committenza/packages/{pkg['package_id']}/documents", json=add_data)
        
        # Try to analyze
        response = api_client.post(f"{BASE_URL}/api/committenza/analizza/{pkg['package_id']}")
        
        if response.status_code != 200:
            pytest.skip("AI analysis not available")
        
        analysis = response.json()
        
        # Try to generate without approving
        response = api_client.post(f"{BASE_URL}/api/committenza/analisi/{analysis['analysis_id']}/genera-obblighi")
        assert response.status_code == 400
        assert "approvata" in response.json().get("detail", "").lower()
        
        print("PASSED: genera-obblighi correctly rejects non-approved analysis")
    
    def test_review_nonexistent_analysis(self, api_client):
        """PATCH /api/committenza/analisi/{id}/review - returns 400 for invalid ID."""
        response = api_client.patch(
            f"{BASE_URL}/api/committenza/analisi/invalid_id/review",
            json={"obligations_review": [], "anomalies_review": [], "mismatches_review": [], "questions_answers": []}
        )
        assert response.status_code == 400
        print("PASSED: Review nonexistent analysis returns 400")
    
    def test_approve_nonexistent_analysis(self, api_client):
        """POST /api/committenza/analisi/{id}/approve - returns 400 for invalid ID."""
        response = api_client.post(f"{BASE_URL}/api/committenza/analisi/invalid_id/approve")
        assert response.status_code == 400
        print("PASSED: Approve nonexistent analysis returns 400")


class TestC1Integration:
    """Integration tests for the full C1 flow."""
    
    def test_full_flow_without_llm(self, api_client, test_commessa, test_archive_doc):
        """Test the full C1 flow - package creation, doc management."""
        # 1. Create package
        pkg_data = {
            "commessa_id": test_commessa["commessa_id"],
            "title": f"TEST_C1_FullFlow_{uuid.uuid4().hex[:8]}"
        }
        response = api_client.post(f"{BASE_URL}/api/committenza/packages", json=pkg_data)
        assert response.status_code == 200
        pkg = response.json()
        print(f"Step 1: Created package {pkg['package_id']}")
        
        # 2. Add document
        add_data = {"doc_id": test_archive_doc["doc_id"], "category": "contratto"}
        response = api_client.post(
            f"{BASE_URL}/api/committenza/packages/{pkg['package_id']}/documents",
            json=add_data
        )
        assert response.status_code == 200
        print(f"Step 2: Added document to package")
        
        # 3. Verify package has document
        response = api_client.get(f"{BASE_URL}/api/committenza/packages/{pkg['package_id']}")
        assert response.status_code == 200
        pkg = response.json()
        assert len(pkg["document_refs"]) == 1
        print(f"Step 3: Verified package has 1 document")
        
        # 4. Try to analyze (may fail without LLM)
        response = api_client.post(f"{BASE_URL}/api/committenza/analizza/{pkg['package_id']}")
        if response.status_code == 200:
            analysis = response.json()
            print(f"Step 4: Analysis created: {analysis['analysis_id']}")
            
            # 5. Review
            obligations_review = [
                {"code": o["code"], "confirmed": True, "note": ""}
                for o in analysis.get("extracted_obligations", [])
            ]
            response = api_client.patch(
                f"{BASE_URL}/api/committenza/analisi/{analysis['analysis_id']}/review",
                json={"obligations_review": obligations_review, "anomalies_review": [], "mismatches_review": [], "questions_answers": []}
            )
            assert response.status_code == 200
            print(f"Step 5: Review saved")
            
            # 6. Approve
            response = api_client.post(f"{BASE_URL}/api/committenza/analisi/{analysis['analysis_id']}/approve")
            assert response.status_code == 200
            print(f"Step 6: Analysis approved")
            
            # 7. Generate obligations
            response = api_client.post(f"{BASE_URL}/api/committenza/analisi/{analysis['analysis_id']}/genera-obblighi")
            assert response.status_code == 200
            result = response.json()
            print(f"Step 7: Generated {result['created']} obligations")
            
            # 8. Verify deduplication
            response = api_client.post(f"{BASE_URL}/api/committenza/analisi/{analysis['analysis_id']}/genera-obblighi")
            assert response.status_code == 200
            result2 = response.json()
            assert result2["created"] == 0
            print(f"Step 8: Deduplication verified (0 new on second call)")
        else:
            print(f"Step 4: Analysis skipped (LLM not available): {response.json().get('detail', '')}")
        
        # 5. Remove document
        response = api_client.delete(
            f"{BASE_URL}/api/committenza/packages/{pkg['package_id']}/documents/{test_archive_doc['doc_id']}"
        )
        assert response.status_code == 200
        print(f"Step 5: Removed document from package")
        
        print("PASSED: Full C1 flow completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
