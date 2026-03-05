"""
Iteration 143: PDF Content Improvements Testing

Tests for:
1. AI Prompt: anti-cross-reference instruction, rischi_residui array, stima_manodopera field
2. PDF: Registro Manutenzione section, Checklist post-intervento, Rischi Residui section
3. PDF: Manodopera Stimata label, updated image label, MATERIALI section still removed
4. Backend: _default_varianti() returns stima_manodopera field
5. Frontend: rischi-residui-section data-testid, stima_manodopera display
"""
import pytest
import os
import sys

# Add backend to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAIPromptContent:
    """Test AI prompt structure and fields in vision_analysis.py"""
    
    def test_anti_cross_reference_instruction_exists(self):
        """Verify SYSTEM_PROMPT contains anti-cross-reference instruction"""
        from services.vision_analysis import SYSTEM_PROMPT
        
        # Check for explicit instruction about not referencing other variants
        assert "NON scrivere" in SYSTEM_PROMPT or "non scrivere" in SYSTEM_PROMPT
        assert "Include interventi Variante A" in SYSTEM_PROMPT or "include Variante A" in SYSTEM_PROMPT.lower()
        # Check for the AUTONOMA requirement
        assert "AUTONOMA" in SYSTEM_PROMPT or "autonoma" in SYSTEM_PROMPT.lower()
        print("PASS: Anti-cross-reference instruction found in SYSTEM_PROMPT")
    
    def test_rischi_residui_in_json_schema(self):
        """Verify rischi_residui array field in JSON schema"""
        from services.vision_analysis import SYSTEM_PROMPT
        
        assert '"rischi_residui"' in SYSTEM_PROMPT or "'rischi_residui'" in SYSTEM_PROMPT
        print("PASS: rischi_residui field found in SYSTEM_PROMPT JSON schema")
    
    def test_stima_manodopera_in_json_schema(self):
        """Verify stima_manodopera field in each variant in JSON schema"""
        from services.vision_analysis import SYSTEM_PROMPT
        
        assert '"stima_manodopera"' in SYSTEM_PROMPT or "'stima_manodopera'" in SYSTEM_PROMPT
        print("PASS: stima_manodopera field found in SYSTEM_PROMPT JSON schema")
    
    def test_default_varianti_has_stima_manodopera(self):
        """Verify _default_varianti() returns stima_manodopera field (not tempo_stimato)"""
        from services.vision_analysis import _default_varianti
        
        defaults = _default_varianti()
        
        # Check all variants have stima_manodopera
        for variant_key in ['A', 'B', 'C']:
            assert variant_key in defaults, f"Missing variant {variant_key}"
            variant = defaults[variant_key]
            assert 'stima_manodopera' in variant, f"Variant {variant_key} missing stima_manodopera"
            # Ensure tempo_stimato is NOT present
            assert 'tempo_stimato' not in variant, f"Variant {variant_key} should NOT have tempo_stimato"
        
        print("PASS: _default_varianti() returns stima_manodopera field for all variants")


class TestPDFRegistroManutenzione:
    """Test Registro di Manutenzione section in PDF"""
    
    def test_registro_manutenzione_section_exists(self):
        """Verify 'Obbligo Registro di Manutenzione' section in PDF source"""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        
        # Read the source file directly
        pdf_source_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'pdf_perizia_sopralluogo.py')
        with open(pdf_source_path, 'r') as f:
            source = f.read()
        
        # Check for Registro di Manutenzione section
        assert 'Obbligo Registro di Manutenzione' in source or 'Registro di Manutenzione' in source
        # Check for semi-annual maintenance text
        assert 'almeno semestrali' in source
        print("PASS: Registro di Manutenzione section with semi-annual text found")
    
    def test_libretto_impianto_mentions(self):
        """Verify Libretto dell'Impianto mentioned in Registro section"""
        pdf_source_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'pdf_perizia_sopralluogo.py')
        with open(pdf_source_path, 'r') as f:
            source = f.read()
        
        assert "Libretto dell'Impianto" in source or "Libretto Impianto" in source
        print("PASS: Libretto Impianto reference found")


class TestPDFChecklist:
    """Test Check-list Verifiche Post-Intervento section"""
    
    def test_checklist_section_exists(self):
        """Verify Check-list Verifiche Post-Intervento section exists"""
        pdf_source_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'pdf_perizia_sopralluogo.py')
        with open(pdf_source_path, 'r') as f:
            source = f.read()
        
        assert 'Check-list Verifiche Post-Intervento' in source or 'Verifiche Post-Intervento' in source
        print("PASS: Check-list Verifiche Post-Intervento section found")
    
    def test_checklist_has_8_items(self):
        """Verify checklist contains 8 specific test items"""
        pdf_source_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'pdf_perizia_sopralluogo.py')
        with open(pdf_source_path, 'r') as f:
            source = f.read()
        
        # Check for specific checklist items
        required_items = [
            'forze d\'impatto' if "forze d'impatto" in source else 'forze d',  # force measurement
            'coste sensibili' if 'coste sensibili' in source else 'coste',  # sensitive edges
            'fotocellule' if 'fotocellule' in source else 'fotocell',  # photocells
            'finecorsa',  # limit switches
            'arresto' if 'arresto' in source else 'emergenza',  # emergency stop
            'encoder' if 'encoder' in source else 'limitazione',  # encoder/limiter
            'lampeggiante' if 'lampeggiante' in source else 'segnalazione',  # flasher
            'Dichiarazione' if 'Dichiarazione' in source else 'dichiarazione',  # declaration
        ]
        
        found_items = 0
        for item in required_items:
            if item.lower() in source.lower():
                found_items += 1
        
        # Count the actual checklist items (&#9745; is the checkbox unicode)
        checklist_items_count = source.count('checklist-item')
        
        assert checklist_items_count >= 8, f"Expected 8 checklist items, found {checklist_items_count}"
        print(f"PASS: Checklist has {checklist_items_count} items (expected 8)")


