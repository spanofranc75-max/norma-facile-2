"""
Test Suite: Fatture Ricevute SDI Deduplication Fix
================================================================
Tests the deduplication logic for import-xml, import-xml-batch, and preview-xml endpoints.
Dedup logic uses $or: (numero+piva+data) OR (piva+data+totale)

Test Cases:
- TEST 1: First import of test_xml_2rate.xml → 200/201 OK
- TEST 2: Re-import same file → HTTP 409 "Fattura già importata"
- TEST 3: Preview of same file → duplicata=true
- TEST 4: Batch import with 1 new + 1 already imported → imported=1, skipped=1
- TEST 5: Batch import with both already imported → imported=0, skipped=2
- TEST 6: MongoDB check - no duplicate fr_ids
- TEST 7: MongoDB check - unique index on fr_id exists
"""

import pytest
import requests
import os
from pymongo import MongoClient

# Configuration
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_dedup_1772991921856"  # Valid session for user_97c773827822
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

# Test XML file paths
TEST_XML_2RATE_PATH = "/app/backend/tests/test_xml_2rate.xml"
TEST_XML_NOPAG_PATH = "/app/backend/tests/test_xml_nopagamento.xml"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
    })
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


@pytest.fixture(scope="module")
def mongo_client():
    """MongoDB client for direct DB checks."""
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


@pytest.fixture(scope="module", autouse=True)
def cleanup_before_and_after(mongo_client):
    """Clean up test documents before and after test suite."""
    # Before: Clean any leftover TEST- documents
    result = mongo_client.fatture_ricevute.delete_many({
        "numero_documento": {"$regex": "^TEST-", "$options": "i"}
    })
    print(f"\n[SETUP] Cleaned up {result.deleted_count} leftover test documents")
    
    yield
    
    # After: Clean up test documents
    result = mongo_client.fatture_ricevute.delete_many({
        "numero_documento": {"$regex": "^TEST-", "$options": "i"}
    })
    print(f"\n[TEARDOWN] Cleaned up {result.deleted_count} test documents")


