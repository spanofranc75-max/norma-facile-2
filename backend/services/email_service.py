"""
NormaFacile - Email Service (Resend)
Transactional email service for invoices, DDTs, welcome emails.
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


async def send_welcome_email(to_email: str, user_name: str) -> bool:
    """Send welcome email to new user."""
    if not _init_resend():
        logger.info(f"[EMAIL SKIP] Welcome email to {to_email} (Resend not configured)")
        return False

    try:
        html = f"""
        <div style="font-family: 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 40px 20px;">
            <div style="background: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 24px;">
                    <h1 style="color: #0055FF; font-size: 28px; margin: 0;">NormaFacile</h1>
                    <p style="color: #64748b; font-size: 14px; margin-top: 4px;">Il tuo gestionale per fabbri certificati</p>
                </div>
                <h2 style="color: #1e293b; font-size: 20px;">Benvenuto, {user_name}!</h2>
                <p style="color: #475569; font-size: 15px; line-height: 1.6;">
                    Il tuo account NormaFacile è stato creato con successo.
                    Ora puoi gestire preventivi, fatture, DDT, certificazioni CE e molto altro.
                </p>
                <div style="background: #f0f4ff; border-radius: 8px; padding: 16px; margin: 20px 0;">
                    <p style="color: #0055FF; font-weight: 600; margin: 0 0 8px 0;">Per iniziare:</p>
                    <ul style="color: #475569; font-size: 14px; margin: 0; padding-left: 20px;">
                        <li>Configura i dati aziendali in Impostazioni</li>
                        <li>Carica il logo aziendale</li>
                        <li>Aggiungi il tuo primo cliente</li>
                        <li>Crea il primo preventivo</li>
                    </ul>
                </div>
                <a href="{settings.domain_url}/dashboard" 
                   style="display: inline-block; background: #0055FF; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 15px;">
                    Vai alla Dashboard
                </a>
            </div>
            <p style="text-align: center; color: #94a3b8; font-size: 12px; margin-top: 20px;">
                {settings.sender_name} &mdash; {settings.domain_url}
            </p>
        </div>
        """

        params = {
            "from": f"{settings.sender_name} <{settings.sender_email}>",
            "to": [to_email],
            "subject": f"Benvenuto su NormaFacile, {user_name}!",
            "html": html,
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
) -> bool:
    """Send invoice/document email with optional PDF attachment."""
    if not _init_resend():
        logger.info(f"[EMAIL SKIP] Invoice email to {to_email} (Resend not configured)")
        return False

    type_labels = {
        "FT": "Fattura",
        "NC": "Nota di Credito",
        "PRV": "Preventivo",
    }
    doc_label = type_labels.get(document_type, "Documento")
    total_fmt = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    try:
        html = f"""
        <div style="font-family: 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 40px 20px;">
            <div style="background: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 24px;">
                    <h1 style="color: #0055FF; font-size: 24px; margin: 0;">NormaFacile</h1>
                </div>
                <h2 style="color: #1e293b; font-size: 18px;">Gentile {client_name},</h2>
                <p style="color: #475569; font-size: 15px; line-height: 1.6;">
                    In allegato trova la {doc_label} n. <strong>{document_number}</strong>.
                </p>
                <div style="background: #f0f4ff; border-radius: 8px; padding: 16px; margin: 20px 0; text-align: center;">
                    <p style="color: #64748b; font-size: 13px; margin: 0;">Importo totale</p>
                    <p style="color: #0055FF; font-size: 28px; font-weight: 700; margin: 4px 0 0 0;">&euro; {total_fmt}</p>
                </div>
                <p style="color: #475569; font-size: 14px;">
                    Per qualsiasi chiarimento non esiti a contattarci.
                </p>
                <p style="color: #475569; font-size: 14px;">Cordiali saluti,<br/><strong>{settings.sender_name}</strong></p>
            </div>
            <p style="text-align: center; color: #94a3b8; font-size: 12px; margin-top: 20px;">
                Email inviata tramite {settings.sender_name}
            </p>
        </div>
        """

        params = {
            "from": f"{settings.sender_name} <{settings.sender_email}>",
            "to": [to_email],
            "subject": f"{doc_label} n. {document_number} - {settings.sender_name}",
            "html": html,
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
) -> bool:
    """Send DDT email with optional PDF attachment."""
    if not _init_resend():
        logger.info(f"[EMAIL SKIP] DDT email to {to_email} (Resend not configured)")
        return False

    type_labels = {
        "vendita": "Vendita",
        "conto_lavoro": "Conto Lavoro",
        "rientro": "Rientro",
    }
    type_label = type_labels.get(ddt_type, "Trasporto")

    try:
        html = f"""
        <div style="font-family: 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 40px 20px;">
            <div style="background: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 24px;">
                    <h1 style="color: #0055FF; font-size: 24px; margin: 0;">NormaFacile</h1>
                </div>
                <h2 style="color: #1e293b; font-size: 18px;">Gentile {client_name},</h2>
                <p style="color: #475569; font-size: 15px; line-height: 1.6;">
                    In allegato il Documento di Trasporto n. <strong>{ddt_number}</strong> ({type_label}).
                </p>
                <p style="color: #475569; font-size: 14px;">Cordiali saluti,<br/><strong>{settings.sender_name}</strong></p>
            </div>
        </div>
        """

        params = {
            "from": f"{settings.sender_name} <{settings.sender_email}>",
            "to": [to_email],
            "subject": f"DDT n. {ddt_number} ({type_label}) - {settings.sender_name}",
            "html": html,
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
        html = f"""
        <div style="font-family: 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 40px 20px;">
            <div style="background: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 24px;">
                    <h1 style="color: #0055FF; font-size: 24px; margin: 0;">Richiesta di Preventivo</h1>
                </div>
                <h2 style="color: #1e293b; font-size: 18px;">Spett.le {fornitore_name},</h2>
                <p style="color: #475569; font-size: 15px; line-height: 1.6;">
                    In allegato la nostra richiesta di preventivo (rif. <strong>{rdp_id}</strong>)
                    relativa alla commessa <strong>{commessa_numero}</strong>.
                </p>
                <div style="background: #f0f4ff; border-radius: 8px; padding: 16px; margin: 20px 0;">
                    <p style="color: #0055FF; font-weight: 600; margin: 0;">
                        Materiali richiesti: {num_righe} voci
                    </p>
                </div>
                <p style="color: #475569; font-size: 14px; line-height: 1.6;">
                    Si prega di rispondere indicando prezzi, tempi di consegna e 
                    disponibilità certificati 3.1 ove richiesti.
                </p>
                <p style="color: #475569; font-size: 14px;">
                    In attesa di cortese riscontro, porgiamo distinti saluti.<br/>
                    <strong>{company_name}</strong>
                </p>
            </div>
            <p style="text-align: center; color: #94a3b8; font-size: 12px; margin-top: 20px;">
                Email inviata tramite {settings.sender_name}
            </p>
        </div>
        """

        params = {
            "from": f"{settings.sender_name} <{settings.sender_email}>",
            "to": [to_email],
            "subject": f"Richiesta Preventivo {rdp_id} - Commessa {commessa_numero} - {company_name}",
            "html": html,
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
        html = f"""
        <div style="font-family: 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 40px 20px;">
            <div style="background: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 24px;">
                    <h1 style="color: #059669; font-size: 24px; margin: 0;">Ordine di Acquisto</h1>
                </div>
                <h2 style="color: #1e293b; font-size: 18px;">Spett.le {fornitore_name},</h2>
                <p style="color: #475569; font-size: 15px; line-height: 1.6;">
                    In allegato il nostro ordine di acquisto n. <strong>{ordine_id}</strong>
                    relativo alla commessa <strong>{commessa_numero}</strong>.
                </p>
                <div style="background: #f0fdf4; border-radius: 8px; padding: 16px; margin: 20px 0; text-align: center;">
                    <p style="color: #64748b; font-size: 13px; margin: 0;">Importo ordine</p>
                    <p style="color: #059669; font-size: 28px; font-weight: 700; margin: 4px 0 0 0;">&euro; {total_fmt}</p>
                </div>
                <p style="color: #475569; font-size: 14px; line-height: 1.6;">
                    Si prega di confermare l'ordine e comunicare la data di consegna prevista.
                </p>
                <p style="color: #475569; font-size: 14px;">
                    Distinti saluti,<br/>
                    <strong>{company_name}</strong>
                </p>
            </div>
            <p style="text-align: center; color: #94a3b8; font-size: 12px; margin-top: 20px;">
                Email inviata tramite {settings.sender_name}
            </p>
        </div>
        """

        params = {
            "from": f"{settings.sender_name} <{settings.sender_email}>",
            "to": [to_email],
            "subject": f"Ordine n. {ordine_id} - Commessa {commessa_numero} - {company_name}",
            "html": html,
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
) -> bool:
    """Generic email sender with PDF attachment. Used for Conto Lavoro DDTs."""
    if not _init_resend():
        logger.info(f"[EMAIL SKIP] Generic email to {to_email} (Resend not configured)")
        return False

    try:
        # Convert plain text body to simple HTML
        body_html = body.replace("\n", "<br/>")
        html = f"""
        <div style="font-family: 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 40px 20px;">
            <div style="background: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <p style="color: #1e293b; font-size: 15px; line-height: 1.7;">{body_html}</p>
            </div>
            <p style="text-align: center; color: #94a3b8; font-size: 12px; margin-top: 20px;">
                Email inviata tramite {settings.sender_name}
            </p>
        </div>
        """

        params = {
            "from": f"{settings.sender_name} <{settings.sender_email}>",
            "to": [to_email],
            "subject": subject,
            "html": html,
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
