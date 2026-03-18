"""Test PDF Invoice Modern — verifica layout ReportLab.

Testa:
  - Generazione PDF fattura con tutti i campi
  - Generazione PDF preventivo con condizioni vendita
  - Caratteri speciali (€, •, à, è, —)
  - Scadenze pagamento
  - Ritenuta d'acconto
  - Caso minimo (dati mancanti)
"""
import pytest
from services.pdf_invoice_modern import generate_modern_invoice_pdf, _fmt, _date


# ─── Dati di test ───

COMPANY = {
    "business_name": "Steel Project Design Srls",
    "address": "Via Industria 15",
    "cap": "36100",
    "city": "Vicenza",
    "province": "VI",
    "partita_iva": "04287400241",
    "codice_fiscale": "04287400241",
    "phone": "+39 0444 123456",
    "email": "info@steelprojectdesign.it",
    "bank_details": {
        "bank_name": "Intesa Sanpaolo",
        "iban": "IT60X0306909606100000012345",
        "bic_swift": "BCITITMM",
    },
    "condizioni_vendita": "I prezzi si intendono franco partenza.\nPagamento nei termini indicati.",
}

CLIENT = {
    "business_name": "Costruzioni Rossi S.r.l.",
    "address": "Via Roma 42",
    "cap": "20100",
    "city": "Milano",
    "province": "MI",
    "partita_iva": "12345678901",
    "codice_fiscale": "RSSMRC80A01F205X",
    "codice_sdi": "ABCDEFG",
    "pec": "rossi@pec.it",
}

INVOICE_FT = {
    "document_type": "FT",
    "document_number": "FT-7/2026",
    "issue_date": "2026-02-27",
    "due_date": "2026-03-29",
    "payment_method": "bonifico",
    "payment_terms": "30gg",
    "payment_type_label": "Bonifico Bancario 30gg DFFM",
    "notes": "Nota con caratteri: \u00e0, \u00e8, \u00e9, \u00f2, \u00f9, \u20ac",
    "lines": [
        {
            "description": "Struttura metallica EN 1090-1 EXC3",
            "quantity": 1,
            "unit_price": 5800.00,
            "vat_rate": "22",
            "line_total": 5800.00,
        },
        {
            "description": "Zincatura a caldo",
            "quantity": 2,
            "unit_price": 450.00,
            "vat_rate": "22",
            "line_total": 900.00,
        },
    ],
    "totals": {},
    "scadenze_pagamento": [
        {"rata": 1, "data_scadenza": "2026-03-29", "quota_pct": 50, "importo": 4331.00, "pagata": False},
        {"rata": 2, "data_scadenza": "2026-04-29", "quota_pct": 50, "importo": 4270.00, "pagata": False},
    ],
}


class TestPDFInvoiceModern:
    """Test generazione PDF fattura moderna."""

    def test_generate_fattura_pdf(self):
        """Genera PDF fattura con tutti i campi."""
        pdf = generate_modern_invoice_pdf(INVOICE_FT, CLIENT, COMPANY)
        assert isinstance(pdf, bytes)
        assert len(pdf) > 1000
        assert pdf[:5] == b"%PDF-"

    def test_generate_preventivo_pdf(self):
        """Genera PDF preventivo con pagina condizioni."""
        prv = {**INVOICE_FT, "document_type": "PRV", "document_number": "PRV-15/2026"}
        pdf = generate_modern_invoice_pdf(prv, CLIENT, COMPANY)
        assert isinstance(pdf, bytes)
        assert len(pdf) > 1000
        assert pdf[:5] == b"%PDF-"

    def test_generate_nota_credito(self):
        """Genera PDF nota di credito."""
        nc = {**INVOICE_FT, "document_type": "NC", "document_number": "NC-3/2026"}
        pdf = generate_modern_invoice_pdf(nc, CLIENT, COMPANY)
        assert isinstance(pdf, bytes)
        assert pdf[:5] == b"%PDF-"

    def test_minimal_data(self):
        """Genera PDF con dati minimi (no scadenze, no note, no banca)."""
        invoice = {
            "document_type": "FT",
            "document_number": "FT-1/2026",
            "issue_date": "2026-01-15",
            "lines": [
                {"description": "Articolo test", "quantity": 1, "unit_price": 100, "vat_rate": "22", "line_total": 100},
            ],
            "totals": {},
        }
        pdf = generate_modern_invoice_pdf(invoice, {"business_name": "Test"}, {"business_name": "Azienda"})
        assert isinstance(pdf, bytes)
        assert pdf[:5] == b"%PDF-"

    def test_ritenuta_acconto(self):
        """Genera PDF con ritenuta d'acconto."""
        inv = {**INVOICE_FT, "totals": {"ritenuta": 200.0}}
        pdf = generate_modern_invoice_pdf(inv, CLIENT, COMPANY)
        assert isinstance(pdf, bytes)
        assert len(pdf) > 1000

    def test_special_characters_in_pdf(self):
        """Verifica che i caratteri speciali siano presenti nel PDF."""
        pdf = generate_modern_invoice_pdf(INVOICE_FT, CLIENT, COMPANY)
        try:
            from pdfminer.high_level import extract_text
            from io import BytesIO
            text = extract_text(BytesIO(pdf))
            assert "\u20ac" in text, "Euro symbol missing"
            assert "Costruzioni Rossi" in text, "Client name missing"
            assert "Steel Project Design" in text, "Company name missing"
            assert "7/2026" in text, "Doc number missing"
            assert "Rata 1" in text, "Payment schedule missing"
            assert "Intesa Sanpaolo" in text, "Bank info missing"
            assert "NormaFacile" in text, "Footer missing"
            assert "EN 1090-1 EXC3" in text, "Certification footer missing"
        except ImportError:
            pytest.skip("pdfminer non installato")

    def test_empty_lines(self):
        """Genera PDF senza articoli (caso edge)."""
        inv = {**INVOICE_FT, "lines": []}
        pdf = generate_modern_invoice_pdf(inv, CLIENT, COMPANY)
        assert isinstance(pdf, bytes)
        assert pdf[:5] == b"%PDF-"


class TestUtilityFunctions:
    """Test funzioni utility."""

    def test_fmt_italian(self):
        assert _fmt(1234.56) == "1.234,56"
        assert _fmt(0) == "0,00"
        assert _fmt(None) == "0,00"
        assert _fmt("abc") == "0,00"
        assert _fmt(100) == "100,00"

    def test_date_format(self):
        assert _date("2026-02-27") == "27/02/2026"
        assert _date("2026-02-27T08:40:00") == "27/02/2026"
        assert _date("") == ""
        assert _date(None) == ""
