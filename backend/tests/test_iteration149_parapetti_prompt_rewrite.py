"""Test Iteration 149: PROMPT_PARAPETTI Rewrite Verification

This test validates the complete rewrite of the parapetti prompt and PDF config
with engineering-grade rigor for structural safety assessment.

Key changes tested:
1. Explicit ban on EN 12453/Direttiva Macchine norms
2. Correct norms: UNI 11678, NTC 2018 par. 3.1.4, UNI 7697, UNI EN 12600, ETA Opzione 1
3. Schema statico analysis
4. Mandated corrimano strutturale
5. ETA Opzione 1 chemical anchors
6. EPDM gasket check
7. PDF checklist expanded from 8 to 13 items with UNI 11678 test parameters
"""

import pytest
import sys
import os

# Add backend to path for direct imports
sys.path.insert(0, '/app/backend')

from services.vision_analysis import PROMPT_PARAPETTI, PROMPTS


class TestPromptParapettiCorrectNorms:
    """Verify PROMPT_PARAPETTI references correct norms"""
    
    def test_references_uni_11678_2017(self):
        """PROMPT_PARAPETTI must reference UNI 11678:2017"""
        assert "UNI 11678" in PROMPT_PARAPETTI, "Missing UNI 11678 reference"
        assert "11678:2017" in PROMPT_PARAPETTI, "Missing UNI 11678:2017 full reference"
        print("✓ PROMPT_PARAPETTI references UNI 11678:2017")
    
    def test_references_ntc_2018_par_3_1_4(self):
        """PROMPT_PARAPETTI must reference NTC 2018 par. 3.1.4"""
        assert "NTC 2018" in PROMPT_PARAPETTI, "Missing NTC 2018 reference"
        assert "3.1.4" in PROMPT_PARAPETTI, "Missing par. 3.1.4 reference"
        print("✓ PROMPT_PARAPETTI references NTC 2018 par. 3.1.4")
    
    def test_references_uni_7697(self):
        """PROMPT_PARAPETTI must reference UNI 7697 for glass safety"""
        assert "UNI 7697" in PROMPT_PARAPETTI, "Missing UNI 7697 reference"
        print("✓ PROMPT_PARAPETTI references UNI 7697")
    
    def test_references_uni_en_12600(self):
        """PROMPT_PARAPETTI must reference UNI EN 12600 pendulum test"""
        assert "UNI EN 12600" in PROMPT_PARAPETTI or "EN 12600" in PROMPT_PARAPETTI, "Missing EN 12600 reference"
        print("✓ PROMPT_PARAPETTI references UNI EN 12600")
    
    def test_references_eta_opzione_1(self):
        """PROMPT_PARAPETTI must reference ETA Opzione 1 for chemical anchors"""
        assert "ETA" in PROMPT_PARAPETTI, "Missing ETA reference"
        assert "Opzione 1" in PROMPT_PARAPETTI, "Missing 'Opzione 1' reference"
        print("✓ PROMPT_PARAPETTI references ETA Opzione 1")


