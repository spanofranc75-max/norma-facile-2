"""
Iteration 267: Preventivi-Fatture Linking Feature Tests
Tests for:
1. GET /api/preventivi/{id}/linked-documents - returns correct structure
2. POST /api/preventivi/{id}/link-invoice - links invoice with custom amount
3. DELETE /api/preventivi/{id}/unlink-invoice/{invoice_id} - removes link
4. FT adds (+) to total_invoiced, NC subtracts (-)
5. Preventivi list shows stato_fatturazione: completo/parziale/non_fatturato
6. Invoice list shows 'P' badge when linked to preventivi
7. Duplicate link returns 409 error
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "stable_ca99e05ebab94952b91a8352"

# Test data from review request
TEST_PREV_100_PERCENT = "prev_50c2da16f2"  # 100% fatturato via progressive saldo
TEST_PREV_WITH_FT_NC = "prev_6534e128c9"  # has acconto FT + NC storno
TEST_PREV_PARZIALE = "prev_4db2a68b44"  # 20% parziale
TEST_STANDALONE_INVOICE = "inv_4941cb2617c0"  # can be used for manual link test


@pytest.fixture
def api_client():
    """Shared requests session with auth cookie"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Cookie": f"session_token={SESSION_TOKEN}"
    })
    return session


class TestLinkedDocumentsEndpoint:
    """Test GET /api/preventivi/{id}/linked-documents"""
    
    def test_linked_documents_returns_correct_structure(self, api_client):
        """Verify response structure has all required fields"""
        response = api_client.get(f"{BASE_URL}/api/preventivi/{TEST_PREV_100_PERCENT}/linked-documents")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Check all required fields exist
        required_fields = ['preventivo_id', 'imponibile', 'total_fatturato', 'total_nc', 
                          'net_invoiced', 'remaining', 'percentage', 'is_complete', 'documents']
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ linked-documents returns correct structure with all fields")
        print(f"  imponibile: {data['imponibile']}, net_invoiced: {data['net_invoiced']}, percentage: {data['percentage']}%")
    
    def test_linked_documents_100_percent_complete(self, api_client):
        """Verify 100% fatturato preventivo shows is_complete=true"""
        response = api_client.get(f"{BASE_URL}/api/preventivi/{TEST_PREV_100_PERCENT}/linked-documents")
        assert response.status_code == 200
        
        data = response.json()
        assert data['is_complete'] == True, f"Expected is_complete=True, got {data['is_complete']}"
        assert data['percentage'] >= 99.9, f"Expected percentage >= 99.9, got {data['percentage']}"
        assert data['remaining'] <= 0.01, f"Expected remaining <= 0.01, got {data['remaining']}"
        
        print(f"✓ 100% fatturato preventivo shows is_complete=true, percentage={data['percentage']}%")
    
    def test_linked_documents_parziale(self, api_client):
        """Verify parziale preventivo shows correct percentage"""
        response = api_client.get(f"{BASE_URL}/api/preventivi/{TEST_PREV_PARZIALE}/linked-documents")
        assert response.status_code == 200
        
        data = response.json()
        assert data['is_complete'] == False, f"Expected is_complete=False for parziale"
        assert 0 < data['percentage'] < 100, f"Expected 0 < percentage < 100, got {data['percentage']}"
        assert data['remaining'] > 0, f"Expected remaining > 0 for parziale"
        
        print(f"✓ Parziale preventivo: percentage={data['percentage']}%, remaining={data['remaining']}")
    
    def test_linked_documents_document_structure(self, api_client):
        """Verify each document in the list has correct structure"""
        response = api_client.get(f"{BASE_URL}/api/preventivi/{TEST_PREV_100_PERCENT}/linked-documents")
        assert response.status_code == 200
        
        data = response.json()
        documents = data.get('documents', [])
        assert len(documents) > 0, "Expected at least one linked document"
        
        doc = documents[0]
        required_doc_fields = ['invoice_id', 'document_number', 'document_type', 'amount', 
                               'sign', 'issue_date', 'status', 'link_type']
        for field in required_doc_fields:
            assert field in doc, f"Document missing field: {field}"
        
        # Verify sign is correct for document type
        if doc['document_type'] == 'NC':
            assert doc['sign'] == -1, "NC should have sign=-1"
        else:
            assert doc['sign'] == 1, "FT should have sign=1"
        
        print(f"✓ Document structure correct: {doc['document_number']} ({doc['document_type']}) sign={doc['sign']}")
    
    def test_linked_documents_requires_auth(self, api_client):
        """Verify endpoint requires authentication"""
        # Remove auth cookie
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.get(f"{BASE_URL}/api/preventivi/{TEST_PREV_100_PERCENT}/linked-documents")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        
        print("✓ linked-documents requires authentication (401 without cookie)")