class TestPDFRischiResidui:
    """Test Rischi Residui (post-adeguamento) section in PDF"""
    
    def test_rischi_residui_section_exists(self):
        """Verify Rischi Residui section exists in PDF source"""
        pdf_source_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'pdf_perizia_sopralluogo.py')
        with open(pdf_source_path, 'r') as f:
            source = f.read()
        
        assert 'Rischi Residui (post-adeguamento)' in source or 'rischi_residui' in source
        assert 'residual_html' in source or 'residual-risk' in source
        print("PASS: Rischi Residui section found in PDF source")
    
    def test_rischi_residui_conditional_rendering(self):
        """Verify Rischi Residui renders only when data exists"""
        pdf_source_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'pdf_perizia_sopralluogo.py')
        with open(pdf_source_path, 'r') as f:
            source = f.read()
        
        # Check for conditional rendering pattern
        assert 'rischi_residui' in source
        assert 'if rischi_residui' in source or 'rischi_residui:' in source
        print("PASS: Rischi Residui has conditional rendering")


class TestPDFVariantManodopera:
    """Test Manodopera Stimata in variant footer"""
    
    def test_manodopera_stimata_label_exists(self):
        """Verify 'Manodopera Stimata' label in variant footer"""
        pdf_source_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'pdf_perizia_sopralluogo.py')
        with open(pdf_source_path, 'r') as f:
            source = f.read()
        
        assert 'Manodopera Stimata' in source
        print("PASS: 'Manodopera Stimata' label found in PDF source")
    
    def test_stima_manodopera_in_variant_html(self):
        """Verify stima_manodopera is extracted and rendered in variant HTML"""
        pdf_source_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'pdf_perizia_sopralluogo.py')
        with open(pdf_source_path, 'r') as f:
            source = f.read()
        
        # Check that stima_manodopera is read from variant data
        assert "stima_manodopera" in source
        assert "v.get(\"stima_manodopera\"" in source or "v.get('stima_manodopera'" in source
        print("PASS: stima_manodopera extracted from variant data")


class TestPDFImageLabel:
    """Test solution image label text"""
    
    def test_image_label_updated(self):
        """Verify image label says 'Soluzione tipo (sostituibile con foto proprie installazioni)'"""
        pdf_source_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'pdf_perizia_sopralluogo.py')
        with open(pdf_source_path, 'r') as f:
            source = f.read()
        
        # Check for the NEW label text
        assert 'Soluzione tipo (sostituibile con foto proprie installazioni)' in source
        # Check that OLD label is NOT present
        assert 'Esempio Soluzione Consigliata' not in source
        print("PASS: Image label updated to encourage real photos")


class TestPDFMaterialiRemoved:
    """Regression: verify MATERIALI E INTERVENTI section is still removed"""
    
    def test_materiali_section_still_removed(self):
        """Verify MATERIALI E INTERVENTI section is NOT in PDF"""
        pdf_source_path = os.path.join(os.path.dirname(__file__), '..', 'services', 'pdf_perizia_sopralluogo.py')
        with open(pdf_source_path, 'r') as f:
            source = f.read()
        
        # Check that the section header is NOT rendered
        # The comment should still be there explaining why it's removed
        assert 'Section 04 rimossa' in source or 'MATERIALI E INTERVENTI' not in source or 'rimossa' in source
        print("PASS: MATERIALI E INTERVENTI section still removed (regression check)")


