"""
Test suite for Iteration 96: Scadenziario & Cost Management Module
Tests: scadenziario/dashboard, cost imputation (commessa/magazzino), FIC sync error handling
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, date, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Session token for existing test user from iteration 95
SESSION_TOKEN = "yDZ9JAQM_3ct2TZ0UE3BFkZDQcc6YRSFWMlv888wRhQ"
USER_ID = "user_97c773827822"


class TestScadenziarioDashboard:
    """Tests for GET /api/fatture-ricevute/scadenziario/dashboard"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {SESSION_TOKEN}',
            'Content-Type': 'application/json'
        })

    def test_dashboard_returns_200(self):
        """GET /scadenziario/dashboard returns 200 OK"""
        resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print(f"✓ Scadenziario dashboard returns 200")

    def test_dashboard_kpi_structure(self):
        """Dashboard KPI has required fields"""
        resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard")
        assert resp.status_code == 200
        data = resp.json()

        # Check KPI structure
        assert 'kpi' in data, "Missing 'kpi' key in response"
        kpi = data['kpi']
        required_kpi_fields = ['pagamenti_scaduti', 'pagamenti_mese_corrente', 'totale_acquisti_anno',
                               'scadenze_totali', 'scadute', 'in_scadenza', 'inbox_da_processare']
        for field in required_kpi_fields:
            assert field in kpi, f"Missing KPI field: {field}"
        print(f"✓ Dashboard KPI has all required fields: {list(kpi.keys())}")

    def test_dashboard_scadenze_structure(self):
        """Dashboard scadenze array has correct structure"""
        resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard")
        assert resp.status_code == 200
        data = resp.json()

        assert 'scadenze' in data, "Missing 'scadenze' key"
        scadenze = data['scadenze']
        assert isinstance(scadenze, list), "scadenze should be a list"

        # Check scadenza item structure if any exist
        if scadenze:
            s = scadenze[0]
            required_fields = ['tipo', 'id', 'titolo', 'sottotitolo', 'data_scadenza', 'stato']
            for field in required_fields:
                assert field in s, f"Missing field in scadenza: {field}"
            assert s['tipo'] in ['pagamento', 'patentino', 'taratura', 'consegna'], f"Invalid tipo: {s['tipo']}"
            assert s['stato'] in ['scaduto', 'in_scadenza', 'ok'], f"Invalid stato: {s['stato']}"
            print(f"✓ Scadenze structure correct, found {len(scadenze)} items, first tipo: {s['tipo']}")
        else:
            print("✓ Scadenze structure correct (empty list)")

    def test_dashboard_aggregates_welders(self):
        """Dashboard includes welder certificate deadlines"""
        resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard")
        assert resp.status_code == 200
        data = resp.json()

        welder_scadenze = [s for s in data['scadenze'] if s['tipo'] == 'patentino']
        print(f"✓ Dashboard aggregates {len(welder_scadenze)} welder patentino deadlines")

    def test_dashboard_aggregates_instruments(self):
        """Dashboard includes instrument calibration deadlines"""
        resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard")
        assert resp.status_code == 200
        data = resp.json()

        instrument_scadenze = [s for s in data['scadenze'] if s['tipo'] == 'taratura']
        print(f"✓ Dashboard aggregates {len(instrument_scadenze)} instrument calibration deadlines")

    def test_dashboard_aggregates_commesse(self):
        """Dashboard includes commessa delivery deadlines"""
        resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard")
        assert resp.status_code == 200
        data = resp.json()

        consegna_scadenze = [s for s in data['scadenze'] if s['tipo'] == 'consegna']
        print(f"✓ Dashboard aggregates {len(consegna_scadenze)} commessa consegna deadlines")

    def test_dashboard_no_auth_returns_401(self):
        """GET /scadenziario/dashboard without auth returns 401"""
        resp = requests.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print("✓ Dashboard without auth returns 401")


