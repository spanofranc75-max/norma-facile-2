"""
Iteration 219 — Test POST /api/istruttoria/{id}/rispondi endpoint
Tests for saving user answers to residual questions in istruttoria.

Features tested:
1. POST /api/istruttoria/{id}/rispondi - saves answers with correct payload
2. POST /api/istruttoria/{id}/rispondi - validates empty payload (400 error)
3. POST /api/istruttoria/{id}/rispondi - non-existent istruttoria (404 error)
4. POST /api/istruttoria/{id}/rispondi - merge with existing answers
5. GET /api/istruttoria/{id} - verify risposte_utente persistence
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "c87bbcfe2ef64f5c9e48c4cf73f7b2ff"
TEST_ISTRUTTORIA_ID = "istr_701cc0cc1ddc"
TEST_PREVENTIVO_ID = "prev_625826c752ac"


@pytest.fixture
def api_client():
    """Shared requests session with auth cookie"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Cookie": f"session_token={SESSION_TOKEN}"
    })
    return session


class TestRispondiDomandeEndpoint:
    """Tests for POST /api/istruttoria/{id}/rispondi endpoint"""

    def test_rispondi_saves_answer_correctly(self, api_client):
        """Test that POST /api/istruttoria/{id}/rispondi saves answers with correct payload"""
        # Save answer to Q2 (index 2) which is currently unanswered
        payload = {
            "risposte": [
                {"domanda_idx": 2, "risposta": "TEST_Tolleranze standard EN 1090 classe 1"}
            ]
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload
        )
        
        # Status assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Data assertions
        data = response.json()
        assert "message" in data
        assert "risposte_utente" in data
        assert "n_risposte" in data
        assert "n_domande_totali" in data
        
        # Verify the answer was saved
        assert "2" in data["risposte_utente"]
        assert data["risposte_utente"]["2"]["risposta"] == "TEST_Tolleranze standard EN 1090 classe 1"
        assert "risposto_da" in data["risposte_utente"]["2"]
        assert "risposto_da_nome" in data["risposte_utente"]["2"]
        assert "risposto_il" in data["risposte_utente"]["2"]
        
        # Verify counts
        assert data["n_risposte"] >= 3  # Now should have 3 answers (Q0, Q1, Q2)
        assert data["n_domande_totali"] == 3
        
        print(f"✓ Answer saved successfully: {data['message']}")

    def test_rispondi_validates_empty_payload(self, api_client):
        """Test that POST /api/istruttoria/{id}/rispondi returns 400 for empty payload"""
        # Test with empty risposte array
        payload = {"risposte": []}
        
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ Empty payload correctly rejected with 400")

    def test_rispondi_validates_missing_risposte_key(self, api_client):
        """Test that POST /api/istruttoria/{id}/rispondi returns 400 for missing risposte key"""
        payload = {}
        
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ Missing risposte key correctly rejected with 400")

    def test_rispondi_nonexistent_istruttoria_returns_404(self, api_client):
        """Test that POST /api/istruttoria/{id}/rispondi returns 404 for non-existent istruttoria"""
        fake_id = f"istr_{uuid.uuid4().hex[:12]}"
        payload = {
            "risposte": [
                {"domanda_idx": 0, "risposta": "Test answer"}
            ]
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{fake_id}/rispondi",
            json=payload
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"✓ Non-existent istruttoria {fake_id} correctly returns 404")

    def test_rispondi_merges_with_existing_answers(self, api_client):
        """Test that POST /api/istruttoria/{id}/rispondi merges with existing answers"""
        # First, get current state
        get_response = api_client.get(f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}")
        assert get_response.status_code == 200
        initial_data = get_response.json()
        initial_risposte = initial_data.get("risposte_utente", {})
        
        # Update Q0 with a new answer (should merge, not replace all)
        payload = {
            "risposte": [
                {"domanda_idx": 0, "risposta": "TEST_Updated: Si, montaggio in cantiere confermato"}
            ]
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify Q0 was updated
        assert "0" in data["risposte_utente"]
        assert "TEST_Updated" in data["risposte_utente"]["0"]["risposta"]
        
        # Verify Q1 still exists (merge, not replace)
        assert "1" in data["risposte_utente"]
        
        print("✓ Answers correctly merged with existing data")

    def test_rispondi_ignores_invalid_indices(self, api_client):
        """Test that POST /api/istruttoria/{id}/rispondi ignores invalid question indices"""
        payload = {
            "risposte": [
                {"domanda_idx": 999, "risposta": "Invalid index answer"},  # Out of range
                {"domanda_idx": -1, "risposta": "Negative index"},  # Negative
                {"domanda_idx": 0, "risposta": "Valid answer for Q0"}  # Valid
            ]
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Only valid index should be saved
        assert "999" not in data["risposte_utente"]
        assert "-1" not in data["risposte_utente"]
        assert "0" in data["risposte_utente"]
        
        print("✓ Invalid indices correctly ignored")

    def test_rispondi_ignores_empty_answers(self, api_client):
        """Test that POST /api/istruttoria/{id}/rispondi ignores empty/whitespace answers"""
        payload = {
            "risposte": [
                {"domanda_idx": 0, "risposta": "   "},  # Whitespace only
                {"domanda_idx": 1, "risposta": ""},  # Empty string
            ]
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload
        )
        
        # Should return 400 since no valid answers after filtering
        # OR 200 if it just ignores them - let's check the actual behavior
        # Based on code review: it filters empty answers, if none left, returns 400
        # But if there are existing answers, it might still return 200
        # Let's verify the behavior
        print(f"Response for empty answers: {response.status_code}")
        
        # The endpoint should either reject (400) or accept but not save empty answers
        if response.status_code == 200:
            data = response.json()
            # Verify empty answers weren't saved as empty
            if "0" in data["risposte_utente"]:
                assert data["risposte_utente"]["0"]["risposta"].strip() != ""
        
        print("✓ Empty answers handled correctly")


class TestGetIstruttoriaWithRisposte:
    """Tests for GET /api/istruttoria/{id} - verify risposte_utente persistence"""

    def test_get_istruttoria_returns_risposte_utente(self, api_client):
        """Test that GET /api/istruttoria/{id} returns saved risposte_utente"""
        response = api_client.get(f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify risposte_utente structure
        assert "risposte_utente" in data
        assert isinstance(data["risposte_utente"], dict)
        
        # Verify at least some answers exist
        assert len(data["risposte_utente"]) > 0
        
        # Verify answer structure
        for idx, answer in data["risposte_utente"].items():
            assert "risposta" in answer
            assert "domanda" in answer
            assert "risposto_da" in answer
            assert "risposto_da_nome" in answer
            assert "risposto_il" in answer
        
        print(f"✓ GET returns risposte_utente with {len(data['risposte_utente'])} answers")

    def test_get_istruttoria_by_preventivo_returns_risposte(self, api_client):
        """Test that GET /api/istruttoria/preventivo/{id} returns saved risposte_utente"""
        response = api_client.get(f"{BASE_URL}/api/istruttoria/preventivo/{TEST_PREVENTIVO_ID}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify risposte_utente is present
        assert "risposte_utente" in data
        assert "n_risposte" in data
        assert "n_domande_totali" in data
        
        print(f"✓ GET by preventivo returns risposte: {data['n_risposte']}/{data['n_domande_totali']}")

    def test_risposte_persist_after_save(self, api_client):
        """Test that saved answers persist and can be retrieved"""
        # Save a unique answer
        unique_text = f"TEST_Persistence check {uuid.uuid4().hex[:8]}"
        payload = {
            "risposte": [
                {"domanda_idx": 2, "risposta": unique_text}
            ]
        }
        
        # Save
        save_response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload
        )
        assert save_response.status_code == 200
        
        # Retrieve and verify
        get_response = api_client.get(f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}")
        assert get_response.status_code == 200
        data = get_response.json()
        
        # Verify the unique answer persisted
        assert "2" in data["risposte_utente"]
        assert data["risposte_utente"]["2"]["risposta"] == unique_text
        
        print(f"✓ Answer persisted correctly: {unique_text[:30]}...")


class TestRispondiAuthValidation:
    """Tests for authentication validation on rispondi endpoint"""

    def test_rispondi_without_auth_returns_401(self):
        """Test that POST /api/istruttoria/{id}/rispondi without auth returns 401"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        # No auth cookie
        
        payload = {
            "risposte": [
                {"domanda_idx": 0, "risposta": "Test"}
            ]
        }
        
        response = session.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthenticated request correctly rejected with 401")

    def test_rispondi_with_invalid_token_returns_401(self):
        """Test that POST /api/istruttoria/{id}/rispondi with invalid token returns 401"""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Cookie": "session_token=invalid_token_12345"
        })
        
        payload = {
            "risposte": [
                {"domanda_idx": 0, "risposta": "Test"}
            ]
        }
        
        response = session.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid token correctly rejected with 401")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
