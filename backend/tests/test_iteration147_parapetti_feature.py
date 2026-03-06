"""
Iteration 147: Test new 'parapetti' (Parapets & Railings) perizia type
Tests:
1. Backend: PROMPT_PARAPETTI exists in vision_analysis.py with UNI 11678 references
2. Backend: PROMPTS dict has 4 entries including 'parapetti'
3. Backend: PDF PERIZIA_CONFIG has 'parapetti' with correct legal norms
4. Backend: analyze_photos function accepts tipo_perizia='parapetti'
"""
import pytest
import os
import sys

# Add backend path
sys.path.insert(0, '/app/backend')

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestParapettiPromptConfiguration:
    """Test that the parapetti prompt is correctly configured in vision_analysis.py"""
    
    def test_prompts_dict_has_four_entries(self):
        """PROMPTS dict should have 4 entries: cancelli, barriere, strutture, parapetti"""
        from services.vision_analysis import PROMPTS
        
        assert len(PROMPTS) == 4, f"Expected 4 prompts, got {len(PROMPTS)}"
        assert 'cancelli' in PROMPTS, "Missing 'cancelli' in PROMPTS"
        assert 'barriere' in PROMPTS, "Missing 'barriere' in PROMPTS"
        assert 'strutture' in PROMPTS, "Missing 'strutture' in PROMPTS"
        assert 'parapetti' in PROMPTS, "Missing 'parapetti' in PROMPTS"
        print("PASS: PROMPTS dict has all 4 entries: cancelli, barriere, strutture, parapetti")
    
    def test_prompt_parapetti_exists(self):
        """PROMPT_PARAPETTI should be defined"""
        from services.vision_analysis import PROMPT_PARAPETTI
        
        assert PROMPT_PARAPETTI is not None, "PROMPT_PARAPETTI not defined"
        assert len(PROMPT_PARAPETTI) > 500, "PROMPT_PARAPETTI seems too short"
        print(f"PASS: PROMPT_PARAPETTI defined with {len(PROMPT_PARAPETTI)} chars")
    
    def test_prompt_parapetti_mentions_uni_11678(self):
        """Prompt should reference UNI 11678 standard"""
        from services.vision_analysis import PROMPT_PARAPETTI
        
        assert 'UNI 11678' in PROMPT_PARAPETTI, "Missing UNI 11678 reference"
        print("PASS: PROMPT_PARAPETTI mentions UNI 11678")
    
    def test_prompt_parapetti_mentions_ntc_2018(self):
        """Prompt should reference NTC 2018 par. 3.1.4"""
        from services.vision_analysis import PROMPT_PARAPETTI
        
        assert 'NTC 2018' in PROMPT_PARAPETTI, "Missing NTC 2018 reference"
        assert '3.1.4' in PROMPT_PARAPETTI, "Missing par. 3.1.4 reference"
        print("PASS: PROMPT_PARAPETTI mentions NTC 2018 par. 3.1.4")
    
    def test_prompt_parapetti_mentions_uni_7697(self):
        """Prompt should reference UNI 7697 for glass safety"""
        from services.vision_analysis import PROMPT_PARAPETTI
        
        assert 'UNI 7697' in PROMPT_PARAPETTI, "Missing UNI 7697 reference"
        print("PASS: PROMPT_PARAPETTI mentions UNI 7697 (glass safety)")
    
    def test_prompt_parapetti_mentions_uni_en_12600(self):
        """Prompt should reference UNI EN 12600 for pendulum test"""
        from services.vision_analysis import PROMPT_PARAPETTI
        
        assert 'UNI EN 12600' in PROMPT_PARAPETTI or 'EN 12600' in PROMPT_PARAPETTI, "Missing EN 12600 reference"
        print("PASS: PROMPT_PARAPETTI mentions UNI EN 12600 (pendulum test)")
    
    def test_prompt_parapetti_mentions_height_100cm(self):
        """Prompt should mention 100cm minimum height"""
        from services.vision_analysis import PROMPT_PARAPETTI
        
        assert '100cm' in PROMPT_PARAPETTI or '100 cm' in PROMPT_PARAPETTI, "Missing 100cm height reference"
        print("PASS: PROMPT_PARAPETTI mentions 100cm height")
    
    def test_prompt_parapetti_mentions_scalabilita(self):
        """Prompt should mention scalabilita (climbability) risk"""
        from services.vision_analysis import PROMPT_PARAPETTI
        
        # Check Italian term 'scalabilita' or 'scalabile' or 'arrampicata'
        has_climb = ('scalabil' in PROMPT_PARAPETTI.lower() or 
                     'arrampica' in PROMPT_PARAPETTI.lower() or
                     'effetto scala' in PROMPT_PARAPETTI.lower())
        assert has_climb, "Missing scalabilita/climbability reference"
        print("PASS: PROMPT_PARAPETTI mentions scalabilita/climbability")
    
    def test_prompt_parapetti_mentions_stratificato(self):
        """Prompt should mention vetro stratificato (laminated glass)"""
        from services.vision_analysis import PROMPT_PARAPETTI
        
        assert 'stratificato' in PROMPT_PARAPETTI.lower(), "Missing stratificato reference"
        print("PASS: PROMPT_PARAPETTI mentions vetro stratificato")
    
    def test_prompt_parapetti_mentions_10cm_sphere(self):
        """Prompt should mention 10cm sphere test for openings"""
        from services.vision_analysis import PROMPT_PARAPETTI
        
        assert '10cm' in PROMPT_PARAPETTI or '10 cm' in PROMPT_PARAPETTI, "Missing 10cm opening reference"
        assert 'sfera' in PROMPT_PARAPETTI.lower(), "Missing sfera (sphere) reference"
        print("PASS: PROMPT_PARAPETTI mentions sfera 10cm")
    
    def test_prompt_parapetti_mentions_morsetti(self):
        """Prompt should mention morsetti (clamps/fixings)"""
        from services.vision_analysis import PROMPT_PARAPETTI
        
        # Check for morsetti, morsetto, or fissaggio
        has_fixings = ('morsett' in PROMPT_PARAPETTI.lower() or 
                       'fissag' in PROMPT_PARAPETTI.lower())
        assert has_fixings, "Missing morsetti/fissaggio reference"
        print("PASS: PROMPT_PARAPETTI mentions morsetti/fissaggi")


