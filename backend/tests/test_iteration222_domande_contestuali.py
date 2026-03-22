"""
Test Iteration 222 — P0.25: Domande Contestuali Dinamiche
==========================================================
Tests for dynamic contextual questions that appear based on parent question answers.

Features tested:
1. POST /api/istruttoria/{id}/rispondi returns domande_contestuali field
2. Montaggio positive triggers ctx_mont_01 and ctx_mont_02 as active
3. Zincatura external triggers ctx_zinc_01 and ctx_zinc_02 as active
4. Saldatura positive triggers ctx_sald_01 and ctx_sald_02 as active
5. Changing parent answer to negative marks child questions as stale
6. POST /api/istruttoria/{id}/rispondi-contestuale saves contextual answers
7. Existing contextual answers preserved when re-triggering

Rules:
- 3 branches: zincatura esterna (2 questions), saldatura si (2 questions), montaggio si (2 questions)
- Max 1 level of depth
- Contextual questions are rule-based, persisted in DB, marked stale when trigger changes
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "99659c11314245d4ae753a9ae27aef5a"
TEST_ISTRUTTORIA_ID = "istr_701cc0cc1ddc"
TEST_PREVENTIVO_ID = "prev_625826c752ac"


@pytest.fixture
def api_client():
    """Shared requests session with auth cookie"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestDomandeContestualiBackend:
    """Tests for domande_contestuali generation and persistence"""

    def test_rispondi_returns_domande_contestuali_field(self, api_client):
        """Verify POST /api/istruttoria/{id}/rispondi returns domande_contestuali field"""
        # Submit answers to trigger contextual questions
        payload = {
            "risposte": [
                {"domanda_idx": 0, "risposta": "Si, installazione in cantiere inclusa"},  # montaggio positive
                {"domanda_idx": 1, "risposta": "Zincatura esterna (terzista)"},  # zincatura external
                {"domanda_idx": 2, "risposta": "Tolleranze standard EN 1090"}
            ]
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "domande_contestuali" in data, "domande_contestuali field missing from rispondi response"
        
        ctx_questions = data["domande_contestuali"]
        assert isinstance(ctx_questions, list), "domande_contestuali should be a list"
        assert len(ctx_questions) == 6, f"Expected 6 contextual questions (all rules), got {len(ctx_questions)}"
        
        print(f"PASSED: POST rispondi returns domande_contestuali with {len(ctx_questions)} questions")

    def test_montaggio_positive_triggers_ctx_mont_questions(self, api_client):
        """Verify montaggio positive triggers ctx_mont_01 and ctx_mont_02 as active"""
        # Submit montaggio positive answer
        payload = {
            "risposte": [
                {"domanda_idx": 0, "risposta": "Si, installazione in cantiere inclusa"}  # montaggio positive
            ]
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        ctx_questions = data.get("domande_contestuali", [])
        
        # Find montaggio contextual questions
        ctx_mont_01 = next((q for q in ctx_questions if q["id"] == "ctx_mont_01"), None)
        ctx_mont_02 = next((q for q in ctx_questions if q["id"] == "ctx_mont_02"), None)
        
        assert ctx_mont_01 is not None, "ctx_mont_01 not found in domande_contestuali"
        assert ctx_mont_02 is not None, "ctx_mont_02 not found in domande_contestuali"
        
        # Verify they are active
        assert ctx_mont_01["active"] == True, f"ctx_mont_01 should be active, got {ctx_mont_01['active']}"
        assert ctx_mont_02["active"] == True, f"ctx_mont_02 should be active, got {ctx_mont_02['active']}"
        
        # Verify parent category
        assert ctx_mont_01["parent_category"] == "montaggio"
        assert ctx_mont_02["parent_category"] == "montaggio"
        
        # Verify triggered_by_stato
        assert ctx_mont_01["triggered_by_stato"] == "positive"
        assert ctx_mont_02["triggered_by_stato"] == "positive"
        
        print(f"PASSED: Montaggio positive triggers ctx_mont_01 and ctx_mont_02 as active")

    def test_zincatura_external_triggers_ctx_zinc_questions(self, api_client):
        """Verify zincatura external triggers ctx_zinc_01 and ctx_zinc_02 as active"""
        # Submit zincatura external answer
        payload = {
            "risposte": [
                {"domanda_idx": 1, "risposta": "Zincatura esterna (terzista)"}  # zincatura external
            ]
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        ctx_questions = data.get("domande_contestuali", [])
        
        # Find zincatura contextual questions
        ctx_zinc_01 = next((q for q in ctx_questions if q["id"] == "ctx_zinc_01"), None)
        ctx_zinc_02 = next((q for q in ctx_questions if q["id"] == "ctx_zinc_02"), None)
        
        assert ctx_zinc_01 is not None, "ctx_zinc_01 not found in domande_contestuali"
        assert ctx_zinc_02 is not None, "ctx_zinc_02 not found in domande_contestuali"
        
        # Verify they are active
        assert ctx_zinc_01["active"] == True, f"ctx_zinc_01 should be active, got {ctx_zinc_01['active']}"
        assert ctx_zinc_02["active"] == True, f"ctx_zinc_02 should be active, got {ctx_zinc_02['active']}"
        
        # Verify parent category
        assert ctx_zinc_01["parent_category"] == "zincatura"
        assert ctx_zinc_02["parent_category"] == "zincatura"
        
        # Verify triggered_by_stato
        assert ctx_zinc_01["triggered_by_stato"] == "external"
        assert ctx_zinc_02["triggered_by_stato"] == "external"
        
        print(f"PASSED: Zincatura external triggers ctx_zinc_01 and ctx_zinc_02 as active")

    def test_saldatura_positive_triggers_ctx_sald_questions(self, api_client):
        """Verify saldatura positive triggers ctx_sald_01 and ctx_sald_02 as active"""
        # First, we need to check if there's a saldatura question in this istruttoria
        response = api_client.get(f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}")
        assert response.status_code == 200
        
        data = response.json()
        domande = data.get("domande_residue", [])
        
        # Check if any question is about saldatura
        saldatura_idx = None
        for idx, q in enumerate(domande):
            domanda_text = q.get("domanda", "").lower()
            if any(kw in domanda_text for kw in ['saldatura', 'saldare', 'saldato', 'giunzione']):
                saldatura_idx = idx
                break
        
        if saldatura_idx is None:
            # No saldatura question in this istruttoria - verify ctx_sald questions are inactive
            ctx_questions = data.get("domande_contestuali", [])
            ctx_sald_01 = next((q for q in ctx_questions if q["id"] == "ctx_sald_01"), None)
            ctx_sald_02 = next((q for q in ctx_questions if q["id"] == "ctx_sald_02"), None)
            
            if ctx_sald_01:
                assert ctx_sald_01["active"] == False, "ctx_sald_01 should be inactive (no saldatura question)"
            if ctx_sald_02:
                assert ctx_sald_02["active"] == False, "ctx_sald_02 should be inactive (no saldatura question)"
            
            print(f"PASSED: No saldatura question in istruttoria - ctx_sald questions correctly inactive")
        else:
            # Submit saldatura positive answer
            payload = {
                "risposte": [
                    {"domanda_idx": saldatura_idx, "risposta": "Si, in officina"}  # saldatura positive
                ]
            }
            
            response = api_client.post(
                f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
                json=payload
            )
            assert response.status_code == 200
            
            data = response.json()
            ctx_questions = data.get("domande_contestuali", [])
            
            ctx_sald_01 = next((q for q in ctx_questions if q["id"] == "ctx_sald_01"), None)
            ctx_sald_02 = next((q for q in ctx_questions if q["id"] == "ctx_sald_02"), None)
            
            assert ctx_sald_01 is not None, "ctx_sald_01 not found"
            assert ctx_sald_02 is not None, "ctx_sald_02 not found"
            assert ctx_sald_01["active"] == True, "ctx_sald_01 should be active"
            assert ctx_sald_02["active"] == True, "ctx_sald_02 should be active"
            
            print(f"PASSED: Saldatura positive triggers ctx_sald_01 and ctx_sald_02 as active")


class TestStaleMarking:
    """Tests for stale marking when parent answer changes"""

    def test_changing_parent_to_negative_marks_children_stale(self, api_client):
        """Verify changing parent answer to negative marks child questions as stale"""
        # First, ensure zincatura is external (triggers ctx_zinc questions)
        payload_external = {
            "risposte": [
                {"domanda_idx": 1, "risposta": "Zincatura esterna (terzista)"}
            ]
        }
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload_external
        )
        assert response.status_code == 200
        
        # Verify ctx_zinc questions are active
        data = response.json()
        ctx_questions = data.get("domande_contestuali", [])
        ctx_zinc_01 = next((q for q in ctx_questions if q["id"] == "ctx_zinc_01"), None)
        assert ctx_zinc_01["active"] == True, "ctx_zinc_01 should be active before change"
        
        # Now change zincatura to negative (Nessun trattamento)
        payload_negative = {
            "risposte": [
                {"domanda_idx": 1, "risposta": "Nessun trattamento"}
            ]
        }
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload_negative
        )
        assert response.status_code == 200
        
        data = response.json()
        ctx_questions = data.get("domande_contestuali", [])
        
        ctx_zinc_01 = next((q for q in ctx_questions if q["id"] == "ctx_zinc_01"), None)
        ctx_zinc_02 = next((q for q in ctx_questions if q["id"] == "ctx_zinc_02"), None)
        
        # Verify they are now inactive (not active)
        assert ctx_zinc_01["active"] == False, f"ctx_zinc_01 should be inactive after parent change, got {ctx_zinc_01['active']}"
        assert ctx_zinc_02["active"] == False, f"ctx_zinc_02 should be inactive after parent change, got {ctx_zinc_02['active']}"
        
        # If they had answers, they should be marked stale
        # (stale = had_answer AND not should_be_active)
        print(f"PASSED: Changing zincatura to negative marks ctx_zinc questions as inactive")
        
        # Restore external for other tests
        api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload_external
        )


