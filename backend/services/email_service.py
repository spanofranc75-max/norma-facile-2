"""
Email Service (Resend)
Transactional email service for invoices, DDTs, welcome emails.
Uses company name from DB (company_settings.business_name) as sender identity.
"""
import logging
from typing import Optional
from core.config import settings

logger = logging.getLogger(__name__)

try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
    logger.warning("resend package not installed. Email service disabled.")


def _init_resend():
    """Initialize Resend with API key."""
    if not RESEND_AVAILABLE:
        return False
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured. Email service disabled.")
        return False
    resend.api_key = settings.resend_api_key
    return True


async def _get_company_name(user_id: Optional[str] = None) -> str:
    """Fetch company name from DB settings. Falls back to config sender_name."""
    if user_id:
        try:
            from core.database import db
            company = await db.company_settings.find_one(
                {"user_id": user_id}, {"_id": 0, "business_name": 1}
            )
            if company and company.get("business_name"):
                return company["business_name"]
        except Exception:
            pass
    return settings.sender_name


def _email_wrapper(company_name: str, inner_html: str, accent_color: str = "#1e3a5f") -> str:
    """Build consistent email wrapper with company branding."""
    return f"""
    <div style="font-family: 'Segoe UI', Tahoma, sans-serif; max-width: 600px; margin: 0 auto; background: #f1f5f9; padding: 32px 16px;">
        <div style="background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
            <div style="background: {accent_color}; padding: 20px 32px; text-align: center;">
                <h1 style="color: white; font-size: 20px; margin: 0; font-weight: 700; letter-spacing: 0.5px;">{company_name}</h1>
            </div>
            <div style="padding: 28px 32px;">
                {inner_html}
            </div>
        </div>
        <p style="text-align: center; color: #94a3b8; font-size: 11px; margin-top: 16px; line-height: 1.5;">
            Questa email è stata inviata da {company_name} tramite il sistema gestionale.
        </p>
    </div>
    """


async def send_welcome_email(to_email: str, user_name: str, user_id: Optional[str] = None) -> bool:
    """Send welcome email to new user."""
    if not _init_resend():
        logger.info(f"[EMAIL SKIP] Welcome email to {to_email} (Resend not configured)")
        return False

    company = await _get_company_name(user_id)

    try:
        inner = f"""
            <h2 style="color: #1e293b; font-size: 18px; margin-top: 0;">Benvenuto, {user_name}!</h2>
            <p style="color: #475569; font-size: 15px; line-height: 1.7;">
                Il tuo account è stato creato con successo.
                Ora puoi gestire preventivi, fatture, DDT, certificazioni e molto altro.
            </p>
            <div style="background: #f0f4ff; border-radius: 8px; padding: 16px; margin: 20px 0;">
                <p style="color: #1e3a5f; font-weight: 600; margin: 0 0 8px 0;">Per iniziare:</p>
                <ul style="color: #475569; font-size: 14px; margin: 0; padding-left: 20px; line-height: 1.8;">
                    <li>Configura i dati aziendali in Impostazioni</li>
                    <li>Carica il logo aziendale</li>
                    <li>Aggiungi il tuo primo cliente</li>
                    <li>Crea il primo preventivo</li>
                </ul>
            </div>
            <div style="text-align: center; margin-top: 24px;">
                <a href="{settings.domain_url}/dashboard"
                   style="display: inline-block; background: #1e3a5f; color: white; padding: 12px 28px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px;">
                    Vai alla Dashboard
                </a>
            </div>
        """

        params = {
            "from": f"{company} <{settings.sender_email}>",
            "to": [to_email],
            "subject": f"Benvenuto — {company}",
            "html": _email_wrapper(company, inner),
        }
        resend.Emails.send(params)
        logger.info(f"[EMAIL] Welcome email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] Welcome email to {to_email}: {e}")
        return False


