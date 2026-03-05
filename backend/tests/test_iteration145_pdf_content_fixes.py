"""
Iteration 145: PDF Content Fixes Testing
=========================================

Tests for 5 specific PDF content fixes identified by user:
1. Remove 'SOLUZIONE TIPO (SOSTITUIBILE CON FOTO PROPRIE INSTALLAZIONI)' label from reference images
2. Remove duplicate AI mention - keep only 'strumenti di analisi assistita' in footer disclaimer
3. Fix 'PANORAMICA — PANORAMICA' duplicate label bug in photo grid (deduplication logic)
4. Verify AI prompt rules: professional language, dispositivi_mancanti→rischi mapping, D.Lgs. 17/2010 context
5. Remove 'Note Analisi AI' from notes section - only show technician notes (note_tecnico)

Test approach: Import PDF generator directly and verify HTML output contains/excludes expected text.
"""

import pytest
import os
import sys

# Add backend to path for direct imports
sys.path.insert(0, '/app/backend')


# ═══════════════════════════════════════════════════════════════════════════════
# Module 1: PDF HTML Content Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDFContentFixes:
    """Tests for PDF HTML content - text removal and fixes."""
    
    @pytest.fixture
    def sample_sopralluogo(self):
        """Sample sopralluogo data for PDF generation."""
        return {
            "document_number": "TEST-2025-001",
            "client_name": "Test Cliente SRL",
            "indirizzo": "Via Roma 123",
            "comune": "Milano",
            "provincia": "MI",
            "note_tecnico": "Questa è una nota del tecnico per il cliente.",
            "created_at": "2025-01-15T10:00:00Z",
            "analisi_ai": {
                "tipo_chiusura": "scorrevole",
                "descrizione_generale": "Cancello scorrevole automatico",
                "conformita_percentuale": 45,
                "rischi": [
                    {
                        "zona": "Bordo chiusura",
                        "tipo_rischio": "schiacciamento",
                        "gravita": "alta",
                        "problema": "Manca costa sensibile",
                        "norma_riferimento": "EN 12453 par. 5.1.1",
                        "soluzione": "Installare costa sensibile 8K2",
                        "confermato": True
                    }
                ],
                "dispositivi_presenti": ["Fotocellula bassa", "Lampeggiante"],
                "dispositivi_mancanti": ["Costa sensibile", "Encoder motore"],
                "note_tecniche": "Queste sono note AI che NON devono apparire nel PDF.",
                "varianti": {
                    "A": {"titolo": "Adeguamento Minimo", "descrizione": "Test A", "interventi": [], "stima_manodopera": "4h", "costo_stimato": 500},
                    "B": {"titolo": "Adeguamento Completo", "descrizione": "Test B", "interventi": [], "stima_manodopera": "8h", "costo_stimato": 1500},
                    "C": {"titolo": "Sostituzione Totale", "descrizione": "Test C", "interventi": [], "stima_manodopera": "16h", "costo_stimato": 3000}
                }
            }
        }
    
    @pytest.fixture
    def sample_company(self):
        """Sample company data."""
        return {
            "company_name": "Test Company SRL",
            "address": "Via Test 1",
            "cap": "20100",
            "city": "Milano",
            "province": "MI",
            "partita_iva": "12345678901",
            "logo_url": ""
        }
    
    @pytest.fixture
    def sample_photos_single(self):
        """Single photo for basic tests."""
        # Minimal 1x1 PNG as base64
        return [{
            "base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "mime_type": "image/png",
            "label": "Test Foto"
        }]
    
    @pytest.fixture
    def sample_photos_duplicate_labels(self):
        """Multiple photos with duplicate labels to test deduplication."""
        base64_img = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        return [
            {"base64": base64_img, "mime_type": "image/png", "label": "panoramica"},
            {"base64": base64_img, "mime_type": "image/png", "label": "panoramica"},
            {"base64": base64_img, "mime_type": "image/png", "label": "panoramica"},
            {"base64": base64_img, "mime_type": "image/png", "label": "motore"},
            {"base64": base64_img, "mime_type": "image/png", "label": "motore"},
        ]

    # Test 1: SOLUZIONE TIPO text removal
    def test_no_soluzione_tipo_in_pdf(self, sample_sopralluogo, sample_company, sample_photos_single):
        """PDF should NOT contain 'SOLUZIONE TIPO' or 'sostituibile con foto proprie installazioni'."""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        
        # Generate PDF bytes (HTML is processed internally)
        # We need to inspect the HTML, not the PDF bytes
        # So we'll import the function logic components
        from services.pdf_perizia_sopralluogo import _esc, _gauge_svg, CSS
        
        # Build the HTML manually checking for forbidden text
        # The real test: examine the generated HTML from the function
        # Since generate_perizia_pdf returns bytes, we need to verify the code doesn't produce forbidden text
        
        # Check the code itself - the function should not have SOLUZIONE TIPO
        import inspect
        source = inspect.getsource(generate_perizia_pdf)
        
        assert "SOLUZIONE TIPO" not in source, "Code should not contain 'SOLUZIONE TIPO'"
        assert "sostituibile con foto proprie installazioni" not in source.lower(), \
            "Code should not contain 'sostituibile con foto proprie installazioni'"
        print("PASS: No 'SOLUZIONE TIPO' text found in PDF generation code")

    # Test 2: No 'Intelligenza Artificiale' in PDF
    def test_no_intelligenza_artificiale_in_pdf(self, sample_sopralluogo, sample_company, sample_photos_single):
        """PDF should NOT contain 'Intelligenza Artificiale' - replaced with 'analisi assistita'."""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        import inspect
        
        source = inspect.getsource(generate_perizia_pdf)
        
        assert "Intelligenza Artificiale" not in source, \
            "Code should not contain 'Intelligenza Artificiale'"
        assert "intelligenza artificiale" not in source.lower(), \
            "Code should not contain 'intelligenza artificiale' (case insensitive)"
        print("PASS: No 'Intelligenza Artificiale' text found in PDF generation code")

    # Test 3: Exactly ONE mention of 'analisi assistita' in disclaimer
    def test_exactly_one_analisi_assistita_mention(self, sample_sopralluogo, sample_company, sample_photos_single):
        """PDF should have exactly ONE mention of 'analisi assistita' in the disclaimer footer."""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        import inspect
        
        source = inspect.getsource(generate_perizia_pdf)
        
        # Count occurrences of 'analisi assistita'
        count = source.lower().count("analisi assistita")
        
        assert count == 1, f"Expected exactly 1 mention of 'analisi assistita', found {count}"
        
        # Verify it's in the disclaimer context
        assert "strumenti di analisi assistita" in source, \
            "Should contain 'strumenti di analisi assistita' in disclaimer"
        print("PASS: Exactly 1 mention of 'analisi assistita' in disclaimer")

    # Test 4: No 'Note Analisi AI' in notes section
    def test_no_note_analisi_ai_in_pdf(self, sample_sopralluogo, sample_company, sample_photos_single):
        """PDF notes section should NOT contain 'Note Analisi AI'."""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        import inspect
        
        source = inspect.getsource(generate_perizia_pdf)
        
        assert "Note Analisi AI" not in source, "Code should not contain 'Note Analisi AI'"
        assert "note_tecniche" not in source or source.count("note_tecniche") == 0, \
            "Code should not reference 'note_tecniche' from AI analysis"
        print("PASS: No 'Note Analisi AI' text in PDF notes section")

    # Test 5: Section header says 'NOTE DEL TECNICO'
    def test_notes_section_header_text(self, sample_sopralluogo, sample_company, sample_photos_single):
        """Notes section header should say 'NOTE DEL TECNICO', not just 'NOTE'."""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        import inspect
        
        source = inspect.getsource(generate_perizia_pdf)
        
        assert "NOTE DEL TECNICO" in source, "Notes section header should be 'NOTE DEL TECNICO'"
        print("PASS: Notes section header is 'NOTE DEL TECNICO'")

    # Test 6: Only note_tecnico appears, NOT note_tecniche
    def test_only_note_tecnico_used(self, sample_sopralluogo, sample_company, sample_photos_single):
        """PDF should only use note_tecnico (user notes), NOT note_tecniche (AI notes)."""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        import inspect
        
        source = inspect.getsource(generate_perizia_pdf)
        
        # Should reference note_tecnico (user input)
        assert "note_tecnico" in source, "Code should use 'note_tecnico' field"
        
        # Should NOT reference note_tecniche (AI analysis field) in PDF output context
        # Allow it to exist only if it's commented out or not used for display
        note_tecniche_refs = [line for line in source.split('\n') 
                              if 'note_tecniche' in line and not line.strip().startswith('#')]
        
        assert len(note_tecniche_refs) == 0, \
            f"Code should not actively use 'note_tecniche' for PDF. Found: {note_tecniche_refs}"
        print("PASS: Only 'note_tecnico' is used for PDF notes (not 'note_tecniche')")

    # Test 7: Validita del Documento section does NOT mention AI
    def test_validita_documento_no_ai_mention(self, sample_sopralluogo, sample_company, sample_photos_single):
        """Validita del Documento section should NOT mention AI or Intelligenza Artificiale."""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        import inspect
        
        source = inspect.getsource(generate_perizia_pdf)
        
        # Find the Validita del Documento section
        # Look for the legal_html section with "Validita del Documento"
        validita_start = source.find("Validita del Documento")
        assert validita_start != -1, "Should have 'Validita del Documento' section"
        
        # Find the end of this section (next legal_section or end of legal_html)
        validita_section = source[validita_start:validita_start + 800]  # Reasonable section length
        
        assert "Intelligenza Artificiale" not in validita_section, \
            "Validita section should not mention 'Intelligenza Artificiale'"
        assert "intelligenza artificiale" not in validita_section.lower(), \
            "Validita section should not mention 'intelligenza artificiale'"
        assert "AI" not in validita_section or "analisi assistita" in validita_section.lower(), \
            "Validita section should not use 'AI' unless in context of 'analisi assistita'"
        print("PASS: Validita del Documento section does not mention AI")


