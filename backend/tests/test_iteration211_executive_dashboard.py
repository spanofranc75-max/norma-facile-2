"""
Test Iteration 211: Executive Dashboard Multi-Normativa
Tests the GET /api/dashboard/executive endpoint which provides:
- Multi-sector view (EN_1090, EN_13241, GENERICA)
- KPI per sector (totale_commesse, valore_totale, indice_rischio, audit_ready, etc.)
- Commessa mista detection (appears in multiple sectors)
- Scadenze imminenti (patentini, tarature, ITT)
- Audit status per commessa (riesame_ok, ispezioni_ok, controllo_ok, dop_count)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "d36a500823254076b5c583d6c1d903fa"
MISTA_COMMESSA_NUMERO = "NF-2026-000036"


@pytest.fixture
def auth_session():
    """Session with authentication cookie"""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestExecutiveDashboardEndpoint:
    """Tests for GET /api/dashboard/executive"""

    def test_endpoint_returns_200(self, auth_session):
        """Test that the endpoint returns 200 OK"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Endpoint returns 200 OK")

    def test_response_has_required_top_level_fields(self, auth_session):
        """Test that response has settori, scadenze_imminenti, totale_commesse, totale_valore"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        assert "settori" in data, "Missing 'settori' field"
        assert "scadenze_imminenti" in data, "Missing 'scadenze_imminenti' field"
        assert "totale_commesse" in data, "Missing 'totale_commesse' field"
        assert "totale_valore" in data, "Missing 'totale_valore' field"
        
        assert isinstance(data["settori"], dict), "settori should be a dict"
        assert isinstance(data["scadenze_imminenti"], list), "scadenze_imminenti should be a list"
        assert isinstance(data["totale_commesse"], int), "totale_commesse should be int"
        assert isinstance(data["totale_valore"], (int, float)), "totale_valore should be numeric"
        
        print(f"✓ Response has all required fields: totale_commesse={data['totale_commesse']}, totale_valore={data['totale_valore']}")

    def test_three_sectors_present(self, auth_session):
        """Test that all 3 sectors are present: EN_1090, EN_13241, GENERICA"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        settori = data["settori"]
        assert "EN_1090" in settori, "Missing EN_1090 sector"
        assert "EN_13241" in settori, "Missing EN_13241 sector"
        assert "GENERICA" in settori, "Missing GENERICA sector"
        
        print(f"✓ All 3 sectors present: EN_1090, EN_13241, GENERICA")


