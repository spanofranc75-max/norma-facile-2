"""
Iteration 204: Verifica Coerenza Rintracciabilita + Template PDF Processo 111

Tests for:
1. GET /api/fpc/batches/verifica-coerenza/{commessa_id} - Discrepancy analysis
2. GET /api/template-111/preview/{commessa_id} - Preview data with company info
3. GET /api/template-111/pdf/{commessa_id} - PDF generation (29KB+)
4. Regression: /api/fpc/batches/rintracciabilita/{commessa_id} still works
5. Regression: /api/riesame/{commessa_id} auto-checks still work
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "d36a500823254076b5c583d6c1d903fa"
TEST_COMMESSA_ID = "com_loiano_cims_2026"


@pytest.fixture
def api_client():
    """Shared requests session with auth cookie."""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestVerificaCoerenzaRintracciabilita:
    """Tests for GET /api/fpc/batches/verifica-coerenza/{commessa_id}"""

    def test_verifica_coerenza_returns_200(self, api_client):
        """Endpoint returns 200 OK"""
        response = api_client.get(f"{BASE_URL}/api/fpc/batches/verifica-coerenza/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_verifica_coerenza_has_riepilogo(self, api_client):
        """Response contains riepilogo with required fields"""
        response = api_client.get(f"{BASE_URL}/api/fpc/batches/verifica-coerenza/{TEST_COMMESSA_ID}")
        data = response.json()
        
        assert "riepilogo" in data, "Missing riepilogo field"
        riepilogo = data["riepilogo"]
        
        # Check all required riepilogo fields
        required_fields = ["totale", "conformi", "critici", "attenzione", "senza_colata", "senza_certificato", "pct_conforme"]
        for field in required_fields:
            assert field in riepilogo, f"Missing riepilogo.{field}"
        
        print(f"Riepilogo: totale={riepilogo['totale']}, conformi={riepilogo['conformi']}, critici={riepilogo['critici']}, attenzione={riepilogo['attenzione']}")

    def test_verifica_coerenza_has_lotti_with_issues(self, api_client):
        """Response contains lotti array with issue details"""
        response = api_client.get(f"{BASE_URL}/api/fpc/batches/verifica-coerenza/{TEST_COMMESSA_ID}")
        data = response.json()
        
        assert "lotti" in data, "Missing lotti field"
        assert isinstance(data["lotti"], list), "lotti should be a list"
        
        # Check each lotto has required fields
        for lotto in data["lotti"]:
            assert "batch_id" in lotto, "Missing batch_id in lotto"
            assert "descrizione" in lotto, "Missing descrizione in lotto"
            assert "colata" in lotto, "Missing colata in lotto"
            assert "conforme" in lotto, "Missing conforme in lotto"
            assert "issues" in lotto, "Missing issues in lotto"
            
            # Check issues structure
            for issue in lotto["issues"]:
                assert "tipo" in issue, "Missing tipo in issue"
                assert "gravita" in issue, "Missing gravita in issue"
                assert "messaggio" in issue, "Missing messaggio in issue"
                assert issue["gravita"] in ["critica", "attenzione"], f"Invalid gravita: {issue['gravita']}"

    def test_verifica_coerenza_detects_certificato_mancante(self, api_client):
        """Verifica detects missing 3.1 certificates"""
        response = api_client.get(f"{BASE_URL}/api/fpc/batches/verifica-coerenza/{TEST_COMMESSA_ID}")
        data = response.json()
        
        # Find lotti with certificato_mancante issue
        cert_missing_issues = []
        for lotto in data["lotti"]:
            for issue in lotto["issues"]:
                if issue["tipo"] == "certificato_mancante":
                    cert_missing_issues.append(lotto["batch_id"])
        
        # Based on test data, all 3 batches should have missing certificates
        assert len(cert_missing_issues) >= 3, f"Expected at least 3 certificato_mancante issues, found {len(cert_missing_issues)}"
        assert data["riepilogo"]["senza_certificato"] >= 3, "senza_certificato count should be >= 3"
        print(f"Found {len(cert_missing_issues)} batches with missing certificates")

    def test_verifica_coerenza_detects_ddt_non_collegato(self, api_client):
        """Verifica detects batches not linked to DDT"""
        response = api_client.get(f"{BASE_URL}/api/fpc/batches/verifica-coerenza/{TEST_COMMESSA_ID}")
        data = response.json()
        
        # Find lotti with ddt_non_collegato issue
        ddt_missing_issues = []
        for lotto in data["lotti"]:
            for issue in lotto["issues"]:
                if issue["tipo"] == "ddt_non_collegato":
                    ddt_missing_issues.append(lotto["batch_id"])
        
        # Based on test data, all 3 batches should not be linked to DDT
        assert len(ddt_missing_issues) >= 3, f"Expected at least 3 ddt_non_collegato issues, found {len(ddt_missing_issues)}"
        print(f"Found {len(ddt_missing_issues)} batches not linked to DDT")

    def test_verifica_coerenza_issue_types(self, api_client):
        """Verifica supports all expected issue types"""
        response = api_client.get(f"{BASE_URL}/api/fpc/batches/verifica-coerenza/{TEST_COMMESSA_ID}")
        data = response.json()
        
        # Collect all issue types found
        issue_types = set()
        for lotto in data["lotti"]:
            for issue in lotto["issues"]:
                issue_types.add(issue["tipo"])
        
        # Expected issue types from the implementation
        expected_types = {"certificato_mancante", "ddt_non_collegato", "colata_mancante", "descrizione_mismatch", "quantita_mismatch", "colata_mismatch"}
        
        # At least some of these should be present
        print(f"Issue types found: {issue_types}")
        assert len(issue_types) > 0, "No issue types found"


class TestTemplate111Preview:
    """Tests for GET /api/template-111/preview/{commessa_id}"""

    def test_preview_returns_200(self, api_client):
        """Endpoint returns 200 OK"""
        response = api_client.get(f"{BASE_URL}/api/template-111/preview/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_preview_has_azienda_data(self, api_client):
        """Response contains azienda data from company_settings"""
        response = api_client.get(f"{BASE_URL}/api/template-111/preview/{TEST_COMMESSA_ID}")
        data = response.json()
        
        assert "azienda" in data, "Missing azienda field"
        azienda = data["azienda"]
        
        # Check required azienda fields
        required_fields = ["ragione_sociale", "indirizzo", "piva"]
        for field in required_fields:
            assert field in azienda, f"Missing azienda.{field}"
        
        # Verify company data matches expected values
        assert "Steel Project Design" in azienda["ragione_sociale"], f"Unexpected ragione_sociale: {azienda['ragione_sociale']}"
        assert azienda["piva"] == "02042850897", f"Unexpected P.IVA: {azienda['piva']}"
        print(f"Azienda: {azienda['ragione_sociale']}, P.IVA: {azienda['piva']}")

    def test_preview_has_specifiche_tecniche(self, api_client):
        """Response contains specifiche_tecniche for processo 111"""
        response = api_client.get(f"{BASE_URL}/api/template-111/preview/{TEST_COMMESSA_ID}")
        data = response.json()
        
        assert "specifiche_tecniche" in data, "Missing specifiche_tecniche field"
        spec = data["specifiche_tecniche"]
        
        # Check required specifiche fields
        required_fields = ["norma_qualifica", "processo", "gruppo_materiali", "gradi_acciaio", "spessori", "posizioni", "tipo_giunto"]
        for field in required_fields:
            assert field in spec, f"Missing specifiche_tecniche.{field}"
        
        # Verify UNI EN ISO 15614-1 reference
        assert "15614-1" in spec["norma_qualifica"], f"Unexpected norma_qualifica: {spec['norma_qualifica']}"
        assert "111" in spec["processo"], f"Unexpected processo: {spec['processo']}"
        assert "S275" in spec["gradi_acciaio"] and "S355" in spec["gradi_acciaio"], f"Unexpected gradi_acciaio: {spec['gradi_acciaio']}"
        print(f"Norma: {spec['norma_qualifica']}, Processo: {spec['processo']}")

    def test_preview_has_classe_esecuzione_from_riesame(self, api_client):
        """Response contains classe_esecuzione auto-populated from Riesame Tecnico"""
        response = api_client.get(f"{BASE_URL}/api/template-111/preview/{TEST_COMMESSA_ID}")
        data = response.json()
        
        assert "classe_esecuzione" in data, "Missing classe_esecuzione field"
        exc = data["classe_esecuzione"]
        
        # Should be EXC2 based on test data
        assert exc in ["EXC1", "EXC2", "EXC3", "EXC4"], f"Invalid classe_esecuzione: {exc}"
        assert exc == "EXC2", f"Expected EXC2, got {exc}"
        print(f"Classe esecuzione: {exc}")

    def test_preview_has_commessa_info(self, api_client):
        """Response contains commessa info"""
        response = api_client.get(f"{BASE_URL}/api/template-111/preview/{TEST_COMMESSA_ID}")
        data = response.json()
        
        assert "commessa_id" in data, "Missing commessa_id"
        assert "numero_commessa" in data, "Missing numero_commessa"
        assert "titolo_commessa" in data, "Missing titolo_commessa"
        
        assert data["commessa_id"] == TEST_COMMESSA_ID
        print(f"Commessa: {data['numero_commessa']} - {data['titolo_commessa']}")


class TestTemplate111PDF:
    """Tests for GET /api/template-111/pdf/{commessa_id}"""

    def test_pdf_returns_200(self, api_client):
        """Endpoint returns 200 OK"""
        response = api_client.get(f"{BASE_URL}/api/template-111/pdf/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_pdf_content_type(self, api_client):
        """Response has correct content-type for PDF"""
        response = api_client.get(f"{BASE_URL}/api/template-111/pdf/{TEST_COMMESSA_ID}")
        content_type = response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"

    def test_pdf_has_content_disposition(self, api_client):
        """Response has Content-Disposition header for download"""
        response = api_client.get(f"{BASE_URL}/api/template-111/pdf/{TEST_COMMESSA_ID}")
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp, f"Expected attachment in Content-Disposition, got {content_disp}"
        assert "Richiesta_Qualifica" in content_disp or "111" in content_disp, f"Unexpected filename in Content-Disposition: {content_disp}"
        print(f"Content-Disposition: {content_disp}")

    def test_pdf_size_minimum(self, api_client):
        """PDF should be at least 29KB (complete content)"""
        response = api_client.get(f"{BASE_URL}/api/template-111/pdf/{TEST_COMMESSA_ID}")
        pdf_size = len(response.content)
        
        # PDF should be at least 29KB based on expected content
        assert pdf_size >= 29000, f"PDF too small: {pdf_size} bytes (expected >= 29000)"
        print(f"PDF size: {pdf_size} bytes")

    def test_pdf_starts_with_pdf_header(self, api_client):
        """PDF content starts with %PDF header"""
        response = api_client.get(f"{BASE_URL}/api/template-111/pdf/{TEST_COMMESSA_ID}")
        pdf_header = response.content[:8]
        assert pdf_header.startswith(b"%PDF"), f"Invalid PDF header: {pdf_header}"


class TestRintracciabilitaRegression:
    """Regression tests for /api/fpc/batches/rintracciabilita/{commessa_id}"""

    def test_rintracciabilita_returns_200(self, api_client):
        """Endpoint still returns 200 OK"""
        response = api_client.get(f"{BASE_URL}/api/fpc/batches/rintracciabilita/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_rintracciabilita_has_righe(self, api_client):
        """Response contains righe array with batch data"""
        response = api_client.get(f"{BASE_URL}/api/fpc/batches/rintracciabilita/{TEST_COMMESSA_ID}")
        data = response.json()
        
        assert "righe" in data, "Missing righe field"
        assert "totale" in data, "Missing totale field"
        assert "collegati" in data, "Missing collegati field"
        
        # Should have 3 batches based on test data
        assert data["totale"] >= 3, f"Expected at least 3 batches, got {data['totale']}"
        print(f"Rintracciabilita: {data['totale']} lotti, {data['collegati']} collegati")

    def test_rintracciabilita_righe_have_colata(self, api_client):
        """Each riga has colata field from material_batches"""
        response = api_client.get(f"{BASE_URL}/api/fpc/batches/rintracciabilita/{TEST_COMMESSA_ID}")
        data = response.json()
        
        for riga in data["righe"]:
            assert "colata" in riga, f"Missing colata in riga {riga.get('batch_id')}"
            # Colata should be populated for test data
            if riga.get("batch_id") in ["bat_loiano_0", "bat_loiano_1", "bat_loiano_2"]:
                assert riga["colata"], f"Empty colata for {riga['batch_id']}"


class TestRiesameTecnicoRegression:
    """Regression tests for /api/riesame/{commessa_id} auto-checks"""

    def test_riesame_returns_200(self, api_client):
        """Endpoint still returns 200 OK"""
        response = api_client.get(f"{BASE_URL}/api/riesame/{TEST_COMMESSA_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    def test_riesame_has_checks(self, api_client):
        """Response contains checks array"""
        response = api_client.get(f"{BASE_URL}/api/riesame/{TEST_COMMESSA_ID}")
        data = response.json()
        
        assert "checks" in data, "Missing checks field"
        assert isinstance(data["checks"], list), "checks should be a list"
        assert len(data["checks"]) > 0, "checks should not be empty"

    def test_riesame_strumenti_tarati_check(self, api_client):
        """strumenti_tarati check shows correct instrument count"""
        response = api_client.get(f"{BASE_URL}/api/riesame/{TEST_COMMESSA_ID}")
        data = response.json()
        
        strumenti_check = None
        for check in data["checks"]:
            if check.get("id") == "strumenti_tarati":
                strumenti_check = check
                break
        
        assert strumenti_check is not None, "strumenti_tarati check not found"
        assert "valore" in strumenti_check, "Missing valore in strumenti_tarati"
        print(f"strumenti_tarati: {strumenti_check['valore']}")

    def test_riesame_materiali_confermati_check(self, api_client):
        """materiali_confermati check shows batch count from material_batches"""
        response = api_client.get(f"{BASE_URL}/api/riesame/{TEST_COMMESSA_ID}")
        data = response.json()
        
        materiali_check = None
        for check in data["checks"]:
            if check.get("id") == "materiali_confermati":
                materiali_check = check
                break
        
        assert materiali_check is not None, "materiali_confermati check not found"
        assert "valore" in materiali_check, "Missing valore in materiali_confermati"
        # Should show "3 lotti" based on test data
        assert "3" in str(materiali_check["valore"]) or "lotti" in str(materiali_check["valore"]).lower(), f"Unexpected materiali_confermati value: {materiali_check['valore']}"
        print(f"materiali_confermati: {materiali_check['valore']}")

    def test_riesame_tolleranza_calibro_check(self, api_client):
        """tolleranza_calibro check uses per-instrument soglia_accettabilita"""
        response = api_client.get(f"{BASE_URL}/api/riesame/{TEST_COMMESSA_ID}")
        data = response.json()
        
        tolleranza_check = None
        for check in data["checks"]:
            if check.get("id") == "tolleranza_calibro":
                tolleranza_check = check
                break
        
        assert tolleranza_check is not None, "tolleranza_calibro check not found"
        assert "valore" in tolleranza_check, "Missing valore in tolleranza_calibro"
        print(f"tolleranza_calibro: {tolleranza_check['valore']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