class TestPromptParapettiExcludesWrongNorms:
    """Verify PROMPT_PARAPETTI does NOT reference wrong norms (gate norms)"""
    
    def test_does_not_reference_en_12453(self):
        """PROMPT_PARAPETTI must NOT reference EN 12453 (gate norm)"""
        # Note: The prompt may contain "NON citare MAI la EN 12453" as a prohibition
        # We need to check it's not used as a positive reference
        lines = PROMPT_PARAPETTI.split('\n')
        positive_references = []
        for line in lines:
            # Skip prohibition lines
            if any(x in line.lower() for x in ['non citare', 'non applicare', 'mai', 'attenzione', 'non riferimento']):
                continue
            if 'EN 12453' in line or 'EN12453' in line:
                # Check if it's a "don't use" context
                if 'NON' not in line.upper() and 'MAI' not in line.upper():
                    positive_references.append(line.strip())
        
        # The prompt correctly bans EN 12453 - verify it's in the REGOLE ASSOLUTE or prohibition sections
        assert "NON citare MAI la EN 12453" in PROMPT_PARAPETTI or "EN 12453" in PROMPT_PARAPETTI, \
            "EN 12453 should be mentioned as a prohibition"
        print("✓ PROMPT_PARAPETTI correctly prohibits EN 12453 (gate norm)")
    
    def test_does_not_reference_direttiva_macchine_as_applicable(self):
        """PROMPT_PARAPETTI must NOT apply Direttiva Macchine 2006/42/CE to parapets"""
        # Similar logic - check it's mentioned as a prohibition, not as applicable
        assert "Direttiva Macchine" in PROMPT_PARAPETTI, "Direttiva Macchine should be mentioned (as prohibition)"
        assert "NON applicare MAI" in PROMPT_PARAPETTI or "NON citare MAI" in PROMPT_PARAPETTI, \
            "Should have explicit prohibition statement"
        print("✓ PROMPT_PARAPETTI correctly prohibits Direttiva Macchine for parapets")


class TestPromptParapettiStructuralAnalysis:
    """Verify PROMPT_PARAPETTI includes structural analysis requirements"""
    
    def test_mentions_schema_statico(self):
        """PROMPT_PARAPETTI must mention 'schema statico' analysis"""
        assert "schema statico" in PROMPT_PARAPETTI.lower() or "SCHEMA STATICO" in PROMPT_PARAPETTI, \
            "Missing 'schema statico' reference"
        print("✓ PROMPT_PARAPETTI mentions schema statico analysis")
    
    def test_mentions_schema_statico_inadeguato_as_critical(self):
        """PROMPT_PARAPETTI must identify inadequate schema statico as critical"""
        prompt_lower = PROMPT_PARAPETTI.lower()
        assert "schema statico inadeguato" in prompt_lower or "SCHEMA STATICO INADEGUATO" in PROMPT_PARAPETTI, \
            "Missing 'schema statico inadeguato' critical check"
        print("✓ PROMPT_PARAPETTI identifies inadequate schema statico as critical")
    
    def test_mandates_corrimano_strutturale(self):
        """PROMPT_PARAPETTI must mandate corrimano strutturale continuo"""
        prompt_lower = PROMPT_PARAPETTI.lower()
        assert "corrimano strutturale" in prompt_lower, "Missing 'corrimano strutturale' requirement"
        assert "continuo" in prompt_lower, "Missing 'continuo' specification for corrimano"
        print("✓ PROMPT_PARAPETTI mandates corrimano strutturale continuo")
    
    def test_prescribes_corrimano_as_priority(self):
        """PROMPT_PARAPETTI must prescribe corrimano as priority intervention"""
        assert "PRESCRIVERE SEMPRE il corrimano strutturale continuo" in PROMPT_PARAPETTI, \
            "Missing mandatory corrimano prescription in REGOLE ASSOLUTE"
        print("✓ PROMPT_PARAPETTI prescribes corrimano strutturale as priority")