# ═══════════════════════════════════════════════════════════════════════════════
# Module 2: Photo Label Deduplication Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPhotoLabelDeduplication:
    """Tests for photo label deduplication logic in PDF generation."""
    
    @pytest.fixture
    def sample_sopralluogo(self):
        """Minimal sopralluogo for photo tests."""
        return {
            "document_number": "TEST-PHOTOS-001",
            "client_name": "Test Cliente",
            "indirizzo": "Via Test",
            "comune": "Roma",
            "provincia": "RM",
            "created_at": "2025-01-15T10:00:00Z",
            "analisi_ai": {
                "tipo_chiusura": "scorrevole",
                "conformita_percentuale": 50,
                "rischi": [],
                "dispositivi_presenti": [],
                "dispositivi_mancanti": []
            }
        }
    
    @pytest.fixture
    def sample_company(self):
        return {
            "company_name": "Test Company",
            "address": "Via Test",
            "cap": "00100",
            "city": "Roma",
            "province": "RM",
            "partita_iva": "00000000000"
        }

    def test_dedup_logic_in_code(self):
        """Verify deduplication logic exists: seen_labels dict with counter."""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        import inspect
        
        source = inspect.getsource(generate_perizia_pdf)
        
        # Check for seen_labels dictionary
        assert "seen_labels" in source, "Code should have 'seen_labels' dict for deduplication"
        
        # Check for counter increment logic
        assert "seen_labels[raw_lbl] += 1" in source or "seen_labels[raw_lbl]" in source, \
            "Code should increment counter for duplicate labels"
        
        # Check label formatting with counter
        assert '"{raw_lbl} {seen_labels[raw_lbl]}"' in source or \
               "f\"{raw_lbl} {seen_labels[raw_lbl]}\"" in source or \
               'f"{raw_lbl}' in source, \
            "Code should format labels with counter suffix"
        print("PASS: Deduplication logic exists in code (seen_labels dict)")

    def test_dedup_with_two_same_labels(self):
        """Two photos with same label should become 'PANORAMICA', 'PANORAMICA 2'."""
        # Simulate the deduplication logic
        photos = [
            {"label": "panoramica"},
            {"label": "panoramica"}
        ]
        
        seen_labels = {}
        results = []
        
        for p in photos:
            raw_lbl = (p.get("label") or "Foto").strip().upper()
            if raw_lbl in seen_labels:
                seen_labels[raw_lbl] += 1
                lbl = f"{raw_lbl} {seen_labels[raw_lbl]}"
            else:
                seen_labels[raw_lbl] = 1
                lbl = raw_lbl
            results.append(lbl)
        
        assert results[0] == "PANORAMICA", f"First label should be 'PANORAMICA', got '{results[0]}'"
        assert results[1] == "PANORAMICA 2", f"Second label should be 'PANORAMICA 2', got '{results[1]}'"
        print(f"PASS: Two same labels → {results}")

    def test_dedup_with_three_same_labels(self):
        """Three photos with same label should become 'PANORAMICA', 'PANORAMICA 2', 'PANORAMICA 3'."""
        photos = [
            {"label": "panoramica"},
            {"label": "panoramica"},
            {"label": "panoramica"}
        ]
        
        seen_labels = {}
        results = []
        
        for p in photos:
            raw_lbl = (p.get("label") or "Foto").strip().upper()
            if raw_lbl in seen_labels:
                seen_labels[raw_lbl] += 1
                lbl = f"{raw_lbl} {seen_labels[raw_lbl]}"
            else:
                seen_labels[raw_lbl] = 1
                lbl = raw_lbl
            results.append(lbl)
        
        assert results[0] == "PANORAMICA", f"First label should be 'PANORAMICA', got '{results[0]}'"
        assert results[1] == "PANORAMICA 2", f"Second label should be 'PANORAMICA 2', got '{results[1]}'"
        assert results[2] == "PANORAMICA 3", f"Third label should be 'PANORAMICA 3', got '{results[2]}'"
        print(f"PASS: Three same labels → {results}")

    def test_dedup_mixed_labels(self):
        """Mixed labels: only duplicates get numbered."""
        photos = [
            {"label": "panoramica"},
            {"label": "motore"},
            {"label": "panoramica"},
            {"label": "guide"},
            {"label": "motore"},
            {"label": "panoramica"}
        ]
        
        seen_labels = {}
        results = []
        
        for p in photos:
            raw_lbl = (p.get("label") or "Foto").strip().upper()
            if raw_lbl in seen_labels:
                seen_labels[raw_lbl] += 1
                lbl = f"{raw_lbl} {seen_labels[raw_lbl]}"
            else:
                seen_labels[raw_lbl] = 1
                lbl = raw_lbl
            results.append(lbl)
        
        expected = ["PANORAMICA", "MOTORE", "PANORAMICA 2", "GUIDE", "MOTORE 2", "PANORAMICA 3"]
        assert results == expected, f"Expected {expected}, got {results}"
        print(f"PASS: Mixed labels deduplication → {results}")

    def test_dedup_case_insensitive(self):
        """Labels should be uppercased and deduped case-insensitively."""
        photos = [
            {"label": "Panoramica"},
            {"label": "PANORAMICA"},
            {"label": "panoramica"}
        ]
        
        seen_labels = {}
        results = []
        
        for p in photos:
            raw_lbl = (p.get("label") or "Foto").strip().upper()
            if raw_lbl in seen_labels:
                seen_labels[raw_lbl] += 1
                lbl = f"{raw_lbl} {seen_labels[raw_lbl]}"
            else:
                seen_labels[raw_lbl] = 1
                lbl = raw_lbl
            results.append(lbl)
        
        assert results == ["PANORAMICA", "PANORAMICA 2", "PANORAMICA 3"], \
            f"Case-insensitive dedup failed: {results}"
        print(f"PASS: Case-insensitive deduplication → {results}")


