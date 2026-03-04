"""PDF generation service for invoices — WeasyPrint unified template."""
from io import BytesIO
from datetime import datetime
from typing import Optional
import logging
from services.pdf_template import (
    fmt_it, safe, build_header_html, compute_iva_groups,
    build_totals_html, build_conditions_html, render_pdf, format_date,
)

logger = logging.getLogger(__name__)

DOC_TYPE_NAMES = {
    "FT": "FATTURA",
    "PRV": "PREVENTIVO",
    "DDT": "DOCUMENTO DI TRASPORTO",
    "NC": "NOTA DI CREDITO",
}

PAYMENT_METHOD_NAMES = {
    "bonifico": "Bonifico Bancario",
    "contanti": "Contanti",
    "carta": "Carta di Credito",
    "assegno": "Assegno",
    "riba": "RiBa",
    "altro": "Altro",
}


class PDFService:
    """Generate professional Italian invoice PDFs via WeasyPrint."""

    @staticmethod
    def format_currency(value: float) -> str:
        return f"\u20ac {fmt_it(value)}"

    @staticmethod
    def format_date(d) -> str:
        return format_date(d)

    @staticmethod
    def generate_invoice_pdf(invoice: dict, client: dict, company: dict) -> bytes:
        from services.pdf_invoice_modern import generate_modern_invoice_pdf
        return generate_modern_invoice_pdf(invoice, client, company)


pdf_service = PDFService()