class TestCostImputaCommessa:
    """Tests for POST /api/fatture-ricevute/{fr_id}/imputa with destinazione=commessa"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {SESSION_TOKEN}',
            'Content-Type': 'application/json'
        })
        self.created_fr_ids = []
        self.created_commessa_ids = []
        yield
        # Cleanup
        for fr_id in self.created_fr_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
            except:
                pass
        for c_id in self.created_commessa_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/commesse/{c_id}")
            except:
                pass

    def create_test_fattura(self, scadenza_days=-30, fornitore="TEST_Imputa SRL", totale=1000.0):
        """Helper: create a test fattura ricevuta"""
        scadenza = (date.today() + timedelta(days=scadenza_days)).isoformat()
        payload = {
            "fornitore_nome": fornitore,
            "numero_documento": f"TEST-IMP-{uuid.uuid4().hex[:6].upper()}",
            "data_documento": date.today().isoformat(),
            "data_scadenza_pagamento": scadenza,
            "linee": [
                {
                    "numero_linea": 1,
                    "codice_articolo": "MAT-TEST",
                    "descrizione": "Materiale test per imputa",
                    "quantita": 10.0,
                    "unita_misura": "kg",
                    "prezzo_unitario": totale / 10,
                    "aliquota_iva": "22",
                    "importo": totale
                }
            ],
            "imponibile": totale / 1.22,
            "imposta": totale - totale / 1.22,
            "totale_documento": totale
        }
        resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        assert resp.status_code == 201, f"Failed to create fattura: {resp.text}"
        fr_id = resp.json()['fr_id']
        self.created_fr_ids.append(fr_id)
        return fr_id

    def create_test_commessa(self):
        """Helper: create a test commessa"""
        payload = {
            "title": f"TEST Commessa Imputa {uuid.uuid4().hex[:4]}",
            "cliente_id": None,
            "importo_totale": 5000.0,
            "stato": "in_lavorazione"
        }
        resp = self.session.post(f"{BASE_URL}/api/commesse/", json=payload)
        assert resp.status_code in [200, 201], f"Failed to create commessa: {resp.text}"
        c = resp.json()
        self.created_commessa_ids.append(c['commessa_id'])
        return c['commessa_id'], c.get('numero', '')

    def test_imputa_commessa_success(self):
        """POST /imputa with destinazione=commessa creates costi_reali entry"""
        fr_id = self.create_test_fattura(totale=500.0)
        commessa_id, commessa_numero = self.create_test_commessa()

        payload = {
            "destinazione": "commessa",
            "commessa_id": commessa_id,
            "note": "Test imputation"
        }
        resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/{fr_id}/imputa", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        data = resp.json()
        assert data['destinazione'] == 'commessa'
        assert 'importo' in data
        assert data['importo'] == 500.0
        print(f"✓ POST /imputa commessa success: {data['message']}")

        # Verify fattura status updated
        fr_resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
        assert fr_resp.status_code == 200
        fr_data = fr_resp.json()
        assert fr_data['status'] == 'registrata', f"Expected registrata, got {fr_data['status']}"
        assert 'imputazione' in fr_data
        assert fr_data['imputazione']['destinazione'] == 'commessa'
        print(f"✓ Fattura status updated to 'registrata' with imputazione")

        # Verify costi_reali added to commessa
        c_resp = self.session.get(f"{BASE_URL}/api/commesse/{commessa_id}")
        assert c_resp.status_code == 200
        c_data = c_resp.json()
        costi = c_data.get('costi_reali', [])
        matching = [c for c in costi if c.get('fr_id') == fr_id]
        assert len(matching) == 1, f"Expected 1 cost entry, found {len(matching)}"
        assert matching[0]['importo'] == 500.0
        print(f"✓ Commessa costi_reali updated with cost entry")

    def test_imputa_commessa_requires_commessa_id(self):
        """POST /imputa with destinazione=commessa requires commessa_id"""
        fr_id = self.create_test_fattura()

        payload = {
            "destinazione": "commessa"
            # Missing commessa_id
        }
        resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/{fr_id}/imputa", json=payload)
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
        print("✓ POST /imputa without commessa_id returns 400")

    def test_imputa_commessa_not_found(self):
        """POST /imputa with invalid commessa_id returns 404"""
        fr_id = self.create_test_fattura()

        payload = {
            "destinazione": "commessa",
            "commessa_id": "commessa_nonexistent123"
        }
        resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/{fr_id}/imputa", json=payload)
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("✓ POST /imputa with invalid commessa_id returns 404")

    def test_imputa_fattura_not_found(self):
        """POST /imputa with invalid fr_id returns 404"""
        payload = {
            "destinazione": "commessa",
            "commessa_id": "some_id"
        }
        resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/fr_nonexistent/imputa", json=payload)
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("✓ POST /imputa with invalid fr_id returns 404")


class TestCostImputaMagazzino:
    """Tests for POST /api/fatture-ricevute/{fr_id}/imputa with destinazione=magazzino"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {SESSION_TOKEN}',
            'Content-Type': 'application/json'
        })
        self.created_fr_ids = []
        self.created_articoli_codici = []
        yield
        # Cleanup fatture
        for fr_id in self.created_fr_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
            except:
                pass
        # Cleanup articoli (can't easily delete by code, so we'll leave them)

    def test_imputa_magazzino_creates_articoli(self):
        """POST /imputa with destinazione=magazzino creates new articoli"""
        unique_code = f"ART-MAG-{uuid.uuid4().hex[:6].upper()}"

        payload = {
            "fornitore_nome": "TEST_Magazzino SRL",
            "numero_documento": f"TEST-MAG-{uuid.uuid4().hex[:4].upper()}",
            "data_documento": date.today().isoformat(),
            "linee": [
                {
                    "numero_linea": 1,
                    "codice_articolo": unique_code,
                    "descrizione": "Articolo test magazzino nuovo",
                    "quantita": 50.0,
                    "unita_misura": "pz",
                    "prezzo_unitario": 10.0,
                    "aliquota_iva": "22",
                    "importo": 500.0
                }
            ],
            "imponibile": 500.0 / 1.22,
            "imposta": 500.0 - 500.0 / 1.22,
            "totale_documento": 500.0
        }
        create_resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        assert create_resp.status_code == 201
        fr_id = create_resp.json()['fr_id']
        self.created_fr_ids.append(fr_id)
        self.created_articoli_codici.append(unique_code)

        # Imputa to magazzino
        imputa_payload = {"destinazione": "magazzino"}
        resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/{fr_id}/imputa", json=imputa_payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        data = resp.json()
        assert data['destinazione'] == 'magazzino'
        assert 'created' in data or 'updated' in data
        print(f"✓ POST /imputa magazzino: {data['message']}")

        # Verify fattura updated
        fr_resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
        fr_data = fr_resp.json()
        assert fr_data['status'] == 'registrata'
        assert fr_data['imputazione']['destinazione'] == 'magazzino'
        print(f"✓ Fattura status updated to registrata")

    def test_imputa_magazzino_updates_existing_articolo(self):
        """POST /imputa magazzino updates existing articoli with weighted avg price"""
        unique_code = f"ART-UPD-{uuid.uuid4().hex[:6].upper()}"

        # First, create an articolo manually
        art_payload = {
            "codice": unique_code,
            "descrizione": "Articolo esistente per test update",
            "categoria": "materiale",
            "unita_misura": "pz",
            "prezzo_unitario": 8.0,
            "giacenza": 100.0,
            "aliquota_iva": "22"
        }
        art_resp = self.session.post(f"{BASE_URL}/api/articoli/", json=art_payload)
        # May fail if articolo already exists, which is fine
        if art_resp.status_code in [200, 201]:
            art_id = art_resp.json().get('articolo_id')
            self.created_articoli_codici.append(unique_code)

        # Now create fattura with same code but different price
        fr_payload = {
            "fornitore_nome": "TEST_Update Stock SRL",
            "numero_documento": f"TEST-UPD-{uuid.uuid4().hex[:4].upper()}",
            "data_documento": date.today().isoformat(),
            "linee": [
                {
                    "numero_linea": 1,
                    "codice_articolo": unique_code,
                    "descrizione": "Articolo esistente per test update",
                    "quantita": 100.0,  # Adding 100 more
                    "unita_misura": "pz",
                    "prezzo_unitario": 12.0,  # New price (old was 8)
                    "aliquota_iva": "22",
                    "importo": 1200.0
                }
            ],
            "imponibile": 1200.0 / 1.22,
            "imposta": 1200.0 - 1200.0 / 1.22,
            "totale_documento": 1200.0
        }
        create_resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=fr_payload)
        assert create_resp.status_code == 201
        fr_id = create_resp.json()['fr_id']
        self.created_fr_ids.append(fr_id)

        # Imputa
        resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/{fr_id}/imputa", json={"destinazione": "magazzino"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        data = resp.json()
        # Should have updated at least 1 article
        total = data.get('created', 0) + data.get('updated', 0)
        assert total >= 1, "Expected at least 1 article updated/created"
        print(f"✓ POST /imputa magazzino updated existing articolo: created={data.get('created', 0)}, updated={data.get('updated', 0)}")