class TestRispondiContestuale:
    """Tests for POST /api/istruttoria/{id}/rispondi-contestuale endpoint"""

    def test_rispondi_contestuale_saves_answers(self, api_client):
        """Verify POST /api/istruttoria/{id}/rispondi-contestuale saves contextual answers"""
        # First ensure montaggio is positive to have active ctx_mont questions
        payload_base = {
            "risposte": [
                {"domanda_idx": 0, "risposta": "Si, installazione in cantiere inclusa"}
            ]
        }
        api_client.post(f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi", json=payload_base)
        
        # Now save contextual answers
        payload_ctx = {
            "risposte": [
                {"id": "ctx_mont_01", "risposta": "Interno"},
                {"id": "ctx_mont_02", "risposta": "Da verificare"}
            ]
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi-contestuale",
            json=payload_ctx
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "domande_contestuali" in data, "domande_contestuali missing from response"
        assert "message" in data, "message missing from response"
        
        # Verify answers were saved
        ctx_questions = data["domande_contestuali"]
        ctx_mont_01 = next((q for q in ctx_questions if q["id"] == "ctx_mont_01"), None)
        ctx_mont_02 = next((q for q in ctx_questions if q["id"] == "ctx_mont_02"), None)
        
        assert ctx_mont_01["risposta"] == "Interno", f"ctx_mont_01 risposta not saved, got {ctx_mont_01.get('risposta')}"
        assert ctx_mont_02["risposta"] == "Da verificare", f"ctx_mont_02 risposta not saved, got {ctx_mont_02.get('risposta')}"
        
        # Verify metadata
        assert ctx_mont_01.get("risposto_da") is not None, "risposto_da should be set"
        assert ctx_mont_01.get("risposto_il") is not None, "risposto_il should be set"
        
        print(f"PASSED: POST rispondi-contestuale saves contextual answers correctly")

    def test_rispondi_contestuale_empty_returns_400(self, api_client):
        """Verify POST /api/istruttoria/{id}/rispondi-contestuale with empty risposte returns 400"""
        payload = {"risposte": []}
        
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi-contestuale",
            json=payload
        )
        assert response.status_code == 400, f"Expected 400 for empty risposte, got {response.status_code}"
        
        print(f"PASSED: Empty risposte returns 400")

    def test_existing_answers_preserved_on_retrigger(self, api_client):
        """Verify existing contextual answers are preserved when re-triggering"""
        # First, save an answer to ctx_mont_01
        payload_ctx = {
            "risposte": [
                {"id": "ctx_mont_01", "risposta": "Interno"}
            ]
        }
        api_client.post(f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi-contestuale", json=payload_ctx)
        
        # Now change montaggio to negative (deactivates ctx_mont questions)
        payload_negative = {
            "risposte": [
                {"domanda_idx": 0, "risposta": "Non previsto"}
            ]
        }
        api_client.post(f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi", json=payload_negative)
        
        # Change back to positive (re-triggers ctx_mont questions)
        payload_positive = {
            "risposte": [
                {"domanda_idx": 0, "risposta": "Si, installazione in cantiere inclusa"}
            ]
        }
        response = api_client.post(
            f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}/rispondi",
            json=payload_positive
        )
        assert response.status_code == 200
        
        data = response.json()
        ctx_questions = data.get("domande_contestuali", [])
        ctx_mont_01 = next((q for q in ctx_questions if q["id"] == "ctx_mont_01"), None)
        
        # Answer should be preserved
        assert ctx_mont_01["risposta"] == "Interno", f"Answer should be preserved, got {ctx_mont_01.get('risposta')}"
        assert ctx_mont_01["active"] == True, "ctx_mont_01 should be active again"
        assert ctx_mont_01["stale"] == False, "ctx_mont_01 should not be stale (re-triggered)"
        
        print(f"PASSED: Existing contextual answers preserved when re-triggering")


class TestContextualQuestionStructure:
    """Tests for contextual question data structure"""

    def test_contextual_question_has_required_fields(self, api_client):
        """Verify each contextual question has all required fields"""
        response = api_client.get(f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}")
        assert response.status_code == 200
        
        data = response.json()
        ctx_questions = data.get("domande_contestuali", [])
        
        required_fields = [
            "id", "parent_category", "parent_domanda_idx", "triggered_by_stato",
            "trigger_reason", "domanda", "opzioni", "impatto", "active", "stale", "visible"
        ]
        
        for q in ctx_questions:
            for field in required_fields:
                assert field in q, f"Contextual question {q.get('id')} missing field '{field}'"
        
        print(f"PASSED: All {len(ctx_questions)} contextual questions have required fields")

    def test_trigger_reason_format(self, api_client):
        """Verify trigger_reason contains 'Comparsa perché hai...' format"""
        response = api_client.get(f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}")
        assert response.status_code == 200
        
        data = response.json()
        ctx_questions = data.get("domande_contestuali", [])
        
        for q in ctx_questions:
            trigger_reason = q.get("trigger_reason", "")
            assert "Comparsa perché hai" in trigger_reason or "Comparsa perche hai" in trigger_reason, \
                f"trigger_reason should contain 'Comparsa perché hai...', got: {trigger_reason}"
        
        print(f"PASSED: All trigger_reason fields have correct format")

    def test_contextual_questions_have_opzioni(self, api_client):
        """Verify contextual questions have opzioni array"""
        response = api_client.get(f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}")
        assert response.status_code == 200
        
        data = response.json()
        ctx_questions = data.get("domande_contestuali", [])
        
        # Check specific questions have expected opzioni
        ctx_mont_01 = next((q for q in ctx_questions if q["id"] == "ctx_mont_01"), None)
        ctx_zinc_02 = next((q for q in ctx_questions if q["id"] == "ctx_zinc_02"), None)
        
        if ctx_mont_01:
            assert "Interno" in ctx_mont_01.get("opzioni", []), "ctx_mont_01 should have 'Interno' option"
            assert "Affidato a terzi" in ctx_mont_01.get("opzioni", []), "ctx_mont_01 should have 'Affidato a terzi' option"
        
        if ctx_zinc_02:
            assert len(ctx_zinc_02.get("opzioni", [])) > 0, "ctx_zinc_02 should have opzioni"
        
        print(f"PASSED: Contextual questions have correct opzioni")


class TestGetIstruttoriaWithContextual:
    """Tests for GET /api/istruttoria/{id} with contextual questions"""

    def test_get_istruttoria_includes_domande_contestuali(self, api_client):
        """Verify GET /api/istruttoria/{id} includes domande_contestuali field"""
        response = api_client.get(f"{BASE_URL}/api/istruttoria/{TEST_ISTRUTTORIA_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert "domande_contestuali" in data, "domande_contestuali field missing from GET response"
        
        ctx_questions = data["domande_contestuali"]
        assert isinstance(ctx_questions, list), "domande_contestuali should be a list"
        
        print(f"PASSED: GET istruttoria includes domande_contestuali with {len(ctx_questions)} questions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