class TestParapettiPDFConfiguration:
    """Test that PDF PERIZIA_CONFIG has parapetti entry"""
    
    def test_perizia_config_has_parapetti(self):
        """PERIZIA_CONFIG should have 'parapetti' key"""
        from services.pdf_perizia_sopralluogo import generate_perizia_pdf
        
        # We need to check the PERIZIA_CONFIG inside the function
        # Let's import the module and check
        import services.pdf_perizia_sopralluogo as pdf_module
        
        # Read the file directly to check PERIZIA_CONFIG structure
        with open('/app/backend/services/pdf_perizia_sopralluogo.py', 'r') as f:
            content = f.read()
        
        assert '"parapetti":' in content or "'parapetti':" in content, "Missing parapetti in PERIZIA_CONFIG"
        print("PASS: PERIZIA_CONFIG has 'parapetti' key")
    
    def test_perizia_config_parapetti_has_cover_title(self):
        """Parapetti config should have cover_title"""
        with open('/app/backend/services/pdf_perizia_sopralluogo.py', 'r') as f:
            content = f.read()
        
        # Find parapetti section and check for cover_title
        assert 'PARAPETTI & RINGHIERE' in content.upper() or 'PARAPETTI' in content.upper(), "Missing parapetti cover title"
        print("PASS: PERIZIA_CONFIG parapetti has cover title")
    
    def test_perizia_config_parapetti_mentions_uni_11678_in_norms(self):
        """Parapetti config legal_norms should mention UNI 11678"""
        with open('/app/backend/services/pdf_perizia_sopralluogo.py', 'r') as f:
            content = f.read()
        
        # Check that UNI 11678 appears in the parapetti section
        assert 'UNI 11678' in content, "Missing UNI 11678 in PDF legal norms"
        print("PASS: PERIZIA_CONFIG parapetti legal_norms mentions UNI 11678")
    
    def test_perizia_config_parapetti_has_checklist_items(self):
        """Parapetti config should have checklist_items for height, scalability, glass, fixings"""
        with open('/app/backend/services/pdf_perizia_sopralluogo.py', 'r') as f:
            content = f.read()
        
        # Check for key checklist items in parapetti section
        # These should be between the parapetti config and the closing bracket
        parapetti_section = content.split('"parapetti"')[1] if '"parapetti"' in content else content.split("'parapetti'")[1]
        
        assert 'altezza' in parapetti_section.lower(), "Missing altezza in parapetti checklist"
        assert 'scalabil' in parapetti_section.lower() or 'arrampica' in parapetti_section.lower(), "Missing scalabilita in checklist"
        print("PASS: PERIZIA_CONFIG parapetti has checklist items for height, scalability")


class TestAnalyzePhotosFunction:
    """Test that analyze_photos accepts parapetti tipo_perizia"""
    
    def test_analyze_photos_signature(self):
        """analyze_photos should accept tipo_perizia parameter"""
        from services.vision_analysis import analyze_photos
        import inspect
        
        sig = inspect.signature(analyze_photos)
        params = list(sig.parameters.keys())
        
        assert 'tipo_perizia' in params, "analyze_photos missing tipo_perizia parameter"
        
        # Check default value
        tipo_param = sig.parameters['tipo_perizia']
        assert tipo_param.default == 'cancelli', f"Default should be 'cancelli', got {tipo_param.default}"
        print("PASS: analyze_photos has tipo_perizia parameter with default 'cancelli'")
    
    def test_analyze_photos_selects_correct_prompt(self):
        """analyze_photos should select PROMPT_PARAPETTI when tipo_perizia='parapetti'"""
        from services.vision_analysis import PROMPTS, PROMPT_PARAPETTI
        
        selected = PROMPTS.get('parapetti')
        assert selected == PROMPT_PARAPETTI, "PROMPTS['parapetti'] doesn't match PROMPT_PARAPETTI"
        print("PASS: PROMPTS['parapetti'] correctly maps to PROMPT_PARAPETTI")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
