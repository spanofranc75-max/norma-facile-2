"""
Test suite for Company Document Versioning features - Iteration 88.
Tests the document revision upload, version history, and version download endpoints.
Endpoints tested:
- POST /api/company/documents/{doc_id}/revision - Upload new revision
- GET /api/company/documents/{doc_id}/versions - Get version history
- GET /api/company/documents/{doc_id}/versions/{version_num}/download - Download specific version
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_3ce08f7a2e65452aa6e466779454ceb0"


@pytest.fixture
def api_session():
    """Authenticated session with cookie"""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestDocumentVersioningAPI:
    """Test versioning-specific endpoints"""
    
    def test_list_documents_includes_version_fields(self, api_session):
        """Verify list response includes version and version_count fields"""
        response = api_session.get(f"{BASE_URL}/api/company/documents/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that documents have version fields
        assert len(data["items"]) > 0, "Expected at least one document"
        
        for doc in data["items"]:
            assert "version" in doc, f"Document {doc['doc_id']} missing 'version' field"
            assert "version_count" in doc, f"Document {doc['doc_id']} missing 'version_count' field"
            assert isinstance(doc["version"], int), "version should be an integer"
            assert isinstance(doc["version_count"], int), "version_count should be an integer"
            assert doc["version"] >= 1, "version should be at least 1"
            assert doc["version_count"] >= 1, "version_count should be at least 1"
        
        print(f"✓ All {len(data['items'])} documents have version fields")
    
    def test_find_versioned_document(self, api_session):
        """Find the document with version > 1 (Manuale Qualita EN 1090 Rev A should have v3)"""
        response = api_session.get(f"{BASE_URL}/api/company/documents/?search=1090")
        
        assert response.status_code == 200
        data = response.json()
        
        # Find the versioned document
        versioned_doc = None
        for doc in data["items"]:
            if doc["version"] > 1:
                versioned_doc = doc
                break
        
        if versioned_doc:
            print(f"✓ Found versioned document: {versioned_doc['title']} (v{versioned_doc['version']}, {versioned_doc['version_count']} versions)")
            assert versioned_doc["version_count"] >= versioned_doc["version"], "version_count should be >= version"
        else:
            print("ℹ No documents with version > 1 found yet")
    
    def test_get_versions_for_existing_document(self, api_session):
        """GET /api/company/documents/{doc_id}/versions - retrieve version history"""
        # First get list to find a document
        list_resp = api_session.get(f"{BASE_URL}/api/company/documents/")
        assert list_resp.status_code == 200
        docs = list_resp.json()["items"]
        
        if len(docs) == 0:
            pytest.skip("No documents available")
        
        # Try to find a versioned document first
        doc = None
        for d in docs:
            if d.get("version", 1) > 1:
                doc = d
                break
        if not doc:
            doc = docs[0]
        
        doc_id = doc["doc_id"]
        
        # Get versions
        response = api_session.get(f"{BASE_URL}/api/company/documents/{doc_id}/versions")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "doc_id" in data, "Response should have doc_id"
        assert "title" in data, "Response should have title"
        assert "current_version" in data, "Response should have current_version"
        assert "versions" in data, "Response should have versions list"
        assert isinstance(data["versions"], list), "versions should be a list"
        assert len(data["versions"]) >= 1, "Should have at least one version (current)"
        
        # Verify version structure
        for v in data["versions"]:
            assert "version" in v, "Each version should have version number"
            assert "filename" in v, "Each version should have filename"
            assert "upload_date" in v, "Each version should have upload_date"
        
        print(f"✓ Get versions for {doc_id}: {len(data['versions'])} version(s), current=v{data['current_version']}")
    
    def test_get_versions_for_versioned_document(self, api_session):
        """Test version history for document with multiple versions"""
        # Search for the 1090 document which should have multiple versions
        list_resp = api_session.get(f"{BASE_URL}/api/company/documents/?search=1090")
        assert list_resp.status_code == 200
        docs = list_resp.json()["items"]
        
        # Find document with version > 1
        versioned_doc = None
        for d in docs:
            if d.get("version", 1) > 1:
                versioned_doc = d
                break
        
        if not versioned_doc:
            pytest.skip("No versioned document found")
        
        doc_id = versioned_doc["doc_id"]
        
        response = api_session.get(f"{BASE_URL}/api/company/documents/{doc_id}/versions")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify we have multiple versions
        assert len(data["versions"]) > 1, f"Expected multiple versions, got {len(data['versions'])}"
        
        # Verify versions are ordered (current first, then descending)
        first_version = data["versions"][0]
        assert first_version["version"] == data["current_version"], "First version should be current"
        
        print(f"✓ Versioned document {doc_id} has {len(data['versions'])} versions: {[v['version'] for v in data['versions']]}")
    
    def test_get_versions_nonexistent_document(self, api_session):
        """GET /api/company/documents/nonexistent/versions - should 404"""
        response = api_session.get(f"{BASE_URL}/api/company/documents/nonexistent_doc_12345/versions")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent document versions returns 404")
    
    def test_download_specific_version(self, api_session):
        """GET /api/company/documents/{doc_id}/versions/{num}/download - download specific version"""
        # Find a versioned document
        list_resp = api_session.get(f"{BASE_URL}/api/company/documents/?search=1090")
        assert list_resp.status_code == 200
        docs = list_resp.json()["items"]
        
        versioned_doc = None
        for d in docs:
            if d.get("version", 1) > 1:
                versioned_doc = d
                break
        
        if not versioned_doc:
            pytest.skip("No versioned document available for version download test")
        
        doc_id = versioned_doc["doc_id"]
        
        # Get versions list
        versions_resp = api_session.get(f"{BASE_URL}/api/company/documents/{doc_id}/versions")
        assert versions_resp.status_code == 200
        versions = versions_resp.json()["versions"]
        
        # Try downloading each version
        for v in versions:
            version_num = v["version"]
            download_resp = api_session.get(
                f"{BASE_URL}/api/company/documents/{doc_id}/versions/{version_num}/download"
            )
            
            assert download_resp.status_code == 200, f"Failed to download v{version_num}: {download_resp.status_code}"
            assert len(download_resp.content) > 0, f"v{version_num} content should not be empty"
            print(f"  ✓ Downloaded v{version_num}: {len(download_resp.content)} bytes")
        
        print(f"✓ All {len(versions)} versions downloadable for {doc_id}")
    
    def test_download_nonexistent_version(self, api_session):
        """GET /api/company/documents/{doc_id}/versions/999/download - should 404"""
        # Get any document
        list_resp = api_session.get(f"{BASE_URL}/api/company/documents/")
        docs = list_resp.json()["items"]
        
        if len(docs) == 0:
            pytest.skip("No documents available")
        
        doc_id = docs[0]["doc_id"]
        
        # Try to download non-existent version
        response = api_session.get(f"{BASE_URL}/api/company/documents/{doc_id}/versions/999/download")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Non-existent version download returns 404")


class TestRevisionUploadAPI:
    """Test revision upload endpoint"""
    
    def test_upload_revision_creates_new_version(self, api_session):
        """POST /api/company/documents/{doc_id}/revision - upload new revision"""
        # First create a new document
        unique_id = uuid.uuid4().hex[:6]
        
        files = {
            'file': (f'TEST_revision_base_{unique_id}.txt', f'Original content v1 {unique_id}'.encode(), 'text/plain')
        }
        form_data = {
            'title': f'TEST_RevisionTest_{unique_id}',
            'category': 'manuali',
            'tags': 'test,revision'
        }
        
        create_resp = api_session.post(
            f"{BASE_URL}/api/company/documents/",
            files=files,
            data=form_data
        )
        assert create_resp.status_code == 200, f"Failed to create: {create_resp.text}"
        
        created_doc = create_resp.json()
        doc_id = created_doc["doc_id"]
        assert created_doc["version"] == 1, "New doc should be v1"
        print(f"✓ Created base document {doc_id} v1")
        
        # Upload revision
        revision_files = {
            'file': (f'TEST_revision_v2_{unique_id}.txt', f'Revised content v2 {unique_id}'.encode(), 'text/plain')
        }
        revision_data = {
            'note': 'Test revision note'
        }
        
        revision_resp = api_session.post(
            f"{BASE_URL}/api/company/documents/{doc_id}/revision",
            files=revision_files,
            data=revision_data
        )
        
        assert revision_resp.status_code == 200, f"Revision upload failed: {revision_resp.status_code} {revision_resp.text}"
        
        revised_doc = revision_resp.json()
        assert revised_doc["version"] == 2, f"Expected v2, got v{revised_doc['version']}"
        assert revised_doc["version_count"] == 2, f"Expected 2 versions, got {revised_doc['version_count']}"
        print(f"✓ Uploaded revision: now v{revised_doc['version']} with {revised_doc['version_count']} versions")
        
        # Verify version history
        versions_resp = api_session.get(f"{BASE_URL}/api/company/documents/{doc_id}/versions")
        assert versions_resp.status_code == 200
        
        versions = versions_resp.json()["versions"]
        assert len(versions) == 2, f"Expected 2 versions in history, got {len(versions)}"
        assert versions[0]["version"] == 2, "Current (v2) should be first"
        assert versions[1]["version"] == 1, "Original (v1) should be second"
        print(f"✓ Version history shows: {[v['version'] for v in versions]}")
        
        # Cleanup
        api_session.delete(f"{BASE_URL}/api/company/documents/{doc_id}")
        print(f"✓ Cleaned up test document {doc_id}")
    
    def test_upload_multiple_revisions(self, api_session):
        """Test uploading multiple revisions to reach v3"""
        unique_id = uuid.uuid4().hex[:6]
        
        # Create base document
        files = {
            'file': (f'TEST_multi_v1_{unique_id}.txt', f'Version 1 {unique_id}'.encode(), 'text/plain')
        }
        form_data = {
            'title': f'TEST_MultiRevision_{unique_id}',
            'category': 'procedure',
            'tags': 'test,multi-revision'
        }
        
        create_resp = api_session.post(
            f"{BASE_URL}/api/company/documents/",
            files=files,
            data=form_data
        )
        assert create_resp.status_code == 200
        doc_id = create_resp.json()["doc_id"]
        print(f"✓ Created base document v1")
        
        # Upload revision 2
        rev2_files = {
            'file': (f'TEST_multi_v2_{unique_id}.txt', f'Version 2 {unique_id}'.encode(), 'text/plain')
        }
        rev2_resp = api_session.post(
            f"{BASE_URL}/api/company/documents/{doc_id}/revision",
            files=rev2_files,
            data={'note': 'Revision 2'}
        )
        assert rev2_resp.status_code == 200
        assert rev2_resp.json()["version"] == 2
        print(f"✓ Uploaded revision v2")
        
        # Upload revision 3
        rev3_files = {
            'file': (f'TEST_multi_v3_{unique_id}.txt', f'Version 3 {unique_id}'.encode(), 'text/plain')
        }
        rev3_resp = api_session.post(
            f"{BASE_URL}/api/company/documents/{doc_id}/revision",
            files=rev3_files,
            data={'note': 'Revision 3'}
        )
        assert rev3_resp.status_code == 200
        
        final_doc = rev3_resp.json()
        assert final_doc["version"] == 3, f"Expected v3, got v{final_doc['version']}"
        assert final_doc["version_count"] == 3, f"Expected 3 versions, got {final_doc['version_count']}"
        print(f"✓ Uploaded revision v3")
        
        # Verify all versions downloadable
        for v in [1, 2, 3]:
            dl_resp = api_session.get(f"{BASE_URL}/api/company/documents/{doc_id}/versions/{v}/download")
            assert dl_resp.status_code == 200, f"v{v} download failed"
            assert f"Version {v}" in dl_resp.text or unique_id in dl_resp.text
        
        print(f"✓ All 3 versions downloadable")
        
        # Cleanup
        api_session.delete(f"{BASE_URL}/api/company/documents/{doc_id}")
        print(f"✓ Cleaned up test document {doc_id}")
    
    def test_revision_nonexistent_document(self, api_session):
        """POST /api/company/documents/nonexistent/revision - should 404"""
        files = {
            'file': ('test.txt', b'test content', 'text/plain')
        }
        
        response = api_session.post(
            f"{BASE_URL}/api/company/documents/nonexistent_doc_12345/revision",
            files=files,
            data={'note': ''}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Revision to non-existent document returns 404")
    
    def test_revision_invalid_file_extension(self, api_session):
        """POST revision with invalid extension should fail"""
        # Get any document
        list_resp = api_session.get(f"{BASE_URL}/api/company/documents/")
        docs = list_resp.json()["items"]
        
        if len(docs) == 0:
            pytest.skip("No documents available")
        
        doc_id = docs[0]["doc_id"]
        
        # Try to upload .exe file
        files = {
            'file': ('malicious.exe', b'bad content', 'application/x-msdownload')
        }
        
        response = api_session.post(
            f"{BASE_URL}/api/company/documents/{doc_id}/revision",
            files=files,
            data={'note': ''}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Invalid file extension in revision rejected")


class TestDeleteWithVersions:
    """Test delete removes all versions"""
    
    def test_delete_removes_all_versions(self, api_session):
        """DELETE should remove document and all archived versions"""
        unique_id = uuid.uuid4().hex[:6]
        
        # Create document with revisions
        files = {
            'file': (f'TEST_del_v1_{unique_id}.txt', b'V1 content', 'text/plain')
        }
        form_data = {
            'title': f'TEST_DeleteVersions_{unique_id}',
            'category': 'altro',
            'tags': 'test'
        }
        
        create_resp = api_session.post(
            f"{BASE_URL}/api/company/documents/",
            files=files,
            data=form_data
        )
        assert create_resp.status_code == 200
        doc_id = create_resp.json()["doc_id"]
        
        # Add revision
        rev_files = {
            'file': (f'TEST_del_v2_{unique_id}.txt', b'V2 content', 'text/plain')
        }
        rev_resp = api_session.post(
            f"{BASE_URL}/api/company/documents/{doc_id}/revision",
            files=rev_files,
            data={'note': ''}
        )
        assert rev_resp.status_code == 200
        assert rev_resp.json()["version"] == 2
        print(f"✓ Created document with 2 versions")
        
        # Delete
        delete_resp = api_session.delete(f"{BASE_URL}/api/company/documents/{doc_id}")
        assert delete_resp.status_code == 200
        print(f"✓ Deleted document")
        
        # Verify document gone
        list_resp = api_session.get(f"{BASE_URL}/api/company/documents/?search={unique_id}")
        found = any(d["doc_id"] == doc_id for d in list_resp.json()["items"])
        assert not found, "Document should not be in list after delete"
        
        # Verify versions endpoint 404
        versions_resp = api_session.get(f"{BASE_URL}/api/company/documents/{doc_id}/versions")
        assert versions_resp.status_code == 404
        
        # Verify version downloads 404
        for v in [1, 2]:
            dl_resp = api_session.get(f"{BASE_URL}/api/company/documents/{doc_id}/versions/{v}/download")
            assert dl_resp.status_code == 404
        
        print(f"✓ All versions removed after delete")