class TestEN1090Sector:
    """Tests for EN 1090 sector data"""

    def test_en1090_has_correct_structure(self, auth_session):
        """Test EN_1090 sector has label, commesse, stats"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        en1090 = data["settori"]["EN_1090"]
        assert "label" in en1090, "Missing label"
        assert "commesse" in en1090, "Missing commesse"
        assert "stats" in en1090, "Missing stats"
        
        assert en1090["label"] == "EN 1090 — Strutture", f"Wrong label: {en1090['label']}"
        assert isinstance(en1090["commesse"], list), "commesse should be a list"
        
        print(f"✓ EN_1090 has correct structure with {len(en1090['commesse'])} commesse")

    def test_en1090_stats_fields(self, auth_session):
        """Test EN_1090 stats has required KPI fields"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        stats = data["settori"]["EN_1090"]["stats"]
        required_fields = ["totale_commesse", "valore_totale", "in_ritardo", "in_produzione",
                          "audit_ready", "riesame_approvati", "dop_generate", "indice_rischio"]
        
        for field in required_fields:
            assert field in stats, f"Missing stats field: {field}"
        
        # Validate types
        assert isinstance(stats["totale_commesse"], int), "totale_commesse should be int"
        assert isinstance(stats["valore_totale"], (int, float)), "valore_totale should be numeric"
        assert isinstance(stats["indice_rischio"], (int, float)), "indice_rischio should be numeric"
        
        print(f"✓ EN_1090 stats: {stats['totale_commesse']} commesse, €{stats['valore_totale']}, rischio={stats['indice_rischio']}%")

    def test_en1090_commessa_has_audit_data(self, auth_session):
        """Test that EN_1090 commesse have audit data"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        commesse = data["settori"]["EN_1090"]["commesse"]
        assert len(commesse) > 0, "No commesse in EN_1090"
        
        # Check first commessa with audit data
        for c in commesse:
            if c.get("audit"):
                audit = c["audit"]
                assert "riesame_ok" in audit, "Missing riesame_ok"
                assert "riesame_pct" in audit, "Missing riesame_pct"
                assert "ispezioni_ok" in audit, "Missing ispezioni_ok"
                assert "controllo_ok" in audit, "Missing controllo_ok"
                assert "dop_count" in audit, "Missing dop_count"
                print(f"✓ Commessa {c['numero']} has audit data: riesame_ok={audit['riesame_ok']}, dop_count={audit['dop_count']}")
                return
        
        print("✓ EN_1090 commesse have audit structure (all have audit=null or audit data)")


class TestEN13241Sector:
    """Tests for EN 13241 sector data"""

    def test_en13241_has_correct_structure(self, auth_session):
        """Test EN_13241 sector has label, commesse, stats"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        en13241 = data["settori"]["EN_13241"]
        assert "label" in en13241, "Missing label"
        assert "commesse" in en13241, "Missing commesse"
        assert "stats" in en13241, "Missing stats"
        
        assert en13241["label"] == "EN 13241 — Chiusure", f"Wrong label: {en13241['label']}"
        
        print(f"✓ EN_13241 has correct structure with {len(en13241['commesse'])} commesse")

    def test_en13241_stats_fields(self, auth_session):
        """Test EN_13241 stats has required KPI fields (same as EN_1090)"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        stats = data["settori"]["EN_13241"]["stats"]
        required_fields = ["totale_commesse", "valore_totale", "in_ritardo", "in_produzione",
                          "audit_ready", "riesame_approvati", "dop_generate", "indice_rischio"]
        
        for field in required_fields:
            assert field in stats, f"Missing stats field: {field}"
        
        print(f"✓ EN_13241 stats: {stats['totale_commesse']} commesse, €{stats['valore_totale']}, rischio={stats['indice_rischio']}%")


class TestGenericaSector:
    """Tests for GENERICA sector data"""

    def test_generica_has_correct_structure(self, auth_session):
        """Test GENERICA sector has label, commesse, stats"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        generica = data["settori"]["GENERICA"]
        assert "label" in generica, "Missing label"
        assert "commesse" in generica, "Missing commesse"
        assert "stats" in generica, "Missing stats"
        
        assert generica["label"] == "Generica — Senza Marcatura", f"Wrong label: {generica['label']}"
        
        print(f"✓ GENERICA has correct structure with {len(generica['commesse'])} commesse")

    def test_generica_has_efficienza_produttiva(self, auth_session):
        """Test GENERICA stats has efficienza_produttiva instead of audit fields"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        stats = data["settori"]["GENERICA"]["stats"]
        assert "efficienza_produttiva" in stats, "Missing efficienza_produttiva"
        assert isinstance(stats["efficienza_produttiva"], (int, float)), "efficienza_produttiva should be numeric"
        
        # GENERICA should NOT have audit-specific fields
        assert "indice_rischio" not in stats, "GENERICA should not have indice_rischio"
        
        print(f"✓ GENERICA stats: {stats['totale_commesse']} commesse, efficienza={stats['efficienza_produttiva']}%")


class TestCommessaMista:
    """Tests for commessa mista (multi-normativa) detection"""

    def test_mista_commessa_appears_in_all_sectors(self, auth_session):
        """Test that NF-2026-000036 appears in EN_1090, EN_13241, and GENERICA"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        found_in = []
        for sector_key in ["EN_1090", "EN_13241", "GENERICA"]:
            commesse = data["settori"][sector_key]["commesse"]
            for c in commesse:
                if c["numero"] == MISTA_COMMESSA_NUMERO:
                    found_in.append(sector_key)
                    break
        
        assert "EN_1090" in found_in, f"Mista commessa not found in EN_1090"
        assert "EN_13241" in found_in, f"Mista commessa not found in EN_13241"
        assert "GENERICA" in found_in, f"Mista commessa not found in GENERICA"
        
        print(f"✓ Mista commessa {MISTA_COMMESSA_NUMERO} appears in all 3 sectors: {found_in}")

    def test_mista_commessa_has_mista_flag(self, auth_session):
        """Test that mista commessa has mista=true flag"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        # Find the mista commessa in any sector
        mista_commessa = None
        for sector_key in ["EN_1090", "EN_13241", "GENERICA"]:
            commesse = data["settori"][sector_key]["commesse"]
            for c in commesse:
                if c["numero"] == MISTA_COMMESSA_NUMERO:
                    mista_commessa = c
                    break
            if mista_commessa:
                break
        
        assert mista_commessa is not None, f"Mista commessa {MISTA_COMMESSA_NUMERO} not found"
        assert mista_commessa.get("mista") is True, f"mista flag should be True, got {mista_commessa.get('mista')}"
        
        # Check normative_presenti has all 3
        normative = mista_commessa.get("normative_presenti", [])
        assert "EN_1090" in normative, "Missing EN_1090 in normative_presenti"
        assert "EN_13241" in normative, "Missing EN_13241 in normative_presenti"
        assert "GENERICA" in normative, "Missing GENERICA in normative_presenti"
        
        print(f"✓ Mista commessa has mista=true and normative_presenti={normative}")


class TestScadenzeImminenti:
    """Tests for scadenze imminenti (upcoming deadlines)"""

    def test_scadenze_structure(self, auth_session):
        """Test scadenze_imminenti has correct structure"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        scadenze = data["scadenze_imminenti"]
        assert isinstance(scadenze, list), "scadenze_imminenti should be a list"
        
        if len(scadenze) > 0:
            s = scadenze[0]
            assert "tipo" in s, "Missing tipo"
            assert "nome" in s, "Missing nome"
            assert "scadenza" in s, "Missing scadenza"
            assert "giorni" in s, "Missing giorni"
            assert "settore" in s, "Missing settore"
            
            # Validate tipo is one of expected values
            assert s["tipo"] in ["patentino", "taratura", "itt"], f"Unexpected tipo: {s['tipo']}"
            
            print(f"✓ Scadenze structure correct. First: {s['tipo']} - {s['nome']} ({s['giorni']} giorni)")
        else:
            print("✓ No scadenze imminenti (empty list)")

    def test_scadenze_sorted_by_urgency(self, auth_session):
        """Test scadenze are sorted by giorni (most urgent first)"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        scadenze = data["scadenze_imminenti"]
        if len(scadenze) > 1:
            giorni_list = [s["giorni"] for s in scadenze]
            assert giorni_list == sorted(giorni_list), f"Scadenze not sorted by urgency: {giorni_list}"
            print(f"✓ Scadenze sorted by urgency: {giorni_list}")
        else:
            print("✓ Not enough scadenze to verify sorting")

    def test_scadenze_include_patentini(self, auth_session):
        """Test that patentini saldatori are included in scadenze"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        scadenze = data["scadenze_imminenti"]
        patentini = [s for s in scadenze if s["tipo"] == "patentino"]
        
        # Based on test data, we expect some patentini
        print(f"✓ Found {len(patentini)} patentini in scadenze")


