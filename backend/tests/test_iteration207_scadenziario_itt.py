"""
Iteration 207: Scadenziario Manutenzioni Unificato + Verbali ITT

Tests for:
1. GET /api/scadenziario-manutenzioni — Unified aggregation of instruments + attrezzature + ITT
2. POST /api/verbali-itt — Create ITT verbale
3. GET /api/verbali-itt — List verbali with expiry status
4. GET /api/verbali-itt/check-validita — Report qualified/expired processes
5. DELETE /api/verbali-itt/{itt_id} — Delete verbale
6. POST /api/verbali-itt/{itt_id}/firma — Digital signature
7. GET /api/verbali-itt/{itt_id}/pdf — PDF generation with WeasyPrint
8. GET /api/riesame/{commessa_id} — New check 'itt_processi_qualificati' (filo conduttore)
"""
import pytest
import requests
import os
from datetime import date, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "d36a500823254076b5c583d6c1d903fa"
USER_ID = "user_e4012a8f48"
TEST_COMMESSA = "comm_sasso_marconi"  # C-2026-0012

# Existing test ITTs from context
EXISTING_ITT_TAGLIO_TERMICO = "itt_1de1f91f53"
EXISTING_ITT_FORATURA = "itt_fa852ec36b"


@pytest.fixture
def auth_headers():
    """Authentication headers with session token cookie"""
    return {
        "Content-Type": "application/json",
        "Cookie": f"session_token={SESSION_TOKEN}"
    }