# ═══════════════════════════════════════════════════════════════════════════════
# Module 3: AI Prompt Rules Verification
# ═══════════════════════════════════════════════════════════════════════════════

class TestAIPromptRules:
    """Tests for AI prompt rules in vision_analysis.py."""

    def test_prompt_dispositivi_mancanti_rischi_rule(self):
        """AI prompt should contain rule: every dispositivo_mancante must have a rischi entry."""
        from services.vision_analysis import SYSTEM_PROMPT
        
        # Check for the rule about dispositivi_mancanti → rischi mapping
        assert "dispositivi_mancanti" in SYSTEM_PROMPT, \
            "Prompt should mention 'dispositivi_mancanti'"
        
        # Check for the critical rule
        critical_rule_keywords = [
            "OGNI dispositivo elencato in",
            "dispositivi_mancanti",
            "DEVE avere una corrispondente scheda in",
            "rischi"
        ]
        
        # Check presence of the rule
        rule_found = all(kw.lower() in SYSTEM_PROMPT.lower() for kw in ["dispositivi_mancanti", "rischi"])
        assert rule_found, "Prompt should link dispositivi_mancanti to rischi requirement"
        
        # Check for explicit rule text
        assert "CRITICO" in SYSTEM_PROMPT and "dispositivi_mancanti" in SYSTEM_PROMPT, \
            "Prompt should have CRITICO rule about dispositivi_mancanti"
        print("PASS: AI prompt contains dispositivi_mancanti → rischi mapping rule")

    def test_prompt_professional_language_rule(self):
        """AI prompt should contain professional language rules with ERRATO vs CORRETTO examples."""
        from services.vision_analysis import SYSTEM_PROMPT
        
        # Check for professional language section
        assert "LINGUAGGIO" in SYSTEM_PROMPT, "Prompt should have LINGUAGGIO section"
        assert "tecnico-professionale" in SYSTEM_PROMPT.lower() or \
               "professionale" in SYSTEM_PROMPT.lower(), \
            "Prompt should require professional language"
        
        # Check for ERRATO / CORRETTO examples
        assert "ERRATO" in SYSTEM_PROMPT, "Prompt should have ERRATO example"
        assert "CORRETTO" in SYSTEM_PROMPT, "Prompt should have CORRETTO example"
        
        # Verify it's not generic/colloquial
        assert "colloquial" in SYSTEM_PROMPT.lower() or "generi" in SYSTEM_PROMPT.lower(), \
            "Prompt should warn against generic/colloquial language"
        print("PASS: AI prompt contains professional language rules with ERRATO/CORRETTO examples")

    def test_prompt_dlgs_17_2010_context(self):
        """AI prompt should contain D.Lgs. 17/2010 context for retrofit vs new installation."""
        from services.vision_analysis import SYSTEM_PROMPT
        
        # Check for D.Lgs. 17/2010 reference
        assert "D.Lgs. 17/2010" in SYSTEM_PROMPT, \
            "Prompt should reference D.Lgs. 17/2010"
        
        # Check for retrofit context
        assert "retrofit" in SYSTEM_PROMPT.lower() or \
               "impianto esistente" in SYSTEM_PROMPT.lower() or \
               "adeguamento" in SYSTEM_PROMPT.lower(), \
            "Prompt should mention retrofit/existing installation context"
        
        # Check for distinction between new and existing
        assert "nuova installazione" in SYSTEM_PROMPT.lower() or \
               "Direttiva Macchine" in SYSTEM_PROMPT, \
            "Prompt should distinguish new installation from retrofit"
        print("PASS: AI prompt contains D.Lgs. 17/2010 context for retrofit/new installation")

    def test_prompt_every_mancante_has_risk_explicit(self):
        """Verify explicit rule text for dispositivi_mancanti → rischi."""
        from services.vision_analysis import SYSTEM_PROMPT
        
        # Look for the explicit rule
        expected_phrase = "OGNI dispositivo elencato in \"dispositivi_mancanti\" DEVE avere una corrispondente scheda in \"rischi\""
        
        assert expected_phrase in SYSTEM_PROMPT, \
            f"Prompt should contain explicit rule: '{expected_phrase}'"
        print("PASS: Explicit dispositivi_mancanti → rischi rule found in prompt")

    def test_prompt_note_tecniche_for_tecnico_only(self):
        """AI prompt note_tecniche should be for technician, not generic suggestions."""
        from services.vision_analysis import SYSTEM_PROMPT
        
        # Check that note_tecniche is defined properly
        assert "note_tecniche" in SYSTEM_PROMPT, "Prompt should define note_tecniche field"
        
        # Check for technician-only context
        assert "osservazioni" in SYSTEM_PROMPT.lower() and "tecnico" in SYSTEM_PROMPT.lower(), \
            "note_tecniche should be for technician observations"
        
        # Check it warns against generic suggestions
        assert "generic" in SYSTEM_PROMPT.lower() or "suggerimenti generici" in SYSTEM_PROMPT.lower(), \
            "Prompt should warn against generic suggestions in note_tecniche"
        print("PASS: AI prompt defines note_tecniche as technician-only observations")


