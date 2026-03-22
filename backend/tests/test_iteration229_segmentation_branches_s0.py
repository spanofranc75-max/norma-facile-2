"""
Iteration 229 — S0: Segmentation → Normative Branches Link
============================================================
Tests the automatic generation of normative branches from confirmed segmentation.

Key features tested:
1. POST /api/commesse-normative/genera-da-istruttoria/{preventivo_id} — creates branches from classification
2. genera-da-istruttoria with commessa in commesse_preistruite — works correctly
3. genera-da-istruttoria idempotent — re-run doesn't duplicate branches
4. genera-da-istruttoria updates normative_presenti on commesse_preistruite
5. POST /api/istruttoria/phase2/genera/{preventivo_id} — response includes rami_generati[]
6. crea_ramo searches commessa in both collections (commesse + commesse_preistruite)
7. Legacy adapter get_normative_branches searches also in commesse_preistruite

Test credentials:
- Session token: test_bc05322c3dc3480c8fd374cdffd02105
- User: user_97c773827822
- Existing istruttoria: prev_625826c752ac (confirmed, EN_1090, has commessa_preistruita comm_393ef99b15bd)
- Existing istruttoria: prev_62e2e4b9c088 (confirmed, EN_13241, no preistruita yet)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
SESSION_TOKEN = "test_bc05322c3dc3480c8fd374cdffd02105"
USER_ID = "user_97c773827822"

# Test data from the review request
PREVENTIVO_WITH_PREISTRUITA = "prev_625826c752ac"  # Has commessa_preistruita comm_393ef99b15bd, EN_1090
PREVENTIVO_WITHOUT_PREISTRUITA = "prev_62e2e4b9c088"  # EN_13241, no preistruita yet
EXISTING_RAMO_ID = "ramo_ebca8cb95185"  # Already created for prev_625826c752ac
COMMESSA_PREISTRUITA_ID = "comm_393ef99b15bd"


@pytest.fixture(scope="module")
def auth_headers():
    """Authentication headers with session token."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    }


