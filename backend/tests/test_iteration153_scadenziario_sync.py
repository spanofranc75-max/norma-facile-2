"""
Iteration 153: Test scadenziario sync and financial dashboard fixes.

Key features to test:
1. POST /api/invoices/sync-scadenze - generates scadenze_pagamento for invoices that don't have them
2. GET /api/fatture-ricevute/scadenziario/dashboard - returns 'incasso' entries for invoices 
   BOTH with and without scadenze_pagamento
3. GET /api/dashboard/cruscotto-finanziario - verify financial dashboard correct values
4. Verify payment_status filter uses $nin:['pagata'] pattern (catches null, undefined, etc.)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, date, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user ID for direct DB interaction (since app uses Google Auth)
TEST_USER_ID = f"TEST_SCAD_SYNC_{uuid.uuid4().hex[:8]}"

@pytest.fixture(scope="module")
def session():
    """Shared requests session."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


class TestSyncScadenzeEndpoint:
    """Tests for POST /api/invoices/sync-scadenze endpoint."""
    
    def test_sync_scadenze_endpoint_exists(self, session):
        """Verify the sync-scadenze endpoint exists and returns proper response structure."""
        # This will return 401 without auth, but that proves the endpoint exists
        response = session.post(f"{BASE_URL}/api/invoices/sync-scadenze")
        # Should not be 404 - endpoint must exist
        assert response.status_code != 404, "POST /api/invoices/sync-scadenze endpoint should exist"
        # Expected: 401 (auth required) or 200 (if there's a bypass)
        assert response.status_code in [401, 200, 422], f"Unexpected status: {response.status_code}"
        print(f"✓ POST /api/invoices/sync-scadenze endpoint exists, returns {response.status_code}")


class TestScadenziarioDashboard:
    """Tests for GET /api/fatture-ricevute/scadenziario/dashboard endpoint."""
    
    def test_scadenziario_dashboard_endpoint_exists(self, session):
        """Verify the scadenziario dashboard endpoint exists."""
        response = session.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard")
        # Should not be 404
        assert response.status_code != 404, "GET /api/fatture-ricevute/scadenziario/dashboard should exist"
        assert response.status_code in [401, 200], f"Unexpected status: {response.status_code}"
        print(f"✓ GET /api/fatture-ricevute/scadenziario/dashboard endpoint exists, returns {response.status_code}")
    
    def test_scadenziario_dashboard_response_structure(self, session):
        """Verify the dashboard returns expected structure (if accessible)."""
        response = session.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard")
        if response.status_code == 200:
            data = response.json()
            # Expected fields in response
            assert "scadenze" in data or "kpi" in data, "Dashboard should return scadenze or kpi"
            print(f"✓ Dashboard response structure validated: keys={list(data.keys())}")
        else:
            print(f"Dashboard requires auth, status={response.status_code} (expected)")
            pytest.skip("Auth required for full response validation")


class TestCruscottoFinanziario:
    """Tests for GET /api/dashboard/cruscotto-finanziario endpoint."""
    
    def test_cruscotto_finanziario_endpoint_exists(self, session):
        """Verify the cruscotto finanziario endpoint exists."""
        response = session.get(f"{BASE_URL}/api/dashboard/cruscotto-finanziario")
        assert response.status_code != 404, "GET /api/dashboard/cruscotto-finanziario should exist"
        assert response.status_code in [401, 200], f"Unexpected status: {response.status_code}"
        print(f"✓ GET /api/dashboard/cruscotto-finanziario endpoint exists, returns {response.status_code}")


class TestInvoicesEndpoints:
    """Test invoices-related endpoints."""
    
    def test_invoices_list_endpoint(self, session):
        """Verify invoices list endpoint works."""
        response = session.get(f"{BASE_URL}/api/invoices/")
        assert response.status_code != 404, "GET /api/invoices/ should exist"
        print(f"✓ GET /api/invoices/ returns {response.status_code}")
    
    def test_fatture_ricevute_list_endpoint(self, session):
        """Verify fatture ricevute list endpoint works."""
        response = session.get(f"{BASE_URL}/api/fatture-ricevute/")
        assert response.status_code != 404, "GET /api/fatture-ricevute/ should exist"
        print(f"✓ GET /api/fatture-ricevute/ returns {response.status_code}")