class TestFattureDeduplication:
    """Sequential test class for deduplication fix verification."""
    
    # Class-level state to track imported documents
    imported_fr_ids = []
    
    def test_01_first_import_2rate_xml(self, api_client):
        """TEST 1: First import of test_xml_2rate.xml should succeed."""
        with open(TEST_XML_2RATE_PATH, 'rb') as f:
            files = {'file': ('test_xml_2rate.xml', f, 'application/xml')}
            # Remove Content-Type from headers for multipart
            headers = {"Cookie": f"session_token={SESSION_TOKEN}"}
            response = requests.post(
                f"{BASE_URL}/api/fatture-ricevute/import-xml",
                files=files,
                cookies={"session_token": SESSION_TOKEN}
            )
        
        print(f"\n[TEST 1] First import response: {response.status_code}")
        print(f"Response body: {response.text[:500]}")
        
        # Should succeed (200 or 201)
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "fattura" in data, "Response should contain 'fattura'"
        assert data["fattura"]["numero_documento"] == "TEST-2RATE-001"
        
        # Store fr_id for later cleanup
        if data.get("fattura", {}).get("fr_id"):
            TestFattureDeduplication.imported_fr_ids.append(data["fattura"]["fr_id"])
        
        print(f"✓ TEST 1 PASSED: First import succeeded with fr_id={data['fattura'].get('fr_id')}")

    def test_02_reimport_same_xml_returns_409(self, api_client):
        """TEST 2: Re-import of the SAME file should return HTTP 409."""
        with open(TEST_XML_2RATE_PATH, 'rb') as f:
            files = {'file': ('test_xml_2rate.xml', f, 'application/xml')}
            response = requests.post(
                f"{BASE_URL}/api/fatture-ricevute/import-xml",
                files=files,
                cookies={"session_token": SESSION_TOKEN}
            )
        
        print(f"\n[TEST 2] Re-import response: {response.status_code}")
        print(f"Response body: {response.text[:500]}")
        
        # MUST return 409 Conflict
        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data, "Response should contain 'detail'"
        assert "già importata" in data["detail"].lower() or "already" in data["detail"].lower(), \
            f"Error message should mention 'già importata': {data['detail']}"
        
        print(f"✓ TEST 2 PASSED: Re-import correctly returned 409 with message: {data['detail']}")

    def test_03_preview_existing_xml_shows_duplicata_true(self, api_client):
        """TEST 3: Preview of already imported file should show duplicata=true."""
        with open(TEST_XML_2RATE_PATH, 'rb') as f:
            files = {'file': ('test_xml_2rate.xml', f, 'application/xml')}
            response = requests.post(
                f"{BASE_URL}/api/fatture-ricevute/preview-xml",
                files=files,
                cookies={"session_token": SESSION_TOKEN}
            )
        
        print(f"\n[TEST 3] Preview response: {response.status_code}")
        print(f"Response body: {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "duplicata" in data, "Response should contain 'duplicata' field"
        assert data["duplicata"] == True, f"Expected duplicata=true, got {data['duplicata']}"
        
        print(f"✓ TEST 3 PASSED: Preview correctly shows duplicata=true")

    def test_04_batch_import_1_new_1_existing(self, api_client):
        """TEST 4: Batch import with 1 new + 1 already imported → imported=1, skipped=1."""
        # test_xml_2rate.xml is already imported (should be skipped)
        with open(TEST_XML_2RATE_PATH, 'rb') as f1, open(TEST_XML_NOPAG_PATH, 'rb') as f2:
            files = [
                ('files', ('test_xml_2rate.xml', f1.read(), 'application/xml')),
                ('files', ('test_xml_nopagamento.xml', f2.read(), 'application/xml'))
            ]
            response = requests.post(
                f"{BASE_URL}/api/fatture-ricevute/import-xml-batch",
                files=files,
                cookies={"session_token": SESSION_TOKEN}
            )
        
        print(f"\n[TEST 4] Batch import response: {response.status_code}")
        print(f"Response body: {response.text[:800]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["imported"] == 1, f"Expected imported=1, got {data['imported']}"
        assert data["skipped"] == 1, f"Expected skipped=1, got {data['skipped']}"
        assert len(data.get("dettaglio_saltate", [])) >= 1, "Should have dettaglio_saltate"
        
        # Verify dettaglio_saltate has the right info
        saltate = data.get("dettaglio_saltate", [])
        assert any(s.get("numero") == "TEST-2RATE-001" or "2RATE" in s.get("numero", "") for s in saltate), \
            f"Should skip TEST-2RATE-001, got: {saltate}"
        
        # Store the new fr_id
        for fat in data.get("fatture", []):
            if fat.get("numero") == "TEST-NOPAG-001":
                print(f"Imported new fattura: {fat}")
        
        print(f"✓ TEST 4 PASSED: Batch imported 1, skipped 1 with dettaglio_saltate")

    def test_05_batch_import_both_existing(self, api_client):
        """TEST 5: Batch import with BOTH files already imported → imported=0, skipped=2."""
        with open(TEST_XML_2RATE_PATH, 'rb') as f1, open(TEST_XML_NOPAG_PATH, 'rb') as f2:
            files = [
                ('files', ('test_xml_2rate.xml', f1.read(), 'application/xml')),
                ('files', ('test_xml_nopagamento.xml', f2.read(), 'application/xml'))
            ]
            response = requests.post(
                f"{BASE_URL}/api/fatture-ricevute/import-xml-batch",
                files=files,
                cookies={"session_token": SESSION_TOKEN}
            )
        
        print(f"\n[TEST 5] Batch import (both existing) response: {response.status_code}")
        print(f"Response body: {response.text[:800]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["imported"] == 0, f"Expected imported=0, got {data['imported']}"
        assert data["skipped"] == 2, f"Expected skipped=2, got {data['skipped']}"
        assert len(data.get("dettaglio_saltate", [])) == 2, f"Should have 2 dettaglio_saltate entries"
        
        print(f"✓ TEST 5 PASSED: Batch correctly skipped both (imported=0, skipped=2)")

    def test_06_no_duplicate_fr_ids_in_db(self, mongo_client):
        """TEST 6: Verify no duplicate fr_ids exist in fatture_ricevute collection."""
        pipeline = [
            {"$group": {"_id": "$fr_id", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ]
        duplicates = list(mongo_client.fatture_ricevute.aggregate(pipeline))
        
        print(f"\n[TEST 6] Duplicate fr_id check: found {len(duplicates)} duplicates")
        if duplicates:
            print(f"Duplicates: {duplicates}")
        
        assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate fr_ids: {duplicates}"
        
        print(f"✓ TEST 6 PASSED: No duplicate fr_ids in database")

    def test_07_unique_index_on_fr_id_exists(self, mongo_client):
        """TEST 7: Verify unique index exists on fatture_ricevute.fr_id."""
        indexes = mongo_client.fatture_ricevute.index_information()
        
        print(f"\n[TEST 7] Checking indexes on fatture_ricevute collection")
        print(f"Found indexes: {list(indexes.keys())}")
        
        # Look for an index on fr_id that is unique
        fr_id_unique_index = None
        for idx_name, idx_info in indexes.items():
            key = idx_info.get("key", [])
            # key is a list of tuples like [('fr_id', 1)]
            if any(k[0] == "fr_id" for k in key):
                print(f"Found fr_id index: {idx_name} -> {idx_info}")
                if idx_info.get("unique", False):
                    fr_id_unique_index = idx_name
                    break
        
        assert fr_id_unique_index is not None, \
            f"No unique index found on fr_id. Available indexes: {indexes}"
        
        print(f"✓ TEST 7 PASSED: Unique index '{fr_id_unique_index}' exists on fr_id")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
