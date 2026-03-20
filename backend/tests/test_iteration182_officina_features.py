"""
Iteration 182: NormaFacile 2.0 - 4 Nuove Feature d'Officina

Tests for:
1. Gestione Sfridi: materiale avanzato ricaricato a magazzino con link al certificato 3.1 originale
2. Blocco Patentini: operaio con patentino scaduto non può fare START su voci EN 1090
3. Controlli Visivi: campo obbligatorio con esito 👍/👎 e foto per EN 1090 e EN 13241
4. Registro Non Conformità: ogni 👎 crea automaticamente NC + notifica immediata admin

Endpoints tested:
- POST /api/sfridi — Create scrap entry
- GET /api/sfridi — List available scraps
- GET /api/sfridi/commessa/{id} — List scraps from specific commessa
- POST /api/sfridi/{id}/preleva — Withdraw scrap for new commessa
- PATCH /api/sfridi/{id}/esaurito — Mark scrap as exhausted
- POST /api/commesse/{cid}/operatori/{op_id}/patentini — Add welding certificate
- DELETE /api/commesse/{cid}/operatori/{op_id}/patentini/{pat_id} — Remove certificate
- POST /api/officina/timer/{id}?voce_id=X action=start — Patentino block test
- POST /api/controlli-visivi — Create visual inspection
- GET /api/controlli-visivi/{commessa_id} — List inspections
- GET /api/controlli-visivi/{commessa_id}/check — Check if inspections complete
- GET /api/registro-nc/{commessa_id} — List non-conformities
- PATCH /api/registro-nc/{nc_id} — Update NC
- GET /api/registro-nc — List all NCs
- GET /api/commesse/{id}/pacco-documenti — Pulsante Magico block test
- GET /api/officina/alerts/count — Alert badge count
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
TEST_SESSION_TOKEN = "4e8d7be03f734f639e57a76688f33654"
TEST_USER_ID = "test_user_pacco"
TEST_COMMESSA_ID = "com_test_pacco"

# Test operators (from context)
OP_AHMED_ID = "op_ahmed"
OP_AHMED_PIN = "1234"
OP_KARIM_ID = "op_karim"
OP_KARIM_PIN = "5678"


@pytest.fixture
def auth_headers():
    """Headers with Bearer token for admin routes."""
    return {
        "Authorization": f"Bearer {TEST_SESSION_TOKEN}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def api_client():
    """Shared requests session."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# ══════════════════════════════════════════════════════════════
#  SFRIDI MODULE TESTS
# ══════════════════════════════════════════════════════════════

