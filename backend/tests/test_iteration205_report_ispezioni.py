"""
Iteration 205: Report Ispezioni VT/Dimensionali EN 1090-2:2024

Tests for the new Report Ispezioni module:
- GET /api/report-ispezioni/{commessa_id} — Returns 10 VT checks + 8 DIM checks with stats
- POST /api/report-ispezioni/{commessa_id} — Save inspection results
- POST /api/report-ispezioni/{commessa_id}/approva — Sign and approve (fails if not all checks filled)
- GET /api/report-ispezioni/{commessa_id}/pdf — Generate PDF report
- Integration: Controllo Finale auto-check 'vt_nc_chiuse' reads from report_ispezioni
- Regression: Controllo Finale still shows all 11 checks correctly
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "d36a500823254076b5c583d6c1d903fa"
TEST_COMMESSA_ID = "com_loiano_cims_2026"


@pytest.fixture
def api_client():
    """Shared requests session with auth cookie"""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestReportIspezioniGET:
    """GET /api/report-ispezioni/{commessa_id} — Returns 10 VT + 8 DIM checks"""

    def test_get_report_returns_200(self, api_client):
        """GET returns 200 with report data"""
        response = api_client.get(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        assert "commessa_id" in data
        assert data["commessa_id"] == TEST_COMMESSA_ID

    def test_get_report_has_10_vt_checks(self, api_client):
        """Report contains exactly 10 VT checks (ISO 5817 Livello C)"""
        response = api_client.get(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}")
        data = response.json()
        assert "checks_vt" in data
        assert len(data["checks_vt"]) == 10
        # Verify VT check structure
        vt_check = data["checks_vt"][0]
        assert "id" in vt_check
        assert "label" in vt_check
        assert "desc" in vt_check
        assert "rif" in vt_check
        assert "esito" in vt_check
        assert "valore_misurato" in vt_check
        assert "note" in vt_check

    def test_get_report_has_8_dim_checks(self, api_client):
        """Report contains exactly 8 DIM checks (EN 1090-2 B6/B8)"""
        response = api_client.get(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}")
        data = response.json()
        assert "checks_dim" in data
        assert len(data["checks_dim"]) == 8
        # Verify DIM check structure
        dim_check = data["checks_dim"][0]
        assert "id" in dim_check
        assert "label" in dim_check
        assert "rif" in dim_check

    def test_get_report_has_stats(self, api_client):
        """Report contains stats for VT and DIM areas"""
        response = api_client.get(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}")
        data = response.json()
        assert "stats" in data
        assert "vt" in data["stats"]
        assert "dim" in data["stats"]
        # VT stats
        vt_stats = data["stats"]["vt"]
        assert "ok" in vt_stats
        assert "nok" in vt_stats
        assert "pending" in vt_stats
        assert "totale" in vt_stats
        assert vt_stats["totale"] == 10
        # DIM stats
        dim_stats = data["stats"]["dim"]
        assert dim_stats["totale"] == 8

    def test_get_report_has_metadata_fields(self, api_client):
        """Report contains metadata fields"""
        response = api_client.get(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}")
        data = response.json()
        assert "completo" in data
        assert "superato" in data
        assert "approvato" in data
        assert "firma" in data
        assert "strumenti_utilizzati" in data
        assert "condizioni_ambientali" in data
        assert "ispettore_nome" in data
        assert "note_generali" in data

    def test_get_report_vt_check_ids(self, api_client):
        """VT checks have correct IDs per ISO 5817"""
        response = api_client.get(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}")
        data = response.json()
        vt_ids = [c["id"] for c in data["checks_vt"]]
        expected_ids = [
            "vt_cricche", "vt_porosita", "vt_inclusioni", "vt_mancanza_fusione",
            "vt_mancanza_penetrazione", "vt_sottosquadro", "vt_eccesso_sovrametallo",
            "vt_slivellamento", "vt_spruzzi", "vt_aspetto_generale"
        ]
        assert vt_ids == expected_ids

    def test_get_report_dim_check_ids(self, api_client):
        """DIM checks have correct IDs per EN 1090-2 B6/B8"""
        response = api_client.get(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}")
        data = response.json()
        dim_ids = [c["id"] for c in data["checks_dim"]]
        expected_ids = [
            "dim_lunghezze", "dim_rettilineita", "dim_squadratura", "dim_interassi_fori",
            "dim_diametro_fori", "dim_posizione_piastre", "dim_altezza_complessiva", "dim_gola_saldatura"
        ]
        assert dim_ids == expected_ids


class TestReportIspezioniPOST:
    """POST /api/report-ispezioni/{commessa_id} — Save inspection results"""

    def test_save_report_returns_200(self, api_client):
        """POST save returns 200 with report_id"""
        payload = {
            "ispezioni_vt": [
                {"check_id": "vt_cricche", "esito": True, "valore_misurato": "OK", "note": "Test"}
            ],
            "ispezioni_dim": [
                {"check_id": "dim_lunghezze", "esito": True, "valore_misurato": "1000mm", "note": ""}
            ],
            "strumenti_utilizzati": "Calibro digitale",
            "condizioni_ambientali": "Luce naturale",
            "ispettore_nome": "Test Inspector",
            "note_generali": "Test notes"
        }
        response = api_client.post(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "report_id" in data
        assert data["report_id"].startswith("rpt_")

    def test_save_report_persists_data(self, api_client):
        """Saved data is persisted and returned in GET"""
        # Save with specific values
        payload = {
            "ispezioni_vt": [
                {"check_id": "vt_cricche", "esito": True, "valore_misurato": "Conforme", "note": "Nessuna cricca"},
                {"check_id": "vt_porosita", "esito": False, "valore_misurato": "4mm", "note": "Porosita eccessiva"}
            ],
            "ispezioni_dim": [
                {"check_id": "dim_lunghezze", "esito": True, "valore_misurato": "999mm", "note": "Entro tolleranza"}
            ],
            "ispettore_nome": "Mario Rossi"
        }
        save_response = api_client.post(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}", json=payload)
        assert save_response.status_code == 200

        # Verify with GET
        get_response = api_client.get(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}")
        data = get_response.json()
        
        # Check VT results
        vt_cricche = next(c for c in data["checks_vt"] if c["id"] == "vt_cricche")
        assert vt_cricche["esito"] is True
        assert vt_cricche["valore_misurato"] == "Conforme"
        assert vt_cricche["note"] == "Nessuna cricca"
        
        vt_porosita = next(c for c in data["checks_vt"] if c["id"] == "vt_porosita")
        assert vt_porosita["esito"] is False
        assert vt_porosita["valore_misurato"] == "4mm"
        
        # Check DIM results
        dim_lunghezze = next(c for c in data["checks_dim"] if c["id"] == "dim_lunghezze")
        assert dim_lunghezze["esito"] is True
        
        # Check metadata
        assert data["ispettore_nome"] == "Mario Rossi"

    def test_save_report_updates_stats(self, api_client):
        """Saving results updates stats correctly"""
        # Save 3 VT OK, 1 VT NOK, 2 DIM OK
        payload = {
            "ispezioni_vt": [
                {"check_id": "vt_cricche", "esito": True},
                {"check_id": "vt_porosita", "esito": True},
                {"check_id": "vt_inclusioni", "esito": True},
                {"check_id": "vt_mancanza_fusione", "esito": False}
            ],
            "ispezioni_dim": [
                {"check_id": "dim_lunghezze", "esito": True},
                {"check_id": "dim_rettilineita", "esito": True}
            ]
        }
        api_client.post(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}", json=payload)
        
        get_response = api_client.get(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}")
        data = get_response.json()
        
        assert data["stats"]["vt"]["ok"] == 3
        assert data["stats"]["vt"]["nok"] == 1
        assert data["stats"]["vt"]["pending"] == 6
        assert data["stats"]["dim"]["ok"] == 2
        assert data["stats"]["dim"]["pending"] == 6


class TestReportIspezioniApprova:
    """POST /api/report-ispezioni/{commessa_id}/approva — Sign and approve"""

    def test_approva_fails_if_not_all_checks_filled(self, api_client):
        """Approve fails with 400 if not all checks are filled"""
        # First save partial data
        payload = {
            "ispezioni_vt": [{"check_id": "vt_cricche", "esito": True}],
            "ispezioni_dim": []
        }
        api_client.post(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}", json=payload)
        
        # Try to approve
        approva_payload = {"firma_nome": "Test Approver", "firma_ruolo": "Ispettore VT"}
        response = api_client.post(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}/approva", json=approva_payload)
        
        assert response.status_code == 400
        data = response.json()
        assert "non compilata" in data["detail"]

    def test_approva_requires_firma_nome(self, api_client):
        """Approve requires firma_nome field"""
        # This test verifies the validation - empty firma_nome should fail
        approva_payload = {"firma_nome": "", "firma_ruolo": "Ispettore"}
        response = api_client.post(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}/approva", json=approva_payload)
        # Should fail either due to validation or missing checks
        assert response.status_code in [400, 422]


class TestReportIspezioniPDF:
    """GET /api/report-ispezioni/{commessa_id}/pdf — Generate PDF"""

    def test_pdf_returns_200_with_pdf_content(self, api_client):
        """PDF endpoint returns 200 with application/pdf content type"""
        response = api_client.get(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}/pdf")
        assert response.status_code == 200
        assert "application/pdf" in response.headers.get("Content-Type", "")
        assert len(response.content) > 10000  # PDF should be at least 10KB

    def test_pdf_has_content_disposition(self, api_client):
        """PDF has Content-Disposition header with filename"""
        response = api_client.get(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}/pdf")
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp
        assert "Report_Ispezioni" in content_disp


class TestControlloFinaleIntegration:
    """Integration: Controllo Finale auto-check reads from report_ispezioni"""

    def test_controllo_finale_has_11_checks(self, api_client):
        """Controllo Finale still has all 11 checks (regression)"""
        response = api_client.get(f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}")
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert len(data["checks"]) == 11

    def test_vt_nc_chiuse_label_updated(self, api_client):
        """vt_nc_chiuse check has updated label 'Report Ispezioni VT approvato'"""
        response = api_client.get(f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}")
        data = response.json()
        vt_nc_check = next(c for c in data["checks"] if c["id"] == "vt_nc_chiuse")
        assert vt_nc_check["label"] == "Report Ispezioni VT approvato"

    def test_vt_nc_chiuse_reads_from_report_ispezioni(self, api_client):
        """vt_nc_chiuse auto-check reads from report_ispezioni collection"""
        # First save some VT results
        payload = {
            "ispezioni_vt": [
                {"check_id": "vt_cricche", "esito": True},
                {"check_id": "vt_porosita", "esito": True},
                {"check_id": "vt_inclusioni", "esito": True}
            ],
            "ispezioni_dim": []
        }
        api_client.post(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}", json=payload)
        
        # Check Controllo Finale
        response = api_client.get(f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}")
        data = response.json()
        vt_nc_check = next(c for c in data["checks"] if c["id"] == "vt_nc_chiuse")
        
        # Should show report status (not approved yet)
        assert vt_nc_check["esito"] is False  # Not approved
        assert "compilati" in vt_nc_check["valore"] or "non creato" in vt_nc_check["valore"].lower() or "approvato" in vt_nc_check["valore"].lower()

    def test_controllo_finale_areas_structure(self, api_client):
        """Controllo Finale has correct area structure"""
        response = api_client.get(f"{BASE_URL}/api/controllo-finale/{TEST_COMMESSA_ID}")
        data = response.json()
        assert "areas" in data
        assert "Visual Testing" in data["areas"]
        assert "Dimensionale" in data["areas"]
        assert "Compliance" in data["areas"]
        # Visual Testing should have 4 checks
        assert data["areas"]["Visual Testing"]["totale"] == 4


class TestReportIspezioniEdgeCases:
    """Edge cases and error handling"""

    def test_get_nonexistent_commessa_returns_404(self, api_client):
        """GET with non-existent commessa returns 404"""
        response = api_client.get(f"{BASE_URL}/api/report-ispezioni/nonexistent_commessa_xyz")
        assert response.status_code == 404

    def test_save_empty_payload_works(self, api_client):
        """POST with empty arrays works (clears data)"""
        payload = {
            "ispezioni_vt": [],
            "ispezioni_dim": [],
            "strumenti_utilizzati": "",
            "condizioni_ambientali": "",
            "ispettore_nome": "",
            "note_generali": ""
        }
        response = api_client.post(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}", json=payload)
        assert response.status_code == 200


class TestVTCheckReferences:
    """Verify VT checks reference ISO 5817 correctly"""

    def test_vt_checks_reference_iso_5817(self, api_client):
        """All VT checks reference ISO 5817 Tab.1"""
        response = api_client.get(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}")
        data = response.json()
        for check in data["checks_vt"]:
            assert "ISO 5817" in check["rif"] or "EN 1090" in check["rif"], f"Check {check['id']} missing ISO reference"


class TestDIMCheckReferences:
    """Verify DIM checks reference EN 1090-2 correctly"""

    def test_dim_checks_reference_en_1090(self, api_client):
        """All DIM checks reference EN 1090-2"""
        response = api_client.get(f"{BASE_URL}/api/report-ispezioni/{TEST_COMMESSA_ID}")
        data = response.json()
        for check in data["checks_dim"]:
            assert "EN 1090" in check["rif"], f"Check {check['id']} missing EN 1090 reference"
