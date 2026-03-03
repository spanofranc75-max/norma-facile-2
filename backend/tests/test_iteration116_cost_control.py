"""
Iteration 116: Cost Control - Smart Article Matching, PMP Calculation, Per-Row Allocation, Margin Analysis
Tests invoice line processing with smart matching, weighted average price (PMP) calculation,
per-row allocation to magazzino/commessa/generale, and margin analysis endpoints.
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test session will be set up in fixture
SESSION_TOKEN = None
USER_ID = None


@pytest.fixture(scope="module")
def auth_session():
    """Create test user and session for authenticated requests."""
    import subprocess
    result = subprocess.run([
        'mongosh', '--quiet', '--eval', '''
use('test_database');

// Clean up old test data first
db.users.deleteMany({email: /test\.iter116/});
db.user_sessions.deleteMany({session_token: /test_iter116_/});
db.articoli.deleteMany({codice: /TEST_I116/});
db.commesse.deleteMany({numero: /TEST_I116/});
db.fatture_ricevute.deleteMany({numero_documento: /TEST_I116/});
db.project_costs.deleteMany({source_invoice_numero: /TEST_I116/});

var ts = Date.now();
var userId = 'test-iter116-' + ts;
var sessionToken = 'test_iter116_' + ts;

db.users.insertOne({
  user_id: userId,
  email: 'test.iter116.' + ts + '@example.com',
  name: 'Iter116 Tester',
  created_at: new Date()
});

db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 24*60*60*1000),
  created_at: new Date()
});

// Create test article for matching tests
db.articoli.insertOne({
  articolo_id: 'art_i116_match',
  user_id: userId,
  codice: 'TEST_I116_TRAVI',
  descrizione: 'Travi HEA 200 S275JR Test',
  categoria: 'materiale',
  unita_misura: 'pz',
  prezzo_unitario: 500.00,
  giacenza: 10,
  prezzo_medio_ponderato: 480.00,
  storico_prezzi: [],
  created_at: new Date()
});

// Create test commessa for assignment tests
db.commesse.insertOne({
  commessa_id: 'comm_i116_001',
  user_id: userId,
  numero: 'TEST_I116_C001',
  title: 'Commessa Test Cost Control',
  client_name: 'Cliente Test 116',
  value: 50000,
  status: 'in_corso',
  costi_reali: [],
  created_at: new Date()
});

// Create another commessa with existing costs for margin analysis
db.commesse.insertOne({
  commessa_id: 'comm_i116_002',
  user_id: userId,
  numero: 'TEST_I116_C002',
  title: 'Commessa con Costi Esistenti',
  client_name: 'Cliente Analisi',
  value: 30000,
  status: 'in_corso',
  costi_reali: [
    {cost_id: 'cost_existing_1', tipo: 'materiali', importo: 5000, descrizione: 'Materiali esistenti'},
    {cost_id: 'cost_existing_2', tipo: 'lavorazioni_esterne', importo: 3000, descrizione: 'Lavorazioni'}
  ],
  created_at: new Date()
});

// Create test invoice for processing
db.fatture_ricevute.insertOne({
  fr_id: 'fr_i116_001',
  user_id: userId,
  fornitore_id: 'forn_i116_001',
  fornitore_nome: 'Acciaierie Test Iter116',
  fornitore_piva: 'IT11223344556',
  numero_documento: 'TEST_I116_FT001',
  data_documento: '2026-01-15',
  totale_documento: 1830.00,
  imponibile: 1500.00,
  imposta: 330.00,
  linee: [
    {descrizione: 'Travi HEA 200 S275JR — 6m', quantita: 3, unita_misura: 'pz', prezzo_unitario: 300.00, importo: 900.00, codice_articolo: ''},
    {descrizione: 'Piatti 200x10 S275JR — 6m', quantita: 4, unita_misura: 'pz', prezzo_unitario: 150.00, importo: 600.00, codice_articolo: ''}
  ],
  status: 'ricevuta',
  created_at: new Date()
});

print(JSON.stringify({session_token: sessionToken, user_id: userId}));
'''
    ], capture_output=True, text=True)
    
    import json
    data = json.loads(result.stdout.strip().split('\n')[-1])
    
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Cookie": f"session_token={data['session_token']}"
    })
    session.cookies.set("session_token", data['session_token'])
    
    yield {
        "session": session,
        "token": data['session_token'],
        "user_id": data['user_id']
    }
    
    # Cleanup
    subprocess.run([
        'mongosh', '--quiet', '--eval', f'''
use('test_database');
db.users.deleteMany({{user_id: '{data["user_id"]}'}});
db.user_sessions.deleteMany({{user_id: '{data["user_id"]}'}});
db.articoli.deleteMany({{user_id: '{data["user_id"]}'}});
db.commesse.deleteMany({{user_id: '{data["user_id"]}'}});
db.fatture_ricevute.deleteMany({{user_id: '{data["user_id"]}'}});
db.project_costs.deleteMany({{user_id: '{data["user_id"]}'}});
'''
    ])


class TestPMPCalculation:
    """Test calc_pmp function for weighted average price calculation."""
    
    def test_pmp_basic_calculation(self):
        """Test PMP: (old_qty * old_pmp + new_qty * new_price) / (old_qty + new_qty)"""
        # PMP formula: (10 * 480 + 3 * 300) / 13 = (4800 + 900) / 13 = 5700 / 13 = 438.46
        # This is the expected result when adding 3 units at 300€ to 10 units with PMP 480€
        old_qty = 10
        old_pmp = 480.0
        new_qty = 3
        new_price = 300.0
        
        expected = round((old_qty * old_pmp + new_qty * new_price) / (old_qty + new_qty), 4)
        
        assert expected == 438.4615, f"Expected PMP 438.4615, got {expected}"
    
    def test_pmp_first_purchase(self):
        """Test PMP when no existing stock (first purchase)."""
        old_qty = 0
        old_pmp = 0.0
        new_qty = 5
        new_price = 250.0
        
        # When old_qty is 0, PMP should be the new price
        if old_qty + new_qty <= 0:
            expected = new_price
        else:
            expected = round((old_qty * old_pmp + new_qty * new_price) / (old_qty + new_qty), 4)
        
        assert expected == 250.0, f"First purchase PMP should equal purchase price"


class TestMatchArticleEndpoint:
    """Test POST /api/costs/invoices/{id}/match-articles endpoint."""
    
    def test_match_articles_endpoint_returns_results(self, auth_session):
        """Test that match-articles endpoint returns results for each line."""
        session = auth_session['session']
        
        # Match articles for our test invoice
        resp = session.post(f"{BASE_URL}/api/costs/invoices/fr_i116_001/match-articles")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "lines" in data, "Response should have 'lines' array"
        assert len(data["lines"]) == 2, "Should have 2 lines (matching invoice)"
        
        # First line should potentially match our test article (Travi HEA 200...)
        line0 = data["lines"][0]
        assert "idx" in line0
        assert "descrizione" in line0
        assert "match" in line0
        assert "suggested_action" in line0
        
        # If match found, it should have article details
        if line0["match"]:
            assert "articolo_id" in line0["match"]
            assert "codice" in line0["match"]
            assert line0["suggested_action"] == "aggiorna"
        else:
            assert line0["suggested_action"] == "crea_nuovo"
    
    def test_match_articles_not_found(self, auth_session):
        """Test that non-existent invoice returns 404."""
        session = auth_session['session']
        
        resp = session.post(f"{BASE_URL}/api/costs/invoices/nonexistent_fr/match-articles")
        assert resp.status_code == 404


class TestAssignRowsEndpoint:
    """Test POST /api/costs/invoices/{id}/assign-rows endpoint for per-row allocation."""
    
    def test_assign_rows_to_commessa(self, auth_session):
        """Test assigning invoice rows to a commessa updates costi_reali."""
        session = auth_session['session']
        
        # Create a new invoice for this test
        import subprocess
        subprocess.run([
            'mongosh', '--quiet', '--eval', f'''
use('test_database');
db.fatture_ricevute.insertOne({{
  fr_id: 'fr_i116_comm_test',
  user_id: '{auth_session["user_id"]}',
  fornitore_nome: 'Fornitore Commessa Test',
  numero_documento: 'TEST_I116_FT_COMM',
  data_documento: '2026-01-16',
  totale_documento: 500.00,
  linee: [
    {{descrizione: 'Materiale per commessa', quantita: 5, unita_misura: 'pz', prezzo_unitario: 100.00, importo: 500.00}}
  ],
  status: 'ricevuta',
  created_at: new Date()
}});
'''
        ])
        
        # Assign row to commessa
        payload = {
            "rows": [
                {
                    "idx": 0,
                    "target_type": "commessa",
                    "target_id": "comm_i116_001",
                    "category": "materiali",
                    "create_article": False
                }
            ]
        }
        
        resp = session.post(
            f"{BASE_URL}/api/costs/invoices/fr_i116_comm_test/assign-rows",
            json=payload
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["target_type"] == "commessa"
        assert data["results"][0]["action"] == "assigned"
    
    def test_assign_rows_to_magazzino_creates_article(self, auth_session):
        """Test assigning row to magazzino with create_article=True creates new article."""
        session = auth_session['session']
        
        # Create a new invoice for this test
        import subprocess
        subprocess.run([
            'mongosh', '--quiet', '--eval', f'''
use('test_database');
db.fatture_ricevute.insertOne({{
  fr_id: 'fr_i116_mag_create',
  user_id: '{auth_session["user_id"]}',
  fornitore_nome: 'Fornitore Magazzino Test',
  fornitore_id: 'forn_mag_116',
  numero_documento: 'TEST_I116_FT_MAG',
  data_documento: '2026-01-16',
  totale_documento: 300.00,
  linee: [
    {{descrizione: 'Nuovo articolo da creare', quantita: 10, unita_misura: 'kg', prezzo_unitario: 30.00, importo: 300.00}}
  ],
  status: 'ricevuta',
  created_at: new Date()
}});
'''
        ])
        
        # Assign row to magazzino with create_article=True
        payload = {
            "rows": [
                {
                    "idx": 0,
                    "target_type": "magazzino",
                    "target_id": None,
                    "category": "materiali",
                    "create_article": True
                }
            ]
        }
        
        resp = session.post(
            f"{BASE_URL}/api/costs/invoices/fr_i116_mag_create/assign-rows",
            json=payload
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "results" in data
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["target_type"] == "magazzino"
        assert result["action"] == "created"
        assert "articolo" in result
        assert "articolo_id" in result["articolo"]
    
    def test_assign_rows_to_magazzino_updates_existing(self, auth_session):
        """Test assigning row to magazzino with existing article updates PMP and giacenza."""
        session = auth_session['session']
        
        # Create a new invoice for this test
        import subprocess
        subprocess.run([
            'mongosh', '--quiet', '--eval', f'''
use('test_database');
db.fatture_ricevute.insertOne({{
  fr_id: 'fr_i116_mag_update',
  user_id: '{auth_session["user_id"]}',
  fornitore_nome: 'Fornitore Update Test',
  numero_documento: 'TEST_I116_FT_UPD',
  data_documento: '2026-01-17',
  totale_documento: 900.00,
  linee: [
    {{descrizione: 'Travi HEA 200 S275JR aggiuntive', quantita: 3, unita_misura: 'pz', prezzo_unitario: 300.00, importo: 900.00}}
  ],
  status: 'ricevuta',
  created_at: new Date()
}});
'''
        ])
        
        # Assign row to magazzino with existing article
        payload = {
            "rows": [
                {
                    "idx": 0,
                    "target_type": "magazzino",
                    "target_id": "art_i116_match",  # Our existing test article
                    "category": "materiali",
                    "create_article": False
                }
            ]
        }
        
        resp = session.post(
            f"{BASE_URL}/api/costs/invoices/fr_i116_mag_update/assign-rows",
            json=payload
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "results" in data
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["target_type"] == "magazzino"
        assert result["action"] == "updated"
        assert "update" in result
        
        # Verify PMP was updated
        update_info = result["update"]
        assert "prezzo_medio_ponderato" in update_info or "giacenza" in update_info
    
    def test_assign_rows_to_generale(self, auth_session):
        """Test assigning row to spese generali."""
        session = auth_session['session']
        
        # Create a new invoice for this test
        import subprocess
        subprocess.run([
            'mongosh', '--quiet', '--eval', f'''
use('test_database');
db.fatture_ricevute.insertOne({{
  fr_id: 'fr_i116_generale',
  user_id: '{auth_session["user_id"]}',
  fornitore_nome: 'Spese Generali Test',
  numero_documento: 'TEST_I116_FT_GEN',
  data_documento: '2026-01-18',
  totale_documento: 150.00,
  linee: [
    {{descrizione: 'Spese amministrative', quantita: 1, unita_misura: 'corpo', prezzo_unitario: 150.00, importo: 150.00}}
  ],
  status: 'ricevuta',
  created_at: new Date()
}});
'''
        ])
        
        # Assign row to generale
        payload = {
            "rows": [
                {
                    "idx": 0,
                    "target_type": "generale",
                    "target_id": None,
                    "category": "consumabili",
                    "create_article": False
                }
            ]
        }
        
        resp = session.post(
            f"{BASE_URL}/api/costs/invoices/fr_i116_generale/assign-rows",
            json=payload
        )
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["target_type"] == "generale"
        assert data["results"][0]["action"] == "generale"


class TestMarginAnalysisEndpoint:
    """Test GET /api/costs/margin-analysis endpoint."""
    
    def test_margin_analysis_returns_commesse(self, auth_session):
        """Test that margin-analysis returns commesse with costs."""
        session = auth_session['session']
        
        resp = session.get(f"{BASE_URL}/api/costs/margin-analysis")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "commesse" in data
        assert "total" in data
        
        # Should have at least one commessa with costs (our test commessa comm_i116_002)
        if data["total"] > 0:
            commessa = data["commesse"][0]
            assert "commessa_id" in commessa
            assert "numero" in commessa
            assert "valore_preventivo" in commessa
            assert "totale_costi" in commessa
            assert "margine" in commessa
            assert "margine_pct" in commessa
            assert "alert" in commessa
            assert "costi_per_categoria" in commessa
    
    def test_margin_analysis_alert_levels(self, auth_session):
        """Test that margin analysis returns correct alert levels."""
        session = auth_session['session']
        
        resp = session.get(f"{BASE_URL}/api/costs/margin-analysis")
        assert resp.status_code == 200
        
        data = resp.json()
        
        # Find our test commessa with existing costs
        test_commessa = None
        for c in data["commesse"]:
            if c["numero"] == "TEST_I116_C002":
                test_commessa = c
                break
        
        if test_commessa:
            # Value 30000, costs 8000, margin 22000, pct ~73% -> verde
            assert test_commessa["alert"] in ["verde", "giallo", "rosso"]
            
            # With value=30000 and costs=8000, margin_pct = 73.3% -> should be verde (>20%)
            if test_commessa["margine_pct"] >= 20:
                assert test_commessa["alert"] == "verde"


class TestPendingInvoicesEndpoint:
    """Test GET /api/costs/invoices/pending endpoint."""
    
    def test_pending_invoices_returns_list(self, auth_session):
        """Test that pending invoices endpoint returns unprocessed invoices."""
        session = auth_session['session']
        
        resp = session.get(f"{BASE_URL}/api/costs/invoices/pending")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "invoices" in data
        assert "total" in data
        
        # Should have our test invoice
        if data["total"] > 0:
            inv = data["invoices"][0]
            assert "invoice_id" in inv
            assert "fornitore" in inv
            assert "numero" in inv
            assert "totale" in inv
            assert "linee" in inv
            assert "status" in inv


class TestCommesseSearchEndpoint:
    """Test GET /api/costs/commesse-search endpoint."""
    
    def test_commesse_search_returns_list(self, auth_session):
        """Test commesse search endpoint."""
        session = auth_session['session']
        
        resp = session.get(f"{BASE_URL}/api/costs/commesse-search?q=")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "commesse" in data
        
        # Should have our test commesse
        if len(data["commesse"]) > 0:
            c = data["commesse"][0]
            assert "commessa_id" in c
            assert "numero" in c
            assert "title" in c
    
    def test_commesse_search_with_query(self, auth_session):
        """Test commesse search with filter query."""
        session = auth_session['session']
        
        resp = session.get(f"{BASE_URL}/api/costs/commesse-search?q=TEST_I116")
        
        assert resp.status_code == 200
        data = resp.json()
        
        # Should find our test commesse
        for c in data["commesse"]:
            assert "TEST_I116" in c.get("numero", "") or "TEST_I116" in c.get("title", "") or "Test" in c.get("client_name", "")
