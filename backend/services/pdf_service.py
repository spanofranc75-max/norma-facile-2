"""PDF generation service - usa pdf_invoice_modern per layout professionale."""
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class PDFService:
    @staticmethod
    def generate_invoice_pdf(invoice: dict, client: dict, company: dict) -> bytes:
        """Genera PDF fattura con layout professionale (pdf_invoice_modern)."""
        from services.pdf_invoice_modern import generate_modern_invoice_pdf
        buf = generate_modern_invoice_pdf(invoice, client, company)
        if isinstance(buf, BytesIO):
            return buf.getvalue()
        return buf


pdf_service = PDFService()
