"""PDF Preventivo - riusa pdf_invoice_modern."""
from io import BytesIO


def generate_modern_preventivo_pdf(prev: dict, client: dict, company: dict) -> BytesIO:
    from services.pdf_invoice_modern import generate_modern_invoice_pdf
    invoice_like = {
        "invoice_id": prev.get("preventivo_id", ""),
        "number": prev.get("number", ""),
        "doc_type": "PRV",
        "invoice_type_label": "PREVENTIVO",
        "issue_date": prev.get("created_at", ""),
        "payment_type_label": prev.get("payment_type_label", ""),
        "lines": prev.get("lines", []),
        "notes": prev.get("notes", ""),
        "riferimento": prev.get("riferimento") or prev.get("subject", ""),
        "banca": prev.get("banca", ""),
        "iban": prev.get("iban", ""),
        "sconto_globale": prev.get("sconto_globale", 0),
        "scadenze": [],
    }
    buf = generate_modern_invoice_pdf(invoice_like, client, company)
    return buf if isinstance(buf, BytesIO) else BytesIO(buf)