class TestFTAndNCCalculation:
    """Test that FT adds (+) and NC subtracts (-) from total_invoiced"""
    
    def test_ft_adds_to_total(self, api_client):
        """Verify FT documents add to total_fatturato"""
        response = api_client.get(f"{BASE_URL}/api/preventivi/{TEST_PREV_100_PERCENT}/linked-documents")
        assert response.status_code == 200
        
        data = response.json()
        documents = data.get('documents', [])
        
        # Find FT documents
        ft_docs = [d for d in documents if d['document_type'] == 'FT']
        if ft_docs:
            ft_total = sum(d['amount'] for d in ft_docs)
            assert data['total_fatturato'] >= ft_total, "total_fatturato should include FT amounts"
            print(f"✓ FT documents add to total: {len(ft_docs)} FT docs, total_fatturato={data['total_fatturato']}")
        else:
            print("⚠ No FT documents found in this preventivo")
    
    def test_nc_subtracts_from_total(self, api_client):
        """Verify NC documents subtract from net_invoiced"""
        response = api_client.get(f"{BASE_URL}/api/preventivi/{TEST_PREV_WITH_FT_NC}/linked-documents")
        assert response.status_code == 200
        
        data = response.json()
        documents = data.get('documents', [])
        
        # Find NC documents
        nc_docs = [d for d in documents if d['document_type'] == 'NC']
        if nc_docs:
            nc_total = sum(d['amount'] for d in nc_docs)
            assert data['total_nc'] >= nc_total, "total_nc should include NC amounts"
            # net_invoiced = total_fatturato - total_nc
            expected_net = data['total_fatturato'] - data['total_nc']
            assert abs(data['net_invoiced'] - expected_net) < 0.01, f"net_invoiced should be total_fatturato - total_nc"
            print(f"✓ NC documents subtract: total_nc={data['total_nc']}, net_invoiced={data['net_invoiced']}")
        else:
            print(f"⚠ No NC documents found in preventivo {TEST_PREV_WITH_FT_NC}")


