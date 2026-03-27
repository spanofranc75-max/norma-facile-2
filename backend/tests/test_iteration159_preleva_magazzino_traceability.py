"""
Iteration 159 Tests: Warehouse Pickup (Preleva da Magazzino) with Traceability

Tests the POST /api/commesse/{cid}/preleva-da-magazzino endpoint:
1. When picking a stock item WITH certificate metadata (numero_colata or heat_number),
   verify material_batch and lotto_cam records are created in MongoDB
2. When picking a stock item WITHOUT certificate metadata,
   verify NO material_batch or lotto_cam records are created (backward compat)
3. Verify stock quantity is decremented correctly
4. Verify cost entry is added to commessa
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://cors-token-migration.preview.emergentagent.com"


class TestPrelevaMagazzinoTraceability:
    """Test warehouse pickup with EN 1090 traceability"""

    @pytest.fixture(autouse=True)
    def setup_test_data(self, api_client):
        """Create test user, session, commessa, and articoli for testing"""
        self.test_id = uuid.uuid4().hex[:8]
        self.user_id = f"test_user_{self.test_id}"
        self.session_token = f"test_session_{self.test_id}"
        
        # Create test user and session via mongosh
        import subprocess
        setup_script = f"""
        use('test_database');
        db.users.insertOne({{
            user_id: '{self.user_id}',
            email: 'test.preleva.{self.test_id}@example.com',
            name: 'Test Preleva User',
            created_at: new Date()
        }});
        db.user_sessions.insertOne({{
            user_id: '{self.user_id}',
            session_token: '{self.session_token}',
            expires_at: new Date(Date.now() + 7*24*60*60*1000),
            created_at: new Date()
        }});
        
        // Create test commessa
        db.commesse.insertOne({{
            commessa_id: 'comm_test_{self.test_id}',
            user_id: '{self.user_id}',
            numero: 'TEST-{self.test_id}',
            cliente: 'Test Client',
            descrizione: 'Test Commessa for Preleva',
            stato: 'in_corso',
            costi_reali: [],
            eventi: [],
            created_at: new Date(),
            updated_at: new Date()
        }});
        
        // Create test article WITH certificate metadata
        db.articoli.insertOne({{
            articolo_id: 'art_with_cert_{self.test_id}',
            user_id: '{self.user_id}',
            codice: 'HEA-200-CERT',
            descrizione: 'HEA 200 S275JR con certificato',
            categoria: 'profili',
            unita_misura: 'kg',
            prezzo_unitario: 1.5,
            giacenza: 1000,
            numero_colata: 'COLATA-12345',
            heat_number: 'HEAT-12345',
            qualita_acciaio: 'S275JR',
            acciaieria: 'Acciaieria Test',
            fornitore_nome: 'Fornitore Test',
            source_cert_id: 'cert_test_123',
            metodo_produttivo: 'forno_elettrico_non_legato',
            percentuale_riciclato: 85,
            created_at: new Date(),
            updated_at: new Date()
        }});
        
        // Create test article WITHOUT certificate metadata
        db.articoli.insertOne({{
            articolo_id: 'art_no_cert_{self.test_id}',
            user_id: '{self.user_id}',
            codice: 'VITI-M12',
            descrizione: 'Viti M12x50 zincate',
            categoria: 'ferramenta',
            unita_misura: 'pz',
            prezzo_unitario: 0.35,
            giacenza: 500,
            numero_colata: null,
            heat_number: null,
            created_at: new Date(),
            updated_at: new Date()
        }});
        print('Test data created');
        """
        result = subprocess.run(['mongosh', '--quiet', '--eval', setup_script], 
                               capture_output=True, text=True)
        
        self.commessa_id = f"comm_test_{self.test_id}"
        self.art_with_cert_id = f"art_with_cert_{self.test_id}"
        self.art_no_cert_id = f"art_no_cert_{self.test_id}"
        
        yield
        
        # Cleanup
        cleanup_script = f"""
        use('test_database');
        db.users.deleteOne({{ user_id: '{self.user_id}' }});
        db.user_sessions.deleteOne({{ session_token: '{self.session_token}' }});
        db.commesse.deleteOne({{ commessa_id: '{self.commessa_id}' }});
        db.articoli.deleteMany({{ user_id: '{self.user_id}' }});
        db.material_batches.deleteMany({{ user_id: '{self.user_id}' }});
        db.lotti_cam.deleteMany({{ user_id: '{self.user_id}' }});
        print('Test data cleaned up');
        """
        subprocess.run(['mongosh', '--quiet', '--eval', cleanup_script], 
                      capture_output=True, text=True)

    @pytest.fixture
    def api_client(self):
        """Create requests session"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        return session

    @pytest.fixture
    def auth_cookies(self):
        """Return auth cookies for the test user"""
        return {"session_token": self.session_token}

    def test_preleva_with_certificate_creates_traceability(self, api_client, auth_cookies):
        """
        Test: When picking a stock item WITH certificate metadata,
        verify material_batch and lotto_cam records are created
        """
        # Perform the withdrawal
        url = f"{BASE_URL}/api/commesse/{self.commessa_id}/preleva-da-magazzino"
        payload = {
            "articolo_id": self.art_with_cert_id,
            "quantita": 100,
            "note": "Test prelievo con certificato"
        }
        
        response = api_client.post(url, json=payload, cookies=auth_cookies)
        
        # Should succeed
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response contains traceability info
        assert data.get("tracciabilita_creata") == True, "tracciabilita_creata should be True"
        assert "colata" in data.get("message", "").lower() or "1090" in data.get("message", ""), \
            f"Message should mention colata or 1090: {data.get('message')}"
        
        # Verify cost entry was created
        assert "cost_entry" in data, "Response should contain cost_entry"
        assert data["cost_entry"]["importo"] == 150.0  # 100 * 1.5
        assert data["cost_entry"]["tipo"] == "materiale_magazzino"
        
        # Verify stock was decremented
        assert data["giacenza_residua"] == 900, f"Expected giacenza_residua 900, got {data['giacenza_residua']}"
        
        # Verify in MongoDB that material_batch and lotto_cam were created
        import subprocess
        check_script = f"""
        use('test_database');
        var batch = db.material_batches.findOne({{ 
            commessa_id: '{self.commessa_id}', 
            heat_number: 'COLATA-12345',
            origine: 'prelievo_magazzino'
        }});
        var cam = db.lotti_cam.findOne({{ 
            commessa_id: '{self.commessa_id}', 
            numero_colata: 'COLATA-12345'
        }});
        print('BATCH_EXISTS=' + (batch ? 'true' : 'false'));
        print('CAM_EXISTS=' + (cam ? 'true' : 'false'));
        if (batch) {{
            print('BATCH_SUPPLIER=' + batch.supplier_name);
            print('BATCH_MATERIAL=' + batch.material_type);
        }}
        if (cam) {{
            print('CAM_QUALITA=' + cam.qualita_acciaio);
            print('CAM_CONFORME=' + cam.conforme_cam);
        }}
        """
        result = subprocess.run(['mongosh', '--quiet', '--eval', check_script], 
                               capture_output=True, text=True)
        output = result.stdout
        
        assert 'BATCH_EXISTS=true' in output, f"material_batch should be created: {output}"
        assert 'CAM_EXISTS=true' in output, f"lotto_cam should be created: {output}"
        assert 'BATCH_SUPPLIER=Fornitore Test' in output, f"Batch should have supplier: {output}"
        assert 'CAM_QUALITA=S275JR' in output, f"CAM should have qualita_acciaio: {output}"
        assert 'CAM_CONFORME=true' in output, f"CAM should be conforme (85% >= 75%): {output}"
        
        print("✓ Test passed: Traceability records created for certified material")

    def test_preleva_without_certificate_no_traceability(self, api_client, auth_cookies):
        """
        Test: When picking a stock item WITHOUT certificate metadata,
        verify NO material_batch or lotto_cam records are created
        """
        # Perform the withdrawal
        url = f"{BASE_URL}/api/commesse/{self.commessa_id}/preleva-da-magazzino"
        payload = {
            "articolo_id": self.art_no_cert_id,
            "quantita": 50,
            "note": "Test prelievo senza certificato"
        }
        
        response = api_client.post(url, json=payload, cookies=auth_cookies)
        
        # Should succeed
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response indicates NO traceability
        assert data.get("tracciabilita_creata") == False, "tracciabilita_creata should be False"
        
        # Verify cost entry was still created
        assert "cost_entry" in data, "Response should contain cost_entry"
        assert data["cost_entry"]["importo"] == 17.5  # 50 * 0.35
        
        # Verify stock was decremented
        assert data["giacenza_residua"] == 450, f"Expected giacenza_residua 450, got {data['giacenza_residua']}"
        
        # Verify in MongoDB that NO material_batch or lotto_cam were created for this article
        import subprocess
        check_script = f"""
        use('test_database');
        var batch = db.material_batches.findOne({{ 
            commessa_id: '{self.commessa_id}', 
            articolo_id: '{self.art_no_cert_id}'
        }});
        var cam = db.lotti_cam.findOne({{ 
            commessa_id: '{self.commessa_id}', 
            articolo_id: '{self.art_no_cert_id}'
        }});
        print('BATCH_EXISTS=' + (batch ? 'true' : 'false'));
        print('CAM_EXISTS=' + (cam ? 'true' : 'false'));
        """
        result = subprocess.run(['mongosh', '--quiet', '--eval', check_script], 
                               capture_output=True, text=True)
        output = result.stdout
        
        assert 'BATCH_EXISTS=false' in output, f"material_batch should NOT be created: {output}"
        assert 'CAM_EXISTS=false' in output, f"lotto_cam should NOT be created: {output}"
        
        print("✓ Test passed: No traceability records for non-certified material")

    def test_preleva_decrements_stock_correctly(self, api_client, auth_cookies):
        """
        Test: Verify stock quantity is decremented correctly after prelievo
        """
        # First, get the initial stock
        import subprocess
        initial_check = f"""
        use('test_database');
        var art = db.articoli.findOne({{ articolo_id: '{self.art_with_cert_id}' }});
        print('INITIAL_GIACENZA=' + art.giacenza);
        """
        result = subprocess.run(['mongosh', '--quiet', '--eval', initial_check], 
                               capture_output=True, text=True)
        initial_output = result.stdout
        assert 'INITIAL_GIACENZA=1000' in initial_output, f"Initial giacenza should be 1000: {initial_output}"
        
        # Perform withdrawal
        url = f"{BASE_URL}/api/commesse/{self.commessa_id}/preleva-da-magazzino"
        payload = {
            "articolo_id": self.art_with_cert_id,
            "quantita": 250,
            "note": "Test decremento stock"
        }
        
        response = api_client.post(url, json=payload, cookies=auth_cookies)
        assert response.status_code == 200
        
        data = response.json()
        assert data["giacenza_residua"] == 750
        
        # Verify in MongoDB
        final_check = f"""
        use('test_database');
        var art = db.articoli.findOne({{ articolo_id: '{self.art_with_cert_id}' }});
        print('FINAL_GIACENZA=' + art.giacenza);
        """
        result = subprocess.run(['mongosh', '--quiet', '--eval', final_check], 
                               capture_output=True, text=True)
        final_output = result.stdout
        assert 'FINAL_GIACENZA=750' in final_output, f"Final giacenza should be 750: {final_output}"
        
        print("✓ Test passed: Stock correctly decremented from 1000 to 750")

    def test_preleva_adds_cost_entry_to_commessa(self, api_client, auth_cookies):
        """
        Test: Verify cost entry is added to commessa.costi_reali
        """
        # Perform withdrawal
        url = f"{BASE_URL}/api/commesse/{self.commessa_id}/preleva-da-magazzino"
        payload = {
            "articolo_id": self.art_with_cert_id,
            "quantita": 200,
            "note": "Test costo commessa"
        }
        
        response = api_client.post(url, json=payload, cookies=auth_cookies)
        assert response.status_code == 200
        
        data = response.json()
        cost_entry = data["cost_entry"]
        
        # Verify cost entry fields
        assert cost_entry["tipo"] == "materiale_magazzino"
        assert cost_entry["importo"] == 300.0  # 200 * 1.5
        assert cost_entry["quantita"] == 200
        assert cost_entry["prezzo_unitario"] == 1.5
        assert cost_entry["articolo_id"] == self.art_with_cert_id
        assert "HEA-200-CERT" in cost_entry["descrizione"]
        
        # Verify in MongoDB that commessa has the cost
        import subprocess
        check_script = f"""
        use('test_database');
        var comm = db.commesse.findOne({{ commessa_id: '{self.commessa_id}' }});
        var costs = comm.costi_reali || [];
        var prelevoCost = costs.find(c => c.tipo === 'materiale_magazzino');
        print('COST_COUNT=' + costs.length);
        if (prelevoCost) {{
            print('COST_IMPORTO=' + prelevoCost.importo);
            print('COST_TIPO=' + prelevoCost.tipo);
        }}
        """
        result = subprocess.run(['mongosh', '--quiet', '--eval', check_script], 
                               capture_output=True, text=True)
        output = result.stdout
        
        assert 'COST_IMPORTO=300' in output, f"Cost importo should be 300: {output}"
        assert 'COST_TIPO=materiale_magazzino' in output, f"Cost tipo should be materiale_magazzino: {output}"
        
        print("✓ Test passed: Cost entry correctly added to commessa")

    def test_preleva_insufficient_stock_returns_error(self, api_client, auth_cookies):
        """
        Test: Verify that trying to pick more than available stock returns 400 error
        """
        url = f"{BASE_URL}/api/commesse/{self.commessa_id}/preleva-da-magazzino"
        payload = {
            "articolo_id": self.art_with_cert_id,
            "quantita": 99999,  # More than available
            "note": "Test giacenza insufficiente"
        }
        
        response = api_client.post(url, json=payload, cookies=auth_cookies)
        
        assert response.status_code == 400, f"Expected 400 for insufficient stock, got {response.status_code}"
        assert "giacenza insufficiente" in response.text.lower(), f"Error should mention insufficient stock: {response.text}"
        
        print("✓ Test passed: Insufficient stock correctly returns 400 error")

    def test_preleva_nonexistent_article_returns_404(self, api_client, auth_cookies):
        """
        Test: Verify that trying to pick nonexistent article returns 404
        """
        url = f"{BASE_URL}/api/commesse/{self.commessa_id}/preleva-da-magazzino"
        payload = {
            "articolo_id": "nonexistent_article_id",
            "quantita": 10,
            "note": "Test articolo inesistente"
        }
        
        response = api_client.post(url, json=payload, cookies=auth_cookies)
        
        assert response.status_code == 404, f"Expected 404 for nonexistent article, got {response.status_code}"
        
        print("✓ Test passed: Nonexistent article correctly returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