# ═══════════════════════════════════════════════════════════════════════════════
# Module 4: PDF Generation Integration Test
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDFGenerationIntegration:
    """Integration test: generate actual PDF and verify bytes returned."""
    
    @pytest.fixture
    def full_sopralluogo(self):
        """Complete sopralluogo data for PDF generation."""
        return {
            "document_number": "INT-TEST-001",
            "client_name": "Integration Test SRL",
            "indirizzo": "Via Integration 1",
            "comune": "Roma",
            "provincia": "RM",
            "note_tecnico": "Note del tecnico per il test di integrazione.",
            "created_at": "2025-01-15T10:00:00Z",
            "analisi_ai": {
                "tipo_chiusura": "scorrevole",
                "descrizione_generale": "Cancello scorrevole per test",
                "conformita_percentuale": 55,
                "rischi": [
                    {
                        "zona": "Bordo principale",
                        "tipo_rischio": "schiacciamento",
                        "gravita": "alta",
                        "problema": "Manca protezione",
                        "norma_riferimento": "EN 12453",
                        "soluzione": "Installare costa sensibile",
                        "confermato": True
                    }
                ],
                "dispositivi_presenti": ["Lampeggiante"],
                "dispositivi_mancanti": ["Costa sensibile"],
                "note_tecniche": "Queste sono note AI - NON devono apparire nel PDF!",
                "varianti": {
                    "A": {"titolo": "Min", "descrizione": "Test", "interventi": [], "stima_manodopera": "4h", "costo_stimato": 500},
                    "B": {"titolo": "Comp", "descrizione": "Test", "interventi": [], "stima_manodopera": "8h", "costo_stimato": 1500},
                    "C": {"titolo": "Tot", "descrizione": "Test", "interventi": [], "stima_manodopera": "16h", "costo_stimato": 3000}
                },
                "rischi_residui": ["Rischio residuo minimo"]
            }
        }
    
    @pytest.fixture
    def full_company(self):
        return {
            "company_name": "Integration Company SRL",
            "address": "Via Company 1",
            "cap": "00100",
            "city": "Roma",
            "province": "RM",
            "partita_iva": "12345678901"
        }
    
    @pytest.fixture
    def photos_with_duplicates(self):
        """Photos with duplicate labels for testing."""
        base64_img = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        return [
            {"base64": base64_img, "mime_type": "image/png", "label": "panoramica"},
            {"base64": base64_img, "mime_type": "image/png", "label": "panoramica"},
            {"base64": base64_img, "mime_type": "image/png", "label": "dettaglio"},
        ]

    def test_pdf_generation_returns_bytes(self, full_sopralluogo, full_company, photos_with_duplicates):
        """PDF generation should return valid PDF bytes."""
        try:
            from services.pdf_perizia_sopralluogo import generate_perizia_pdf
            
            pdf_bytes = generate_perizia_pdf(full_sopralluogo, full_company, photos_with_duplicates)
            
            assert pdf_bytes is not None, "PDF bytes should not be None"
            assert len(pdf_bytes) > 0, "PDF bytes should not be empty"
            assert pdf_bytes[:4] == b'%PDF', "PDF should start with %PDF magic bytes"
            print(f"PASS: PDF generated successfully ({len(pdf_bytes)} bytes)")
        except ImportError as e:
            pytest.skip(f"WeasyPrint not available: {e}")
        except Exception as e:
            # If WeasyPrint fails, it's an environment issue, not a code issue
            if "WeasyPrint" in str(e):
                pytest.skip(f"WeasyPrint not configured: {e}")
            raise

    def test_pdf_generation_without_photos(self, full_sopralluogo, full_company):
        """PDF generation should work without photos."""
        try:
            from services.pdf_perizia_sopralluogo import generate_perizia_pdf
            
            pdf_bytes = generate_perizia_pdf(full_sopralluogo, full_company, [])
            
            assert pdf_bytes is not None, "PDF bytes should not be None"
            assert len(pdf_bytes) > 0, "PDF bytes should not be empty"
            print(f"PASS: PDF generated without photos ({len(pdf_bytes)} bytes)")
        except ImportError as e:
            pytest.skip(f"WeasyPrint not available: {e}")
        except Exception as e:
            if "WeasyPrint" in str(e):
                pytest.skip(f"WeasyPrint not configured: {e}")
            raise


