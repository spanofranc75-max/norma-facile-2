"""
Test Iteration 262: Cantiere Pre-fill Fix
==========================================
Tests the fix for missing data when creating Scheda Cantiere from Commessa.
The crea_cantiere() function should pre-fill:
- attivita_cantiere from commessa.description/oggetto
- indirizzo, citta, provincia from commessa.cantiere.indirizzo (parses 'Via X, Citta (PROV)' pattern)
- COMMITTENTE soggetto with client business_name, email from client collection
- commessa_numero and commessa_title for list display

Also tests list_cantieri() enrichment with client_name and commessa info.
"""

import pytest
import asyncio
import os
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timezone


# ═══════════════════════════════════════════════════════════════════
#  Test Data Constants
# ═══════════════════════════════════════════════════════════════════

TEST_USER_ID = "user_97c773827822"
TEST_COMMESSA_ID = "comm_sasso_marconi"
TEST_CLIENT_ID = "cli_sasso_marconi"

# Expected values from the test data
EXPECTED_CLIENT_NAME = "Costruzioni Edili Sasso Marconi S.r.l."
EXPECTED_CLIENT_EMAIL = "info@cessm.it"
EXPECTED_ADDRESS = "Via Porrettana 156, Sasso Marconi (BO)"
EXPECTED_PARSED_INDIRIZZO = "Via Porrettana 156"
EXPECTED_PARSED_CITTA = "Sasso Marconi"
EXPECTED_PARSED_PROVINCIA = "BO"
EXPECTED_DESCRIPTION = "Fornitura e posa solaio carpenteria metallica - Edificio antisismico Classe 3"


# ═══════════════════════════════════════════════════════════════════
#  Test: Address Regex Parsing
# ═══════════════════════════════════════════════════════════════════

class TestAddressRegexParsing:
    """Test the regex pattern for parsing 'Via X, Citta (PROV)' addresses."""
    
    def test_regex_pattern_full_address(self):
        """Test regex parses full address with provincia."""
        import re
        raw_addr = "Via Porrettana 156, Sasso Marconi (BO)"
        m = re.match(r"^(.+?),\s*(.+?)(?:\s*\((\w{2})\))?$", raw_addr)
        
        assert m is not None, "Regex should match full address pattern"
        assert m.group(1).strip() == "Via Porrettana 156", f"Indirizzo mismatch: {m.group(1)}"
        assert m.group(2).strip() == "Sasso Marconi", f"Citta mismatch: {m.group(2)}"
        assert m.group(3) == "BO", f"Provincia mismatch: {m.group(3)}"
    
    def test_regex_pattern_without_provincia(self):
        """Test regex parses address without provincia."""
        import re
        raw_addr = "Via Roma 10, Milano"
        m = re.match(r"^(.+?),\s*(.+?)(?:\s*\((\w{2})\))?$", raw_addr)
        
        assert m is not None, "Regex should match address without provincia"
        assert m.group(1).strip() == "Via Roma 10"
        assert m.group(2).strip() == "Milano"
        assert m.group(3) is None, "Provincia should be None"
    
    def test_regex_pattern_complex_street(self):
        """Test regex with complex street name."""
        import re
        raw_addr = "Viale della Repubblica 123/A, Bologna (BO)"
        m = re.match(r"^(.+?),\s*(.+?)(?:\s*\((\w{2})\))?$", raw_addr)
        
        assert m is not None
        assert m.group(1).strip() == "Viale della Repubblica 123/A"
        assert m.group(2).strip() == "Bologna"
        assert m.group(3) == "BO"


# ═══════════════════════════════════════════════════════════════════
#  Test: crea_cantiere() Pre-fill - All tests in single function
# ═══════════════════════════════════════════════════════════════════

