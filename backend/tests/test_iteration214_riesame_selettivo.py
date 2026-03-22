"""
Iteration 214 — Riesame Tecnico Selettivo Testing
Tests the selective technical review system where compliance checks are filtered
based on normativa_tipo (EN_1090, EN_13241, GENERICA) of voci_lavoro in a commessa.

Test scenarios:
1. Mixed commessa (EN_1090 + EN_13241 + GENERICA) - all 12 checks applicable
2. GENERICA-only commessa - only 3 universal checks applicable (normativa=None)
3. EN_13241-only commessa - 5 applicable checks (universals + EN_13241 specific)
4. Approval skips validation for non-applicable checks
5. PDF generation includes normative info
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "test_riesame_e19148d8f838452d"
USER_ID = "user_97c773827822"

# Test commessa IDs from the review request
MIXED_COMMESSA = "com_2c57c1283871"  # EN_1090 + EN_13241 + GENERICA
GENERICA_ONLY_COMMESSA = "com_test_generica_only"  # GENERICA only
EN13241_ONLY_COMMESSA = "com_test_en13241_only"  # EN_13241 only


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth cookie"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestRiesameSelettivo:
    """Tests for the Riesame Tecnico Selettivo feature"""

    def test_01_mixed_commessa_all_checks_applicable(self, api_client):
        """
        Mixed commessa (EN_1090 + EN_13241 + GENERICA) should have all 12 checks applicable.
        normative_attive should include all three normativa types.
        """
        response = api_client.get(f"{BASE_URL}/api/riesame/{MIXED_COMMESSA}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify normative_attive contains all three types
        normative_attive = data.get("normative_attive", [])
        assert "EN_1090" in normative_attive, f"EN_1090 should be in normative_attive: {normative_attive}"
        assert "EN_13241" in normative_attive, f"EN_13241 should be in normative_attive: {normative_attive}"
        assert "GENERICA" in normative_attive, f"GENERICA should be in normative_attive: {normative_attive}"
        
        # Verify all 12 checks are present
        checks = data.get("checks", [])
        assert len(checks) == 12, f"Expected 12 checks, got {len(checks)}"
        
        # Verify all checks are applicable for mixed commessa
        n_applicabili = data.get("n_applicabili", 0)
        n_non_applicabili = data.get("n_non_applicabili", 0)
        
        assert n_applicabili == 12, f"Expected 12 applicable checks, got {n_applicabili}"
        assert n_non_applicabili == 0, f"Expected 0 non-applicable checks, got {n_non_applicabili}"
        
        # Verify each check has applicabile=True
        for ck in checks:
            assert ck.get("applicabile") == True, f"Check {ck['id']} should be applicabile for mixed commessa"
        
        print(f"✓ Mixed commessa test passed: {n_applicabili} applicable, {n_non_applicabili} N/A")

    def test_02_generica_only_commessa_limited_checks(self, api_client):
        """
        GENERICA-only commessa should have only 3 applicable checks (universal checks with normativa=None).
        The 9 normativa-specific checks should be marked as non-applicable.
        """
        response = api_client.get(f"{BASE_URL}/api/riesame/{GENERICA_ONLY_COMMESSA}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify normative_attive contains only GENERICA
        normative_attive = data.get("normative_attive", [])
        assert "GENERICA" in normative_attive, f"GENERICA should be in normative_attive: {normative_attive}"
        assert "EN_1090" not in normative_attive, f"EN_1090 should NOT be in normative_attive: {normative_attive}"
        assert "EN_13241" not in normative_attive, f"EN_13241 should NOT be in normative_attive: {normative_attive}"
        
        # Verify counts
        n_applicabili = data.get("n_applicabili", 0)
        n_non_applicabili = data.get("n_non_applicabili", 0)
        
        # Universal checks (normativa=None): disegni_validati, attrezzature_idonee, documenti_aziendali = 3
        assert n_applicabili == 3, f"Expected 3 applicable checks for GENERICA-only, got {n_applicabili}"
        assert n_non_applicabili == 9, f"Expected 9 non-applicable checks for GENERICA-only, got {n_non_applicabili}"
        
        # Verify specific checks
        checks = data.get("checks", [])
        universal_check_ids = ["disegni_validati", "attrezzature_idonee", "documenti_aziendali"]
        
        for ck in checks:
            if ck["id"] in universal_check_ids:
                assert ck.get("applicabile") == True, f"Universal check {ck['id']} should be applicabile"
            else:
                assert ck.get("applicabile") == False, f"Check {ck['id']} should NOT be applicabile for GENERICA-only"
                assert ck.get("valore") == "N/A", f"Non-applicable check {ck['id']} should have valore='N/A'"
        
        print(f"✓ GENERICA-only commessa test passed: {n_applicabili} applicable, {n_non_applicabili} N/A")

    def test_03_en13241_only_commessa_partial_checks(self, api_client):
        """
        EN_13241-only commessa should have 5 applicable checks:
        - 3 universal checks (normativa=None)
        - 2 checks that include EN_13241: materiali_confermati, strumenti_tarati
        """
        response = api_client.get(f"{BASE_URL}/api/riesame/{EN13241_ONLY_COMMESSA}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify normative_attive contains only EN_13241
        normative_attive = data.get("normative_attive", [])
        assert "EN_13241" in normative_attive, f"EN_13241 should be in normative_attive: {normative_attive}"
        assert "EN_1090" not in normative_attive, f"EN_1090 should NOT be in normative_attive: {normative_attive}"
        
        # Verify counts
        n_applicabili = data.get("n_applicabili", 0)
        n_non_applicabili = data.get("n_non_applicabili", 0)
        
        # Universal (3) + EN_13241 specific (materiali_confermati, strumenti_tarati) = 5
        assert n_applicabili == 5, f"Expected 5 applicable checks for EN_13241-only, got {n_applicabili}"
        assert n_non_applicabili == 7, f"Expected 7 non-applicable checks for EN_13241-only, got {n_non_applicabili}"
        
        # Verify specific checks
        checks = data.get("checks", [])
        applicable_check_ids = [
            "disegni_validati", "attrezzature_idonee", "documenti_aziendali",  # Universal
            "materiali_confermati", "strumenti_tarati"  # EN_13241 specific
        ]
        
        for ck in checks:
            if ck["id"] in applicable_check_ids:
                assert ck.get("applicabile") == True, f"Check {ck['id']} should be applicabile for EN_13241-only"
            else:
                assert ck.get("applicabile") == False, f"Check {ck['id']} should NOT be applicabile for EN_13241-only"
        
        print(f"✓ EN_13241-only commessa test passed: {n_applicabili} applicable, {n_non_applicabili} N/A")

    def test_04_check_structure_has_required_fields(self, api_client):
        """Verify each check has all required fields including applicabile and normativa"""
        response = api_client.get(f"{BASE_URL}/api/riesame/{MIXED_COMMESSA}")
        
        assert response.status_code == 200
        
        data = response.json()
        checks = data.get("checks", [])
        
        required_fields = ["id", "sezione", "label", "desc", "auto", "esito", "valore", "applicabile"]
        
        for ck in checks:
            for field in required_fields:
                assert field in ck, f"Check {ck.get('id', 'unknown')} missing field: {field}"
            
            # Verify normativa field is present (can be None or list)
            assert "normativa" in ck, f"Check {ck['id']} missing normativa field"
        
        print(f"✓ Check structure validation passed for {len(checks)} checks")

    def test_05_response_includes_normative_counts(self, api_client):
        """Verify response includes n_applicabili and n_non_applicabili counts"""
        response = api_client.get(f"{BASE_URL}/api/riesame/{MIXED_COMMESSA}")
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify required fields in response
        assert "normative_attive" in data, "Response missing normative_attive"
        assert "n_applicabili" in data, "Response missing n_applicabili"
        assert "n_non_applicabili" in data, "Response missing n_non_applicabili"
        assert "n_totale" in data, "Response missing n_totale"
        assert "n_ok" in data, "Response missing n_ok"
        
        # Verify counts are consistent
        n_totale = data["n_totale"]
        n_applicabili = data["n_applicabili"]
        n_non_applicabili = data["n_non_applicabili"]
        
        assert n_totale == 12, f"Expected n_totale=12, got {n_totale}"
        assert n_applicabili + n_non_applicabili == n_totale, \
            f"n_applicabili ({n_applicabili}) + n_non_applicabili ({n_non_applicabili}) should equal n_totale ({n_totale})"
        
        print(f"✓ Response structure validation passed")

    def test_06_pdf_generation_returns_valid_pdf(self, api_client):
        """Verify PDF generation endpoint returns valid PDF with normative info"""
        response = api_client.get(f"{BASE_URL}/api/riesame/{MIXED_COMMESSA}/pdf")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("Content-Type") == "application/pdf", \
            f"Expected Content-Type application/pdf, got {response.headers.get('Content-Type')}"
        
        # Verify PDF has content
        pdf_content = response.content
        assert len(pdf_content) > 1000, f"PDF too small ({len(pdf_content)} bytes), expected >1000"
        
        # Verify PDF magic bytes
        assert pdf_content[:4] == b'%PDF', "Response is not a valid PDF"
        
        print(f"✓ PDF generation test passed ({len(pdf_content)} bytes)")

    def test_07_non_applicable_checks_have_motivo_esclusione(self, api_client):
        """Verify non-applicable checks include motivo_esclusione explaining why"""
        response = api_client.get(f"{BASE_URL}/api/riesame/{GENERICA_ONLY_COMMESSA}")
        
        assert response.status_code == 200
        
        data = response.json()
        checks = data.get("checks", [])
        
        for ck in checks:
            if not ck.get("applicabile"):
                # Non-applicable checks should have nota explaining why
                nota = ck.get("nota", "")
                assert nota, f"Non-applicable check {ck['id']} should have nota/motivo_esclusione"
                assert "Non richiesto" in nota or "Non applicabile" in nota, \
                    f"Check {ck['id']} nota should explain exclusion: {nota}"
        
        print(f"✓ Motivo esclusione validation passed")

    def test_08_superato_only_considers_applicable_checks(self, api_client):
        """Verify superato flag only considers applicable checks, not N/A ones"""
        response = api_client.get(f"{BASE_URL}/api/riesame/{GENERICA_ONLY_COMMESSA}")
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Get applicable checks
        checks = data.get("checks", [])
        applicable_checks = [c for c in checks if c.get("applicabile")]
        
        # Verify n_ok counts only applicable checks that passed
        n_ok = data.get("n_ok", 0)
        actual_ok = sum(1 for c in applicable_checks if c.get("esito"))
        
        assert n_ok == actual_ok, f"n_ok ({n_ok}) should match actual passed applicable checks ({actual_ok})"
        
        # Verify superato is based on applicable checks only
        superato = data.get("superato", False)
        all_applicable_passed = all(c.get("esito") for c in applicable_checks)
        
        assert superato == all_applicable_passed, \
            f"superato ({superato}) should match all applicable checks passed ({all_applicable_passed})"
        
        print(f"✓ Superato calculation validation passed")


class TestRiesameApproval:
    """Tests for the approval endpoint with selective checks"""

    def test_09_approval_skips_non_applicable_checks(self, api_client):
        """
        POST /api/riesame/{commessa_id}/approva should skip validation for non-applicable checks.
        For GENERICA-only commessa, only the 3 universal checks should be validated.
        """
        # First, save manual checks for the universal checks
        save_response = api_client.post(
            f"{BASE_URL}/api/riesame/{GENERICA_ONLY_COMMESSA}",
            json={
                "checks_manuali": {
                    "disegni_validati": True  # The only manual universal check
                },
                "note_generali": "Test approval with selective checks"
            }
        )
        
        # Note: This test may fail if auto checks don't pass, which is expected behavior
        # The important thing is that it doesn't fail due to non-applicable checks
        if save_response.status_code == 200:
            print(f"✓ Save riesame for GENERICA-only commessa succeeded")
        else:
            print(f"Save response: {save_response.status_code} - {save_response.text}")
        
        # Try to approve - this will fail if auto checks don't pass, but should NOT fail
        # due to non-applicable checks like exc_class, wps_assegnate, etc.
        approve_response = api_client.post(
            f"{BASE_URL}/api/riesame/{GENERICA_ONLY_COMMESSA}/approva",
            json={
                "firma_nome": "Test User",
                "firma_ruolo": "QA Tester"
            }
        )
        
        # If it fails, verify it's not because of non-applicable checks
        if approve_response.status_code != 200:
            error_msg = approve_response.text.lower()
            # These are EN_1090 specific checks that should NOT cause failure for GENERICA-only
            non_applicable_checks = [
                "exc_class", "tolleranze_en1090", "wps_assegnate", 
                "saldatori_qualificati", "tolleranza_calibro", 
                "consumabili_disponibili", "itt_processi_qualificati"
            ]
            for check_id in non_applicable_checks:
                assert check_id not in error_msg, \
                    f"Approval failed due to non-applicable check '{check_id}': {approve_response.text}"
            
            print(f"✓ Approval correctly skipped non-applicable checks (failed due to applicable checks)")
        else:
            print(f"✓ Approval succeeded for GENERICA-only commessa")


class TestFilterChecksLogic:
    """Tests for the _filter_checks logic"""

    def test_10_universal_checks_always_applicable(self, api_client):
        """Universal checks (normativa=None) should always be applicable regardless of normative_attive"""
        universal_check_ids = ["disegni_validati", "attrezzature_idonee", "documenti_aziendali"]
        
        # Test with GENERICA-only
        response = api_client.get(f"{BASE_URL}/api/riesame/{GENERICA_ONLY_COMMESSA}")
        assert response.status_code == 200
        
        checks = response.json().get("checks", [])
        for ck in checks:
            if ck["id"] in universal_check_ids:
                assert ck.get("applicabile") == True, \
                    f"Universal check {ck['id']} should be applicabile even for GENERICA-only"
        
        print(f"✓ Universal checks always applicable test passed")

    def test_11_en1090_specific_checks_filtered(self, api_client):
        """EN_1090 specific checks should be filtered out when EN_1090 is not active"""
        en1090_only_checks = [
            "exc_class", "tolleranze_en1090", "wps_assegnate", 
            "saldatori_qualificati", "tolleranza_calibro",
            "consumabili_disponibili", "itt_processi_qualificati"
        ]
        
        # Test with GENERICA-only (no EN_1090)
        response = api_client.get(f"{BASE_URL}/api/riesame/{GENERICA_ONLY_COMMESSA}")
        assert response.status_code == 200
        
        checks = response.json().get("checks", [])
        for ck in checks:
            if ck["id"] in en1090_only_checks:
                assert ck.get("applicabile") == False, \
                    f"EN_1090 specific check {ck['id']} should NOT be applicabile for GENERICA-only"
        
        print(f"✓ EN_1090 specific checks filtered test passed")

    def test_12_shared_checks_applicable_when_any_normativa_active(self, api_client):
        """Checks with multiple normativa (e.g., EN_1090 + EN_13241) should be applicable if ANY is active"""
        # materiali_confermati and strumenti_tarati have normativa=["EN_1090", "EN_13241"]
        shared_check_ids = ["materiali_confermati", "strumenti_tarati"]
        
        # Test with EN_13241-only (should have these checks applicable)
        response = api_client.get(f"{BASE_URL}/api/riesame/{EN13241_ONLY_COMMESSA}")
        assert response.status_code == 200
        
        checks = response.json().get("checks", [])
        for ck in checks:
            if ck["id"] in shared_check_ids:
                assert ck.get("applicabile") == True, \
                    f"Shared check {ck['id']} should be applicabile when EN_13241 is active"
        
        print(f"✓ Shared checks applicable test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
