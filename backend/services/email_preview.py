"""
Email Preview Builder — generates email HTML + subject for preview before sending.
Mirrors the exact templates used by email_service.py for actual sending.
"""
from core.config import settings


def _sender_name():
    return settings.sender_name or "NormaFacile"


def _fmt_eur(val):
    try:
        v = float(val or 0)
    except (ValueError, TypeError):
        v = 0
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _wrap_body(inner_html: str) -> str:
    """Wrap email content in the standard NormaFacile email frame."""
    return f"""
    <div style="font-family: 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 40px 20px;">
        <div style="background: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            {inner_html}
        </div>
        <p style="text-align: center; color: #94a3b8; font-size: 12px; margin-top: 20px;">
            Email inviata tramite {_sender_name()}
        </p>
    </div>
    """


# ── Invoice / Preventivo ──────────────────────────────────────

def build_invoice_email(client_name: str, document_number: str, document_type: str, total: float) -> dict:
    type_labels = {"FT": "Fattura", "NC": "Nota di Credito", "PRV": "Preventivo"}
    doc_label = type_labels.get(document_type, "Documento")
    total_fmt = _fmt_eur(total)
    subject = f"{doc_label} n. {document_number} - {_sender_name()}"
    inner = f"""
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
        <p style="color: #475569; font-size: 14px;">Cordiali saluti,<br/><strong>{_sender_name()}</strong></p>
    """
    return {"subject": subject, "html_body": _wrap_body(inner)}


# ── DDT ──────────────────────────────────────────────────

def build_ddt_email(client_name: str, ddt_number: str, ddt_type: str) -> dict:
    type_labels = {"vendita": "Vendita", "conto_lavoro": "Conto Lavoro", "rientro": "Rientro"}
    type_label = type_labels.get(ddt_type, "Trasporto")
    subject = f"DDT n. {ddt_number} ({type_label}) - {_sender_name()}"
    inner = f"""
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #0055FF; font-size: 24px; margin: 0;">NormaFacile</h1>
        </div>
        <h2 style="color: #1e293b; font-size: 18px;">Gentile {client_name},</h2>
        <p style="color: #475569; font-size: 15px; line-height: 1.6;">
            In allegato il Documento di Trasporto n. <strong>{ddt_number}</strong> ({type_label}).
        </p>
        <p style="color: #475569; font-size: 14px;">Cordiali saluti,<br/><strong>{_sender_name()}</strong></p>
    """
    return {"subject": subject, "html_body": _wrap_body(inner)}


# ── RdP (Richiesta di Preventivo) ──────────────────────────────

def build_rdp_email(fornitore_name: str, rdp_id: str, commessa_numero: str, company_name: str, num_righe: int) -> dict:
    subject = f"Richiesta Preventivo {rdp_id} - Commessa {commessa_numero} - {company_name}"
    inner = f"""
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
            disponibilit&agrave; certificati 3.1 ove richiesti.
        </p>
        <p style="color: #475569; font-size: 14px;">
            In attesa di cortese riscontro, porgiamo distinti saluti.<br/>
            <strong>{company_name}</strong>
        </p>
    """
    return {"subject": subject, "html_body": _wrap_body(inner)}


# ── OdA (Ordine di Acquisto) ──────────────────────────────

def build_oda_email(fornitore_name: str, ordine_id: str, commessa_numero: str, company_name: str, importo_totale: float) -> dict:
    total_fmt = _fmt_eur(importo_totale)
    subject = f"Ordine n. {ordine_id} - Commessa {commessa_numero} - {company_name}"
    inner = f"""
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
    """
    return {"subject": subject, "html_body": _wrap_body(inner)}


# ── Conto Lavoro DDT ──────────────────────────────

def build_cl_email(fornitore_nome: str, tipo: str, ral: str, commessa_numero: str, company_name: str) -> dict:
    tipo_labels = {"verniciatura": "VERNICIATURA", "zincatura": "ZINCATURA A CALDO", "sabbiatura": "SABBIATURA", "altro": "LAVORAZIONE ESTERNA"}
    tipo_label = tipo_labels.get(tipo, tipo.upper())
    ral_note = f"\nColore RAL: {ral}" if ral else ""
    subject = f"DDT Conto Lavoro {tipo_label} — {company_name} — Rif. {commessa_numero}"
    inner = f"""
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #7c3aed; font-size: 24px; margin: 0;">DDT Conto Lavoro</h1>
            <p style="color: #8b5cf6; font-size: 16px; margin-top: 4px;">{tipo_label}</p>
        </div>
        <h2 style="color: #1e293b; font-size: 18px;">Gentile {fornitore_nome},</h2>
        <p style="color: #475569; font-size: 15px; line-height: 1.6;">
            In allegato il DDT per lavorazione in conto terzi.
        </p>
        <div style="background: #f5f3ff; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="color: #475569; margin: 0; font-size: 14px;">
                <strong>Tipo:</strong> {tipo_label}<br/>
                <strong>Commessa:</strong> {commessa_numero}
                {"<br/><strong>RAL:</strong> " + ral if ral else ""}
            </p>
        </div>
        <p style="color: #475569; font-size: 14px;">
            Cordiali saluti,<br/>
            <strong>{company_name}</strong>
        </p>
    """
    return {"subject": subject, "html_body": _wrap_body(inner)}