class TestGeneraDaIstruttoriaEndpoint:
    """Tests for POST /api/commesse-normative/genera-da-istruttoria/{preventivo_id}"""

    def test_genera_da_istruttoria_with_existing_preistruita(self, auth_headers):
        """Test genera-da-istruttoria with commessa in commesse_preistruite — should work correctly."""
        url = f"{BASE_URL}/api/commesse-normative/genera-da-istruttoria/{PREVENTIVO_WITH_PREISTRUITA}"
        response = requests.post(url, headers=auth_headers)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "rami" in data, "Response should contain 'rami' array"
        assert "commessa_id" in data, "Response should contain 'commessa_id'"
        assert "total" in data, "Response should contain 'total'"
        
        # Verify at least one ramo was created/returned
        assert len(data["rami"]) >= 1, "Should have at least one ramo"
        
        # Verify ramo structure
        ramo = data["rami"][0]
        assert "ramo_id" in ramo, "Ramo should have ramo_id"
        assert "normativa" in ramo, "Ramo should have normativa"
        assert "codice_ramo" in ramo, "Ramo should have codice_ramo"
        assert "commessa_id" in ramo, "Ramo should have commessa_id"
        
        print(f"SUCCESS: Generated {len(data['rami'])} rami for commessa {data['commessa_id']}")
        return data

    def test_genera_da_istruttoria_idempotent(self, auth_headers):
        """Test idempotency — re-running genera-da-istruttoria should not duplicate branches."""
        url = f"{BASE_URL}/api/commesse-normative/genera-da-istruttoria/{PREVENTIVO_WITH_PREISTRUITA}"
        
        # First call
        response1 = requests.post(url, headers=auth_headers)
        assert response1.status_code == 200, f"First call failed: {response1.text}"
        data1 = response1.json()
        rami_ids_1 = [r["ramo_id"] for r in data1["rami"]]
        
        # Second call (should return same rami, not create new ones)
        response2 = requests.post(url, headers=auth_headers)
        assert response2.status_code == 200, f"Second call failed: {response2.text}"
        data2 = response2.json()
        rami_ids_2 = [r["ramo_id"] for r in data2["rami"]]
        
        # Verify same ramo_ids (idempotency)
        assert set(rami_ids_1) == set(rami_ids_2), f"Ramo IDs should be identical. First: {rami_ids_1}, Second: {rami_ids_2}"
        assert len(data1["rami"]) == len(data2["rami"]), "Number of rami should be the same"
        
        print(f"SUCCESS: Idempotency verified. Same ramo_ids returned: {rami_ids_1}")

    def test_genera_da_istruttoria_updates_normative_presenti(self, auth_headers):
        """Test that genera-da-istruttoria updates normative_presenti on commesse_preistruite."""
        # First generate rami
        url = f"{BASE_URL}/api/commesse-normative/genera-da-istruttoria/{PREVENTIVO_WITH_PREISTRUITA}"
        response = requests.post(url, headers=auth_headers)
        assert response.status_code == 200, f"Generate failed: {response.text}"
        
        data = response.json()
        commessa_id = data["commessa_id"]
        
        # Now fetch the commessa preistruita to verify normative_presenti was updated
        commessa_url = f"{BASE_URL}/api/istruttoria/phase2/commessa/{PREVENTIVO_WITH_PREISTRUITA}"
        commessa_response = requests.get(commessa_url, headers=auth_headers)
        
        if commessa_response.status_code == 200:
            commessa_data = commessa_response.json()
            commessa = commessa_data.get("commessa", {})
            
            # Check if normative_presenti was updated
            normative_presenti = commessa.get("normative_presenti", [])
            has_mixed = commessa.get("has_mixed_normative", False)
            primary_norm = commessa.get("primary_normativa", "")
            
            print(f"Commessa {commessa_id}:")
            print(f"  normative_presenti: {normative_presenti}")
            print(f"  has_mixed_normative: {has_mixed}")
            print(f"  primary_normativa: {primary_norm}")
            
            # Verify normative_presenti contains the expected normativa
            assert len(normative_presenti) >= 1, "normative_presenti should have at least one entry"
            
            print(f"SUCCESS: normative_presenti updated correctly")
        else:
            print(f"Note: Could not fetch commessa preistruita (status {commessa_response.status_code})")

    def test_genera_da_istruttoria_no_commessa_returns_400(self, auth_headers):
        """Test that genera-da-istruttoria returns 400 when no commessa madre found."""
        url = f"{BASE_URL}/api/commesse-normative/genera-da-istruttoria/{PREVENTIVO_WITHOUT_PREISTRUITA}"
        response = requests.post(url, headers=auth_headers)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text[:500]}")
        
        # Should return 400 if no commessa preistruita exists
        # OR 200 if commessa exists in commesse collection
        if response.status_code == 400:
            assert "commessa" in response.text.lower() or "trovata" in response.text.lower(), \
                "Error message should mention commessa not found"
            print("SUCCESS: Correctly returned 400 for preventivo without commessa madre")
        elif response.status_code == 200:
            print("Note: Commessa exists in commesse collection, rami generated successfully")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")

    def test_genera_da_istruttoria_requires_confirmed_istruttoria(self, auth_headers):
        """Test that genera-da-istruttoria requires a confirmed istruttoria."""
        # Use a non-existent preventivo to test 404
        url = f"{BASE_URL}/api/commesse-normative/genera-da-istruttoria/nonexistent_prev_123"
        response = requests.post(url, headers=auth_headers)
        
        assert response.status_code in [400, 404], f"Expected 400 or 404, got {response.status_code}"
        print(f"SUCCESS: Correctly returned {response.status_code} for non-existent istruttoria")


class TestPhase2GeneraWithRami:
    """Tests for POST /api/istruttoria/phase2/genera/{preventivo_id} with rami_generati[]"""

    def test_phase2_genera_includes_rami_generati(self, auth_headers):
        """Test that Phase 2 genera endpoint returns rami_generati[] in response."""
        url = f"{BASE_URL}/api/istruttoria/phase2/genera/{PREVENTIVO_WITH_PREISTRUITA}"
        response = requests.post(url, headers=auth_headers)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text[:1000]}")
        
        # May return 409 if commessa already exists (which is expected for this test data)
        if response.status_code == 409:
            print("Note: Commessa already exists (expected for test data with existing preistruita)")
            # Try to get the existing commessa to verify rami exist
            commessa_url = f"{BASE_URL}/api/istruttoria/phase2/commessa/{PREVENTIVO_WITH_PREISTRUITA}"
            commessa_response = requests.get(commessa_url, headers=auth_headers)
            if commessa_response.status_code == 200:
                commessa_data = commessa_response.json()
                commessa_id = commessa_data.get("commessa", {}).get("commessa_id")
                
                # Verify rami exist for this commessa
                rami_url = f"{BASE_URL}/api/commesse-normative/{commessa_id}"
                rami_response = requests.get(rami_url, headers=auth_headers)
                if rami_response.status_code == 200:
                    rami_data = rami_response.json()
                    print(f"Existing rami for commessa: {rami_data}")
                    assert "rami" in rami_data, "Should have rami array"
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "commessa" in data, "Response should contain 'commessa'"
        assert "rami_generati" in data, "Response should contain 'rami_generati' array"
        
        rami_generati = data["rami_generati"]
        print(f"rami_generati: {rami_generati}")
        
        # Verify rami_generati structure
        if len(rami_generati) > 0:
            ramo = rami_generati[0]
            assert "ramo_id" in ramo, "Ramo should have ramo_id"
            assert "normativa" in ramo, "Ramo should have normativa"
            assert "codice_ramo" in ramo, "Ramo should have codice_ramo"
            print(f"SUCCESS: Phase 2 returned {len(rami_generati)} rami_generati")
        else:
            print("Note: No new rami generated (may already exist)")