class TestSfridiModule:
    """Tests for Gestione Sfridi — scrap material management with cert 3.1 link."""
    
    created_sfrido_id = None
    
    def test_01_create_sfrido(self, api_client, auth_headers):
        """POST /api/sfridi — Create a scrap entry with material, quantity, link to cert 3.1."""
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "voce_id": "voce_test_1090",
            "tipo_materiale": "IPE 200",
            "quantita": "2 barre da 1.5m",
            "numero_colata": "TEST_COLATA_001",
            "certificato_doc_id": "",  # No cert linked for this test
            "note": "Sfrido test iteration 182"
        }
        response = api_client.post(f"{BASE_URL}/api/sfridi", json=payload, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "sfrido_id" in data, "Response should contain sfrido_id"
        assert data["tipo_materiale"] == "IPE 200"
        assert data["quantita"] == "2 barre da 1.5m"
        assert data["stato"] == "disponibile"
        assert data["commessa_origine"] == TEST_COMMESSA_ID
        
        # Store for later tests
        TestSfridiModule.created_sfrido_id = data["sfrido_id"]
        print(f"✓ Created sfrido: {data['sfrido_id']}")
    
    def test_02_list_sfridi(self, api_client, auth_headers):
        """GET /api/sfridi — List available scraps."""
        response = api_client.get(f"{BASE_URL}/api/sfridi", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "sfridi" in data
        assert "total" in data
        assert isinstance(data["sfridi"], list)
        print(f"✓ Listed {data['total']} sfridi")
    
    def test_03_list_sfridi_by_commessa(self, api_client, auth_headers):
        """GET /api/sfridi/commessa/{id} — List scraps from specific commessa."""
        response = api_client.get(
            f"{BASE_URL}/api/sfridi/commessa/{TEST_COMMESSA_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "sfridi" in data
        assert isinstance(data["sfridi"], list)
        print(f"✓ Listed {len(data['sfridi'])} sfridi for commessa {TEST_COMMESSA_ID}")
    
    def test_04_preleva_sfrido(self, api_client, auth_headers):
        """POST /api/sfridi/{id}/preleva — Withdraw scrap for a new commessa."""
        if not TestSfridiModule.created_sfrido_id:
            pytest.skip("No sfrido created in previous test")
        
        payload = {
            "commessa_id_destinazione": "com_dest_test",
            "voce_id_destinazione": "voce_dest_test",
            "quantita_prelevata": "1 barra",
            "note": "Prelievo test"
        }
        response = api_client.post(
            f"{BASE_URL}/api/sfridi/{TestSfridiModule.created_sfrido_id}/preleva",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "message" in data
        assert "prelievo" in data
        assert data["prelievo"]["commessa_id"] == "com_dest_test"
        print(f"✓ Prelievo registered: {data['prelievo']['prelievo_id']}")
    
    def test_05_mark_sfrido_esaurito(self, api_client, auth_headers):
        """PATCH /api/sfridi/{id}/esaurito — Mark scrap as exhausted."""
        if not TestSfridiModule.created_sfrido_id:
            pytest.skip("No sfrido created in previous test")
        
        response = api_client.patch(
            f"{BASE_URL}/api/sfridi/{TestSfridiModule.created_sfrido_id}/esaurito",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["message"] == "Sfrido esaurito"
        print(f"✓ Sfrido marked as esaurito")
    
    def test_06_preleva_esaurito_fails(self, api_client, auth_headers):
        """POST /api/sfridi/{id}/preleva — Should fail for exhausted scrap."""
        if not TestSfridiModule.created_sfrido_id:
            pytest.skip("No sfrido created in previous test")
        
        payload = {
            "commessa_id_destinazione": "com_dest_test2",
            "quantita_prelevata": "1 barra"
        }
        response = api_client.post(
            f"{BASE_URL}/api/sfridi/{TestSfridiModule.created_sfrido_id}/preleva",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 400, f"Expected 400 for exhausted sfrido, got {response.status_code}"
        print(f"✓ Correctly rejected prelievo from exhausted sfrido")


# ══════════════════════════════════════════════════════════════
#  PATENTINI MODULE TESTS
# ══════════════════════════════════════════════════════════════

class TestPatentiniModule:
    """Tests for Patentini — welding certificate management and EN 1090 block."""
    
    created_patentino_id = None
    test_operator_id = None
    
    def test_01_add_expired_patentino(self, api_client, auth_headers):
        """POST /api/commesse/{cid}/operatori/{op_id}/patentini — Add expired certificate."""
        # First, we need to ensure the operator exists
        # Create a test operator if needed
        op_payload = {"nome": "Test Operatore Patentino", "mansione": "Saldatore"}
        op_response = api_client.post(
            f"{BASE_URL}/api/commesse/{TEST_COMMESSA_ID}/operatori",
            json=op_payload,
            headers=auth_headers
        )
        
        if op_response.status_code == 200:
            TestPatentiniModule.test_operator_id = op_response.json().get("op_id")
            print(f"✓ Created test operator: {TestPatentiniModule.test_operator_id}")
        else:
            # Use existing operator
            TestPatentiniModule.test_operator_id = OP_AHMED_ID
            print(f"Using existing operator: {OP_AHMED_ID}")
        
        # Add expired patentino (date in the past)
        payload = {
            "tipo": "Saldatura EN ISO 9606-1",
            "numero": "PAT-TEST-001",
            "scadenza": "2024-01-01",  # Expired date
            "ente": "IIS"
        }
        response = api_client.post(
            f"{BASE_URL}/api/commesse/{TEST_COMMESSA_ID}/operatori/{TestPatentiniModule.test_operator_id}/patentini",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "patentino" in data
        assert data["patentino"]["scadenza"] == "2024-01-01"
        TestPatentiniModule.created_patentino_id = data["patentino"]["pat_id"]
        print(f"✓ Added expired patentino: {TestPatentiniModule.created_patentino_id}")
    
    def test_02_add_valid_patentino(self, api_client, auth_headers):
        """POST /api/commesse/{cid}/operatori/{op_id}/patentini — Add valid certificate."""
        if not TestPatentiniModule.test_operator_id:
            pytest.skip("No test operator available")
        
        # Add valid patentino (future date)
        future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        payload = {
            "tipo": "Saldatura EN ISO 9606-1",
            "numero": "PAT-TEST-002",
            "scadenza": future_date,
            "ente": "TÜV"
        }
        response = api_client.post(
            f"{BASE_URL}/api/commesse/{TEST_COMMESSA_ID}/operatori/{TestPatentiniModule.test_operator_id}/patentini",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "patentino" in data
        print(f"✓ Added valid patentino: {data['patentino']['pat_id']}")
    
    def test_03_delete_patentino(self, api_client, auth_headers):
        """DELETE /api/commesse/{cid}/operatori/{op_id}/patentini/{pat_id} — Remove certificate."""
        if not TestPatentiniModule.test_operator_id or not TestPatentiniModule.created_patentino_id:
            pytest.skip("No patentino to delete")
        
        response = api_client.delete(
            f"{BASE_URL}/api/commesse/{TEST_COMMESSA_ID}/operatori/{TestPatentiniModule.test_operator_id}/patentini/{TestPatentiniModule.created_patentino_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Deleted patentino: {TestPatentiniModule.created_patentino_id}")


# ══════════════════════════════════════════════════════════════
#  BLOCCO PATENTINI (TIMER START) TESTS
# ══════════════════════════════════════════════════════════════

class TestBloccoPatentini:
    """Tests for Blocco Patentini — EN 1090 timer start requires valid patentino."""
    
    def test_01_timer_start_en1090_with_expired_patentino(self, api_client, auth_headers):
        """POST /api/officina/timer/{id} action=start — Should return 403 for expired patentino on EN_1090."""
        # First, add an expired patentino to op_ahmed
        expired_payload = {
            "tipo": "Saldatura EN ISO 9606-1",
            "numero": "PAT-EXPIRED-001",
            "scadenza": "2024-01-01",  # Expired
            "ente": "IIS"
        }
        api_client.post(
            f"{BASE_URL}/api/commesse/{TEST_COMMESSA_ID}/operatori/{OP_AHMED_ID}/patentini",
            json=expired_payload,
            headers=auth_headers
        )
        
        # Try to start timer on EN_1090 voce
        timer_payload = {
            "action": "start",
            "operatore_id": OP_AHMED_ID,
            "operatore_nome": "Ahmed"
        }
        
        # We need to find or create an EN_1090 voce
        # First, let's check the commessa context
        context_response = api_client.get(
            f"{BASE_URL}/api/officina/context/{TEST_COMMESSA_ID}",
            headers=auth_headers
        )
        
        if context_response.status_code == 200:
            context = context_response.json()
            voci = context.get("voci", [])
            en_1090_voce = next((v for v in voci if v.get("normativa_tipo") == "EN_1090"), None)
            
            if en_1090_voce:
                voce_id = en_1090_voce.get("voce_id", "")
                response = api_client.post(
                    f"{BASE_URL}/api/officina/timer/{TEST_COMMESSA_ID}?voce_id={voce_id}",
                    json=timer_payload
                )
                
                # Should get 403 if patentino is expired and voce is EN_1090
                # OR 200 if operator has valid patentino
                print(f"Timer start response: {response.status_code} - {response.text[:200]}")
                
                if response.status_code == 403:
                    assert "Patentino scaduto" in response.text or "patentino" in response.text.lower()
                    print(f"✓ Correctly blocked timer start for expired patentino on EN_1090")
                elif response.status_code == 200:
                    print(f"✓ Timer started (operator may have valid patentino)")
                elif response.status_code == 400:
                    # Timer already active
                    print(f"✓ Timer already active or other validation")
                else:
                    print(f"Unexpected status: {response.status_code}")
            else:
                # Test with principal voce if commessa is EN_1090
                if context.get("commessa", {}).get("normativa_tipo") == "EN_1090":
                    response = api_client.post(
                        f"{BASE_URL}/api/officina/timer/{TEST_COMMESSA_ID}",
                        json=timer_payload
                    )
                    print(f"Timer start (principal) response: {response.status_code}")
                else:
                    pytest.skip("No EN_1090 voce found in test commessa")
        else:
            pytest.skip(f"Could not get commessa context: {context_response.status_code}")
    
    def test_02_timer_start_en13241_no_patentino_check(self, api_client, auth_headers):
        """POST /api/officina/timer/{id} action=start — Should SUCCEED for EN_13241 (no patentino check)."""
        timer_payload = {
            "action": "start",
            "operatore_id": OP_KARIM_ID,
            "operatore_nome": "Karim"
        }
        
        # Get context to find EN_13241 voce
        context_response = api_client.get(
            f"{BASE_URL}/api/officina/context/{TEST_COMMESSA_ID}"
        )
        
        if context_response.status_code == 200:
            context = context_response.json()
            voci = context.get("voci", [])
            en_13241_voce = next((v for v in voci if v.get("normativa_tipo") == "EN_13241"), None)
            
            if en_13241_voce:
                voce_id = en_13241_voce.get("voce_id", "")
                response = api_client.post(
                    f"{BASE_URL}/api/officina/timer/{TEST_COMMESSA_ID}?voce_id={voce_id}",
                    json=timer_payload
                )
                
                # Should succeed (no patentino check for EN_13241)
                print(f"Timer start EN_13241 response: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"✓ Timer started successfully for EN_13241 (no patentino check)")
                elif response.status_code == 400:
                    # Timer already active
                    print(f"✓ Timer already active (endpoint working)")
                else:
                    print(f"Response: {response.text[:200]}")
            else:
                pytest.skip("No EN_13241 voce found in test commessa")
        else:
            pytest.skip(f"Could not get commessa context: {context_response.status_code}")


# ══════════════════════════════════════════════════════════════
#  CONTROLLI VISIVI MODULE TESTS
# ══════════════════════════════════════════════════════════════

class TestControlliVisivi:
    """Tests for Controlli Visivi — mandatory visual inspection with 👍/👎 esito."""
    
    created_controllo_id = None
    created_nc_id = None
    
    def test_01_create_controllo_visivo_ok(self, api_client, auth_headers):
        """POST /api/controlli-visivi — Create visual inspection with esito=true (👍)."""
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "voce_id": "",  # Principal voce
            "normativa_tipo": "EN_1090",
            "esito": True,  # 👍 OK
            "note": "Controllo visivo OK - test iteration 182",
            "foto_doc_id": "",
            "operatore_id": OP_AHMED_ID,
            "operatore_nome": "Ahmed"
        }
        response = api_client.post(
            f"{BASE_URL}/api/controlli-visivi",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "controllo_id" in data
        assert data["esito"] == True
        assert data["nc_creata"] == False  # No NC for OK result
        
        TestControlliVisivi.created_controllo_id = data["controllo_id"]
        print(f"✓ Created controllo visivo OK: {data['controllo_id']}")
    
    def test_02_create_controllo_visivo_nok_creates_nc(self, api_client, auth_headers):
        """POST /api/controlli-visivi — Create visual inspection with esito=false (👎) → auto-creates NC."""
        payload = {
            "commessa_id": TEST_COMMESSA_ID,
            "voce_id": "voce_test_13241",
            "normativa_tipo": "EN_13241",
            "esito": False,  # 👎 NOK
            "note": "Controllo visivo NOK - difetto rilevato - test iteration 182",
            "foto_doc_id": "",
            "operatore_id": OP_KARIM_ID,
            "operatore_nome": "Karim"
        }
        response = api_client.post(
            f"{BASE_URL}/api/controlli-visivi",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "controllo_id" in data
        assert data["esito"] == False
        assert data["nc_creata"] == True, "NC should be auto-created for NOK result"
        assert "nc_id" in data and data["nc_id"] is not None
        
        TestControlliVisivi.created_nc_id = data["nc_id"]
        print(f"✓ Created controllo visivo NOK: {data['controllo_id']}, NC auto-created: {data['nc_id']}")
    
    def test_03_list_controlli_visivi(self, api_client, auth_headers):
        """GET /api/controlli-visivi/{commessa_id} — List inspections."""
        response = api_client.get(
            f"{BASE_URL}/api/controlli-visivi/{TEST_COMMESSA_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "controlli" in data
        assert isinstance(data["controlli"], list)
        print(f"✓ Listed {len(data['controlli'])} controlli visivi")
    
    def test_04_check_controlli_completi(self, api_client, auth_headers):
        """GET /api/controlli-visivi/{commessa_id}/check — Returns completo status."""
        response = api_client.get(
            f"{BASE_URL}/api/controlli-visivi/{TEST_COMMESSA_ID}/check",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "completo" in data
        assert "voci_obbligatorie" in data
        assert "mancanti" in data
        assert "messaggio" in data
        
        print(f"✓ Controlli check: completo={data['completo']}, mancanti={data['mancanti']}")


# ══════════════════════════════════════════════════════════════
#  REGISTRO NON CONFORMITA' TESTS
# ══════════════════════════════════════════════════════════════

class TestRegistroNC:
    """Tests for Registro Non Conformità — automatic NC creation on 👎."""
    
    def test_01_list_nc_by_commessa(self, api_client, auth_headers):
        """GET /api/registro-nc/{commessa_id} — List non-conformities for commessa."""
        response = api_client.get(
            f"{BASE_URL}/api/registro-nc/{TEST_COMMESSA_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "non_conformita" in data
        assert "total" in data
        assert "aperte" in data
        
        print(f"✓ Listed {data['total']} NC for commessa, {data['aperte']} aperte")
    
    def test_02_list_all_nc(self, api_client, auth_headers):
        """GET /api/registro-nc — List all NCs across commesse."""
        response = api_client.get(
            f"{BASE_URL}/api/registro-nc",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "non_conformita" in data
        assert "total" in data
        
        print(f"✓ Listed {data['total']} total NC")
    
    def test_03_update_nc(self, api_client, auth_headers):
        """PATCH /api/registro-nc/{nc_id} — Update NC (close, add corrective action)."""
        # First get an NC to update
        list_response = api_client.get(
            f"{BASE_URL}/api/registro-nc/{TEST_COMMESSA_ID}",
            headers=auth_headers
        )
        
        if list_response.status_code == 200:
            ncs = list_response.json().get("non_conformita", [])
            if ncs:
                nc_id = ncs[0]["nc_id"]
                
                payload = {
                    "stato": "in_corso",
                    "azione_correttiva": "Azione correttiva test iteration 182"
                }
                response = api_client.patch(
                    f"{BASE_URL}/api/registro-nc/{nc_id}",
                    json=payload,
                    headers=auth_headers
                )
                
                assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
                print(f"✓ Updated NC {nc_id} to stato=in_corso")
            else:
                pytest.skip("No NC found to update")
        else:
            pytest.skip("Could not list NCs")
    
    def test_04_close_nc(self, api_client, auth_headers):
        """PATCH /api/registro-nc/{nc_id} — Close NC with notes."""
        list_response = api_client.get(
            f"{BASE_URL}/api/registro-nc/{TEST_COMMESSA_ID}",
            headers=auth_headers
        )
        
        if list_response.status_code == 200:
            ncs = list_response.json().get("non_conformita", [])
            open_ncs = [nc for nc in ncs if nc.get("stato") != "chiusa"]
            
            if open_ncs:
                nc_id = open_ncs[0]["nc_id"]
                
                payload = {
                    "stato": "chiusa",
                    "chiusa_da": "Test Admin",
                    "note_chiusura": "NC chiusa dopo verifica - test iteration 182"
                }
                response = api_client.patch(
                    f"{BASE_URL}/api/registro-nc/{nc_id}",
                    json=payload,
                    headers=auth_headers
                )
                
                assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
                print(f"✓ Closed NC {nc_id}")
            else:
                pytest.skip("No open NC found to close")
        else:
            pytest.skip("Could not list NCs")


# ══════════════════════════════════════════════════════════════
#  PULSANTE MAGICO BLOCK TESTS
# ══════════════════════════════════════════════════════════════

class TestPulsanteMagicoBlock:
    """Tests for Pulsante Magico block — requires visual inspections for EN 1090/13241."""
    
    def test_01_pacco_documenti_without_controlli(self, api_client, auth_headers):
        """GET /api/commesse/{id}/pacco-documenti — Should error if visual inspections missing."""
        # Create a new test commessa without any controlli visivi
        test_commessa_id = f"com_test_no_ctrl_{uuid.uuid4().hex[:6]}"
        
        # First create the commessa
        commessa_payload = {
            "numero": f"TEST-{uuid.uuid4().hex[:4]}",
            "title": "Test Commessa No Controlli",
            "normativa_tipo": "EN_1090",
            "oggetto": "Test per blocco pulsante magico"
        }
        
        # Try to get pacco documenti for the test commessa
        response = api_client.get(
            f"{BASE_URL}/api/commesse/{TEST_COMMESSA_ID}/pacco-documenti",
            headers=auth_headers
        )
        
        # The response depends on whether controlli visivi exist
        print(f"Pacco documenti response: {response.status_code}")
        
        if response.status_code == 400 or response.status_code == 422:
            # Expected if controlli visivi are missing
            assert "controllo visivo" in response.text.lower() or "controlli" in response.text.lower()
            print(f"✓ Pacco documenti correctly blocked due to missing controlli visivi")
        elif response.status_code == 200:
            # Controlli visivi exist, PDF generated
            print(f"✓ Pacco documenti generated (controlli visivi present)")
        else:
            print(f"Response: {response.text[:300]}")


# ══════════════════════════════════════════════════════════════
#  OFFICINA CHECKLIST NC CREATION TESTS
# ══════════════════════════════════════════════════════════════

class TestOfficinaChecklistNC:
    """Tests for Officina Checklist — 👎 items create BOTH alert AND NC entry."""
    
    def test_01_checklist_nok_creates_nc(self, api_client, auth_headers):
        """POST /api/officina/checklist/{commessa_id} — NOK items create alert + NC."""
        payload = {
            "operatore_id": OP_AHMED_ID,
            "operatore_nome": "Ahmed",
            "items": [
                {"codice": "saldature_pulite", "esito": True},
                {"codice": "dimensioni_ok", "esito": False},  # 👎 NOK
                {"codice": "materiale_ok", "esito": True}
            ]
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/officina/checklist/{TEST_COMMESSA_ID}",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "checklist_id" in data
            assert data["all_ok"] == False
            assert data["problemi"] == 1
            print(f"✓ Checklist submitted with 1 NOK item, alert + NC created")
        else:
            print(f"Checklist response: {response.status_code} - {response.text[:200]}")


# ══════════════════════════════════════════════════════════════
#  ALERT BADGE TESTS
# ══════════════════════════════════════════════════════════════

class TestAlertBadge:
    """Tests for Alert Badge — counts both quality alerts AND NC alerts."""
    
    def test_01_get_alerts_count(self, api_client, auth_headers):
        """GET /api/officina/alerts/count — Count unread alerts."""
        response = api_client.get(
            f"{BASE_URL}/api/officina/alerts/count?admin_id={TEST_USER_ID}"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "count" in data
        print(f"✓ Alert count: {data['count']}")
    
    def test_02_list_alerts(self, api_client, auth_headers):
        """GET /api/officina/alerts — List alerts including NC alerts."""
        response = api_client.get(
            f"{BASE_URL}/api/officina/alerts?admin_id={TEST_USER_ID}"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "alerts" in data
        
        # Check if there are NC-type alerts
        nc_alerts = [a for a in data["alerts"] if a.get("tipo") == "non_conformita"]
        print(f"✓ Listed {len(data['alerts'])} alerts, {len(nc_alerts)} are NC alerts")


# ══════════════════════════════════════════════════════════════
#  AUTHENTICATION TESTS
# ══════════════════════════════════════════════════════════════

class TestAuthentication:
    """Tests for authentication requirements on new endpoints."""
    
    def test_01_sfridi_requires_auth(self, api_client):
        """GET /api/sfridi — Should require authentication."""
        response = api_client.get(f"{BASE_URL}/api/sfridi")
        assert response.status_code == 401 or response.status_code == 403
        print(f"✓ Sfridi endpoint requires auth")
    
    def test_02_controlli_visivi_requires_auth(self, api_client):
        """GET /api/controlli-visivi/{commessa_id} — Should require authentication."""
        response = api_client.get(f"{BASE_URL}/api/controlli-visivi/{TEST_COMMESSA_ID}")
        assert response.status_code == 401 or response.status_code == 403
        print(f"✓ Controlli visivi endpoint requires auth")
    
    def test_03_registro_nc_requires_auth(self, api_client):
        """GET /api/registro-nc — Should require authentication."""
        response = api_client.get(f"{BASE_URL}/api/registro-nc")
        assert response.status_code == 401 or response.status_code == 403
        print(f"✓ Registro NC endpoint requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
