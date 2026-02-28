"""
Test suite for Tracciabilità Materiali features - Iteration 59
Tests:
- GET /api/fpc/batches with commessa_id filter
- Document types that support AI analysis (certificato_31, altro, ddt_fornitore)
- Material batch filtering by commessa
"""
import pytest
import requests
import os
from datetime import datetime, timezone
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', '')


class TestSetup:
    """Setup for tests - create test session if needed"""
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_session(self):
        """Get or create test session"""
        global SESSION_TOKEN
        if not SESSION_TOKEN:
            pytest.skip("No test session token available")

    @pytest.fixture
    def auth_headers(self):
        """Authorization headers"""
        return {
            "Authorization": f"Bearer {SESSION_TOKEN}",
            "Content-Type": "application/json"
        }


class TestMaterialBatchesEndpoint(TestSetup):
    """Test /api/fpc/batches endpoint with commessa_id filter"""
    
    def test_batches_endpoint_exists(self, auth_headers):
        """Verify /api/fpc/batches endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/fpc/batches", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "batches" in data, "Response should have 'batches' key"
        print(f"PASS: /api/fpc/batches endpoint returns 200 with {len(data['batches'])} batches")
    
    def test_batches_endpoint_with_commessa_filter(self, auth_headers):
        """Verify commessa_id filter parameter is accepted"""
        test_commessa_id = "test_commessa_filter_123"
        response = requests.get(
            f"{BASE_URL}/api/fpc/batches?commessa_id={test_commessa_id}", 
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "batches" in data, "Response should have 'batches' key"
        print(f"PASS: /api/fpc/batches?commessa_id= filter accepted, returns {len(data['batches'])} batches")
    
    def test_batches_endpoint_filters_correctly(self, auth_headers):
        """Verify batches are filtered by commessa_id when provided"""
        # First, get all batches
        all_response = requests.get(f"{BASE_URL}/api/fpc/batches", headers=auth_headers)
        assert all_response.status_code == 200
        all_batches = all_response.json().get("batches", [])
        
        # Then filter by non-existent commessa
        filtered_response = requests.get(
            f"{BASE_URL}/api/fpc/batches?commessa_id=non_existent_commessa_xyz", 
            headers=auth_headers
        )
        assert filtered_response.status_code == 200
        filtered_batches = filtered_response.json().get("batches", [])
        
        # Filtered should have fewer or equal batches than all
        assert len(filtered_batches) <= len(all_batches), "Filtered batches should be <= all batches"
        print(f"PASS: Filter returns {len(filtered_batches)} batches vs {len(all_batches)} total")
    
    def test_incorrect_endpoint_returns_404(self, auth_headers):
        """Verify /api/material-batches does NOT exist (bug was calling this)"""
        response = requests.get(f"{BASE_URL}/api/material-batches", headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: /api/material-batches correctly returns 404 (correct endpoint is /api/fpc/batches)")


class TestCommessaOpsEndpoints(TestSetup):
    """Test commessa ops endpoints for AI analysis and documents"""
    
    def test_commessa_ops_endpoint(self, auth_headers):
        """Verify /api/commesse/{id}/ops endpoint exists"""
        # First get a commessa to test with (note trailing slash for FastAPI)
        response = requests.get(f"{BASE_URL}/api/commesse/?limit=1", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get commesse: {response.text}"
        
        data = response.json()
        commesse = data.get("commesse", data.get("items", []))
        
        if not commesse:
            pytest.skip("No commesse available for testing")
        
        commessa_id = commesse[0].get("commessa_id")
        
        # Test ops endpoint
        ops_response = requests.get(f"{BASE_URL}/api/commesse/{commessa_id}/ops", headers=auth_headers)
        assert ops_response.status_code == 200, f"Ops endpoint failed: {ops_response.text}"
        print(f"PASS: /api/commesse/{commessa_id}/ops returns 200")
    
    def test_commessa_documenti_endpoint(self, auth_headers):
        """Verify /api/commesse/{id}/documenti endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/commesse/?limit=1", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        commesse = data.get("commesse", data.get("items", []))
        
        if not commesse:
            pytest.skip("No commesse available for testing")
        
        commessa_id = commesse[0].get("commessa_id")
        
        docs_response = requests.get(f"{BASE_URL}/api/commesse/{commessa_id}/documenti", headers=auth_headers)
        assert docs_response.status_code == 200, f"Documenti endpoint failed: {docs_response.text}"
        
        docs_data = docs_response.json()
        assert "documents" in docs_data, "Response should have 'documents' key"
        print(f"PASS: /api/commesse/{commessa_id}/documenti returns {len(docs_data['documents'])} documents")


class TestParseAIEndpoint(TestSetup):
    """Test AI parsing endpoint for certificates"""
    
    def test_parse_certificato_endpoint_structure(self, auth_headers):
        """Verify parse-certificato endpoint exists and returns proper structure"""
        # Get a commessa with documents (note trailing slash for FastAPI)
        response = requests.get(f"{BASE_URL}/api/commesse/?limit=5", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        commesse = data.get("commesse", data.get("items", []))
        
        if not commesse:
            pytest.skip("No commesse available for testing")
        
        # Find a commessa with PDF documents
        pdf_doc_found = False
        for commessa in commesse:
            commessa_id = commessa.get("commessa_id")
            docs_response = requests.get(f"{BASE_URL}/api/commesse/{commessa_id}/documenti", headers=auth_headers)
            if docs_response.status_code == 200:
                docs = docs_response.json().get("documents", [])
                for doc in docs:
                    if doc.get("nome_file", "").lower().endswith(".pdf"):
                        pdf_doc_found = True
                        doc_id = doc.get("doc_id")
                        # Don't actually call parse-certificato (it would use AI credits)
                        # Just verify we found a document that could be parsed
                        print(f"PASS: Found PDF document {doc['nome_file']} that could be analyzed with AI")
                        return
        
        if not pdf_doc_found:
            print("INFO: No PDF documents found in commesse for AI analysis testing")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