async def send_invoice_email(
    to_email: str,
    client_name: str,
    document_number: str,
    document_type: str,
    total: float,
    pdf_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
    user_id: Optional[str] = None,
    commessa_ref: Optional[str] = None,
) -> bool:
    """Send invoice/document email with optional PDF attachment."""
    if not _init_resend():
        logger.info(f"[EMAIL SKIP] Invoice email to {to_email} (Resend not configured)")
        return False

    company = await _get_company_name(user_id)

    type_labels = {
        "FT": "Fattura",
        "NC": "Nota di Credito",
        "PRV": "Preventivo",
    }
    doc_label = type_labels.get(document_type, "Documento")
    total_fmt = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    commessa_line = f" per la commessa <strong>{commessa_ref}</strong>" if commessa_ref else ""

    try:
        inner = f"""
            <p style="color: #1e293b; font-size: 15px; line-height: 1.7; margin-top: 0;">
                Gentile <strong>{client_name}</strong>,
            </p>
            <p style="color: #475569; font-size: 15px; line-height: 1.7;">
                in allegato trasmettiamo la {doc_label} n. <strong>{document_number}</strong>{commessa_line}.
            </p>
            <div style="background: #f0f4ff; border-radius: 8px; padding: 16px; margin: 20px 0; text-align: center;">
                <p style="color: #64748b; font-size: 12px; margin: 0; text-transform: uppercase; letter-spacing: 1px;">Importo totale</p>
                <p style="color: #1e3a5f; font-size: 28px; font-weight: 700; margin: 6px 0 0 0;">&euro; {total_fmt}</p>
            </div>
            <p style="color: #475569; font-size: 14px; line-height: 1.7;">
                Restiamo a disposizione per qualsiasi chiarimento.
            </p>
            <p style="color: #475569; font-size: 14px; margin-bottom: 0;">
                Cordiali saluti,<br/><strong>{company}</strong>
            </p>
        """

        params = {
            "from": f"{company} <{settings.sender_email}>",
            "to": [to_email],
            "subject": f"Invio {doc_label} n. {document_number} da {company}",
            "html": _email_wrapper(company, inner),
        }

        if pdf_bytes and filename:
            import base64
            params["attachments"] = [{
                "filename": filename,
                "content": base64.b64encode(pdf_bytes).decode("utf-8"),
                "content_type": "application/pdf",
            }]

        resend.Emails.send(params)
        logger.info(f"[EMAIL] {doc_label} {document_number} sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] Invoice email to {to_email}: {e}")
        return False


async def send_ddt_email(
    to_email: str,
    client_name: str,
    ddt_number: str,
    ddt_type: str,
    pdf_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
    user_id: Optional[str] = None,
) -> bool:
    """Send DDT email with optional PDF attachment."""
    if not _init_resend():
        logger.info(f"[EMAIL SKIP] DDT email to {to_email} (Resend not configured)")
        return False

    company = await _get_company_name(user_id)

    type_labels = {
        "vendita": "Vendita",
        "conto_lavoro": "Conto Lavoro",
        "rientro": "Rientro",
    }
    type_label = type_labels.get(ddt_type, "Trasporto")

    try:
        inner = f"""
            <p style="color: #1e293b; font-size: 15px; line-height: 1.7; margin-top: 0;">
                Gentile <strong>{client_name}</strong>,
            </p>
            <p style="color: #475569; font-size: 15px; line-height: 1.7;">
                in allegato trasmettiamo il Documento di Trasporto n. <strong>{ddt_number}</strong> ({type_label}).
            </p>
            <p style="color: #475569; font-size: 14px; line-height: 1.7;">
                Restiamo a disposizione per qualsiasi chiarimento.
            </p>
            <p style="color: #475569; font-size: 14px; margin-bottom: 0;">
                Cordiali saluti,<br/><strong>{company}</strong>
            </p>
        """

        params = {
            "from": f"{company} <{settings.sender_email}>",
            "to": [to_email],
            "subject": f"Invio DDT n. {ddt_number} ({type_label}) da {company}",
            "html": _email_wrapper(company, inner),
        }

        if pdf_bytes and filename:
            import base64
            params["attachments"] = [{
                "filename": filename,
                "content": base64.b64encode(pdf_bytes).decode("utf-8"),
                "content_type": "application/pdf",
            }]

        resend.Emails.send(params)
        logger.info(f"[EMAIL] DDT {ddt_number} sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] DDT email to {to_email}: {e}")
        return False