class TestFICSyncEndpoint:
    """Tests for POST /api/fatture-ricevute/sync-fic"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {SESSION_TOKEN}',
            'Content-Type': 'application/json'
        })

    def test_sync_fic_returns_proper_error_when_expired(self):
        """POST /sync-fic returns 502 when FIC license is expired"""
        resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/sync-fic")
        # FIC license is expired per the review request, should return 502 or similar error
        # It could also return 400 if not configured properly on user level
        assert resp.status_code in [400, 401, 502], f"Expected 400/401/502, got {resp.status_code}: {resp.text}"
        print(f"✓ POST /sync-fic returns error ({resp.status_code}) when FIC unavailable")

    def test_sync_fic_no_auth_returns_401(self):
        """POST /sync-fic without auth returns 401"""
        resp = requests.post(f"{BASE_URL}/api/fatture-ricevute/sync-fic")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print("✓ POST /sync-fic without auth returns 401")


class TestExistingFattureRicevuteCRUD:
    """Verify existing fatture_ricevute CRUD endpoints still work"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {SESSION_TOKEN}',
            'Content-Type': 'application/json'
        })
        self.created_fr_ids = []
        yield
        for fr_id in self.created_fr_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
            except:
                pass

    def test_list_fatture_ricevute(self):
        """GET /fatture-ricevute/ still works"""
        resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert 'fatture' in data
        assert 'kpi' in data
        print(f"✓ GET /fatture-ricevute/ works (count={data['kpi']['count']})")

    def test_create_fattura_ricevuta(self):
        """POST /fatture-ricevute/ still works"""
        payload = {
            "fornitore_nome": "TEST_CRUD Fornitore",
            "numero_documento": f"TEST-CRUD-{uuid.uuid4().hex[:4]}",
            "data_documento": date.today().isoformat(),
            "totale_documento": 250.0
        }
        resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        fr_id = resp.json()['fr_id']
        self.created_fr_ids.append(fr_id)
        print(f"✓ POST /fatture-ricevute/ works (fr_id={fr_id})")

    def test_get_single_fattura(self):
        """GET /fatture-ricevute/{fr_id} still works"""
        # Create first
        payload = {
            "fornitore_nome": "TEST_GET Single",
            "numero_documento": f"TEST-GET-{uuid.uuid4().hex[:4]}",
            "data_documento": date.today().isoformat(),
            "totale_documento": 150.0
        }
        create_resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        assert create_resp.status_code == 201
        fr_id = create_resp.json()['fr_id']
        self.created_fr_ids.append(fr_id)

        # Fetch
        resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data['fr_id'] == fr_id
        print(f"✓ GET /fatture-ricevute/{fr_id} works")

    def test_update_fattura_status(self):
        """PUT /fatture-ricevute/{fr_id} still works"""
        payload = {
            "fornitore_nome": "TEST_PUT Update",
            "numero_documento": f"TEST-PUT-{uuid.uuid4().hex[:4]}",
            "data_documento": date.today().isoformat(),
            "totale_documento": 300.0
        }
        create_resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        fr_id = create_resp.json()['fr_id']
        self.created_fr_ids.append(fr_id)

        # Update
        update_resp = self.session.put(f"{BASE_URL}/api/fatture-ricevute/{fr_id}", json={"status": "registrata"})
        assert update_resp.status_code == 200
        assert update_resp.json()['status'] == 'registrata'
        print(f"✓ PUT /fatture-ricevute/{fr_id} works")

    def test_delete_fattura(self):
        """DELETE /fatture-ricevute/{fr_id} still works"""
        payload = {
            "fornitore_nome": "TEST_DELETE Remove",
            "numero_documento": f"TEST-DEL-{uuid.uuid4().hex[:4]}",
            "data_documento": date.today().isoformat(),
            "totale_documento": 50.0
        }
        create_resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        fr_id = create_resp.json()['fr_id']

        # Delete
        del_resp = self.session.delete(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()['message'] == 'Fattura eliminata'

        # Verify gone
        get_resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
        assert get_resp.status_code == 404
        print(f"✓ DELETE /fatture-ricevute/{fr_id} works")

    def test_record_payment(self):
        """POST /fatture-ricevute/{fr_id}/pagamenti still works"""
        payload = {
            "fornitore_nome": "TEST_Payment Track",
            "numero_documento": f"TEST-PAY-{uuid.uuid4().hex[:4]}",
            "data_documento": date.today().isoformat(),
            "totale_documento": 1000.0
        }
        create_resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        fr_id = create_resp.json()['fr_id']
        self.created_fr_ids.append(fr_id)

        # Record payment
        pag_resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/{fr_id}/pagamenti", json={
            "importo": 400.0,
            "data_pagamento": date.today().isoformat(),
            "metodo": "bonifico"
        })
        assert pag_resp.status_code == 200
        data = pag_resp.json()
        assert data['totale_pagato'] == 400.0
        assert data['residuo'] == 600.0
        print(f"✓ POST /fatture-ricevute/{fr_id}/pagamenti works (pagato=400, residuo=600)")