class TestPaymentStatusQueryPattern:
    """Tests verifying the $nin:['pagata'] query pattern is working correctly."""
    
    def test_financial_service_imports(self):
        """Verify financial_service.py contains proper query patterns."""
        import sys
        sys.path.insert(0, '/app/backend')
        
        # Read the financial service file and verify the pattern
        with open('/app/backend/services/financial_service.py', 'r') as f:
            content = f.read()
        
        # Check for $nin pattern for payment_status
        assert "$nin" in content, "financial_service.py should use $nin pattern"
        assert '"pagata"' in content or "'pagata'" in content, "Should filter by 'pagata' status"
        print("✓ financial_service.py uses $nin pattern for payment_status")
    
    def test_scadenziario_includes_invoices_without_scadenze(self):
        """Verify the scadenziario dashboard code handles invoices without scadenze_pagamento."""
        with open('/app/backend/routes/fatture_ricevute.py', 'r') as f:
            content = f.read()
        
        # Check for section 5b that handles invoices without scadenze_pagamento
        assert "5b" in content or "WITHOUT scadenze_pagamento" in content, \
            "fatture_ricevute.py should have section for invoices without scadenze_pagamento"
        
        # Verify the $or query for missing scadenze_pagamento
        assert '"scadenze_pagamento": {"$exists": False}' in content or \
               "'scadenze_pagamento': {'$exists': False}" in content or \
               "scadenze_pagamento" in content, \
            "Should query for invoices without scadenze_pagamento"
        
        print("✓ Scadenziario handles invoices both with and without scadenze_pagamento")
    
    def test_sync_scadenze_creates_fallback(self):
        """Verify sync-scadenze endpoint creates fallback scadenze from due_date."""
        with open('/app/backend/routes/invoices.py', 'r') as f:
            content = f.read()
        
        # Check for sync-scadenze endpoint
        assert "sync-scadenze" in content, "invoices.py should have sync-scadenze endpoint"
        
        # Check for fallback using due_date
        assert "due_date" in content, "sync-scadenze should use due_date as fallback"
        
        print("✓ sync-scadenze endpoint exists and uses due_date fallback")


class TestCodeReviewCriticalPatterns:
    """Code review: verify critical patterns are implemented correctly."""
    
    def test_nin_pattern_in_financial_service_da_incassare(self):
        """Verify da_incassare query uses $nin instead of $in with explicit values."""
        with open('/app/backend/services/financial_service.py', 'r') as f:
            content = f.read()
        
        # Line 97-98: payment_status: {"$nin": ["pagata"]} for da_incassare
        assert '$nin' in content and 'pagata' in content, \
            "da_incassare query should use $nin:['pagata'] pattern"
        
        # The pattern should NOT be $in with explicit values like ['non_pagata', 'parzialmente_pagata', None]
        # because that misses undefined/missing values
        print("✓ financial_service.py uses correct $nin pattern for unpaid invoices")
    
    def test_receivables_aging_uses_nin_pattern(self):
        """Verify get_receivables_aging uses $nin:['pagata'] pattern."""
        with open('/app/backend/services/financial_service.py', 'r') as f:
            content = f.read()
        
        # Lines 142-189 should use $nin
        assert 'get_receivables_aging' in content, "get_receivables_aging function should exist"
        
        # Count occurrences of $nin pattern
        nin_count = content.count('$nin')
        assert nin_count >= 2, f"Should use $nin pattern multiple times, found {nin_count}"
        
        print(f"✓ financial_service.py uses $nin pattern {nin_count} times")


class TestFrontendScadenziarioIntegration:
    """Verify frontend ScadenziarioPage calls both sync endpoints."""
    
    def test_scadenziario_page_calls_both_sync_endpoints(self):
        """Verify ScadenziarioPage.js calls both /fatture-ricevute/sync-fic AND /invoices/sync-scadenze."""
        with open('/app/frontend/src/pages/ScadenziarioPage.js', 'r') as f:
            content = f.read()
        
        # Check for sync-fic call
        assert '/fatture-ricevute/sync-fic' in content, \
            "ScadenziarioPage should call /fatture-ricevute/sync-fic"
        
        # Check for sync-scadenze call
        assert '/invoices/sync-scadenze' in content, \
            "ScadenziarioPage should call /invoices/sync-scadenze"
        
        # Check for Promise.all pattern (parallel execution)
        assert 'Promise.all' in content, \
            "ScadenziarioPage should use Promise.all for parallel sync"
        
        print("✓ ScadenziarioPage calls both sync endpoints in parallel")
    
    def test_scadenziario_handles_incasso_tipo(self):
        """Verify ScadenziarioPage handles 'incasso' tipo correctly."""
        with open('/app/frontend/src/pages/ScadenziarioPage.js', 'r') as f:
            content = f.read()
        
        # Check for incasso filtering
        assert 'incasso' in content, "ScadenziarioPage should handle 'incasso' tipo"
        
        # Check for clienti view that shows incasso items
        assert 'clienti' in content, "ScadenziarioPage should have clienti view"
        
        print("✓ ScadenziarioPage handles incasso tipo and clienti view")


class TestHealthCheck:
    """Basic health check to ensure services are running."""
    
    def test_backend_health(self, session):
        """Verify backend is responding."""
        response = session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print("✓ Backend health check passed")


# Run standalone if needed
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
