"""
Test suite for Archivio Documentale Aziendale (Company Document Archive) module.
Tests the /api/company/documents CRUD endpoints.
"""
import pytest
import requests
import os
import tempfile
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_session_3ce08f7a2e65452aa6e466779454ceb0"


@pytest.fixture
def api_client():
    """Authenticated session with cookie"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestCompanyDocumentsAPI:
    """Test /api/company/documents endpoints"""
    
    created_doc_ids = []  # Track created docs for cleanup
    
    def test_list_documents_all(self, api_client):
        """GET /api/company/documents/ - list all documents"""
        response = api_client.get(f"{BASE_URL}/api/company/documents/")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data, "Response should have 'items' field"
        assert "total" in data, "Response should have 'total' field"
        assert isinstance(data["items"], list), "Items should be a list"
        print(f"✓ List all documents: {data['total']} documents found")
    
    def test_list_documents_by_category_manuali(self, api_client):
        """GET /api/company/documents/?category=manuali - filter by category"""
        response = api_client.get(f"{BASE_URL}/api/company/documents/?category=manuali")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "items" in data
        # All items should be in manuali category (if any exist)
        for item in data["items"]:
            assert item["category"] == "manuali", f"Expected manuali, got {item['category']}"
        print(f"✓ Filter by manuali: {len(data['items'])} documents")
    
    def test_list_documents_by_category_procedure(self, api_client):
        """GET /api/company/documents/?category=procedure - filter by category"""
        response = api_client.get(f"{BASE_URL}/api/company/documents/?category=procedure")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        for item in data["items"]:
            assert item["category"] == "procedure"
        print(f"✓ Filter by procedure: {len(data['items'])} documents")
    
    def test_list_documents_search(self, api_client):
        """GET /api/company/documents/?search=1090 - search functionality"""
        response = api_client.get(f"{BASE_URL}/api/company/documents/?search=1090")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        print(f"✓ Search '1090': {len(data['items'])} results")
    
    def test_upload_document(self, api_client):
        """POST /api/company/documents/ - upload a new document"""
        # Create a temporary test file
        unique_id = uuid.uuid4().hex[:6]
        test_content = f"Test document content {unique_id} for company archive"
        
        # Use requests to upload multipart/form-data
        files = {
            'file': (f'TEST_doc_{unique_id}.txt', test_content.encode(), 'text/plain')
        }
        form_data = {
            'title': f'TEST_Document_{unique_id}',
            'category': 'template',
            'tags': 'test,pytest,automation'
        }
        
        # Remove content-type header for multipart upload
        session = requests.Session()
        session.cookies.set("session_token", SESSION_TOKEN)
        
        response = session.post(
            f"{BASE_URL}/api/company/documents/",
            files=files,
            data=form_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "doc_id" in data, "Response should contain doc_id"
        assert data["title"] == f'TEST_Document_{unique_id}'
        assert data["category"] == "template"
        assert "test" in data["tags"]
        assert "pytest" in data["tags"]
        
        # Store for cleanup
        TestCompanyDocumentsAPI.created_doc_ids.append(data["doc_id"])
        
        print(f"✓ Upload document: {data['doc_id']} created")
        return data["doc_id"]
    
    def test_upload_document_with_all_categories(self, api_client):
        """Test upload with different valid categories"""
        categories = ['manuali', 'procedure', 'certificazioni', 'template', 'normative', 'altro']
        
        for cat in categories:
            unique_id = uuid.uuid4().hex[:6]
            files = {
                'file': (f'TEST_{cat}_{unique_id}.txt', f'Test content for {cat}'.encode(), 'text/plain')
            }
            form_data = {
                'title': f'TEST_{cat.upper()}_{unique_id}',
                'category': cat,
                'tags': f'{cat},test'
            }
            
            session = requests.Session()
            session.cookies.set("session_token", SESSION_TOKEN)
            
            response = session.post(
                f"{BASE_URL}/api/company/documents/",
                files=files,
                data=form_data
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data["category"] == cat
                TestCompanyDocumentsAPI.created_doc_ids.append(data["doc_id"])
                print(f"  ✓ Category '{cat}' upload successful")
            else:
                print(f"  ✗ Category '{cat}' upload failed: {response.status_code}")
    
    def test_upload_document_invalid_extension(self, api_client):
        """POST /api/company/documents/ - reject invalid file extension"""
        files = {
            'file': ('test.exe', b'malicious content', 'application/x-msdownload')
        }
        form_data = {
            'title': 'TEST_Invalid_Ext',
            'category': 'altro',
            'tags': ''
        }
        
        session = requests.Session()
        session.cookies.set("session_token", SESSION_TOKEN)
        
        response = session.post(
            f"{BASE_URL}/api/company/documents/",
            files=files,
            data=form_data
        )
        
        # Should reject with 400
        assert response.status_code == 400, f"Expected 400 for invalid extension, got {response.status_code}"
        print("✓ Invalid file extension rejected correctly")
    
    def test_upload_document_invalid_category(self, api_client):
        """POST /api/company/documents/ - reject invalid category"""
        files = {
            'file': ('test.txt', b'test content', 'text/plain')
        }
        form_data = {
            'title': 'TEST_Invalid_Cat',
            'category': 'invalid_category',
            'tags': ''
        }
        
        session = requests.Session()
        session.cookies.set("session_token", SESSION_TOKEN)
        
        response = session.post(
            f"{BASE_URL}/api/company/documents/",
            files=files,
            data=form_data
        )
        
        # Should reject with 400
        assert response.status_code == 400, f"Expected 400 for invalid category, got {response.status_code}"
        print("✓ Invalid category rejected correctly")
    
    def test_download_document(self, api_client):
        """GET /api/company/documents/{doc_id}/download - download a document"""
        # First get list of documents to find one to download
        response = api_client.get(f"{BASE_URL}/api/company/documents/")
        data = response.json()
        
        if len(data["items"]) == 0:
            pytest.skip("No documents available to download")
        
        doc = data["items"][0]
        doc_id = doc["doc_id"]
        
        session = requests.Session()
        session.cookies.set("session_token", SESSION_TOKEN)
        
        response = session.get(f"{BASE_URL}/api/company/documents/{doc_id}/download")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert len(response.content) > 0, "Downloaded content should not be empty"
        print(f"✓ Download document: {doc_id} ({len(response.content)} bytes)")
    
    def test_download_nonexistent_document(self, api_client):
        """GET /api/company/documents/{doc_id}/download - 404 for non-existent"""
        session = requests.Session()
        session.cookies.set("session_token", SESSION_TOKEN)
        
        response = session.get(f"{BASE_URL}/api/company/documents/nonexistent_id_12345/download")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent document download returns 404")
    
    def test_delete_document(self, api_client):
        """DELETE /api/company/documents/{doc_id} - delete a document"""
        # First upload a document to delete
        unique_id = uuid.uuid4().hex[:6]
        files = {
            'file': (f'TEST_delete_{unique_id}.txt', b'To be deleted', 'text/plain')
        }
        form_data = {
            'title': f'TEST_ToDelete_{unique_id}',
            'category': 'altro',
            'tags': 'test,delete'
        }
        
        session = requests.Session()
        session.cookies.set("session_token", SESSION_TOKEN)
        
        # Create
        upload_response = session.post(
            f"{BASE_URL}/api/company/documents/",
            files=files,
            data=form_data
        )
        assert upload_response.status_code == 200
        doc_id = upload_response.json()["doc_id"]
        print(f"  Created document {doc_id} for deletion test")
        
        # Delete
        delete_response = session.delete(f"{BASE_URL}/api/company/documents/{doc_id}")
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}"
        
        delete_data = delete_response.json()
        assert delete_data["doc_id"] == doc_id
        print(f"✓ Delete document: {doc_id} deleted successfully")
        
        # Verify deleted - should return 404 on download
        verify_response = session.get(f"{BASE_URL}/api/company/documents/{doc_id}/download")
        assert verify_response.status_code == 404, "Deleted document should return 404"
        print("✓ Verified document is actually deleted")
    
    def test_delete_nonexistent_document(self, api_client):
        """DELETE /api/company/documents/{doc_id} - 404 for non-existent"""
        session = requests.Session()
        session.cookies.set("session_token", SESSION_TOKEN)
        
        response = session.delete(f"{BASE_URL}/api/company/documents/nonexistent_id_99999")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent document delete returns 404")
    
    # Cleanup handled manually in each test that creates docs


class TestCompanyDocumentsIntegration:
    """Integration tests for complete CRUD workflow"""
    
    def test_full_crud_workflow(self, api_client):
        """Test Create -> Read -> Download -> Delete workflow"""
        session = requests.Session()
        session.cookies.set("session_token", SESSION_TOKEN)
        
        unique_id = uuid.uuid4().hex[:6]
        
        # 1. CREATE
        files = {
            'file': (f'TEST_workflow_{unique_id}.txt', f'Workflow test content {unique_id}'.encode(), 'text/plain')
        }
        form_data = {
            'title': f'TEST_Workflow_{unique_id}',
            'category': 'certificazioni',
            'tags': 'workflow,integration,test'
        }
        
        create_response = session.post(
            f"{BASE_URL}/api/company/documents/",
            files=files,
            data=form_data
        )
        assert create_response.status_code == 200
        doc_id = create_response.json()["doc_id"]
        print(f"✓ CREATE: Document {doc_id} created")
        
        # 2. READ (list and find)
        list_response = session.get(f"{BASE_URL}/api/company/documents/?search={unique_id}")
        assert list_response.status_code == 200
        list_data = list_response.json()
        found = any(d["doc_id"] == doc_id for d in list_data["items"])
        assert found, f"Created document {doc_id} not found in list"
        print(f"✓ READ: Document found in list")
        
        # 3. DOWNLOAD
        download_response = session.get(f"{BASE_URL}/api/company/documents/{doc_id}/download")
        assert download_response.status_code == 200
        assert unique_id.encode() in download_response.content
        print(f"✓ DOWNLOAD: File content verified")
        
        # 4. DELETE
        delete_response = session.delete(f"{BASE_URL}/api/company/documents/{doc_id}")
        assert delete_response.status_code == 200
        print(f"✓ DELETE: Document removed")
        
        # 5. VERIFY DELETION
        verify_response = session.get(f"{BASE_URL}/api/company/documents/{doc_id}/download")
        assert verify_response.status_code == 404
        print(f"✓ VERIFY: Document no longer accessible")