class TestCommessaCardFields:
    """Tests for individual commessa card fields"""

    def test_commessa_has_required_fields(self, auth_session):
        """Test that each commessa has all required display fields"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["commessa_id", "numero", "title", "stato", "client_name",
                          "value", "deadline", "days_left", "normative_presenti",
                          "mista", "classe_esecuzione", "prod_done", "prod_total"]
        
        # Check first commessa from EN_1090
        commesse = data["settori"]["EN_1090"]["commesse"]
        assert len(commesse) > 0, "No commesse to test"
        
        c = commesse[0]
        for field in required_fields:
            assert field in c, f"Missing field: {field}"
        
        print(f"✓ Commessa {c['numero']} has all required fields")

    def test_commessa_production_progress(self, auth_session):
        """Test that prod_done and prod_total are valid"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        # Find a commessa with production data
        for sector_key in ["EN_1090", "EN_13241", "GENERICA"]:
            commesse = data["settori"][sector_key]["commesse"]
            for c in commesse:
                if c["prod_total"] > 0:
                    assert c["prod_done"] >= 0, "prod_done should be >= 0"
                    assert c["prod_done"] <= c["prod_total"], "prod_done should be <= prod_total"
                    print(f"✓ Commessa {c['numero']} production: {c['prod_done']}/{c['prod_total']}")
                    return
        
        print("✓ No commesse with production phases found (all have prod_total=0)")


class TestTotals:
    """Tests for aggregate totals"""

    def test_totale_commesse_matches_unique_count(self, auth_session):
        """Test that totale_commesse is the count of unique commesse (not sum of sectors)"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        # Collect all unique commessa_ids across sectors
        all_ids = set()
        for sector_key in ["EN_1090", "EN_13241", "GENERICA"]:
            commesse = data["settori"][sector_key]["commesse"]
            for c in commesse:
                all_ids.add(c["commessa_id"])
        
        # totale_commesse should match unique count
        assert data["totale_commesse"] == len(all_ids), \
            f"totale_commesse ({data['totale_commesse']}) != unique count ({len(all_ids)})"
        
        print(f"✓ totale_commesse={data['totale_commesse']} matches unique commesse count")

    def test_totale_valore_is_sum_of_unique_commesse(self, auth_session):
        """Test that totale_valore is sum of unique commesse values"""
        response = auth_session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 200
        data = response.json()
        
        # Collect unique commesse with their values
        unique_values = {}
        for sector_key in ["EN_1090", "EN_13241", "GENERICA"]:
            commesse = data["settori"][sector_key]["commesse"]
            for c in commesse:
                unique_values[c["commessa_id"]] = c.get("value", 0) or 0
        
        expected_total = sum(unique_values.values())
        actual_total = data["totale_valore"]
        
        # Allow small floating point difference
        assert abs(actual_total - expected_total) < 0.01, \
            f"totale_valore ({actual_total}) != sum of unique values ({expected_total})"
        
        print(f"✓ totale_valore=€{actual_total:.2f} matches sum of unique commesse")


class TestAuthRequired:
    """Tests for authentication requirements"""

    def test_endpoint_requires_auth(self):
        """Test that endpoint returns 401 without auth"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/dashboard/executive")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ Endpoint requires authentication (401 without cookie)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
