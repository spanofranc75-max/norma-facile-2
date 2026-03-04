"""
═══════════════════════════════════════════════════════════════════════════
⚠️  TEST DI BLINDATURA — MATCHING OdA  ⚠️
Se questo test fallisce, significa che qualcuno ha rotto la logica di
matching. RIPRISTINARE IMMEDIATAMENTE!
═══════════════════════════════════════════════════════════════════════════

Scenario:
- OdA (Ordine d'Acquisto) ha 2 profili: "Piatto 120x12 S275JR" e "HEB 120"
- Certificato ha 5 profili: FLAT 120X12, FLAT 120X7, HEB 120, FLAT 80X10, FLAT 60X8
- RISULTATO ATTESO: Solo 2 profili devono essere associati alla commessa
  (FLAT 120X12 → PIATTO120X12 match OdA, HEB 120 → HEB120 match OdA)
- Gli altri 3 devono andare in ARCHIVIO, NON alla commessa!
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from routes.commessa_ops import _extract_profile_base, _normalize_profilo


class TestOdAMatchingBlindatura(unittest.TestCase):
    """
    Se questo test fallisce → LA LOGICA È ROTTA.
    Non rimuovere, non commentare, non modificare.
    """

    def test_BLINDATURA_5_profili_cert_solo_2_match_oda(self):
        """
        IL TEST CRITICO: 5 profili nel certificato, OdA ne ha solo 2.
        Solo 2 devono fare match. Gli altri 3 vanno in archivio.
        """
        # OdA descriptions (quello che è stato effettivamente ordinato)
        oda_descriptions = [
            "Piatto 120x12 S275JR",  # → PIATTO120X12
            "HEB 120",               # → HEB120
        ]

        # Certificate profiles (quello che dice il fornitore)
        cert_profiles = [
            "FLAT 120X12",   # → PIATTO120X12 ← DEVE MATCHARE (uguale a OdA)
            "FLAT 120X7",    # → PIATTO120X7  ← NON deve matchare (spessore diverso!)
            "HEB 120",       # → HEB120       ← DEVE MATCHARE
            "FLAT 80X10",    # → PIATTO80X10  ← NON deve matchare (non in OdA)
            "FLAT 60X8",     # → PIATTO60X8   ← NON deve matchare (non in OdA)
        ]

        # Build lookup (same as _match_profili_to_commesse does)
        base_to_commesse = {}
        for desc in oda_descriptions:
            base = _extract_profile_base(desc)
            if base:
                base_to_commesse.setdefault(base, set()).add("com_test")

        # Verify OdA lookup has exactly 2 entries
        self.assertEqual(len(base_to_commesse), 2,
                         f"OdA lookup deve avere 2 profili, ha: {base_to_commesse}")
        self.assertIn("PIATTO120X12", base_to_commesse)
        self.assertIn("HEB120", base_to_commesse)

        # Match each certificate profile
        matched = []
        unmatched = []
        for cert_desc in cert_profiles:
            cert_base = _extract_profile_base(cert_desc)
            if cert_base and cert_base in base_to_commesse:
                matched.append(cert_desc)
            else:
                unmatched.append(cert_desc)

        # CRITICAL ASSERTIONS
        self.assertEqual(len(matched), 2,
                         f"SOLO 2 profili devono matchare! Matched: {matched}")
        self.assertEqual(len(unmatched), 3,
                         f"3 profili devono andare in archivio! Unmatched: {unmatched}")

        self.assertIn("FLAT 120X12", matched, "FLAT 120X12 DEVE matchare con Piatto 120x12")
        self.assertIn("HEB 120", matched, "HEB 120 DEVE matchare con HEB 120")

        self.assertIn("FLAT 120X7", unmatched, "FLAT 120X7 NON deve matchare (spessore 7 ≠ 12)")
        self.assertIn("FLAT 80X10", unmatched, "FLAT 80X10 NON deve matchare")
        self.assertIn("FLAT 60X8", unmatched, "FLAT 60X8 NON deve matchare")

    def test_BLINDATURA_piatto_spessore_diverso_NON_match(self):
        """
        PIATTO 120X12 e PIATTO 120X7 DEVONO avere chiavi DIVERSE.
        Se questo test fallisce, la _extract_profile_base è rotta!
        """
        k1 = _extract_profile_base("FLAT 120X12")
        k2 = _extract_profile_base("FLAT 120X7")
        self.assertNotEqual(k1, k2,
                            "FATAL: FLAT 120X12 e FLAT 120X7 hanno la stessa chiave! "
                            "La logica di matching è ROTTA!")
        self.assertEqual(k1, "PIATTO120X12")
        self.assertEqual(k2, "PIATTO120X7")

    def test_BLINDATURA_profili_standard_solo_numero_principale(self):
        """IPE/HEB estraggono solo il numero principale, non tutte le dimensioni."""
        self.assertEqual(_extract_profile_base("IPE 100"), "IPE100")
        self.assertEqual(_extract_profile_base("HEB 200"), "HEB200")
        # IPE con dimensioni complete → solo il numero principale
        result = _extract_profile_base("IPE 100X55X4.1")
        self.assertEqual(result, "IPE100")

    def test_BLINDATURA_tubo_dimensioni_complete(self):
        """Tubi devono avere TUTTE le dimensioni."""
        k1 = _extract_profile_base("TUBO 60X60X3")
        k2 = _extract_profile_base("TUBO 60X60X5")
        self.assertNotEqual(k1, k2)
        self.assertEqual(k1, "TUBO60X60X3")
        self.assertEqual(k2, "TUBO60X60X5")

    def test_BLINDATURA_angolare_dimensioni_complete(self):
        """Angolari devono avere TUTTE le dimensioni."""
        k1 = _extract_profile_base("ANGOLARE 50X50X5")
        k2 = _extract_profile_base("ANGOLARE 50X50X7")
        self.assertNotEqual(k1, k2)

    def test_BLINDATURA_normalizzazione_flat_piatto(self):
        """FLAT e Piatto devono produrre la stessa chiave."""
        k1 = _extract_profile_base("FLAT 120X12")
        k2 = _extract_profile_base("Piatto 120x12")
        k3 = _extract_profile_base("Barra ferro piatta 120x12 mm S275JR")
        self.assertEqual(k1, k2, "FLAT e Piatto devono matchare!")
        self.assertEqual(k2, k3, "Barra ferro piatta e Piatto devono matchare!")


if __name__ == "__main__":
    unittest.main()
