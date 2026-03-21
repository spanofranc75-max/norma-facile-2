"""
Test Iteration 192: ML Calibrazione for Preventivatore Predittivo

Tests the ML calibration system that analyzes historical completed projects
to calculate correction factors for improving future estimates.

Endpoints tested:
- GET /api/calibrazione/status - Training stats with accuracy pre/post ML
- POST /api/calibrazione/calcola-fattori - Calculate correction factors for target project
- POST /api/calibrazione/applica - Apply calibration to raw estimate
- POST /api/calibrazione/feedback - Register completed project for training
- POST /api/preventivatore/calcola with applica_calibrazione=true - Integration
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AUTH_TOKEN = "test_cal_2026"
REAL_SESSION = "sXLRQVAMtJAFhjM60UrZAjE_8wtJUdJ4sQQpbS5SFsY"


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def auth_headers():
    """Auth headers with test token"""
    return {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def real_session_headers():
    """Auth headers with real session cookie"""
    return {
        "Cookie": f"session={REAL_SESSION}",
        "Content-Type": "application/json"
    }


class TestCalibrazioneStatus:
    """GET /api/calibrazione/status - Training stats and accuracy metrics"""
    
    def test_status_no_auth(self, api_client):
        """Should return 401 without authentication"""
        response = api_client.get(f"{BASE_URL}/api/calibrazione/status")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/calibrazione/status without auth returns 401")
    
    def test_status_with_auth(self, api_client, auth_headers):
        """Should return training stats with auth"""
        response = api_client.get(f"{BASE_URL}/api/calibrazione/status", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "n_progetti" in data, "Missing n_progetti in response"
        assert "calibrato" in data, "Missing calibrato in response"
        
        print(f"✓ GET /api/calibrazione/status returns 200")
        print(f"  - n_progetti: {data.get('n_progetti')}")
        print(f"  - calibrato: {data.get('calibrato')}")
        
        # If calibrated, verify additional fields
        if data.get("calibrato"):
            assert "fattori" in data, "Missing fattori when calibrato=True"
            assert "accuracy_pre_calibrazione" in data, "Missing accuracy_pre_calibrazione"
            assert "accuracy_post_calibrazione" in data, "Missing accuracy_post_calibrazione"
            assert "miglioramento_pct" in data, "Missing miglioramento_pct"
            assert "distribuzione_tipologia" in data, "Missing distribuzione_tipologia"
            assert "evoluzione" in data, "Missing evoluzione"
            
            print(f"  - accuracy_pre: {data.get('accuracy_pre_calibrazione')}%")
            print(f"  - accuracy_post: {data.get('accuracy_post_calibrazione')}%")
            print(f"  - miglioramento: {data.get('miglioramento_pct')}%")
            print(f"  - fattori: {data.get('fattori')}")
    
    def test_status_with_test_session(self, api_client):
        """Should return training stats with test session (test_cal_session_192)"""
        headers = {
            "Authorization": "Bearer test_cal_session_192",
            "Content-Type": "application/json"
        }
        response = api_client.get(f"{BASE_URL}/api/calibrazione/status", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "n_progetti" in data
        # This test user has 10 seeded projects
        assert data.get("n_progetti") == 10, f"Expected 10 projects, got {data.get('n_progetti')}"
        assert data.get("calibrato") == True, "Expected calibrato=True with 10 projects"
        print(f"✓ GET /api/calibrazione/status with test session returns 200")
        print(f"  - n_progetti: {data.get('n_progetti')}")
        print(f"  - calibrato: {data.get('calibrato')}")


class TestCalcolaFattori:
    """POST /api/calibrazione/calcola-fattori - Calculate correction factors"""
    
    def test_calcola_fattori_no_auth(self, api_client):
        """Should return 401 without authentication"""
        response = api_client.post(
            f"{BASE_URL}/api/calibrazione/calcola-fattori",
            json={"peso_kg": 5000, "classe_antisismica": 2, "nodi_strutturali": 10, "tipologia": "media"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/calibrazione/calcola-fattori without auth returns 401")
    
    def test_calcola_fattori_with_auth(self, api_client, auth_headers):
        """Should calculate correction factors for target project"""
        target = {
            "peso_kg": 5000,
            "classe_antisismica": 2,
            "nodi_strutturali": 10,
            "tipologia": "media"
        }
        response = api_client.post(
            f"{BASE_URL}/api/calibrazione/calcola-fattori",
            headers=auth_headers,
            json=target
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "calibrato" in data, "Missing calibrato in response"
        assert "fattori" in data, "Missing fattori in response"
        assert "n_progetti" in data, "Missing n_progetti in response"
        
        # Verify fattori structure
        fattori = data.get("fattori", {})
        assert "ore" in fattori, "Missing ore in fattori"
        assert "materiali" in fattori, "Missing materiali in fattori"
        assert "manodopera" in fattori, "Missing manodopera in fattori"
        assert "conto_lavoro" in fattori, "Missing conto_lavoro in fattori"
        
        print(f"✓ POST /api/calibrazione/calcola-fattori returns 200")
        print(f"  - calibrato: {data.get('calibrato')}")
        print(f"  - n_progetti: {data.get('n_progetti')}")
        print(f"  - fattori: {fattori}")
        
        if data.get("calibrato"):
            assert "accuracy" in data, "Missing accuracy when calibrato=True"
            assert "similarita_media" in data, "Missing similarita_media when calibrato=True"
            print(f"  - accuracy: {data.get('accuracy')}%")
            print(f"  - similarita_media: {data.get('similarita_media')}")
    
    def test_calcola_fattori_different_tipologia(self, api_client, auth_headers):
        """Should calculate factors for different structure types"""
        tipologie = ["leggera", "media", "pesante", "complessa"]
        
        for tipo in tipologie:
            target = {
                "peso_kg": 3000,
                "classe_antisismica": 1,
                "nodi_strutturali": 5,
                "tipologia": tipo
            }
            response = api_client.post(
                f"{BASE_URL}/api/calibrazione/calcola-fattori",
                headers=auth_headers,
                json=target
            )
            assert response.status_code == 200, f"Failed for tipologia={tipo}: {response.text}"
            print(f"✓ calcola-fattori for tipologia={tipo} returns 200")


class TestApplicaCalibrazione:
    """POST /api/calibrazione/applica - Apply calibration to raw estimate"""
    
    def test_applica_no_auth(self, api_client):
        """Should return 401 without authentication"""
        response = api_client.post(
            f"{BASE_URL}/api/calibrazione/applica",
            json={
                "ore_totali": 100,
                "costo_materiali": 5000,
                "costo_manodopera": 3500,
                "costo_cl": 1000,
                "target": {"peso_kg": 5000, "classe_antisismica": 2, "nodi_strutturali": 10, "tipologia": "media"}
            }
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/calibrazione/applica without auth returns 401")
    
    def test_applica_with_auth(self, api_client, auth_headers):
        """Should apply calibration to raw estimate"""
        payload = {
            "ore_totali": 100,
            "costo_materiali": 5000,
            "costo_manodopera": 3500,
            "costo_cl": 1000,
            "target": {
                "peso_kg": 5000,
                "classe_antisismica": 2,
                "nodi_strutturali": 10,
                "tipologia": "media"
            }
        }
        response = api_client.post(
            f"{BASE_URL}/api/calibrazione/applica",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "calibrata" in data, "Missing calibrata in response"
        assert "stima_originale" in data, "Missing stima_originale in response"
        assert "stima_calibrata" in data, "Missing stima_calibrata in response"
        assert "fattori" in data, "Missing fattori in response"
        
        print(f"✓ POST /api/calibrazione/applica returns 200")
        print(f"  - calibrata: {data.get('calibrata')}")
        
        if data.get("calibrata"):
            assert "delta" in data, "Missing delta when calibrata=True"
            assert "n_progetti" in data, "Missing n_progetti when calibrata=True"
            assert "accuracy" in data, "Missing accuracy when calibrata=True"
            
            orig = data.get("stima_originale", {})
            cal = data.get("stima_calibrata", {})
            delta = data.get("delta", {})
            
            print(f"  - stima_originale: ore={orig.get('ore_totali')}, totale={orig.get('totale')}")
            print(f"  - stima_calibrata: ore={cal.get('ore_totali')}, totale={cal.get('totale')}")
            print(f"  - delta: ore={delta.get('ore')}, materiali={delta.get('materiali')}")
            print(f"  - fattori: {data.get('fattori')}")
    
    def test_applica_verifies_delta_calculation(self, api_client, auth_headers):
        """Verify delta is correctly calculated as calibrated - original"""
        payload = {
            "ore_totali": 100,
            "costo_materiali": 5000,
            "costo_manodopera": 3500,
            "costo_cl": 1000,
            "target": {
                "peso_kg": 5000,
                "classe_antisismica": 2,
                "nodi_strutturali": 10,
                "tipologia": "media"
            }
        }
        response = api_client.post(
            f"{BASE_URL}/api/calibrazione/applica",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200
        
        data = response.json()
        if data.get("calibrata"):
            orig = data.get("stima_originale", {})
            cal = data.get("stima_calibrata", {})
            delta = data.get("delta", {})
            
            # Verify delta calculations
            expected_ore_delta = round(cal.get("ore_totali", 0) - orig.get("ore_totali", 0), 1)
            assert abs(delta.get("ore", 0) - expected_ore_delta) < 0.2, "Delta ore calculation incorrect"
            print("✓ Delta calculations verified correctly")


class TestFeedback:
    """POST /api/calibrazione/feedback - Register completed project"""
    
    def test_feedback_no_auth(self, api_client):
        """Should return 401 without authentication"""
        response = api_client.post(
            f"{BASE_URL}/api/calibrazione/feedback",
            json={
                "commessa_id": "test_comm_001",
                "title": "Test Project",
                "peso_kg": 5000,
                "ore_stimate": 100,
                "ore_reali": 110
            }
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ POST /api/calibrazione/feedback without auth returns 401")
    
    def test_feedback_with_auth(self, api_client, auth_headers):
        """Should register completed project and recalculate calibration"""
        payload = {
            "commessa_id": "TEST_feedback_proj_001",
            "title": "TEST Progetto Feedback",
            "peso_kg": 4500,
            "classe_antisismica": 2,
            "nodi_strutturali": 8,
            "tipologia": "media",
            "ore_stimate": 90,
            "ore_reali": 95,
            "costo_materiali_stimato": 4000,
            "costo_materiali_reale": 4200,
            "costo_manodopera_stimato": 3000,
            "costo_manodopera_reale": 3150,
            "costo_cl_stimato": 800,
            "costo_cl_reale": 850
        }
        response = api_client.post(
            f"{BASE_URL}/api/calibrazione/feedback",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "message" in data, "Missing message in response"
        assert "project_id" in data, "Missing project_id in response"
        assert "calibrazione_aggiornata" in data, "Missing calibrazione_aggiornata in response"
        assert "n_progetti_totali" in data, "Missing n_progetti_totali in response"
        
        print(f"✓ POST /api/calibrazione/feedback returns 200")
        print(f"  - message: {data.get('message')}")
        print(f"  - project_id: {data.get('project_id')}")
        print(f"  - calibrazione_aggiornata: {data.get('calibrazione_aggiornata')}")
        print(f"  - n_progetti_totali: {data.get('n_progetti_totali')}")
        print(f"  - nuova_accuracy: {data.get('nuova_accuracy')}")


class TestPreventivatoreCalcolaWithCalibrazione:
    """POST /api/preventivatore/calcola with applica_calibrazione=true"""
    
    def test_calcola_without_calibrazione(self, api_client, auth_headers):
        """Should calculate without calibration by default"""
        payload = {
            "materiali": [
                {"tipo": "IPE", "profilo": "IPE 200", "lunghezza_mm": 6000, "quantita": 4}
            ],
            "tipologia_struttura": "media",
            "margine_materiali": 25,
            "margine_manodopera": 30,
            "margine_conto_lavoro": 20,
            "applica_calibrazione": False
        }
        response = api_client.post(
            f"{BASE_URL}/api/preventivatore/calcola",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "calibrazione" not in data or data.get("calibrazione") is None, "Calibrazione should be None when applica_calibrazione=False"
        print("✓ POST /api/preventivatore/calcola without calibrazione returns 200")
    
    def test_calcola_with_calibrazione(self, api_client, auth_headers):
        """Should apply ML calibration when applica_calibrazione=true"""
        payload = {
            "materiali": [
                {"tipo": "IPE", "profilo": "IPE 200", "lunghezza_mm": 6000, "quantita": 4}
            ],
            "tipologia_struttura": "media",
            "margine_materiali": 25,
            "margine_manodopera": 30,
            "margine_conto_lavoro": 20,
            "applica_calibrazione": True,
            "peso_kg_target": 5000,
            "classe_antisismica_target": 2,
            "nodi_target": 10
        }
        response = api_client.post(
            f"{BASE_URL}/api/preventivatore/calcola",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify calibrazione is present
        assert "calibrazione" in data, "Missing calibrazione in response"
        
        cal = data.get("calibrazione")
        if cal:
            assert "calibrata" in cal, "Missing calibrata in calibrazione"
            assert "stima_originale" in cal, "Missing stima_originale in calibrazione"
            assert "stima_calibrata" in cal, "Missing stima_calibrata in calibrazione"
            assert "fattori" in cal, "Missing fattori in calibrazione"
            
            print(f"✓ POST /api/preventivatore/calcola with calibrazione returns 200")
            print(f"  - calibrata: {cal.get('calibrata')}")
            print(f"  - fattori: {cal.get('fattori')}")
            if cal.get("calibrata"):
                print(f"  - stima_originale totale: {cal.get('stima_originale', {}).get('totale')}")
                print(f"  - stima_calibrata totale: {cal.get('stima_calibrata', {}).get('totale')}")
        else:
            print("✓ POST /api/preventivatore/calcola with calibrazione returns 200 (calibrazione=None - not enough training data)")


class TestCalibrazioneDataValidation:
    """Test data validation and edge cases"""
    
    def test_calcola_fattori_empty_target(self, api_client, auth_headers):
        """Should handle empty target with defaults"""
        response = api_client.post(
            f"{BASE_URL}/api/calibrazione/calcola-fattori",
            headers=auth_headers,
            json={}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ calcola-fattori with empty target returns 200 (uses defaults)")
    
    def test_applica_zero_values(self, api_client, auth_headers):
        """Should handle zero values in estimate"""
        payload = {
            "ore_totali": 0,
            "costo_materiali": 0,
            "costo_manodopera": 0,
            "costo_cl": 0,
            "target": {"peso_kg": 1000, "classe_antisismica": 1, "nodi_strutturali": 0, "tipologia": "leggera"}
        }
        response = api_client.post(
            f"{BASE_URL}/api/calibrazione/applica",
            headers=auth_headers,
            json=payload
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ applica with zero values returns 200")


class TestCalibrazioneStatusDetails:
    """Test detailed status response fields"""
    
    def test_status_evoluzione_structure(self, api_client, auth_headers):
        """Verify evoluzione array structure"""
        response = api_client.get(f"{BASE_URL}/api/calibrazione/status", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        if data.get("calibrato") and data.get("evoluzione"):
            evoluzione = data["evoluzione"]
            assert isinstance(evoluzione, list), "evoluzione should be a list"
            
            if len(evoluzione) > 0:
                item = evoluzione[0]
                assert "progetto" in item, "Missing progetto in evoluzione item"
                assert "accuracy_pre" in item, "Missing accuracy_pre in evoluzione item"
                assert "accuracy_post" in item, "Missing accuracy_post in evoluzione item"
                assert "n" in item, "Missing n in evoluzione item"
                print(f"✓ evoluzione structure verified: {len(evoluzione)} items")
        else:
            print("✓ evoluzione not available (not enough data)")
    
    def test_status_distribuzione_tipologia_structure(self, api_client, auth_headers):
        """Verify distribuzione_tipologia structure"""
        response = api_client.get(f"{BASE_URL}/api/calibrazione/status", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        if data.get("calibrato") and data.get("distribuzione_tipologia"):
            dist = data["distribuzione_tipologia"]
            assert isinstance(dist, dict), "distribuzione_tipologia should be a dict"
            
            for tipo, tipo_data in dist.items():
                assert "count" in tipo_data, f"Missing count for tipologia {tipo}"
                assert "errore_medio_ore" in tipo_data, f"Missing errore_medio_ore for tipologia {tipo}"
                print(f"  - {tipo}: count={tipo_data['count']}, errore={tipo_data['errore_medio_ore']}%")
            print(f"✓ distribuzione_tipologia structure verified")
        else:
            print("✓ distribuzione_tipologia not available (not enough data)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
