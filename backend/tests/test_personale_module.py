"""
Personale Module Backend API Tests
Tests: Dipendenti CRUD, Presenze CRUD, Documenti, Report APIs
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session token created for this test run
SESSION_TOKEN = "test_session_personale_1773129036622"
USER_ID = "test-personale-1773129036622"

@pytest.fixture(scope="module")
def api_client():
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Cookie": f"session_token={SESSION_TOKEN}"
    })
    session.cookies.set("session_token", SESSION_TOKEN)
    return session


class TestPersonaleDipendenti:
    """Dipendenti CRUD tests"""
    
    dipendente_id = None  # Shared across tests
    
    def test_list_dipendenti_requires_auth(self):
        """GET /api/personale/dipendenti without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/personale/dipendenti")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("PASSED: List dipendenti requires authentication")
    
    def test_list_dipendenti_with_auth(self, api_client):
        """GET /api/personale/dipendenti returns list"""
        response = api_client.get(f"{BASE_URL}/api/personale/dipendenti")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "dipendenti" in data
        assert "total" in data
        assert isinstance(data["dipendenti"], list)
        print(f"PASSED: List dipendenti returned {data['total']} records")
    
    def test_create_dipendente(self, api_client):
        """POST /api/personale/dipendenti creates new employee"""
        payload = {
            "nome": "TEST_Mario",
            "cognome": "TEST_Rossi",
            "codice_fiscale": "RSSMRA85M01H501Z",
            "ruolo": "Saldatore",
            "tipo_contratto": "dipendente",
            "ore_settimanali": 40,
            "giorni_lavorativi": ["lun", "mar", "mer", "gio", "ven"],
            "email": "test.mario@example.com"
        }
        response = api_client.post(f"{BASE_URL}/api/personale/dipendenti", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "dipendente_id" in data
        assert data["nome"] == "TEST_Mario"
        assert data["cognome"] == "TEST_Rossi"
        assert data["attivo"] == True
        
        TestPersonaleDipendenti.dipendente_id = data["dipendente_id"]
        print(f"PASSED: Created dipendente with ID {data['dipendente_id']}")
    
    def test_verify_dipendente_in_list(self, api_client):
        """GET dipendenti list includes created employee"""
        response = api_client.get(f"{BASE_URL}/api/personale/dipendenti")
        assert response.status_code == 200
        data = response.json()
        
        dip_ids = [d["dipendente_id"] for d in data["dipendenti"]]
        assert TestPersonaleDipendenti.dipendente_id in dip_ids
        print("PASSED: Created dipendente found in list")
    
    def test_update_dipendente(self, api_client):
        """PUT /api/personale/dipendenti/{id} updates employee"""
        dip_id = TestPersonaleDipendenti.dipendente_id
        assert dip_id is not None, "Dipendente must be created first"
        
        payload = {
            "ruolo": "Capo Squadra",
            "ore_settimanali": 45
        }
        response = api_client.put(f"{BASE_URL}/api/personale/dipendenti/{dip_id}", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["ruolo"] == "Capo Squadra"
        assert data["ore_settimanali"] == 45
        print("PASSED: Updated dipendente successfully")
    
    def test_delete_dipendente_soft(self, api_client):
        """DELETE /api/personale/dipendenti/{id} performs soft delete (attivo=false)"""
        dip_id = TestPersonaleDipendenti.dipendente_id
        assert dip_id is not None
        
        response = api_client.delete(f"{BASE_URL}/api/personale/dipendenti/{dip_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("ok") == True
        
        # Verify not in active list anymore
        list_response = api_client.get(f"{BASE_URL}/api/personale/dipendenti")
        dip_ids = [d["dipendente_id"] for d in list_response.json()["dipendenti"]]
        assert dip_id not in dip_ids, "Soft-deleted dipendente should not be in active list"
        print("PASSED: Soft delete dipendente successful")


class TestPersonalePresenze:
    """Presenze CRUD tests"""
    
    dipendente_id = None
    presenza_id = None
    
    @pytest.fixture(autouse=True)
    def setup_dipendente(self, api_client):
        """Create a dipendente for presence testing"""
        if TestPersonalePresenze.dipendente_id is None:
            payload = {
                "nome": "TEST_Presence",
                "cognome": "TEST_Worker",
                "ruolo": "Operaio",
                "tipo_contratto": "dipendente"
            }
            response = api_client.post(f"{BASE_URL}/api/personale/dipendenti", json=payload)
            if response.status_code == 200:
                TestPersonalePresenze.dipendente_id = response.json()["dipendente_id"]
    
    def test_list_presenze(self, api_client):
        """GET /api/personale/presenze returns attendance list"""
        response = api_client.get(f"{BASE_URL}/api/personale/presenze?mese=2026-01")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "presenze" in data
        assert "total" in data
        print(f"PASSED: List presenze returned {data['total']} records for 2026-01")
    
    def test_create_presenza(self, api_client):
        """POST /api/personale/presenze creates attendance record"""
        dip_id = TestPersonalePresenze.dipendente_id
        assert dip_id is not None, "Dipendente must exist for presence test"
        
        payload = {
            "dipendente_id": dip_id,
            "data": "2026-01-15",
            "tipo": "presente",
            "ore_lavorate": 8,
            "ore_straordinario": 1,
            "note": "Test presenza"
        }
        response = api_client.post(f"{BASE_URL}/api/personale/presenze", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "presenza_id" in data
        assert data["dipendente_id"] == dip_id
        assert data["data"] == "2026-01-15"
        assert data["ore_lavorate"] == 8
        
        TestPersonalePresenze.presenza_id = data["presenza_id"]
        print(f"PASSED: Created presenza with ID {data['presenza_id']}")
    
    def test_update_presenza_via_post(self, api_client):
        """POST /api/personale/presenze with same date updates existing record"""
        dip_id = TestPersonalePresenze.dipendente_id
        
        payload = {
            "dipendente_id": dip_id,
            "data": "2026-01-15",  # Same date
            "tipo": "straordinario",
            "ore_lavorate": 10,
            "ore_straordinario": 2,
            "note": "Updated presenza"
        }
        response = api_client.post(f"{BASE_URL}/api/personale/presenze", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["tipo"] == "straordinario"
        assert data["ore_lavorate"] == 10
        print("PASSED: Updated presenza via POST (upsert behavior)")
    
    def test_bulk_presenze(self, api_client):
        """POST /api/personale/presenze/bulk inserts multiple days"""
        dip_id = TestPersonalePresenze.dipendente_id
        
        payload = {
            "dipendente_id": dip_id,
            "giorni": [
                {"data": "2026-01-20", "tipo": "presente", "ore_lavorate": 8},
                {"data": "2026-01-21", "tipo": "presente", "ore_lavorate": 8},
                {"data": "2026-01-22", "tipo": "ferie", "ore_lavorate": 0},
            ]
        }
        response = api_client.post(f"{BASE_URL}/api/personale/presenze/bulk", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("ok") == True
        assert data.get("inserted") == 3
        print("PASSED: Bulk presenze inserted 3 records")
    
    def test_filter_presenze_by_dipendente(self, api_client):
        """GET /api/personale/presenze?dipendente_id filters correctly"""
        dip_id = TestPersonalePresenze.dipendente_id
        
        response = api_client.get(f"{BASE_URL}/api/personale/presenze?mese=2026-01&dipendente_id={dip_id}")
        assert response.status_code == 200
        
        data = response.json()
        # Should have at least 4 records (1 from create, 3 from bulk)
        assert data["total"] >= 4, f"Expected at least 4 presenze, got {data['total']}"
        
        # All should belong to our dipendente
        for p in data["presenze"]:
            assert p["dipendente_id"] == dip_id
        print(f"PASSED: Filtered presenze by dipendente, got {data['total']} records")


class TestPersonaleDocumenti:
    """Documenti upload/list tests"""
    
    dipendente_id = None
    
    @pytest.fixture(autouse=True)
    def setup_dipendente(self, api_client):
        """Ensure dipendente exists"""
        if TestPersonaleDocumenti.dipendente_id is None:
            payload = {"nome": "TEST_Doc", "cognome": "TEST_Employee", "ruolo": "Admin"}
            response = api_client.post(f"{BASE_URL}/api/personale/dipendenti", json=payload)
            if response.status_code == 200:
                TestPersonaleDocumenti.dipendente_id = response.json()["dipendente_id"]
    
    def test_list_documenti(self, api_client):
        """GET /api/personale/documenti returns document list"""
        response = api_client.get(f"{BASE_URL}/api/personale/documenti")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "documenti" in data
        assert "total" in data
        print(f"PASSED: List documenti returned {data['total']} records")
    
    def test_filter_documenti_by_tipo(self, api_client):
        """GET /api/personale/documenti?tipo= filters by document type"""
        response = api_client.get(f"{BASE_URL}/api/personale/documenti?tipo=busta_paga")
        assert response.status_code == 200
        
        data = response.json()
        # All returned should be of type busta_paga
        for doc in data["documenti"]:
            assert doc["tipo"] == "busta_paga"
        print("PASSED: Filter documenti by tipo works")


class TestPersonaleReport:
    """Report generation tests"""
    
    def test_report_mensile(self, api_client):
        """GET /api/personale/report/mensile returns aggregated report"""
        response = api_client.get(f"{BASE_URL}/api/personale/report/mensile?mese=2026-01")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "mese" in data
        assert data["mese"] == "2026-01"
        assert "report" in data
        assert "totale_dipendenti" in data
        assert "inviato" in data
        
        # Check report structure if we have data
        if data["report"]:
            rep = data["report"][0]
            assert "dipendente_id" in rep
            assert "nome" in rep
            assert "cognome" in rep
            assert "conteggi" in rep
            assert "ore_totali" in rep
            assert "ore_straordinario" in rep
        
        print(f"PASSED: Report mensile returned data for {data['totale_dipendenti']} dipendenti")
    
    def test_report_pdf_download(self, api_client):
        """GET /api/personale/report/pdf generates PDF"""
        response = api_client.get(f"{BASE_URL}/api/personale/report/pdf?mese=2026-01")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "application/pdf" in response.headers.get("Content-Type", "")
        assert len(response.content) > 0, "PDF should have content"
        print(f"PASSED: Report PDF generated, size={len(response.content)} bytes")
    
    def test_report_impostazioni_get(self, api_client):
        """GET /api/personale/report/impostazioni returns settings"""
        response = api_client.get(f"{BASE_URL}/api/personale/report/impostazioni")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "report_presenze_giorno_invio" in data
        assert "report_presenze_email_consulente" in data
        print("PASSED: Report impostazioni retrieved")
    
    def test_report_schedula_save(self, api_client):
        """POST /api/personale/report/schedula saves settings"""
        payload = {
            "report_presenze_giorno_invio": 10,
            "report_presenze_email_consulente": "test.consulente@example.com"
        }
        response = api_client.post(f"{BASE_URL}/api/personale/report/schedula", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("ok") == True
        assert data.get("giorno") == 10
        assert data.get("email") == "test.consulente@example.com"
        
        # Verify saved
        verify = api_client.get(f"{BASE_URL}/api/personale/report/impostazioni")
        verify_data = verify.json()
        assert verify_data["report_presenze_giorno_invio"] == 10
        assert verify_data["report_presenze_email_consulente"] == "test.consulente@example.com"
        print("PASSED: Report schedula settings saved and verified")
    
    def test_report_schedula_validation(self, api_client):
        """POST /api/personale/report/schedula validates input"""
        # Missing email
        payload = {"report_presenze_giorno_invio": 5}
        response = api_client.post(f"{BASE_URL}/api/personale/report/schedula", json=payload)
        assert response.status_code == 400, "Should reject missing email"
        
        # Invalid giorno
        payload = {"report_presenze_giorno_invio": 30, "report_presenze_email_consulente": "test@test.com"}
        response = api_client.post(f"{BASE_URL}/api/personale/report/schedula", json=payload)
        assert response.status_code == 400, "Should reject giorno > 28"
        print("PASSED: Report schedula validation works")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_dipendenti(self, api_client):
        """Clean up TEST_ prefixed dipendenti"""
        response = api_client.get(f"{BASE_URL}/api/personale/dipendenti")
        if response.status_code == 200:
            dips = response.json().get("dipendenti", [])
            count = 0
            for dip in dips:
                if dip.get("nome", "").startswith("TEST_") or dip.get("cognome", "").startswith("TEST_"):
                    del_response = api_client.delete(f"{BASE_URL}/api/personale/dipendenti/{dip['dipendente_id']}")
                    if del_response.status_code == 200:
                        count += 1
            print(f"PASSED: Cleanup deactivated {count} test dipendenti")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