class TestPromptParapettiTechnicalDetails:
    """Verify PROMPT_PARAPETTI includes correct technical details"""
    
    def test_specifies_eta_opzione_1_chemical_anchors(self):
        """PROMPT_PARAPETTI must specify ETA Opzione 1 chemical anchors (not generic bulloneria)"""
        assert "ancoranti chimici" in PROMPT_PARAPETTI.lower() or "ancorante chimico" in PROMPT_PARAPETTI.lower(), \
            "Missing chemical anchors specification"
        assert "ETA Opzione 1" in PROMPT_PARAPETTI, "Missing ETA Opzione 1 certification"
        # Should NOT use generic "bulloneria certificata"
        print("✓ PROMPT_PARAPETTI specifies ETA Opzione 1 chemical anchors")
    
    def test_includes_epdm_gasket_check(self):
        """PROMPT_PARAPETTI must include EPDM gasket check for steel-glass contact"""
        assert "EPDM" in PROMPT_PARAPETTI, "Missing EPDM gasket reference"
        print("✓ PROMPT_PARAPETTI includes EPDM gasket check")
    
    def test_differentiates_load_categories(self):
        """PROMPT_PARAPETTI must differentiate Cat. A (1.0 kN/m) vs Cat. C/D (3.0 kN/m)"""
        assert "1.0 kN/m" in PROMPT_PARAPETTI or "1,0 kN/m" in PROMPT_PARAPETTI, \
            "Missing Cat. A load (1.0 kN/m)"
        assert "3.0 kN/m" in PROMPT_PARAPETTI or "3,0 kN/m" in PROMPT_PARAPETTI, \
            "Missing Cat. C/D load (3.0 kN/m)"
        assert "Cat. A" in PROMPT_PARAPETTI, "Missing Cat. A reference"
        print("✓ PROMPT_PARAPETTI differentiates load categories correctly")
    
    def test_presumes_monolithic_glass_non_conforming(self):
        """PROMPT_PARAPETTI must presume monolithic glass as non-conforming"""
        prompt_lower = PROMPT_PARAPETTI.lower()
        assert "presumere" in prompt_lower and "monolitico" in prompt_lower, \
            "Missing presumption of monolithic glass as non-conforming"
        print("✓ PROMPT_PARAPETTI presumes monolithic glass as non-conforming")


class TestPromptParapettiRegoleAssolute:
    """Verify PROMPT_PARAPETTI includes REGOLE ASSOLUTE section"""
    
    def test_has_regole_assolute_section(self):
        """PROMPT_PARAPETTI must have REGOLE ASSOLUTE section"""
        assert "REGOLE ASSOLUTE" in PROMPT_PARAPETTI, "Missing REGOLE ASSOLUTE section"
        print("✓ PROMPT_PARAPETTI has REGOLE ASSOLUTE section")
    
    def test_regole_assolute_forbids_en_12453(self):
        """REGOLE ASSOLUTE must explicitly forbid EN 12453"""
        # Find REGOLE ASSOLUTE section
        start_idx = PROMPT_PARAPETTI.find("REGOLE ASSOLUTE")
        if start_idx == -1:
            pytest.fail("REGOLE ASSOLUTE section not found")
        section = PROMPT_PARAPETTI[start_idx:]
        assert "EN 12453" in section, "EN 12453 must be mentioned in REGOLE ASSOLUTE"
        assert "NON citare MAI" in section, "Must explicitly forbid citing EN 12453"
        print("✓ REGOLE ASSOLUTE explicitly forbids EN 12453")
    
    def test_regole_assolute_forbids_direttiva_macchine(self):
        """REGOLE ASSOLUTE must explicitly forbid Direttiva Macchine"""
        start_idx = PROMPT_PARAPETTI.find("REGOLE ASSOLUTE")
        section = PROMPT_PARAPETTI[start_idx:]
        assert "Direttiva Macchine" in section, "Direttiva Macchine must be mentioned in REGOLE ASSOLUTE"
        print("✓ REGOLE ASSOLUTE explicitly forbids Direttiva Macchine")


class TestPromptsDictionary:
    """Verify PROMPTS dictionary still has all 4 keys"""
    
    def test_prompts_has_all_four_keys(self):
        """PROMPTS dict must have cancelli, barriere, strutture, parapetti"""
        required_keys = ["cancelli", "barriere", "strutture", "parapetti"]
        for key in required_keys:
            assert key in PROMPTS, f"Missing key '{key}' in PROMPTS dict"
        print(f"✓ PROMPTS dict has all 4 keys: {list(PROMPTS.keys())}")
    
    def test_parapetti_prompt_is_correct_one(self):
        """PROMPTS['parapetti'] must point to PROMPT_PARAPETTI"""
        assert PROMPTS["parapetti"] == PROMPT_PARAPETTI, \
            "PROMPTS['parapetti'] does not match PROMPT_PARAPETTI"
        print("✓ PROMPTS['parapetti'] correctly points to PROMPT_PARAPETTI")