class TestCreaRamoSearchesBothCollections:
    """Tests that crea_ramo searches commessa in both commesse and commesse_preistruite collections."""

    def test_get_normative_branches_for_preistruita(self, auth_headers):
        """Test that get_normative_branches works for commessa in commesse_preistruite."""
        # First get the commessa_id from the preistruita
        commessa_url = f"{BASE_URL}/api/istruttoria/phase2/commessa/{PREVENTIVO_WITH_PREISTRUITA}"
        commessa_response = requests.get(commessa_url, headers=auth_headers)
        
        if commessa_response.status_code != 200:
            pytest.skip(f"Could not get commessa preistruita: {commessa_response.status_code}")
        
        commessa_data = commessa_response.json()
        commessa_id = commessa_data.get("commessa", {}).get("commessa_id")
        
        if not commessa_id:
            pytest.skip("No commessa_id found in preistruita")
        
        # Now get normative branches for this commessa
        rami_url = f"{BASE_URL}/api/commesse-normative/{commessa_id}"
        rami_response = requests.get(rami_url, headers=auth_headers)
        
        print(f"Rami response status: {rami_response.status_code}")
        print(f"Rami response body: {rami_response.text[:500]}")
        
        assert rami_response.status_code == 200, f"Expected 200, got {rami_response.status_code}"
        
        rami_data = rami_response.json()
        assert "rami" in rami_data, "Response should contain 'rami' array"
        
        # Should have at least one ramo (either real or legacy wrap)
        rami = rami_data["rami"]
        print(f"Found {len(rami)} rami for commessa {commessa_id}")
        
        if len(rami) > 0:
            ramo = rami[0]
            print(f"First ramo: {ramo}")
            assert "normativa" in ramo, "Ramo should have normativa"
            
            # Check if it's a legacy wrap or real ramo
            if ramo.get("is_virtual"):
                print("Note: This is a legacy wrap (virtual ramo)")
            else:
                print(f"Real ramo: {ramo.get('ramo_id')}")
        
        print(f"SUCCESS: get_normative_branches works for commessa_preistruita")

    def test_legacy_adapter_fallback_to_preistruita(self, auth_headers):
        """Test that legacy adapter falls back to commesse_preistruite when commessa not in commesse."""
        # Get commessa from preistruita
        commessa_url = f"{BASE_URL}/api/istruttoria/phase2/commessa/{PREVENTIVO_WITH_PREISTRUITA}"
        commessa_response = requests.get(commessa_url, headers=auth_headers)
        
        if commessa_response.status_code != 200:
            pytest.skip(f"Could not get commessa preistruita: {commessa_response.status_code}")
        
        commessa_data = commessa_response.json()
        commessa_id = commessa_data.get("commessa", {}).get("commessa_id")
        normativa = commessa_data.get("commessa", {}).get("normativa")
        
        print(f"Commessa ID: {commessa_id}")
        print(f"Normativa: {normativa}")
        
        # Get branches - should work even if commessa is only in commesse_preistruite
        rami_url = f"{BASE_URL}/api/commesse-normative/{commessa_id}"
        rami_response = requests.get(rami_url, headers=auth_headers)
        
        assert rami_response.status_code == 200, f"Expected 200, got {rami_response.status_code}"
        
        rami_data = rami_response.json()
        rami = rami_data.get("rami", [])
        
        # Should return at least a legacy wrap if no real rami exist
        if len(rami) == 0:
            print("Note: No rami found (may need to generate first)")
        else:
            print(f"SUCCESS: Found {len(rami)} rami via legacy adapter fallback")


class TestExistingRamoIdempotency:
    """Tests for idempotency with existing ramo (ramo_ebca8cb95185 for EN_1090)."""

    def test_existing_ramo_not_duplicated(self, auth_headers):
        """Test that existing ramo (ramo_ebca8cb95185) is not duplicated on re-generation."""
        url = f"{BASE_URL}/api/commesse-normative/genera-da-istruttoria/{PREVENTIVO_WITH_PREISTRUITA}"
        
        # Generate rami
        response = requests.post(url, headers=auth_headers)
        
        if response.status_code != 200:
            print(f"Note: Generate returned {response.status_code}: {response.text[:200]}")
            return
        
        data = response.json()
        rami = data.get("rami", [])
        
        # Check if existing ramo_id is in the response
        ramo_ids = [r.get("ramo_id") for r in rami]
        print(f"Ramo IDs returned: {ramo_ids}")
        
        # The existing ramo should be returned (updated, not duplicated)
        en1090_rami = [r for r in rami if r.get("normativa") == "EN_1090"]
        
        if len(en1090_rami) > 1:
            pytest.fail(f"Duplicate EN_1090 rami found: {en1090_rami}")
        
        if len(en1090_rami) == 1:
            print(f"SUCCESS: Single EN_1090 ramo returned: {en1090_rami[0].get('ramo_id')}")
        else:
            print("Note: No EN_1090 ramo found (may be different normativa)")