class TestScadenziarioManutenzioni:
    """Tests for unified maintenance schedule endpoint"""
    
    def test_get_scadenziario_returns_unified_items(self, auth_headers):
        """GET /api/scadenziario-manutenzioni returns aggregated items from instruments + attrezzature + ITT"""
        response = requests.get(f"{BASE_URL}/api/scadenziario-manutenzioni", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "items" in data, "Response should have 'items' array"
        assert "kpi" in data, "Response should have 'kpi' object"
        assert isinstance(data["items"], list), "items should be a list"
        
        # Verify KPI structure
        kpi = data["kpi"]
        assert "totale" in kpi, "KPI should have 'totale'"
        assert "scaduti" in kpi, "KPI should have 'scaduti'"
        assert "in_scadenza" in kpi, "KPI should have 'in_scadenza'"
        assert "prossimi_90gg" in kpi, "KPI should have 'prossimi_90gg'"
        assert "conformi" in kpi, "KPI should have 'conformi'"
        
        print(f"Scadenziario KPI: totale={kpi['totale']}, scaduti={kpi['scaduti']}, in_scadenza={kpi['in_scadenza']}")
    
    def test_scadenziario_items_have_required_fields(self, auth_headers):
        """Each item in scadenziario should have required fields"""
        response = requests.get(f"{BASE_URL}/api/scadenziario-manutenzioni", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if len(data["items"]) > 0:
            item = data["items"][0]
            required_fields = ["id", "fonte", "nome", "urgenza", "impatto"]
            for field in required_fields:
                assert field in item, f"Item should have '{field}' field"
            
            # Verify fonte is one of expected values
            assert item["fonte"] in ["strumento", "attrezzatura", "itt"], f"fonte should be strumento/attrezzatura/itt, got {item['fonte']}"
            
            # Verify urgenza is one of expected values
            assert item["urgenza"] in ["scaduto", "in_scadenza", "prossimo", "ok", "sconosciuto"], f"Invalid urgenza: {item['urgenza']}"
            
            # Verify impatto is a list
            assert isinstance(item["impatto"], list), "impatto should be a list"
            
            print(f"Sample item: fonte={item['fonte']}, nome={item['nome']}, urgenza={item['urgenza']}")
    
    def test_scadenziario_contains_itt_items(self, auth_headers):
        """Scadenziario should include ITT verbali"""
        response = requests.get(f"{BASE_URL}/api/scadenziario-manutenzioni", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        itt_items = [i for i in data["items"] if i["fonte"] == "itt"]
        print(f"Found {len(itt_items)} ITT items in scadenziario")
        
        # Based on context, we should have at least 2 ITTs (taglio_termico, foratura)
        if len(itt_items) > 0:
            for itt in itt_items:
                assert "ITT" in itt["nome"], f"ITT item name should contain 'ITT': {itt['nome']}"
                assert "Riesame Tecnico" in str(itt["impatto"]), "ITT impatto should reference Riesame Tecnico"
    
    def test_scadenziario_blocchi_riesame_alert(self, auth_headers):
        """Scadenziario should report blocchi_riesame count"""
        response = requests.get(f"{BASE_URL}/api/scadenziario-manutenzioni", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "blocchi_riesame" in data, "Response should have 'blocchi_riesame'"
        assert isinstance(data["blocchi_riesame"], int), "blocchi_riesame should be an integer"
        
        # alert_msg should be present if there are blocchi
        if data["blocchi_riesame"] > 0:
            assert data.get("alert_msg"), "alert_msg should be present when blocchi_riesame > 0"
        
        print(f"Blocchi riesame: {data['blocchi_riesame']}, alert: {data.get('alert_msg', 'None')}")


class TestVerbaliITTCRUD:
    """Tests for Verbali ITT CRUD operations"""
    
    def test_list_verbali_itt(self, auth_headers):
        """GET /api/verbali-itt returns list of verbali"""
        response = requests.get(f"{BASE_URL}/api/verbali-itt", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "verbali" in data, "Response should have 'verbali' array"
        assert "total" in data, "Response should have 'total' count"
        assert isinstance(data["verbali"], list), "verbali should be a list"
        
        print(f"Found {data['total']} verbali ITT")
        
        # Verify each verbale has required fields
        if len(data["verbali"]) > 0:
            v = data["verbali"][0]
            required = ["itt_id", "processo", "macchina", "materiale", "data_prova", "data_scadenza", "esito_globale"]
            for field in required:
                assert field in v, f"Verbale should have '{field}' field"
            
            # Verify status fields are calculated
            assert "scaduto" in v, "Verbale should have 'scaduto' status"
            assert "in_scadenza" in v, "Verbale should have 'in_scadenza' status"
            assert "giorni_rimasti" in v, "Verbale should have 'giorni_rimasti'"
    
    def test_list_verbali_filter_by_processo(self, auth_headers):
        """GET /api/verbali-itt?processo=taglio_termico filters by process"""
        response = requests.get(f"{BASE_URL}/api/verbali-itt?processo=taglio_termico", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned verbali should have processo=taglio_termico
        for v in data["verbali"]:
            assert v["processo"] == "taglio_termico", f"Expected processo=taglio_termico, got {v['processo']}"
        
        print(f"Found {data['total']} verbali for taglio_termico")
    
    def test_create_verbale_itt(self, auth_headers):
        """POST /api/verbali-itt creates a new verbale"""
        today = date.today()
        scadenza = today + timedelta(days=365)
        
        payload = {
            "processo": "punzonatura",
            "descrizione": "TEST - Prova punzonatura lamiere",
            "macchina": "Punzonatrice TEST-001",
            "materiale": "S275JR",
            "spessore_min_mm": 3.0,
            "spessore_max_mm": 12.0,
            "norma_riferimento": "EN 1090-2",
            "data_prova": today.isoformat(),
            "data_scadenza": scadenza.isoformat(),
            "prove": [
                {"parametro": "Diametro foro", "valore_atteso": "20mm", "valore_misurato": "20.1mm", "conforme": True},
                {"parametro": "Posizione", "valore_atteso": "±0.5mm", "valore_misurato": "0.3mm", "conforme": True}
            ],
            "esito_globale": True,
            "note": "Test automatico iteration 207"
        }
        
        response = requests.post(f"{BASE_URL}/api/verbali-itt", json=payload, headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "itt_id" in data, "Response should have 'itt_id'"
        assert data["processo"] == "punzonatura", "processo should match"
        assert data["macchina"] == "Punzonatrice TEST-001", "macchina should match"
        assert data["esito_globale"] == True, "esito_globale should be True"
        assert len(data["prove"]) == 2, "Should have 2 prove"
        
        print(f"Created ITT verbale: {data['itt_id']}")
        
        # Store for cleanup
        self.__class__.created_itt_id = data["itt_id"]
        return data["itt_id"]
    
    def test_create_verbale_invalid_processo(self, auth_headers):
        """POST /api/verbali-itt with invalid processo returns 400"""
        payload = {
            "processo": "processo_invalido",
            "macchina": "Test",
            "materiale": "S275JR",
            "data_prova": date.today().isoformat(),
            "data_scadenza": (date.today() + timedelta(days=365)).isoformat()
        }
        
        response = requests.post(f"{BASE_URL}/api/verbali-itt", json=payload, headers=auth_headers)
        
        assert response.status_code == 400, f"Expected 400 for invalid processo, got {response.status_code}"
        print("Correctly rejected invalid processo")
    
    def test_delete_verbale_itt(self, auth_headers):
        """DELETE /api/verbali-itt/{itt_id} deletes the verbale"""
        # First create one to delete
        today = date.today()
        payload = {
            "processo": "raddrizzatura",
            "macchina": "TEST DELETE",
            "materiale": "S355J2",
            "data_prova": today.isoformat(),
            "data_scadenza": (today + timedelta(days=30)).isoformat(),
            "esito_globale": False,
            "note": "To be deleted"
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/verbali-itt", json=payload, headers=auth_headers)
        assert create_resp.status_code == 200
        itt_id = create_resp.json()["itt_id"]
        
        # Now delete it
        delete_resp = requests.delete(f"{BASE_URL}/api/verbali-itt/{itt_id}", headers=auth_headers)
        
        assert delete_resp.status_code == 200, f"Expected 200, got {delete_resp.status_code}: {delete_resp.text}"
        assert "eliminato" in delete_resp.json().get("message", "").lower(), "Should confirm deletion"
        
        # Verify it's gone
        list_resp = requests.get(f"{BASE_URL}/api/verbali-itt", headers=auth_headers)
        verbali = list_resp.json()["verbali"]
        assert not any(v["itt_id"] == itt_id for v in verbali), "Deleted ITT should not appear in list"
        
        print(f"Successfully deleted ITT: {itt_id}")
    
    def test_delete_nonexistent_verbale(self, auth_headers):
        """DELETE /api/verbali-itt/{itt_id} with invalid ID returns 404"""
        response = requests.delete(f"{BASE_URL}/api/verbali-itt/itt_nonexistent_12345", headers=auth_headers)
        
        assert response.status_code == 404, f"Expected 404 for nonexistent ITT, got {response.status_code}"


class TestVerbaliITTFirma:
    """Tests for ITT digital signature"""
    
    def test_firma_verbale_itt(self, auth_headers):
        """POST /api/verbali-itt/{itt_id}/firma adds digital signature"""
        # Create a verbale to sign
        today = date.today()
        payload = {
            "processo": "piegatura",
            "macchina": "Pressa piegatrice TEST",
            "materiale": "S275JR",
            "data_prova": today.isoformat(),
            "data_scadenza": (today + timedelta(days=180)).isoformat(),
            "esito_globale": True
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/verbali-itt", json=payload, headers=auth_headers)
        assert create_resp.status_code == 200
        itt_id = create_resp.json()["itt_id"]
        
        # Sign it
        firma_payload = {
            "nome": "Mario Rossi",
            "ruolo": "Responsabile Qualita"
        }
        
        firma_resp = requests.post(f"{BASE_URL}/api/verbali-itt/{itt_id}/firma", json=firma_payload, headers=auth_headers)
        
        assert firma_resp.status_code == 200, f"Expected 200, got {firma_resp.status_code}: {firma_resp.text}"
        assert "firmato" in firma_resp.json().get("message", "").lower(), "Should confirm signature"
        
        print(f"Successfully signed ITT: {itt_id}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/verbali-itt/{itt_id}", headers=auth_headers)
    
    def test_firma_without_nome_returns_400(self, auth_headers):
        """POST /api/verbali-itt/{itt_id}/firma without nome returns 400"""
        # Use existing ITT
        firma_payload = {"ruolo": "Test"}
        
        response = requests.post(f"{BASE_URL}/api/verbali-itt/{EXISTING_ITT_TAGLIO_TERMICO}/firma", json=firma_payload, headers=auth_headers)
        
        assert response.status_code == 400, f"Expected 400 for missing nome, got {response.status_code}"


class TestVerbaliITTPDF:
    """Tests for ITT PDF generation"""
    
    def test_generate_itt_pdf(self, auth_headers):
        """GET /api/verbali-itt/{itt_id}/pdf generates valid PDF"""
        response = requests.get(f"{BASE_URL}/api/verbali-itt/{EXISTING_ITT_TAGLIO_TERMICO}/pdf", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("content-type") == "application/pdf", "Should return PDF content-type"
        
        # Verify it's a valid PDF (starts with %PDF)
        content = response.content
        assert content[:4] == b'%PDF', "Content should be a valid PDF"
        assert len(content) > 5000, f"PDF should be substantial, got {len(content)} bytes"
        
        # Check filename in Content-Disposition
        cd = response.headers.get("content-disposition", "")
        assert "Verbale_ITT" in cd, f"Filename should contain 'Verbale_ITT': {cd}"
        
        print(f"Generated PDF: {len(content)} bytes")
    
    def test_pdf_nonexistent_itt_returns_404(self, auth_headers):
        """GET /api/verbali-itt/{itt_id}/pdf with invalid ID returns 404"""
        response = requests.get(f"{BASE_URL}/api/verbali-itt/itt_nonexistent_xyz/pdf", headers=auth_headers)
        
        assert response.status_code == 404, f"Expected 404 for nonexistent ITT, got {response.status_code}"


class TestVerbaliITTCheckValidita:
    """Tests for ITT validity check endpoint"""
    
    def test_check_validita_returns_process_status(self, auth_headers):
        """GET /api/verbali-itt/check-validita returns qualified/expired processes"""
        response = requests.get(f"{BASE_URL}/api/verbali-itt/check-validita", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "processi_qualificati" in data, "Should have 'processi_qualificati'"
        assert "processi_scaduti" in data, "Should have 'processi_scaduti'"
        assert "dettaglio_validi" in data, "Should have 'dettaglio_validi'"
        assert "tutti_i_processi" in data, "Should have 'tutti_i_processi'"
        
        # Verify all processes list
        all_processes = data["tutti_i_processi"]
        expected_processes = ["taglio_termico", "taglio_meccanico", "foratura", "piegatura", "punzonatura", "raddrizzatura"]
        for proc in expected_processes:
            assert proc in all_processes, f"Process '{proc}' should be in tutti_i_processi"
        
        print(f"Processi qualificati: {data['processi_qualificati']}")
        print(f"Processi scaduti: {data['processi_scaduti']}")


class TestRiesameTecnicoITTCheck:
    """Tests for ITT check in Riesame Tecnico (filo conduttore)"""
    
    def test_riesame_has_itt_check(self, auth_headers):
        """GET /api/riesame/{commessa_id} includes itt_processi_qualificati check"""
        response = requests.get(f"{BASE_URL}/api/riesame/{TEST_COMMESSA}", headers=auth_headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify checks array exists
        assert "checks" in data, "Response should have 'checks' array"
        checks = data["checks"]
        
        # Find the ITT check
        itt_check = next((c for c in checks if c["id"] == "itt_processi_qualificati"), None)
        
        assert itt_check is not None, "Riesame should have 'itt_processi_qualificati' check"
        assert itt_check["sezione"] == "Produzione", "ITT check should be in 'Produzione' section"
        assert itt_check["auto"] == True, "ITT check should be automatic"
        assert "label" in itt_check, "ITT check should have label"
        assert "esito" in itt_check, "ITT check should have esito"
        assert "valore" in itt_check, "ITT check should have valore"
        assert "nota" in itt_check, "ITT check should have nota"
        
        print(f"ITT check: esito={itt_check['esito']}, valore={itt_check['valore']}")
        print(f"ITT check nota: {itt_check['nota']}")
    
    def test_riesame_has_12_checks(self, auth_headers):
        """GET /api/riesame/{commessa_id} should have 12 checks (was 11, now includes ITT)"""
        response = requests.get(f"{BASE_URL}/api/riesame/{TEST_COMMESSA}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        n_totale = data.get("n_totale", 0)
        assert n_totale == 12, f"Riesame should have 12 checks (including ITT), got {n_totale}"
        
        print(f"Riesame has {n_totale} checks, {data.get('n_ok', 0)} passed")
    
    def test_riesame_itt_check_shows_missing_processes(self, auth_headers):
        """ITT check should show which processes are missing"""
        response = requests.get(f"{BASE_URL}/api/riesame/{TEST_COMMESSA}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        itt_check = next((c for c in data["checks"] if c["id"] == "itt_processi_qualificati"), None)
        assert itt_check is not None
        
        # Based on context: taglio_termico and foratura are qualified, taglio_meccanico is missing
        nota = itt_check.get("nota", "")
        
        # The check should either show missing processes or confirm all are valid
        if not itt_check["esito"]:
            assert "mancanti" in nota.lower() or "taglio meccanico" in nota.lower(), \
                f"If check fails, nota should mention missing processes: {nota}"
        else:
            assert "validi" in nota.lower() or "qualificati" in nota.lower(), \
                f"If check passes, nota should confirm validity: {nota}"
        
        print(f"ITT check nota: {nota}")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_verbali(self, auth_headers):
        """Remove any test verbali created during testing"""
        response = requests.get(f"{BASE_URL}/api/verbali-itt", headers=auth_headers)
        if response.status_code == 200:
            verbali = response.json().get("verbali", [])
            for v in verbali:
                # Delete verbali with TEST markers
                if "TEST" in v.get("macchina", "") or "TEST" in v.get("note", "") or v.get("processo") == "punzonatura":
                    requests.delete(f"{BASE_URL}/api/verbali-itt/{v['itt_id']}", headers=auth_headers)
                    print(f"Cleaned up test ITT: {v['itt_id']}")
        
        print("Cleanup complete")
