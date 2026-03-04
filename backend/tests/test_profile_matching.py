"""
Unit tests for _extract_profile_base and material traceability matching logic.
Tests that:
- Different dimensions generate unique keys (PIATTO120X12 != PIATTO120X7)
- Standard profiles extract correctly (IPE100, HEB200)
- Product codes are parsed correctly
- Edge cases with spaces around X work
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from routes.commessa_ops import _extract_profile_base


class TestExtractProfileBase(unittest.TestCase):
    """Test _extract_profile_base generates dimension-specific keys."""

    # ── FLATS (PIATTO) ──
    def test_flat_120x12(self):
        self.assertEqual(_extract_profile_base("FLAT 120X12"), "PIATTO120X12")

    def test_flat_120x7(self):
        self.assertEqual(_extract_profile_base("FLAT 120X7"), "PIATTO120X7")

    def test_flat_different_thicknesses_unique(self):
        """Core bug test: FLAT 120X12 and FLAT 120X7 MUST produce different keys."""
        key1 = _extract_profile_base("FLAT 120X12")
        key2 = _extract_profile_base("FLAT 120X7")
        self.assertNotEqual(key1, key2, "FLAT 120X12 and FLAT 120X7 must have different keys!")
        self.assertEqual(key1, "PIATTO120X12")
        self.assertEqual(key2, "PIATTO120X7")

    def test_piatto_120x12_italian(self):
        self.assertEqual(_extract_profile_base("Piatto 120x12"), "PIATTO120X12")

    def test_barra_ferro_piatta(self):
        self.assertEqual(_extract_profile_base("Barra ferro piatta 120x12 mm S275JR"), "PIATTO120X12")

    def test_piatto_with_spaces_around_x(self):
        """Edge case: spaces around x separator."""
        self.assertEqual(_extract_profile_base("FLAT 120 x 12"), "PIATTO120X12")

    def test_piatto_with_multiplication_sign(self):
        self.assertEqual(_extract_profile_base("PIATTO 120×12"), "PIATTO120X12")

    def test_product_code_fepilc(self):
        self.assertEqual(_extract_profile_base("FEPILC-120X12"), "PIATTO120X12")

    def test_product_code_fepilc_with_spaces(self):
        self.assertEqual(_extract_profile_base("FEPILC-120 X 12"), "PIATTO120X12")

    # ── STANDARD PROFILES ──
    def test_ipe_100(self):
        self.assertEqual(_extract_profile_base("IPE 100"), "IPE100")

    def test_ipe_100_with_extra_info(self):
        self.assertEqual(_extract_profile_base("Trave IPE 100 in S275 JR"), "IPE100")

    def test_ipe_200(self):
        self.assertEqual(_extract_profile_base("IPE 200"), "IPE200")

    def test_heb_120(self):
        self.assertEqual(_extract_profile_base("HEB 120"), "HEB120")

    def test_heb_200(self):
        self.assertEqual(_extract_profile_base("HEB 200"), "HEB200")

    def test_upn_100(self):
        self.assertEqual(_extract_profile_base("UPN 100"), "UPN100")

    def test_channel_as_upn(self):
        self.assertEqual(_extract_profile_base("CHANNEL 100"), "UPN100")

    # ── TUBES ──
    def test_tubo_60x60x3(self):
        self.assertEqual(_extract_profile_base("TUBO 60X60X3"), "TUBO60X60X3")

    def test_tubo_ferro_quadro(self):
        self.assertEqual(_extract_profile_base("Tubo ferro quadro 60x60x3"), "TUBO60X60X3")

    def test_tubo_different_sizes_unique(self):
        key1 = _extract_profile_base("TUBO 60X60X3")
        key2 = _extract_profile_base("TUBO 60X60X5")
        self.assertNotEqual(key1, key2)

    # ── ANGLES ──
    def test_angolare_50x50x5(self):
        self.assertEqual(_extract_profile_base("ANGOLARE 50X50X5"), "ANGOLARE50X50X5")

    def test_angle_english(self):
        self.assertEqual(_extract_profile_base("ANGLE 50X50X5"), "ANGOLARE50X50X5")

    def test_elle_profile(self):
        self.assertEqual(_extract_profile_base("Prof. ferro a elle 50x50x5"), "L50X50X5")

    # ── EDGE CASES ──
    def test_empty_string(self):
        self.assertEqual(_extract_profile_base(""), "")

    def test_none(self):
        self.assertEqual(_extract_profile_base(None), "")

    def test_no_match(self):
        self.assertEqual(_extract_profile_base("Bulloni M10"), "")

    def test_ipe_with_full_dimensions(self):
        """IPE should only use main size, not full dimensions."""
        result = _extract_profile_base("IPE 100X55X4.1")
        self.assertEqual(result, "IPE100")


if __name__ == "__main__":
    unittest.main()