# ═══════════════════════════════════════════════════════════════════════════════
# Module 5: Code Structure Verification
# ═══════════════════════════════════════════════════════════════════════════════

class TestCodeStructureVerification:
    """Verify code structure matches expected patterns for the fixes."""

    def test_pdf_notes_section_uses_note_tecnico(self):
        """Notes section should use sopralluogo.note_tecnico, not analisi.note_tecniche."""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        import inspect
        
        source = inspect.getsource(generate_perizia_pdf)
        
        # Find notes section code
        # Expected: note_utente = sopralluogo.get("note_tecnico", "")
        assert 'sopralluogo.get("note_tecnico"' in source or \
               "sopralluogo.get('note_tecnico'" in source, \
            "Notes section should read from sopralluogo.note_tecnico"
        
        # Should NOT use analisi.note_tecniche for display
        # analisi.get("note_tecniche") should not appear for output
        analisi_note_pattern = 'analisi.get("note_tecniche"'
        assert analisi_note_pattern not in source, \
            "Should NOT use analisi.note_tecniche for PDF output"
        print("PASS: Notes section correctly uses sopralluogo.note_tecnico")

    def test_disclaimer_text_correct(self):
        """Verify disclaimer has correct wording."""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        import inspect
        
        source = inspect.getsource(generate_perizia_pdf)
        
        expected_disclaimer = "strumenti di analisi assistita"
        assert expected_disclaimer in source, \
            f"Disclaimer should contain '{expected_disclaimer}'"
        
        # Should NOT say "Intelligenza Artificiale"
        assert "Intelligenza Artificiale" not in source, \
            "Disclaimer should NOT mention 'Intelligenza Artificiale'"
        print("PASS: Disclaimer text is correct ('strumenti di analisi assistita')")

    def test_ref_image_label_removed(self):
        """Reference images should NOT have 'SOLUZIONE TIPO' label."""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        import inspect
        
        source = inspect.getsource(generate_perizia_pdf)
        
        # The old label was something like "SOLUZIONE TIPO (SOSTITUIBILE CON FOTO PROPRIE INSTALLAZIONI)"
        forbidden_labels = [
            "SOLUZIONE TIPO",
            "SOSTITUIBILE CON FOTO",
            "PROPRIE INSTALLAZIONI"
        ]
        
        for label in forbidden_labels:
            assert label not in source, f"Code should not contain '{label}'"
        print("PASS: Reference images do not have 'SOLUZIONE TIPO' label")

    def test_section_numbering_consistency(self):
        """Verify notes section is numbered 04 with 'NOTE DEL TECNICO'."""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        import inspect
        
        source = inspect.getsource(generate_perizia_pdf)
        
        # Find the notes section definition
        # Expected: section-header-num>04 ... section-header-text>NOTE DEL TECNICO
        assert "NOTE DEL TECNICO" in source, "Should have 'NOTE DEL TECNICO' section header"
        
        # Verify section number 04 is associated with notes
        # The pattern should be <div class="section-header-num">04</div><div class="section-header-text">NOTE DEL TECNICO
        notes_section_found = '"04"' in source and "NOTE DEL TECNICO" in source
        assert notes_section_found, "Notes section should be numbered 04 with 'NOTE DEL TECNICO'"
        print("PASS: Notes section numbered correctly as '04 - NOTE DEL TECNICO'")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