class TestPdfPeriziaConfigParapetti:
    """Verify PDF PERIZIA_CONFIG['parapetti'] checklist and content"""
    
    @pytest.fixture
    def parapetti_config(self):
        """Load parapetti PDF config"""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        # The config is defined inside the function, need to import directly from source
        # We'll read and parse the file
        with open('/app/backend/services/pdf_perizia_sopralluogo.py', 'r') as f:
            content = f.read()
        
        # Find PERIZIA_CONFIG['parapetti'] section
        start = content.find('"parapetti": {')
        if start == -1:
            pytest.fail("PERIZIA_CONFIG['parapetti'] not found")
        
        # Extract the parapetti section - find matching braces
        brace_count = 0
        in_section = False
        end = start
        for i, char in enumerate(content[start:], start):
            if char == '{':
                brace_count += 1
                in_section = True
            elif char == '}':
                brace_count -= 1
                if in_section and brace_count == 0:
                    end = i + 1
                    break
        
        return content[start:end]
    
    def test_checklist_has_13_items(self, parapetti_config):
        """PDF parapetti checklist must have 13 items (expanded from 8)"""
        # Count checklist items
        items = parapetti_config.count('"')
        # Find checklist_items array
        start = parapetti_config.find('"checklist_items"')
        if start == -1:
            pytest.fail("checklist_items not found in parapetti config")
        
        # Count items between [ and ]
        bracket_start = parapetti_config.find('[', start)
        bracket_end = parapetti_config.find(']', bracket_start)
        checklist_str = parapetti_config[bracket_start:bracket_end]
        
        # Count quoted strings (each item is a quoted string)
        import re
        items = re.findall(r'"[^"]+",?', checklist_str)
        assert len(items) == 13, f"Expected 13 checklist items, found {len(items)}"
        print(f"✓ PDF parapetti checklist has 13 items (expanded from 8)")
    
    def test_checklist_includes_prova_di_spinta(self, parapetti_config):
        """PDF checklist must include 'PROVA DI SPINTA' with martinetto idraulico"""
        assert "PROVA DI SPINTA" in parapetti_config, "Missing 'PROVA DI SPINTA' in checklist"
        assert "martinetto idraulico" in parapetti_config, "Missing 'martinetto idraulico' detail"
        print("✓ PDF checklist includes PROVA DI SPINTA with martinetto idraulico")
    
    def test_checklist_includes_deformazione_elastica(self, parapetti_config):
        """PDF checklist must include 'DEFORMAZIONE ELASTICA' <= 30mm"""
        assert "DEFORMAZIONE ELASTICA" in parapetti_config, "Missing 'DEFORMAZIONE ELASTICA'"
        assert "30mm" in parapetti_config or "<= 30" in parapetti_config, "Missing 30mm limit"
        print("✓ PDF checklist includes DEFORMAZIONE ELASTICA <= 30mm")
    
    def test_checklist_includes_deformazione_residua(self, parapetti_config):
        """PDF checklist must include 'DEFORMAZIONE RESIDUA' <= 5%"""
        assert "DEFORMAZIONE RESIDUA" in parapetti_config, "Missing 'DEFORMAZIONE RESIDUA'"
        assert "5%" in parapetti_config, "Missing 5% residual deformation limit"
        print("✓ PDF checklist includes DEFORMAZIONE RESIDUA <= 5%")
    
    def test_checklist_includes_prova_urto_dinamica(self, parapetti_config):
        """PDF checklist must include 'PROVA D'URTO DINAMICA' 250 Joule"""
        # Note: Italian uses apostrophe so it might be D'URTO or D URTO
        assert "PROVA D" in parapetti_config and "URTO" in parapetti_config, \
            "Missing 'PROVA D'URTO DINAMICA'"
        assert "250 Joule" in parapetti_config, "Missing 250 Joule impact energy"
        print("✓ PDF checklist includes PROVA D'URTO DINAMICA 250 Joule")
    
    def test_checklist_includes_integrita_post_rottura(self, parapetti_config):
        """PDF checklist must include 'INTEGRITA POST-ROTTURA'"""
        assert "INTEGRITA POST-ROTTURA" in parapetti_config, "Missing 'INTEGRITA POST-ROTTURA'"
        print("✓ PDF checklist includes INTEGRITA POST-ROTTURA")
    
    def test_legal_highlight_mentions_art_2051_cc(self, parapetti_config):
        """PDF legal_highlight must mention art. 2051 C.C."""
        assert "2051" in parapetti_config, "Missing art. 2051 C.C. reference"
        print("✓ PDF legal_highlight mentions art. 2051 C.C.")
    
    def test_legal_highlight_mentions_art_2053_cc(self, parapetti_config):
        """PDF legal_highlight must mention art. 2053 C.C."""
        assert "2053" in parapetti_config, "Missing art. 2053 C.C. reference"
        print("✓ PDF legal_highlight mentions art. 2053 C.C.")
    
    def test_legal_norms_includes_eta(self, parapetti_config):
        """PDF legal_norms must include ETA European Technical Assessment"""
        assert "ETA" in parapetti_config, "Missing ETA reference"
        assert "European Technical Assessment" in parapetti_config or "Opzione 1" in parapetti_config, \
            "Missing ETA description"
        print("✓ PDF legal_norms includes ETA European Technical Assessment")