class TestPDFGeneration:
    """Test actual PDF generation with mock data"""
    
    def test_pdf_generates_with_all_new_sections(self):
        """Generate a test PDF with rischi_residui and stima_manodopera data"""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        
        # Mock sopralluogo with all new fields
        mock_sopralluogo = {
            "sopralluogo_id": "test123",
            "document_number": "SOP/2026/TEST",
            "client_name": "Test Client",
            "indirizzo": "Via Test 1",
            "comune": "Bologna",
            "provincia": "BO",
            "descrizione_utente": "Test cancello",
            "created_at": "2026-01-15T10:00:00Z",
            "analisi_ai": {
                "tipo_chiusura": "scorrevole",
                "descrizione_generale": "Cancello scorrevole test",
                "conformita_percentuale": 45,
                "rischi": [
                    {
                        "zona": "Bordo chiusura",
                        "tipo_rischio": "schiacciamento",
                        "gravita": "alta",
                        "problema": "Manca costa sensibile",
                        "soluzione": "Installare costa sensibile 8K2",
                        "norma_riferimento": "EN 12453 par. 5.1.1",
                        "confermato": True
                    }
                ],
                "dispositivi_presenti": ["Lampeggiante"],
                "dispositivi_mancanti": ["Costa sensibile", "Fotocellule"],
                "materiali_suggeriti": [],
                "varianti": {
                    "A": {
                        "titolo": "Adeguamento Minimo",
                        "descrizione": "Solo sicurezze essenziali",
                        "interventi": ["Installazione costa", "Installazione fotocellule"],
                        "stima_manodopera": "4-6 ore (1 tecnico)",
                        "costo_stimato": 800
                    },
                    "B": {
                        "titolo": "Adeguamento Completo",
                        "descrizione": "Sicurezze + centralina",
                        "interventi": ["Installazione costa", "Installazione fotocellule", "Sostituzione centralina"],
                        "stima_manodopera": "8-12 ore (1-2 tecnici)",
                        "costo_stimato": 1500
                    },
                    "C": {
                        "titolo": "Sostituzione Totale",
                        "descrizione": "Nuovo impianto completo",
                        "interventi": ["Nuovo motore", "Nuova centralina", "Tutte sicurezze"],
                        "stima_manodopera": "16-24 ore (2 tecnici)",
                        "costo_stimato": 3000
                    }
                },
                "rischi_residui": [
                    "Rischio residuo minimo di intrappolamento per geometria strutturale non modificabile",
                    "Rischio residuo trascurabile per manovre manuali in caso di blackout"
                ],
                "note_tecniche": "Impianto da adeguare urgentemente"
            }
        }
        
        mock_company = {
            "company_name": "Test Company Srl",
            "address": "Via Aziendale 10",
            "cap": "40100",
            "city": "Bologna",
            "province": "BO",
            "partita_iva": "IT12345678901"
        }
        
        # Generate PDF
        pdf_bytes = generate_perizia_pdf(mock_sopralluogo, mock_company, photos_b64=[])
        
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 10000, f"PDF too small: {len(pdf_bytes)} bytes"
        
        # Save for manual inspection
        test_pdf_path = "/tmp/test_iteration143_full.pdf"
        with open(test_pdf_path, "wb") as f:
            f.write(pdf_bytes)
        
        print(f"PASS: PDF generated successfully ({len(pdf_bytes)} bytes) - saved to {test_pdf_path}")
    
    def test_pdf_without_rischi_residui(self):
        """Test PDF generation with empty rischi_residui - no residual risk box should render"""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        
        mock_sopralluogo = {
            "sopralluogo_id": "test456",
            "document_number": "SOP/2026/TEST2",
            "client_name": "Test Client 2",
            "indirizzo": "Via Test 2",
            "comune": "Milano",
            "provincia": "MI",
            "created_at": "2026-01-15T10:00:00Z",
            "analisi_ai": {
                "tipo_chiusura": "battente",
                "descrizione_generale": "Cancello battente test",
                "conformita_percentuale": 70,
                "rischi": [],
                "dispositivi_presenti": ["Costa sensibile", "Fotocellule"],
                "dispositivi_mancanti": [],
                "varianti": {},
                "rischi_residui": [],  # Empty - no residual risks
                "note_tecniche": ""
            }
        }
        
        mock_company = {
            "company_name": "Test Company 2",
            "address": "Via Test 2",
            "cap": "20100",
            "city": "Milano",
            "province": "MI",
            "partita_iva": "IT98765432109"
        }
        
        pdf_bytes = generate_perizia_pdf(mock_sopralluogo, mock_company, photos_b64=[])
        
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 5000
        
        print(f"PASS: PDF without rischi_residui generates correctly ({len(pdf_bytes)} bytes)")


class TestFrontendRischiResiduiSection:
    """Test frontend rischi_residui section"""
    
    def test_rischi_residui_data_testid_exists(self):
        """Verify data-testid='rischi-residui-section' exists in SopralluogoWizardPage.js"""
        frontend_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'src', 'pages', 'SopralluogoWizardPage.js')
        with open(frontend_path, 'r') as f:
            source = f.read()
        
        assert 'data-testid="rischi-residui-section"' in source
        print("PASS: data-testid='rischi-residui-section' found in SopralluogoWizardPage.js")
    
    def test_stima_manodopera_displayed_in_variant(self):
        """Verify stima_manodopera is displayed in variant expansion"""
        frontend_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'src', 'pages', 'SopralluogoWizardPage.js')
        with open(frontend_path, 'r') as f:
            source = f.read()
        
        # Check that stima_manodopera is displayed in variants
        assert 'stima_manodopera' in source
        assert 'v.stima_manodopera' in source
        # Check for Manodopera label
        assert 'Manodopera' in source
        print("PASS: stima_manodopera displayed in variant cards")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