class TestCreaCantierePrefillIntegration:
    """Integration test for crea_cantiere() pre-fill functionality.
    
    All tests run in a single async function to avoid event loop issues with Motor.
    """
    
    def test_all_prefill_features(self):
        """Test all pre-fill features in a single async run."""
        
        async def run_all_tests():
            from core.database import db
            from services.cantieri_sicurezza_service import crea_cantiere, list_cantieri
            
            created_cantieri = []
            results = {}
            
            try:
                # ── Setup: Ensure test data exists ──
                commessa = await db.commesse.find_one({"commessa_id": TEST_COMMESSA_ID})
                if not commessa:
                    commessa = {
                        "commessa_id": TEST_COMMESSA_ID,
                        "user_id": TEST_USER_ID,
                        "numero": "2024-001",
                        "title": "Commessa Sasso Marconi",
                        "oggetto": "Fornitura e posa solaio carpenteria metallica",
                        "description": EXPECTED_DESCRIPTION,
                        "client_id": TEST_CLIENT_ID,
                        "client_name": EXPECTED_CLIENT_NAME,
                        "cantiere": {
                            "indirizzo": EXPECTED_ADDRESS,
                            "note": "Cantiere principale"
                        },
                        "status": "in_corso",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                    await db.commesse.insert_one(commessa)
                    print(f"Created test commessa: {TEST_COMMESSA_ID}")
                
                client = await db.clients.find_one({"client_id": TEST_CLIENT_ID})
                if not client:
                    client = {
                        "client_id": TEST_CLIENT_ID,
                        "user_id": TEST_USER_ID,
                        "business_name": EXPECTED_CLIENT_NAME,
                        "name": "CESSM",
                        "email": EXPECTED_CLIENT_EMAIL,
                        "phone": "+39 051 123456",
                        "address_street": "Via Roma 1",
                        "address_city": "Sasso Marconi",
                        "address_province": "BO",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    await db.clients.insert_one(client)
                    print(f"Created test client: {TEST_CLIENT_ID}")
                
                # ── Test 1: attivita_cantiere pre-fill ──
                result = await crea_cantiere(TEST_USER_ID, TEST_COMMESSA_ID)
                created_cantieri.append(result["cantiere_id"])
                
                attivita = result.get("dati_cantiere", {}).get("attivita_cantiere", "")
                results["test_attivita"] = {
                    "passed": bool(attivita) and ("solaio" in attivita.lower() or "carpenteria" in attivita.lower() or "fornitura" in attivita.lower()),
                    "value": attivita,
                    "message": f"attivita_cantiere: {attivita}"
                }
                
                # ── Test 2: indirizzo parsing ──
                dati = result.get("dati_cantiere", {})
                indirizzo = dati.get("indirizzo_cantiere", "")
                citta = dati.get("citta_cantiere", "")
                provincia = dati.get("provincia_cantiere", "")
                
                indirizzo_ok = bool(indirizzo) and ("Via Porrettana" in indirizzo or "Porrettana" in indirizzo)
                citta_ok = bool(citta) and "Sasso Marconi" in citta
                provincia_ok = provincia == "BO"
                
                results["test_indirizzo"] = {
                    "passed": indirizzo_ok,
                    "value": indirizzo,
                    "message": f"indirizzo: {indirizzo}"
                }
                results["test_citta"] = {
                    "passed": citta_ok,
                    "value": citta,
                    "message": f"citta: {citta}"
                }
                results["test_provincia"] = {
                    "passed": provincia_ok,
                    "value": provincia,
                    "message": f"provincia: {provincia}"
                }
                
                # ── Test 3: COMMITTENTE soggetto ──
                soggetti = result.get("soggetti", [])
                committente = next((s for s in soggetti if s.get("ruolo") == "COMMITTENTE"), None)
                
                committente_nome_ok = committente and committente.get("nome") and (
                    EXPECTED_CLIENT_NAME in committente.get("nome", "") or
                    "Costruzioni" in committente.get("nome", "") or
                    "Sasso Marconi" in committente.get("nome", "")
                )
                committente_email_ok = committente and committente.get("email") and "@" in committente.get("email", "")
                committente_status_ok = committente and committente.get("status") == "precompilato"
                
                results["test_committente_nome"] = {
                    "passed": committente_nome_ok,
                    "value": committente.get("nome") if committente else None,
                    "message": f"COMMITTENTE nome: {committente.get('nome') if committente else 'NOT FOUND'}"
                }
                results["test_committente_email"] = {
                    "passed": committente_email_ok,
                    "value": committente.get("email") if committente else None,
                    "message": f"COMMITTENTE email: {committente.get('email') if committente else 'NOT FOUND'}"
                }
                results["test_committente_status"] = {
                    "passed": committente_status_ok,
                    "value": committente.get("status") if committente else None,
                    "message": f"COMMITTENTE status: {committente.get('status') if committente else 'NOT FOUND'}"
                }
                
                # ── Test 4: commessa reference stored ──
                client_name_stored = result.get("client_name", "")
                results["test_client_name_stored"] = {
                    "passed": bool(client_name_stored),
                    "value": client_name_stored,
                    "message": f"client_name stored: {client_name_stored}"
                }
                
                # ── Test 5: parent_commessa_id ──
                parent_id = result.get("parent_commessa_id")
                results["test_parent_commessa_id"] = {
                    "passed": parent_id == TEST_COMMESSA_ID,
                    "value": parent_id,
                    "message": f"parent_commessa_id: {parent_id}"
                }
                
                # ── Test 6: list_cantieri enrichment ──
                cantieri = await list_cantieri(TEST_USER_ID)
                test_cantiere = next((c for c in cantieri if c["cantiere_id"] == result["cantiere_id"]), None)
                
                list_client_name = test_cantiere.get("client_name", "") if test_cantiere else ""
                results["test_list_client_name"] = {
                    "passed": bool(list_client_name),
                    "value": list_client_name,
                    "message": f"list_cantieri client_name: {list_client_name}"
                }
                
                has_commessa_ref = test_cantiere and (
                    test_cantiere.get("commessa_numero") or 
                    test_cantiere.get("commessa_title") or
                    test_cantiere.get("parent_commessa_id")
                )
                results["test_list_commessa_ref"] = {
                    "passed": has_commessa_ref,
                    "value": {
                        "commessa_numero": test_cantiere.get("commessa_numero") if test_cantiere else None,
                        "commessa_title": test_cantiere.get("commessa_title") if test_cantiere else None,
                        "parent_commessa_id": test_cantiere.get("parent_commessa_id") if test_cantiere else None,
                    },
                    "message": f"list_cantieri commessa ref present: {has_commessa_ref}"
                }
                
            finally:
                # ── Cleanup ──
                for cantiere_id in created_cantieri:
                    await db.cantieri_sicurezza.delete_one({"cantiere_id": cantiere_id})
                    print(f"Cleaned up cantiere: {cantiere_id}")
            
            return results
        
        # Run all tests
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(run_all_tests())
        finally:
            loop.close()
        
        # Print results
        print("\n" + "="*60)
        print("CANTIERE PRE-FILL TEST RESULTS")
        print("="*60)
        
        all_passed = True
        for test_name, result in results.items():
            status = "PASS" if result["passed"] else "FAIL"
            print(f"{status}: {test_name} - {result['message']}")
            if not result["passed"]:
                all_passed = False
        
        print("="*60)
        
        # Assert all tests passed
        failed_tests = [name for name, r in results.items() if not r["passed"]]
        assert all_passed, f"Failed tests: {failed_tests}"


# ═══════════════════════════════════════════════════════════════════
#  Test: RBAC Protection (401 without auth)
# ═══════════════════════════════════════════════════════════════════

class TestRBACProtection:
    """Test endpoints return 401 without authentication."""
    
    def test_cantieri_sicurezza_list_401(self):
        """Test GET /api/cantieri-sicurezza returns 401 without auth."""
        import requests
        BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://fatture-v2.preview.emergentagent.com')
        
        response = requests.get(f"{BASE_URL}/api/cantieri-sicurezza")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_cantieri_sicurezza_create_401(self):
        """Test POST /api/cantieri-sicurezza returns 401 without auth."""
        import requests
        BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://fatture-v2.preview.emergentagent.com')
        
        response = requests.post(f"{BASE_URL}/api/cantieri-sicurezza", json={})
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_cantieri_sicurezza_get_401(self):
        """Test GET /api/cantieri-sicurezza/{id} returns 401 without auth."""
        import requests
        BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://fatture-v2.preview.emergentagent.com')
        
        response = requests.get(f"{BASE_URL}/api/cantieri-sicurezza/test_id")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


# ═══════════════════════════════════════════════════════════════════
#  Test: Health Check
# ═══════════════════════════════════════════════════════════════════

class TestHealthCheck:
    """Test health endpoint."""
    
    def test_health_returns_200(self):
        """Test /api/health returns 200."""
        import requests
        BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://fatture-v2.preview.emergentagent.com')
        
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "healthy", f"Status should be healthy: {data}"


# ═══════════════════════════════════════════════════════════════════
#  Test: Service Function Imports
# ═══════════════════════════════════════════════════════════════════

class TestServiceImports:
    """Test service functions can be imported."""
    
    def test_cantieri_sicurezza_service_imports(self):
        """Test cantieri_sicurezza_service imports correctly."""
        from services.cantieri_sicurezza_service import (
            crea_cantiere, get_cantiere, list_cantieri,
            aggiorna_cantiere, elimina_cantiere,
            get_cantieri_by_commessa, calcola_gate_pos
        )
        
        assert callable(crea_cantiere)
        assert callable(get_cantiere)
        assert callable(list_cantieri)
        assert callable(aggiorna_cantiere)
        assert callable(elimina_cantiere)
        assert callable(get_cantieri_by_commessa)
        assert callable(calcola_gate_pos)
    
    def test_set_soggetto_helper_exists(self):
        """Test _set_soggetto helper function exists in service."""
        import inspect
        from services import cantieri_sicurezza_service
        
        source = inspect.getsource(cantieri_sicurezza_service)
        assert "_set_soggetto" in source, "_set_soggetto helper should exist"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