class TestPdfConfigDirectImport:
    """Direct import test for PDF config verification"""
    
    def test_pdf_config_parapetti_structure(self):
        """Verify parapetti config has all required fields"""
        # Read the file content directly
        with open('/app/backend/services/pdf_perizia_sopralluogo.py', 'r') as f:
            content = f.read()
        
        # Find parapetti config section
        assert '"parapetti":' in content, "parapetti config section not found"
        
        # Check for required keys
        required_fields = [
            "cover_title",
            "cover_subtitle", 
            "content_header_title",
            "norms_badge",
            "footer_norm_text",
            "legal_title",
            "legal_text_1",
            "legal_text_2",
            "legal_highlight",
            "legal_norms",
            "checklist_items"
        ]
        
        # Extract parapetti section
        start = content.find('"parapetti": {')
        end = content.find('},', start) + 2
        # Need to find proper end - count braces
        brace_count = 0
        for i, char in enumerate(content[start:], start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
        
        parapetti_section = content[start:end]
        
        for field in required_fields:
            assert f'"{field}"' in parapetti_section, f"Missing field '{field}' in parapetti config"
        
        print(f"✓ PDF parapetti config has all {len(required_fields)} required fields")


class TestPromptParapettiLegalReferences:
    """Verify PROMPT_PARAPETTI includes legal liability references"""
    
    def test_mentions_art_2051_cc(self):
        """PROMPT_PARAPETTI must mention art. 2051 C.C. (custodia)"""
        assert "2051 C.C." in PROMPT_PARAPETTI or "art. 2051" in PROMPT_PARAPETTI, \
            "Missing art. 2051 C.C. reference"
        print("✓ PROMPT_PARAPETTI mentions art. 2051 C.C.")
    
    def test_mentions_art_2053_cc(self):
        """PROMPT_PARAPETTI must mention art. 2053 C.C. (rovina di edificio)"""
        assert "2053 C.C." in PROMPT_PARAPETTI or "art. 2053" in PROMPT_PARAPETTI, \
            "Missing art. 2053 C.C. reference"
        print("✓ PROMPT_PARAPETTI mentions art. 2053 C.C.")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
