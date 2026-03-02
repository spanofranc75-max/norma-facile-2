"""
Test Suite: Split Commessa Feature (Iteration 98)
Tests the new 'Split Commessa' functionality for mixed-normativa preventivi.

Features tested:
- GET /api/commesse/analyze-preventivo/{preventivo_id} - Conflict detection for EN 1090 vs EN 13241
- POST /api/commesse/from-preventivo/{preventivo_id} - Single commessa creation (no conflict)
- POST /api/commesse/from-preventivo/{preventivo_id}/split - Split commessa creation for mixed content

Keywords for classification:
- EN 1090 (structures): tettoia, scala, soppalco, trave, struttura, pensilina, carpenteria, ringhier
- EN 13241 (gates): cancell, portone, scorrevol, battente, chiusura, serranda, sezionale, barriera
"""

import os
import pytest
import requests
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "split_test_session_mm8w07pv"
USER_ID = "user_split_test_mm8w07pv"


@pytest.fixture(scope="module")
def api_client():
    """Create API client with auth cookie"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.cookies.set("session_token", SESSION_TOKEN, domain=BASE_URL.replace("https://", "").replace("http://", "").split("/")[0])
    return session


@pytest.fixture(scope="module")
def mixed_preventivo_id(api_client):
    """Create a preventivo with mixed normativa items (EN 1090 + EN 13241)"""
    payload = {
        "subject": "TEST_Split_Preventivo_Misto",
        "notes": "Test preventivo with mixed normativa items",
        "validity_days": 30,
        "lines": [
            # EN 1090 items (structures)
            {
                "line_id": "ln_1090_tettoia",
                "description": "Tettoia in acciaio zincato 6x4m",
                "quantity": 1,
                "unit": "pz",
                "unit_price": 5000,
                "vat_rate": "22"
            },
            {
                "line_id": "ln_1090_scala",
                "description": "Scala in ferro a chiocciola",
                "quantity": 1,
                "unit": "pz",
                "unit_price": 3500,
                "vat_rate": "22"
            },
            {
                "line_id": "ln_1090_soppalco",
                "description": "Soppalco industriale 10x5m",
                "quantity": 1,
                "unit": "pz",
                "unit_price": 8000,
                "vat_rate": "22"
            },
            # EN 13241 items (gates)
            {
                "line_id": "ln_13241_cancello",
                "description": "Cancello scorrevole automatico 5m",
                "quantity": 1,
                "unit": "pz",
                "unit_price": 4500,
                "vat_rate": "22"
            },
            {
                "line_id": "ln_13241_portone",
                "description": "Portone sezionale industriale 4x4m",
                "quantity": 1,
                "unit": "pz",
                "unit_price": 6000,
                "vat_rate": "22"
            },
            # Non-classified item
            {
                "line_id": "ln_generic_fornitura",
                "description": "Fornitura accessori vari",
                "quantity": 1,
                "unit": "corpo",
                "unit_price": 500,
                "vat_rate": "22"
            }
        ]
    }
    response = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
    assert response.status_code == 201, f"Failed to create mixed preventivo: {response.text}"
    data = response.json()
    yield data["preventivo_id"]
    
    # Cleanup - delete the preventivo
    api_client.delete(f"{BASE_URL}/api/preventivi/{data['preventivo_id']}")


@pytest.fixture(scope="module")
def single_normativa_preventivo_id(api_client):
    """Create a preventivo with only EN 1090 items (no conflict)"""
    payload = {
        "subject": "TEST_Single_Preventivo_Strutture",
        "notes": "Test preventivo with only EN 1090 items",
        "validity_days": 30,
        "lines": [
            {
                "line_id": "ln_only_1090_tettoia",
                "description": "Tettoia copertura auto 6x3m",
                "quantity": 1,
                "unit": "pz",
                "unit_price": 4000,
                "vat_rate": "22"
            },
            {
                "line_id": "ln_only_1090_pensilina",
                "description": "Pensilina ingresso in acciaio",
                "quantity": 1,
                "unit": "pz",
                "unit_price": 2500,
                "vat_rate": "22"
            }
        ]
    }
    response = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
    assert response.status_code == 201, f"Failed to create single normativa preventivo: {response.text}"
    data = response.json()
    yield data["preventivo_id"]
    
    # Cleanup
    api_client.delete(f"{BASE_URL}/api/preventivi/{data['preventivo_id']}")


@pytest.fixture(scope="module")
def gates_only_preventivo_id(api_client):
    """Create a preventivo with only EN 13241 items and motorization"""
    payload = {
        "subject": "TEST_Gates_Only_Preventivo",
        "notes": "Test preventivo with motorized gate",
        "validity_days": 30,
        "lines": [
            {
                "line_id": "ln_gate_cancello_motorizzato",
                "description": "Cancello battente motorizzato con automazione BFT",
                "quantity": 1,
                "unit": "pz",
                "unit_price": 5500,
                "vat_rate": "22"
            },
            {
                "line_id": "ln_gate_fotocellule",
                "description": "Kit fotocellule di sicurezza",
                "quantity": 2,
                "unit": "pz",
                "unit_price": 150,
                "vat_rate": "22"
            }
        ]
    }
    response = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
    assert response.status_code == 201, f"Failed to create gates only preventivo: {response.text}"
    data = response.json()
    yield data["preventivo_id"]
    
    # Cleanup
    api_client.delete(f"{BASE_URL}/api/preventivi/{data['preventivo_id']}")


class TestAnalyzePreventivo:
    """Tests for GET /api/commesse/analyze-preventivo/{preventivo_id}"""
    
    def test_analyze_mixed_preventivo_detects_conflict(self, api_client, mixed_preventivo_id):
        """Analyze a mixed preventivo should detect conflict and return groups"""
        response = api_client.get(f"{BASE_URL}/api/commesse/analyze-preventivo/{mixed_preventivo_id}")
        assert response.status_code == 200, f"Analyze failed: {response.text}"
        
        data = response.json()
        
        # Should detect conflict
        assert data.get("conflict") == True, "Should detect normativa conflict"
        assert data.get("suggested_action") == "split", "Should suggest split action"
        
        # Check groups are populated
        groups = data.get("groups", {})
        assert "en_1090" in groups, "Should have en_1090 group"
        assert "en_13241" in groups, "Should have en_13241 group"
        assert "non_classificati" in groups, "Should have non_classificati group"
        
        # EN 1090 items (tettoia, scala, soppalco)
        en_1090_items = groups.get("en_1090", [])
        assert len(en_1090_items) == 3, f"Expected 3 EN 1090 items, got {len(en_1090_items)}"
        en_1090_descs = [item["description"].lower() for item in en_1090_items]
        assert any("tettoia" in d for d in en_1090_descs), "Should include tettoia"
        assert any("scala" in d for d in en_1090_descs), "Should include scala"
        assert any("soppalco" in d for d in en_1090_descs), "Should include soppalco"
        
        # EN 13241 items (cancello, portone)
        en_13241_items = groups.get("en_13241", [])
        assert len(en_13241_items) == 2, f"Expected 2 EN 13241 items, got {len(en_13241_items)}"
        en_13241_descs = [item["description"].lower() for item in en_13241_items]
        assert any("cancello" in d for d in en_13241_descs), "Should include cancello"
        assert any("portone" in d for d in en_13241_descs), "Should include portone"
        
        # Non-classified items
        non_classificati = groups.get("non_classificati", [])
        assert len(non_classificati) == 1, f"Expected 1 non-classified item, got {len(non_classificati)}"
        assert "fornitura" in non_classificati[0]["description"].lower(), "Should include fornitura item"
        
        print(f"✓ Mixed preventivo analysis: conflict={data['conflict']}, en_1090={len(en_1090_items)}, en_13241={len(en_13241_items)}, other={len(non_classificati)}")
    
    def test_analyze_single_normativa_no_conflict(self, api_client, single_normativa_preventivo_id):
        """Analyze a single normativa preventivo should NOT detect conflict"""
        response = api_client.get(f"{BASE_URL}/api/commesse/analyze-preventivo/{single_normativa_preventivo_id}")
        assert response.status_code == 200, f"Analyze failed: {response.text}"
        
        data = response.json()
        
        # Should NOT detect conflict
        assert data.get("conflict") == False, "Should NOT detect normativa conflict for single normativa"
        assert data.get("suggested_action") == "single", "Should suggest single commessa action"
        assert data.get("single_normativa") == "EN_1090", "Should identify EN_1090 as the normativa"
        
        # Check groups
        groups = data.get("groups", {})
        en_1090_items = groups.get("en_1090", [])
        en_13241_items = groups.get("en_13241", [])
        
        assert len(en_1090_items) == 2, f"Expected 2 EN 1090 items, got {len(en_1090_items)}"
        assert len(en_13241_items) == 0, f"Expected 0 EN 13241 items, got {len(en_13241_items)}"
        
        print(f"✓ Single normativa analysis: conflict={data['conflict']}, normativa={data.get('single_normativa')}")
    
    def test_analyze_gates_detects_motorization(self, api_client, gates_only_preventivo_id):
        """Analyze gates-only preventivo should detect motorization keywords"""
        response = api_client.get(f"{BASE_URL}/api/commesse/analyze-preventivo/{gates_only_preventivo_id}")
        assert response.status_code == 200, f"Analyze failed: {response.text}"
        
        data = response.json()
        
        # Should NOT detect conflict (only gates)
        assert data.get("conflict") == False, "Should NOT detect conflict for gates-only"
        assert data.get("single_normativa") == "EN_13241", "Should identify EN_13241"
        
        # Should detect motorization
        assert data.get("is_motorizzato") == True, "Should detect motorization (BFT keyword)"
        
        print(f"✓ Gates analysis: normativa={data.get('single_normativa')}, motorizzato={data.get('is_motorizzato')}")
    
    def test_analyze_nonexistent_preventivo_404(self, api_client):
        """Analyze nonexistent preventivo should return 404"""
        response = api_client.get(f"{BASE_URL}/api/commesse/analyze-preventivo/nonexistent_id")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestSingleCommessaCreation:
    """Tests for POST /api/commesse/from-preventivo/{preventivo_id}"""
    
    def test_create_single_commessa_from_structures_preventivo(self, api_client, single_normativa_preventivo_id):
        """Create a single commessa from a non-conflicting preventivo"""
        response = api_client.post(f"{BASE_URL}/api/commesse/from-preventivo/{single_normativa_preventivo_id}")
        assert response.status_code == 200, f"Failed to create commessa: {response.text}"
        
        data = response.json()
        
        # Verify commessa created
        assert "commessa_id" in data, "Response should contain commessa_id"
        assert "numero" in data, "Response should contain numero"
        assert data["numero"].startswith("NF-"), "Numero should start with NF-"
        
        # Verify normativa detection
        assert data.get("normativa_tipo") == "EN_1090", f"Expected EN_1090 normativa, got {data.get('normativa_tipo')}"
        
        # Verify preventivo link
        assert data.get("linked_preventivo_id") == single_normativa_preventivo_id, "Should link to source preventivo"
        
        print(f"✓ Single commessa created: {data['numero']} ({data['commessa_id']}), normativa={data.get('normativa_tipo')}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{data['commessa_id']}")
    
    def test_create_commessa_from_gates_auto_creates_gate_cert(self, api_client, gates_only_preventivo_id):
        """Create commessa from gates preventivo should auto-create gate certification"""
        response = api_client.post(f"{BASE_URL}/api/commesse/from-preventivo/{gates_only_preventivo_id}")
        assert response.status_code == 200, f"Failed to create commessa: {response.text}"
        
        data = response.json()
        
        # Verify EN 13241 normativa
        assert data.get("normativa_tipo") == "EN_13241", f"Expected EN_13241 normativa, got {data.get('normativa_tipo')}"
        
        # Verify gate_cert_id is set (auto-created)
        assert data.get("gate_cert_id") is not None, "Should auto-create gate certification for EN 13241"
        
        # Verify motorization detection
        assert data.get("detected_azionamento") == "motorizzato", f"Expected motorizzato, got {data.get('detected_azionamento')}"
        
        print(f"✓ Gates commessa created: {data['numero']}, gate_cert_id={data.get('gate_cert_id')}, azionamento={data.get('detected_azionamento')}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/commesse/{data['commessa_id']}")


class TestSplitCommessaCreation:
    """Tests for POST /api/commesse/from-preventivo/{preventivo_id}/split"""
    
    def test_split_mixed_preventivo_creates_two_commesse(self, api_client, mixed_preventivo_id):
        """Split a mixed preventivo should create 2 separate commesse"""
        # First, analyze to get the indices
        analyze_response = api_client.get(f"{BASE_URL}/api/commesse/analyze-preventivo/{mixed_preventivo_id}")
        assert analyze_response.status_code == 200
        analysis = analyze_response.json()
        
        # Get indices from analysis
        en_1090_indices = [item["index"] for item in analysis["groups"]["en_1090"]]
        en_13241_indices = [item["index"] for item in analysis["groups"]["en_13241"]]
        non_class_indices = [item["index"] for item in analysis["groups"]["non_classificati"]]
        
        # Split: assign non-classified to EN 1090 (default behavior)
        split_payload = {
            "commesse": [
                {
                    "suffix": "A",
                    "normativa": "EN_1090",
                    "item_indices": en_1090_indices + non_class_indices
                },
                {
                    "suffix": "B",
                    "normativa": "EN_13241",
                    "item_indices": en_13241_indices
                }
            ]
        }
        
        response = api_client.post(f"{BASE_URL}/api/commesse/from-preventivo/{mixed_preventivo_id}/split", json=split_payload)
        assert response.status_code == 200, f"Split failed: {response.text}"
        
        data = response.json()
        
        # Verify message
        assert "message" in data, "Response should contain message"
        assert "2" in data["message"], "Message should mention 2 commesse"
        
        # Verify commesse array
        assert "commesse" in data, "Response should contain commesse array"
        commesse = data["commesse"]
        assert len(commesse) == 2, f"Expected 2 commesse, got {len(commesse)}"
        
        # Find commessa A (EN 1090) and B (EN 13241)
        commessa_a = next((c for c in commesse if c.get("split_suffix") == "A"), None)
        commessa_b = next((c for c in commesse if c.get("split_suffix") == "B"), None)
        
        assert commessa_a is not None, "Should have commessa with suffix A"
        assert commessa_b is not None, "Should have commessa with suffix B"
        
        # Verify suffixed numbers
        assert "-A" in commessa_a["numero"], f"Commessa A numero should end with -A: {commessa_a['numero']}"
        assert "-B" in commessa_b["numero"], f"Commessa B numero should end with -B: {commessa_b['numero']}"
        
        # Verify normativa
        assert commessa_a.get("normativa_tipo") == "EN_1090", f"Commessa A should be EN_1090, got {commessa_a.get('normativa_tipo')}"
        assert commessa_b.get("normativa_tipo") == "EN_13241", f"Commessa B should be EN_13241, got {commessa_b.get('normativa_tipo')}"
        
        # Verify gate_cert_id is set for EN 13241 commessa
        assert commessa_b.get("gate_cert_id") is not None, "EN 13241 commessa should have auto-created gate certification"
        
        print(f"✓ Split commesse created:")
        print(f"  - Commessa A: {commessa_a['numero']} (EN_1090) - {len(en_1090_indices) + len(non_class_indices)} items")
        print(f"  - Commessa B: {commessa_b['numero']} (EN_13241) - {len(en_13241_indices)} items, gate_cert={commessa_b.get('gate_cert_id')}")
        
        # Verify preventivo is marked as accettato with split_commesse
        prev_response = api_client.get(f"{BASE_URL}/api/preventivi/{mixed_preventivo_id}")
        assert prev_response.status_code == 200
        prev_data = prev_response.json()
        assert prev_data.get("status") == "accettato", f"Preventivo should be marked as accettato, got {prev_data.get('status')}"
        assert prev_data.get("split_commesse") is not None, "Preventivo should have split_commesse metadata"
        assert len(prev_data.get("split_commesse", [])) == 2, "split_commesse should have 2 entries"
        
        print(f"✓ Preventivo marked as accettato with {len(prev_data.get('split_commesse', []))} split_commesse")
        
        # Cleanup
        for c in commesse:
            api_client.delete(f"{BASE_URL}/api/commesse/{c['commessa_id']}")
    
    def test_split_requires_at_least_2_commesse(self, api_client, mixed_preventivo_id):
        """Split should fail if less than 2 commesse are specified"""
        # Try split with only 1 commessa
        split_payload = {
            "commesse": [
                {
                    "suffix": "A",
                    "normativa": "EN_1090",
                    "item_indices": [0, 1, 2]
                }
            ]
        }
        
        response = api_client.post(f"{BASE_URL}/api/commesse/from-preventivo/{mixed_preventivo_id}/split", json=split_payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "almeno 2" in response.json().get("detail", "").lower(), "Error should mention needing at least 2 commesse"
    
    def test_split_rejects_duplicate_indices(self, api_client, mixed_preventivo_id):
        """Split should fail if same index is assigned to multiple commesse"""
        split_payload = {
            "commesse": [
                {
                    "suffix": "A",
                    "normativa": "EN_1090",
                    "item_indices": [0, 1, 2]  # indices 0-2
                },
                {
                    "suffix": "B",
                    "normativa": "EN_13241",
                    "item_indices": [2, 3, 4]  # index 2 is duplicate!
                }
            ]
        }
        
        response = api_client.post(f"{BASE_URL}/api/commesse/from-preventivo/{mixed_preventivo_id}/split", json=split_payload)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "duplicat" in response.json().get("detail", "").lower(), "Error should mention duplicate indices"


class TestKeywordClassification:
    """Tests verifying the keyword classification logic"""
    
    def test_keyword_classification_en_1090(self, api_client):
        """Test that EN 1090 keywords are correctly classified"""
        # Keywords: tettoia, scala, soppalco, trave, struttura, pensilina, carpenteria, ringhier
        test_cases = [
            ("Tettoia in ferro battuto", "EN_1090"),
            ("Scala a chiocciola", "EN_1090"),
            ("Soppalco industriale", "EN_1090"),
            ("Trave HEA 200 principale", "EN_1090"),  # Note: keyword is "trave" not "travi"
            ("Struttura metallica", "EN_1090"),
            ("Pensilina ingresso", "EN_1090"),
            ("Carpenteria leggera", "EN_1090"),
            ("Ringhiera balcone", "EN_1090"),
        ]
        
        for description, expected in test_cases:
            payload = {
                "subject": f"TEST_Keyword_{expected}",
                "lines": [{"line_id": "ln_test", "description": description, "quantity": 1, "unit": "pz", "unit_price": 1000}]
            }
            response = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
            assert response.status_code == 201
            prev_id = response.json()["preventivo_id"]
            
            analyze = api_client.get(f"{BASE_URL}/api/commesse/analyze-preventivo/{prev_id}")
            assert analyze.status_code == 200
            data = analyze.json()
            
            en_1090_count = len(data["groups"]["en_1090"])
            assert en_1090_count == 1, f"'{description}' should be classified as EN_1090, groups: {data['groups']}"
            
            # Cleanup
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")
        
        print(f"✓ All {len(test_cases)} EN 1090 keywords correctly classified")
    
    def test_keyword_classification_en_13241(self, api_client):
        """Test that EN 13241 keywords are correctly classified"""
        # Keywords: cancell, portone, scorrevol, battente, chiusura, serranda, sezionale, barriera
        test_cases = [
            ("Cancello automatico", "EN_13241"),
            ("Portone industriale", "EN_13241"),
            ("Anta scorrevole", "EN_13241"),
            ("Cancello battente", "EN_13241"),
            ("Chiusura industriale", "EN_13241"),
            ("Serranda avvolgibile", "EN_13241"),
            ("Porta sezionale", "EN_13241"),
            ("Barriera automatica", "EN_13241"),
        ]
        
        for description, expected in test_cases:
            payload = {
                "subject": f"TEST_Keyword_{expected}",
                "lines": [{"line_id": "ln_test", "description": description, "quantity": 1, "unit": "pz", "unit_price": 1000}]
            }
            response = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
            assert response.status_code == 201
            prev_id = response.json()["preventivo_id"]
            
            analyze = api_client.get(f"{BASE_URL}/api/commesse/analyze-preventivo/{prev_id}")
            assert analyze.status_code == 200
            data = analyze.json()
            
            en_13241_count = len(data["groups"]["en_13241"])
            assert en_13241_count == 1, f"'{description}' should be classified as EN_13241, groups: {data['groups']}"
            
            # Cleanup
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")
        
        print(f"✓ All {len(test_cases)} EN 13241 keywords correctly classified")


class TestMotorizationDetection:
    """Tests for motorization keyword detection"""
    
    def test_motorization_keywords_detected(self, api_client):
        """Test that motorization keywords are detected"""
        # Keywords: motore, motorizzat, motorizzaz, bft, came, faac, nice, automazione, fotocellul
        test_cases = [
            "Motore per cancello",
            "Cancello motorizzato",
            "Sistema di motorizzazione",
            "Automazione BFT",
            "Kit CAME completo",
            "Motoriduttore FAAC",
            "Centralina NICE",
            "Automazione completa",
            "Fotocellule di sicurezza",
        ]
        
        for description in test_cases:
            payload = {
                "subject": "TEST_Motor_Detection",
                "lines": [{"line_id": "ln_test", "description": description, "quantity": 1, "unit": "pz", "unit_price": 1000}]
            }
            response = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
            assert response.status_code == 201
            prev_id = response.json()["preventivo_id"]
            
            analyze = api_client.get(f"{BASE_URL}/api/commesse/analyze-preventivo/{prev_id}")
            assert analyze.status_code == 200
            data = analyze.json()
            
            assert data.get("is_motorizzato") == True, f"'{description}' should trigger motorization detection"
            
            # Cleanup
            api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")
        
        print(f"✓ All {len(test_cases)} motorization keywords correctly detected")


class TestEdgeCases:
    """Tests for edge cases and error handling"""
    
    def test_empty_preventivo_lines(self, api_client):
        """Test analysis of preventivo with empty lines"""
        payload = {
            "subject": "TEST_Empty_Lines",
            "lines": []
        }
        response = api_client.post(f"{BASE_URL}/api/preventivi/", json=payload)
        assert response.status_code == 201
        prev_id = response.json()["preventivo_id"]
        
        analyze = api_client.get(f"{BASE_URL}/api/commesse/analyze-preventivo/{prev_id}")
        assert analyze.status_code == 200
        data = analyze.json()
        
        assert data.get("conflict") == False, "Empty preventivo should not have conflict"
        assert len(data["groups"]["en_1090"]) == 0
        assert len(data["groups"]["en_13241"]) == 0
        assert len(data["groups"]["non_classificati"]) == 0
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/preventivi/{prev_id}")
        print("✓ Empty preventivo analyzed without error")
    
    def test_nonexistent_preventivo_split(self, api_client):
        """Split on nonexistent preventivo should return 404"""
        split_payload = {
            "commesse": [
                {"suffix": "A", "normativa": "EN_1090", "item_indices": [0]},
                {"suffix": "B", "normativa": "EN_13241", "item_indices": [1]}
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/commesse/from-preventivo/nonexistent_id/split", json=split_payload)
        assert response.status_code == 404


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_preventivi(self, api_client):
        """Clean up any remaining test preventivi"""
        # List all preventivi and delete test ones
        response = api_client.get(f"{BASE_URL}/api/preventivi/")
        if response.status_code == 200:
            data = response.json()
            for prev in data.get("items", []):
                if prev.get("subject", "").startswith("TEST_"):
                    api_client.delete(f"{BASE_URL}/api/preventivi/{prev['preventivo_id']}")
        
        print("✓ Test data cleanup completed")