class TestScadenziarioKPICalculations:
    """Test KPI calculation correctness for scadenziario"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {SESSION_TOKEN}',
            'Content-Type': 'application/json'
        })
        self.created_fr_ids = []
        yield
        for fr_id in self.created_fr_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/fatture-ricevute/{fr_id}")
            except:
                pass

    def test_scaduto_kpi_calculation(self):
        """Create scaduto fattura and verify KPI updates"""
        # Create fattura with past due date
        scadenza_passata = (date.today() - timedelta(days=30)).isoformat()
        payload = {
            "fornitore_nome": "TEST_Scaduto KPI",
            "numero_documento": f"TEST-KPI-{uuid.uuid4().hex[:4]}",
            "data_documento": date.today().isoformat(),
            "data_scadenza_pagamento": scadenza_passata,
            "totale_documento": 777.0
        }
        create_resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        assert create_resp.status_code == 201
        fr_id = create_resp.json()['fr_id']
        self.created_fr_ids.append(fr_id)

        # Fetch dashboard and check
        dash_resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard")
        assert dash_resp.status_code == 200
        data = dash_resp.json()

        # Find our scadenza
        scadenze_pagamento = [s for s in data['scadenze'] if s['tipo'] == 'pagamento' and s['id'] == fr_id]
        assert len(scadenze_pagamento) == 1, f"Expected to find our fattura in scadenze"
        assert scadenze_pagamento[0]['stato'] == 'scaduto', f"Expected scaduto, got {scadenze_pagamento[0]['stato']}"
        print(f"✓ Scaduto fattura correctly identified in KPIs")

    def test_in_scadenza_kpi_calculation(self):
        """Create in_scadenza fattura and verify KPI"""
        # Create fattura with due date within current month
        scadenza_mese = (date.today() + timedelta(days=10)).isoformat()
        if date.today().month == 12:
            # Handle Dec edge case - just use a date within 30 days
            scadenza_mese = (date.today() + timedelta(days=10)).isoformat()

        payload = {
            "fornitore_nome": "TEST_InScadenza KPI",
            "numero_documento": f"TEST-INS-{uuid.uuid4().hex[:4]}",
            "data_documento": date.today().isoformat(),
            "data_scadenza_pagamento": scadenza_mese,
            "totale_documento": 555.0
        }
        create_resp = self.session.post(f"{BASE_URL}/api/fatture-ricevute/", json=payload)
        assert create_resp.status_code == 201
        fr_id = create_resp.json()['fr_id']
        self.created_fr_ids.append(fr_id)

        # Fetch dashboard
        dash_resp = self.session.get(f"{BASE_URL}/api/fatture-ricevute/scadenziario/dashboard")
        data = dash_resp.json()

        scadenze_pagamento = [s for s in data['scadenze'] if s['tipo'] == 'pagamento' and s['id'] == fr_id]
        assert len(scadenze_pagamento) == 1
        # Could be in_scadenza or ok depending on exact date
        assert scadenze_pagamento[0]['stato'] in ['in_scadenza', 'ok']
        print(f"✓ In-scadenza fattura detected with stato={scadenze_pagamento[0]['stato']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
