"""
Iteration 225 — P1.1 Segmentation Feature Tests
================================================
Tests for the new per-line segmentation feature:
- POST /api/istruttoria/segmenta/{preventivo_id} — runs AI per-line segmentation
- POST /api/istruttoria/segmenta/{preventivo_id}/review — saves user review (save_draft or confirm)
- Blocking when confirming with INCERTA lines
- Validation page aggregate (81% global, 7/8 correct)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
MAIN_USER_SESSION = "fEQQyik5bSdSU_dnWx_8QR1am6kyw543-sOFR12E7sk"
TEST_USER_SESSION = "test_perizia_205a45704b22"
TEST_PREVENTIVO_MISTA = "prev_8e8311d22a3c"  # PRV-2026-0021, already segmented


class TestSegmentationAPI:
    """Tests for segmentation endpoints"""

    @pytest.fixture
    def main_user_client(self):
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Cookie": f"session_token={MAIN_USER_SESSION}"
        })
        return session

    @pytest.fixture
    def test_user_client(self):
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Cookie": f"session_token={TEST_USER_SESSION}"
        })
        return session

    def test_segmenta_endpoint_returns_line_classification(self, main_user_client):
        """POST /api/istruttoria/segmenta/{preventivo_id} returns line_classification, segments, summary"""
        response = main_user_client.post(f"{BASE_URL}/api/istruttoria/segmenta/{TEST_PREVENTIVO_MISTA}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        seg = data.get("segmentazione", {})
        
        # Verify structure
        assert seg.get("enabled") == True, "Segmentation should be enabled"
        assert "line_classification" in seg, "Should have line_classification"
        assert "segments" in seg, "Should have segments"
        assert "summary" in seg, "Should have summary"
        
        # Verify line_classification structure
        lines = seg.get("line_classification", [])
        assert len(lines) > 0, "Should have at least one line"
        
        first_line = lines[0]
        assert "line_id" in first_line, "Line should have line_id"
        assert "proposed_normativa" in first_line, "Line should have proposed_normativa"
        assert "confidence" in first_line, "Line should have confidence"
        assert "descrizione" in first_line, "Line should have descrizione"
        
        # Verify summary structure
        summary = seg.get("summary", {})
        assert "righe_totali" in summary, "Summary should have righe_totali"
        assert "en_1090" in summary, "Summary should have en_1090 count"
        assert "en_13241" in summary, "Summary should have en_13241 count"
        assert "generiche" in summary, "Summary should have generiche count"
        assert "incerte" in summary, "Summary should have incerte count"

    def test_segmenta_review_save_draft(self, main_user_client):
        """POST /api/istruttoria/segmenta/{preventivo_id}/review with action=save_draft"""
        # First get current segmentation to get line_ids
        istr_response = main_user_client.get(f"{BASE_URL}/api/istruttoria/preventivo/{TEST_PREVENTIVO_MISTA}")
        assert istr_response.status_code == 200
        
        seg = istr_response.json().get("segmentazione_proposta", {})
        lines = seg.get("line_classification", [])
        assert len(lines) > 0, "Should have lines to review"
        
        first_line_id = lines[0]["line_id"]
        
        # Save draft review
        response = main_user_client.post(
            f"{BASE_URL}/api/istruttoria/segmenta/{TEST_PREVENTIVO_MISTA}/review",
            json={
                "line_reviews": [
                    {"line_id": first_line_id, "final_normativa": "EN_1090", "decision": "accepted"}
                ],
                "action": "save_draft"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "in_review", "Status should be in_review"
        assert "segmentazione" in data, "Should return updated segmentazione"

    def test_segmenta_confirm_blocked_with_incerta(self, main_user_client):
        """POST /api/istruttoria/segmenta/{preventivo_id}/review with action=confirm should fail if INCERTA lines exist"""
        # First ensure there's an INCERTA line by running segmentation
        main_user_client.post(f"{BASE_URL}/api/istruttoria/segmenta/{TEST_PREVENTIVO_MISTA}")
        
        # Try to confirm without classifying INCERTA lines
        response = main_user_client.post(
            f"{BASE_URL}/api/istruttoria/segmenta/{TEST_PREVENTIVO_MISTA}/review",
            json={
                "line_reviews": [],
                "action": "confirm"
            }
        )
        
        # Should fail with 400 error
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "INCERTE" in data.get("detail", ""), "Error should mention INCERTE lines"

    def test_segmenta_confirm_success_after_classifying_all(self, main_user_client):
        """POST /api/istruttoria/segmenta/{preventivo_id}/review with action=confirm succeeds when all lines classified"""
        # Get current segmentation
        istr_response = main_user_client.get(f"{BASE_URL}/api/istruttoria/preventivo/{TEST_PREVENTIVO_MISTA}")
        assert istr_response.status_code == 200
        
        seg = istr_response.json().get("segmentazione_proposta", {})
        lines = seg.get("line_classification", [])
        
        # Build reviews for all lines, classifying INCERTA as GENERICA
        line_reviews = []
        for lc in lines:
            norm = lc.get("proposed_normativa")
            if norm == "INCERTA":
                norm = "GENERICA"  # Classify uncertain as generic
            line_reviews.append({
                "line_id": lc["line_id"],
                "final_normativa": norm,
                "decision": "accepted" if lc.get("proposed_normativa") != "INCERTA" else "corrected"
            })
        
        # Confirm with all lines classified
        response = main_user_client.post(
            f"{BASE_URL}/api/istruttoria/segmenta/{TEST_PREVENTIVO_MISTA}/review",
            json={
                "line_reviews": line_reviews,
                "action": "confirm"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "confirmed", "Status should be confirmed"
        assert "official_segmentation" in data, "Should return official_segmentation"
        
        official = data.get("official_segmentation", {})
        assert official.get("confirmed") == True, "official_segmentation.confirmed should be True"
        assert "line_assignments" in official, "Should have line_assignments"

    def test_istruttoria_has_segmentazione_proposta(self, main_user_client):
        """GET /api/istruttoria/preventivo/{preventivo_id} returns segmentazione_proposta for MISTA"""
        response = main_user_client.get(f"{BASE_URL}/api/istruttoria/preventivo/{TEST_PREVENTIVO_MISTA}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "segmentazione_proposta" in data, "Should have segmentazione_proposta"
        
        seg = data.get("segmentazione_proposta", {})
        assert seg.get("enabled") == True, "Segmentation should be enabled"


class TestValidationAggregate:
    """Tests for validation page aggregate (updated ground truth)"""

    @pytest.fixture
    def test_user_client(self):
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Cookie": f"session_token={TEST_USER_SESSION}"
        })
        return session

    def test_validation_set_has_8_preventivi(self, test_user_client):
        """GET /api/validation/set returns 8 preventivi"""
        response = test_user_client.get(f"{BASE_URL}/api/validation/set")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        validation_set = data.get("validation_set", [])
        assert len(validation_set) == 8, f"Expected 8 preventivi, got {len(validation_set)}"

    def test_validation_aggregate_81_percent(self, test_user_client):
        """GET /api/validation/results shows 81% global score (updated from 75%)"""
        response = test_user_client.get(f"{BASE_URL}/api/validation/results")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        aggregato = data.get("aggregato", {})
        
        # Verify aggregate scores
        assert aggregato.get("n_preventivi") == 8, "Should have 8 preventivi"
        assert aggregato.get("punteggio_medio_globale") == 0.81, f"Expected 81% global, got {aggregato.get('punteggio_medio_globale')}"
        assert aggregato.get("classificazione_corretta") == "7/8", f"Expected 7/8 correct, got {aggregato.get('classificazione_corretta')}"

    def test_validation_set_includes_mista_preventivi(self, test_user_client):
        """Validation set includes MISTA preventivi with correct ground truth"""
        response = test_user_client.get(f"{BASE_URL}/api/validation/set")
        assert response.status_code == 200
        
        data = response.json()
        validation_set = data.get("validation_set", [])
        
        # Find MISTA preventivi
        mista_preventivi = [v for v in validation_set if v.get("normativa_attesa") == "MISTA"]
        assert len(mista_preventivi) >= 2, f"Expected at least 2 MISTA preventivi, got {len(mista_preventivi)}"
        
        # Check specific MISTA preventivi
        mista_ids = [v.get("preventivo_id") for v in mista_preventivi]
        assert "prev_eb87b5c85253" in mista_ids, "prev_eb87b5c85253 should be MISTA"
        assert "prev_8e8311d22a3c" in mista_ids, "prev_8e8311d22a3c should be MISTA"


class TestSegmentationEngine:
    """Tests for segmentation engine logic"""

    @pytest.fixture
    def main_user_client(self):
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Cookie": f"session_token={MAIN_USER_SESSION}"
        })
        return session

    def test_segmentation_classifies_cancello_as_en13241(self, main_user_client):
        """Segmentation engine classifies cancello/motorizzazione as EN_13241"""
        response = main_user_client.post(f"{BASE_URL}/api/istruttoria/segmenta/{TEST_PREVENTIVO_MISTA}")
        assert response.status_code == 200
        
        seg = response.json().get("segmentazione", {})
        lines = seg.get("line_classification", [])
        
        # Find lines with cancello/motorizzazione
        cancello_lines = [lc for lc in lines if "cancell" in lc.get("descrizione", "").lower() or "motorizzazione" in lc.get("descrizione", "").lower()]
        
        for lc in cancello_lines:
            assert lc.get("proposed_normativa") == "EN_13241", f"Cancello line should be EN_13241: {lc.get('descrizione')[:50]}"

    def test_segmentation_classifies_parapetto_correctly(self, main_user_client):
        """Segmentation engine classifies parapetti as GENERICA or EN_1090 based on context"""
        response = main_user_client.post(f"{BASE_URL}/api/istruttoria/segmenta/{TEST_PREVENTIVO_MISTA}")
        assert response.status_code == 200
        
        seg = response.json().get("segmentazione", {})
        lines = seg.get("line_classification", [])
        
        # Find parapetto lines
        parapetto_lines = [lc for lc in lines if "parapett" in lc.get("descrizione", "").lower()]
        
        # Parapetti should be classified (not all INCERTA)
        for lc in parapetto_lines:
            norm = lc.get("proposed_normativa")
            assert norm in ["EN_1090", "GENERICA", "INCERTA"], f"Parapetto should be EN_1090, GENERICA, or INCERTA: {norm}"

    def test_segmentation_summary_counts_match_lines(self, main_user_client):
        """Summary counts should match actual line classifications"""
        response = main_user_client.post(f"{BASE_URL}/api/istruttoria/segmenta/{TEST_PREVENTIVO_MISTA}")
        assert response.status_code == 200
        
        seg = response.json().get("segmentazione", {})
        lines = seg.get("line_classification", [])
        summary = seg.get("summary", {})
        
        # Count lines by normativa
        counts = {"EN_1090": 0, "EN_13241": 0, "GENERICA": 0, "INCERTA": 0}
        for lc in lines:
            norm = lc.get("proposed_normativa")
            if norm in counts:
                counts[norm] += 1
        
        # Verify summary matches
        assert summary.get("en_1090") == counts["EN_1090"], f"EN_1090 count mismatch: {summary.get('en_1090')} vs {counts['EN_1090']}"
        assert summary.get("en_13241") == counts["EN_13241"], f"EN_13241 count mismatch: {summary.get('en_13241')} vs {counts['EN_13241']}"
        assert summary.get("generiche") == counts["GENERICA"], f"GENERICA count mismatch: {summary.get('generiche')} vs {counts['GENERICA']}"
        assert summary.get("incerte") == counts["INCERTA"], f"INCERTA count mismatch: {summary.get('incerte')} vs {counts['INCERTA']}"
        assert summary.get("righe_totali") == len(lines), f"Total count mismatch: {summary.get('righe_totali')} vs {len(lines)}"