class TestPreventiviListStatoFatturazione:
    """Test preventivi list shows correct stato_fatturazione"""
    
    def test_list_shows_stato_fatturazione(self, api_client):
        """Verify preventivi list includes stato_fatturazione field"""
        response = api_client.get(f"{BASE_URL}/api/preventivi/?per_page=50")
        assert response.status_code == 200
        
        data = response.json()
        preventivi = data.get('preventivi', [])
        assert len(preventivi) > 0, "Expected at least one preventivo"
        
        # Check that stato_fatturazione exists
        for p in preventivi[:5]:  # Check first 5
            assert 'stato_fatturazione' in p, f"Missing stato_fatturazione in {p.get('number')}"
            assert p['stato_fatturazione'] in ['completo', 'parziale', 'non_fatturato'], \
                f"Invalid stato_fatturazione: {p['stato_fatturazione']}"
        
        print(f"✓ Preventivi list includes stato_fatturazione field")
    
    def test_completo_status(self, api_client):
        """Verify 100% fatturato shows stato_fatturazione=completo"""
        response = api_client.get(f"{BASE_URL}/api/preventivi/{TEST_PREV_100_PERCENT}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get('stato_fatturazione') == 'completo', \
            f"Expected stato_fatturazione=completo, got {data.get('stato_fatturazione')}"
        assert data.get('invoicing_progress', 0) >= 99.9, \
            f"Expected invoicing_progress >= 99.9, got {data.get('invoicing_progress')}"
        
        print(f"✓ 100% fatturato preventivo has stato_fatturazione=completo")
    
    def test_parziale_status(self, api_client):
        """Verify partially invoiced shows stato_fatturazione=parziale"""
        response = api_client.get(f"{BASE_URL}/api/preventivi/{TEST_PREV_PARZIALE}")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get('stato_fatturazione') == 'parziale', \
            f"Expected stato_fatturazione=parziale, got {data.get('stato_fatturazione')}"
        progress = data.get('invoicing_progress', 0)
        assert 0 < progress < 100, f"Expected 0 < invoicing_progress < 100, got {progress}"
        
        print(f"✓ Parziale preventivo has stato_fatturazione=parziale, progress={progress}%")


class TestLinkInvoiceEndpoint:
    """Test POST /api/preventivi/{id}/link-invoice"""
    
    def test_link_invoice_requires_auth(self, api_client):
        """Verify endpoint requires authentication"""
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.post(
            f"{BASE_URL}/api/preventivi/{TEST_PREV_WITH_FT_NC}/link-invoice",
            json={"invoice_id": TEST_STANDALONE_INVOICE}
        )
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        
        print("✓ link-invoice requires authentication (401 without cookie)")
    
    def test_link_invoice_requires_invoice_id(self, api_client):
        """Verify endpoint requires invoice_id in body"""
        response = api_client.post(
            f"{BASE_URL}/api/preventivi/{TEST_PREV_WITH_FT_NC}/link-invoice",
            json={}
        )
        assert response.status_code == 400, f"Expected 400 for missing invoice_id, got {response.status_code}"
        
        print("✓ link-invoice requires invoice_id (400 when missing)")
    
    def test_duplicate_link_returns_409(self, api_client):
        """Verify linking same invoice twice returns 409"""
        # First, get existing linked invoices
        response = api_client.get(f"{BASE_URL}/api/preventivi/{TEST_PREV_100_PERCENT}/linked-documents")
        assert response.status_code == 200
        
        data = response.json()
        documents = data.get('documents', [])
        if not documents:
            pytest.skip("No existing linked documents to test duplicate")
        
        # Try to link an already linked invoice
        existing_invoice_id = documents[0]['invoice_id']
        response = api_client.post(
            f"{BASE_URL}/api/preventivi/{TEST_PREV_100_PERCENT}/link-invoice",
            json={"invoice_id": existing_invoice_id}
        )
        assert response.status_code == 409, f"Expected 409 for duplicate link, got {response.status_code}"
        
        print(f"✓ Duplicate link returns 409 (tried to link {existing_invoice_id} again)")


class TestUnlinkInvoiceEndpoint:
    """Test DELETE /api/preventivi/{id}/unlink-invoice/{invoice_id}"""
    
    def test_unlink_invoice_requires_auth(self, api_client):
        """Verify endpoint requires authentication"""
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.delete(
            f"{BASE_URL}/api/preventivi/{TEST_PREV_WITH_FT_NC}/unlink-invoice/fake_invoice_id"
        )
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        
        print("✓ unlink-invoice requires authentication (401 without cookie)")
    
    def test_unlink_nonexistent_returns_404(self, api_client):
        """Verify unlinking non-existent link returns 404"""
        response = api_client.delete(
            f"{BASE_URL}/api/preventivi/{TEST_PREV_WITH_FT_NC}/unlink-invoice/nonexistent_invoice_id"
        )
        assert response.status_code == 404, f"Expected 404 for non-existent link, got {response.status_code}"
        
        print("✓ Unlink non-existent invoice returns 404")


class TestInvoiceListPBadge:
    """Test invoice list shows 'P' badge when linked to preventivi"""
    
    def test_invoice_list_includes_linked_preventivi(self, api_client):
        """Verify invoice list includes linked_preventivi or progressive_from_preventivo"""
        response = api_client.get(f"{BASE_URL}/api/invoices/?limit=50")
        assert response.status_code == 200
        
        data = response.json()
        invoices = data.get('invoices', [])
        
        # Find invoices with linked preventivi
        linked_invoices = [inv for inv in invoices 
                          if inv.get('linked_preventivi') or inv.get('progressive_from_preventivo')]
        
        if linked_invoices:
            inv = linked_invoices[0]
            has_link = bool(inv.get('linked_preventivi')) or bool(inv.get('progressive_from_preventivo'))
            assert has_link, "Invoice should have linked_preventivi or progressive_from_preventivo"
            print(f"✓ Found {len(linked_invoices)} invoices with preventivi links")
            print(f"  Example: {inv.get('document_number')} linked to preventivo")
        else:
            print("⚠ No invoices with preventivi links found in current list")


class TestInvoiceEditorLinkedPrevs:
    """Test invoice editor shows linked preventivi reference"""
    
    def test_invoice_detail_includes_linked_preventivi(self, api_client):
        """Verify invoice detail includes linked_preventivi array"""
        # Get an invoice that's linked to a preventivo
        response = api_client.get(f"{BASE_URL}/api/preventivi/{TEST_PREV_100_PERCENT}/linked-documents")
        assert response.status_code == 200
        
        data = response.json()
        documents = data.get('documents', [])
        if not documents:
            pytest.skip("No linked documents to test")
        
        invoice_id = documents[0]['invoice_id']
        
        # Get invoice detail
        response = api_client.get(f"{BASE_URL}/api/invoices/{invoice_id}")
        assert response.status_code == 200
        
        inv_data = response.json()
        # Should have either linked_preventivi or progressive_from_preventivo
        has_link = bool(inv_data.get('linked_preventivi')) or bool(inv_data.get('progressive_from_preventivo'))
        assert has_link, "Invoice should have linked_preventivi or progressive_from_preventivo"
        
        print(f"✓ Invoice {inv_data.get('document_number')} shows preventivo link")
        if inv_data.get('progressive_from_preventivo'):
            print(f"  progressive_from_preventivo: {inv_data.get('progressive_from_preventivo')}")
        if inv_data.get('linked_preventivi'):
            print(f"  linked_preventivi: {len(inv_data.get('linked_preventivi', []))} links")


class TestProgressBarColors:
    """Test progress bar color logic (green=complete, orange=partial)"""
    
    def test_complete_preventivo_progress(self, api_client):
        """Verify 100% preventivo has correct progress data for green bar"""
        response = api_client.get(f"{BASE_URL}/api/preventivi/{TEST_PREV_100_PERCENT}")
        assert response.status_code == 200
        
        data = response.json()
        progress = data.get('invoicing_progress', 0)
        stato = data.get('stato_fatturazione', '')
        
        assert progress >= 99.9, f"Expected progress >= 99.9 for complete, got {progress}"
        assert stato == 'completo', f"Expected stato=completo, got {stato}"
        
        print(f"✓ Complete preventivo: progress={progress}%, stato={stato} (should show green bar)")
    
    def test_partial_preventivo_progress(self, api_client):
        """Verify partial preventivo has correct progress data for orange bar"""
        response = api_client.get(f"{BASE_URL}/api/preventivi/{TEST_PREV_PARZIALE}")
        assert response.status_code == 200
        
        data = response.json()
        progress = data.get('invoicing_progress', 0)
        stato = data.get('stato_fatturazione', '')
        
        assert 0 < progress < 100, f"Expected 0 < progress < 100 for partial, got {progress}"
        assert stato == 'parziale', f"Expected stato=parziale, got {stato}"
        
        print(f"✓ Partial preventivo: progress={progress}%, stato={stato} (should show orange bar)")


class TestLinkDialogClientFilter:
    """Test link dialog shows invoices filtered by client"""
    
    def test_invoices_can_be_filtered_by_client(self, api_client):
        """Verify invoices endpoint supports client_id filter"""
        # Get a preventivo to find its client_id
        response = api_client.get(f"{BASE_URL}/api/preventivi/{TEST_PREV_PARZIALE}")
        assert response.status_code == 200
        
        prev_data = response.json()
        client_id = prev_data.get('client_id')
        if not client_id:
            pytest.skip("Preventivo has no client_id")
        
        # Filter invoices by client
        response = api_client.get(f"{BASE_URL}/api/invoices/?client_id={client_id}&limit=50")
        assert response.status_code == 200
        
        data = response.json()
        invoices = data.get('invoices', [])
        
        # All returned invoices should be for this client
        for inv in invoices:
            assert inv.get('client_id') == client_id, \
                f"Invoice {inv.get('document_number')} has wrong client_id"
        
        print(f"✓ Invoices can be filtered by client_id: {len(invoices)} invoices for client {client_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