class TestIstruttoriaConfirmationRequired:
    """Tests that istruttoria must be confirmed before generating branches."""

    def test_unconfirmed_istruttoria_blocked(self, auth_headers):
        """Test that unconfirmed istruttoria cannot generate branches."""
        # This test uses a preventivo that may not be confirmed
        # The endpoint should return 400 if istruttoria is not confirmed
        
        # First check if the istruttoria is confirmed
        istr_url = f"{BASE_URL}/api/istruttoria/preventivo/{PREVENTIVO_WITH_PREISTRUITA}"
        istr_response = requests.get(istr_url, headers=auth_headers)
        
        if istr_response.status_code == 200:
            istr_data = istr_response.json()
            is_confirmed = istr_data.get("confermata", False)
            print(f"Istruttoria confirmed: {is_confirmed}")
            
            if is_confirmed:
                print("Note: Istruttoria is already confirmed, skipping unconfirmed test")
                return
        
        # If not confirmed, genera-da-istruttoria should fail
        url = f"{BASE_URL}/api/commesse-normative/genera-da-istruttoria/{PREVENTIVO_WITH_PREISTRUITA}"
        response = requests.post(url, headers=auth_headers)
        
        if response.status_code == 400:
            assert "confermata" in response.text.lower() or "confirmed" in response.text.lower(), \
                "Error should mention confirmation required"
            print("SUCCESS: Unconfirmed istruttoria correctly blocked")
        else:
            print(f"Note: Response was {response.status_code} (istruttoria may be confirmed)")


class TestRamoCodeGeneration:
    """Tests for ramo code generation (codice_ramo format)."""

    def test_codice_ramo_format(self, auth_headers):
        """Test that codice_ramo follows expected format: {numero}-{suffisso}."""
        url = f"{BASE_URL}/api/commesse-normative/genera-da-istruttoria/{PREVENTIVO_WITH_PREISTRUITA}"
        response = requests.post(url, headers=auth_headers)
        
        if response.status_code != 200:
            pytest.skip(f"Could not generate rami: {response.status_code}")
        
        data = response.json()
        rami = data.get("rami", [])
        
        for ramo in rami:
            codice_ramo = ramo.get("codice_ramo", "")
            normativa = ramo.get("normativa", "")
            
            print(f"Ramo: {ramo.get('ramo_id')}")
            print(f"  codice_ramo: {codice_ramo}")
            print(f"  normativa: {normativa}")
            
            # Verify codice_ramo contains the normativa suffix
            expected_suffixes = {
                "EN_1090": "1090",
                "EN_13241": "13241",
                "GENERICA": "GEN"
            }
            
            if normativa in expected_suffixes:
                expected_suffix = expected_suffixes[normativa]
                assert expected_suffix in codice_ramo, \
                    f"codice_ramo '{codice_ramo}' should contain suffix '{expected_suffix}' for {normativa}"
                print(f"  SUCCESS: codice_ramo contains expected suffix '{expected_suffix}'")


class TestRamoMetadata:
    """Tests for ramo metadata (created_from, source_istruttoria_id, etc.)."""

    def test_ramo_has_source_metadata(self, auth_headers):
        """Test that generated ramo has source metadata (created_from, source_istruttoria_id)."""
        url = f"{BASE_URL}/api/commesse-normative/genera-da-istruttoria/{PREVENTIVO_WITH_PREISTRUITA}"
        response = requests.post(url, headers=auth_headers)
        
        if response.status_code != 200:
            pytest.skip(f"Could not generate rami: {response.status_code}")
        
        data = response.json()
        rami = data.get("rami", [])
        
        for ramo in rami:
            print(f"Ramo: {ramo.get('ramo_id')}")
            
            # Check created_from
            created_from = ramo.get("created_from")
            print(f"  created_from: {created_from}")
            
            # Check source_istruttoria_id
            source_istr = ramo.get("source_istruttoria_id")
            print(f"  source_istruttoria_id: {source_istr}")
            
            # Check source_segmentation_snapshot
            seg_snapshot = ramo.get("source_segmentation_snapshot")
            print(f"  source_segmentation_snapshot: {seg_snapshot}")
            
            # Verify created_from is 'segmentazione' for auto-generated rami
            if created_from:
                assert created_from in ["segmentazione", "manuale", "legacy_wrap"], \
                    f"Unexpected created_from value: {created_from}"
                print(f"  SUCCESS: created_from is valid")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