async def send_rdp_email(
    to_email: str,
    fornitore_name: str,
    rdp_id: str,
    commessa_numero: str,
    company_name: str,
    num_righe: int,
    pdf_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
) -> bool:
    """Send Request for Quote (RdP) email to supplier with PDF attachment."""
    if not _init_resend():
        logger.info(f"[EMAIL SKIP] RdP email to {to_email} (Resend not configured)")
        return False

    try:
        inner = f"""
            <p style="color: #1e293b; font-size: 15px; line-height: 1.7; margin-top: 0;">
                Spett.le <strong>{fornitore_name}</strong>,
            </p>
            <p style="color: #475569; font-size: 15px; line-height: 1.7;">
                in allegato la nostra richiesta di preventivo (rif. <strong>{rdp_id}</strong>)
                relativa alla commessa <strong>{commessa_numero}</strong>.
            </p>
            <div style="background: #f0f4ff; border-radius: 8px; padding: 16px; margin: 20px 0;">
                <p style="color: #1e3a5f; font-weight: 600; margin: 0;">
                    Materiali richiesti: {num_righe} voci
                </p>
            </div>
            <p style="color: #475569; font-size: 14px; line-height: 1.7;">
                Si prega di rispondere indicando prezzi, tempi di consegna e
                disponibilità certificati 3.1 ove richiesti.
            </p>
            <p style="color: #475569; font-size: 14px; margin-bottom: 0;">
                In attesa di cortese riscontro, porgiamo distinti saluti.<br/>
                <strong>{company_name}</strong>
            </p>
        """

        params = {
            "from": f"{company_name} <{settings.sender_email}>",
            "to": [to_email],
            "subject": f"Richiesta Preventivo {rdp_id} — Commessa {commessa_numero} — {company_name}",
            "html": _email_wrapper(company_name, inner),
        }

        if pdf_bytes and filename:
            import base64
            params["attachments"] = [{
                "filename": filename,
                "content": base64.b64encode(pdf_bytes).decode("utf-8"),
                "content_type": "application/pdf",
            }]

        resend.Emails.send(params)
        logger.info(f"[EMAIL] RdP {rdp_id} sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] RdP email to {to_email}: {e}")
        return False


async def send_oda_email(
    to_email: str,
    fornitore_name: str,
    ordine_id: str,
    commessa_numero: str,
    company_name: str,
    importo_totale: float,
    pdf_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
) -> bool:
    """Send Purchase Order (OdA) email to supplier with PDF attachment."""
    if not _init_resend():
        logger.info(f"[EMAIL SKIP] OdA email to {to_email} (Resend not configured)")
        return False

    total_fmt = f"{importo_totale:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    try:
        inner = f"""
            <p style="color: #1e293b; font-size: 15px; line-height: 1.7; margin-top: 0;">
                Spett.le <strong>{fornitore_name}</strong>,
            </p>
            <p style="color: #475569; font-size: 15px; line-height: 1.7;">
                in allegato il nostro ordine di acquisto n. <strong>{ordine_id}</strong>
                relativo alla commessa <strong>{commessa_numero}</strong>.
            </p>
            <div style="background: #f0fdf4; border-radius: 8px; padding: 16px; margin: 20px 0; text-align: center;">
                <p style="color: #64748b; font-size: 12px; margin: 0; text-transform: uppercase; letter-spacing: 1px;">Importo ordine</p>
                <p style="color: #059669; font-size: 28px; font-weight: 700; margin: 6px 0 0 0;">&euro; {total_fmt}</p>
            </div>
            <p style="color: #475569; font-size: 14px; line-height: 1.7;">
                Si prega di confermare l'ordine e comunicare la data di consegna prevista.
            </p>
            <p style="color: #475569; font-size: 14px; margin-bottom: 0;">
                Distinti saluti,<br/>
                <strong>{company_name}</strong>
            </p>
        """

        params = {
            "from": f"{company_name} <{settings.sender_email}>",
            "to": [to_email],
            "subject": f"Ordine n. {ordine_id} — Commessa {commessa_numero} — {company_name}",
            "html": _email_wrapper(company_name, inner, accent_color="#059669"),
        }

        if pdf_bytes and filename:
            import base64
            params["attachments"] = [{
                "filename": filename,
                "content": base64.b64encode(pdf_bytes).decode("utf-8"),
                "content_type": "application/pdf",
            }]

        resend.Emails.send(params)
        logger.info(f"[EMAIL] OdA {ordine_id} sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] OdA email to {to_email}: {e}")
        return False


async def send_email_with_attachment(
    to_email: str,
    subject: str,
    body: str,
    pdf_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
    user_id: Optional[str] = None,
) -> bool:
    """Generic email sender with PDF attachment. Used for Conto Lavoro DDTs."""
    if not _init_resend():
        logger.info(f"[EMAIL SKIP] Generic email to {to_email} (Resend not configured)")
        return False

    company = await _get_company_name(user_id)

    try:
        body_html = body.replace("\n", "<br/>")
        inner = f"""
            <p style="color: #1e293b; font-size: 15px; line-height: 1.7; margin: 0;">{body_html}</p>
        """

        params = {
            "from": f"{company} <{settings.sender_email}>",
            "to": [to_email],
            "subject": subject,
            "html": _email_wrapper(company, inner),
        }

        if pdf_bytes and filename:
            import base64 as b64
            params["attachments"] = [{
                "filename": filename,
                "content": b64.b64encode(pdf_bytes).decode("utf-8"),
                "content_type": "application/pdf",
            }]

        resend.Emails.send(params)
        logger.info(f"[EMAIL] Generic email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] Generic email to {to_email}: {e}")
        return False
