"""
Email Preview Builder — generates email HTML + subject for preview before sending.
Mirrors the exact templates used by email_service.py for actual sending.
Uses company name (sender_name) from config, matching the send templates.
"""
from core.config import settings


def _company():
    return settings.sender_name or "Steel Project Design Srls"


def _fmt_eur(val):
    try:
        v = float(val or 0)
    except (ValueError, TypeError):
        v = 0
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _wrap_body(inner_html: str, accent_color: str = "#1e3a5f", company_name: str = None) -> str:
    """Wrap email content in branded email frame — matches email_service.py exactly."""
    company = company_name or _company()
    return f"""
    <div style="font-family: 'Segoe UI', Tahoma, sans-serif; max-width: 600px; margin: 0 auto; background: #f1f5f9; padding: 32px 16px;">
        <div style="background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06);">
            <div style="background: {accent_color}; padding: 20px 32px; text-align: center;">
                <h1 style="color: white; font-size: 20px; margin: 0; font-weight: 700; letter-spacing: 0.5px;">{company}</h1>
            </div>
            <div style="padding: 28px 32px;">
                {inner_html}
            </div>
        </div>
        <p style="text-align: center; color: #94a3b8; font-size: 11px; margin-top: 16px; line-height: 1.5;">
            Questa email è stata inviata da {company} tramite il sistema gestionale.
        </p>
    </div>
    """


# ── Invoice / Preventivo ──────────────────────────────────────

def build_invoice_email(client_name: str, document_number: str, document_type: str, total: float, company_name: str = None) -> dict:
    display_name = company_name or _company()
    type_labels = {"FT": "Fattura", "NC": "Nota di Credito", "PRV": "Preventivo"}
    doc_label = type_labels.get(document_type, "Documento")
    total_fmt = _fmt_eur(total)
    subject = f"Invio {doc_label} n. {document_number} da {display_name}"
    inner = f"""
        <p style="color: #1e293b; font-size: 15px; line-height: 1.7; margin-top: 0;">
            Gentile <strong>{client_name}</strong>,
        </p>
        <p style="color: #475569; font-size: 15px; line-height: 1.7;">
            in allegato trasmettiamo la {doc_label} n. <strong>{document_number}</strong>.
        </p>
        <div style="background: #f0f4ff; border-radius: 8px; padding: 16px; margin: 20px 0; text-align: center;">
            <p style="color: #64748b; font-size: 12px; margin: 0; text-transform: uppercase; letter-spacing: 1px;">Importo totale</p>
            <p style="color: #1e3a5f; font-size: 28px; font-weight: 700; margin: 6px 0 0 0;">&euro; {total_fmt}</p>
        </div>
        <p style="color: #475569; font-size: 14px; line-height: 1.7;">
            Restiamo a disposizione per qualsiasi chiarimento.
        </p>
        <p style="color: #475569; font-size: 14px; margin-bottom: 0;">Cordiali saluti,<br/><strong>{display_name}</strong></p>
    """
    return {"subject": subject, "html_body": _wrap_body(inner, company_name=display_name)}


# ── DDT ──────────────────────────────────────────────────

def build_ddt_email(client_name: str, ddt_number: str, ddt_type: str) -> dict:
    company = _company()
    type_labels = {"vendita": "Vendita", "conto_lavoro": "Conto Lavoro", "rientro": "Rientro"}
    type_label = type_labels.get(ddt_type, "Trasporto")
    subject = f"Invio DDT n. {ddt_number} ({type_label}) da {company}"
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
        <p style="color: #475569; font-size: 14px; margin-bottom: 0;">Cordiali saluti,<br/><strong>{company}</strong></p>
    """
    return {"subject": subject, "html_body": _wrap_body(inner)}


# ── RdP (Richiesta di Preventivo) ──────────────────────────────

def build_rdp_email(fornitore_name: str, rdp_id: str, commessa_numero: str, company_name: str, num_righe: int) -> dict:
    subject = f"Richiesta Preventivo {rdp_id} — Commessa {commessa_numero} — {company_name}"
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
            disponibilit&agrave; certificati 3.1 ove richiesti.
        </p>
        <p style="color: #475569; font-size: 14px; margin-bottom: 0;">
            In attesa di cortese riscontro, porgiamo distinti saluti.<br/>
            <strong>{company_name}</strong>
        </p>
    """
    return {"subject": subject, "html_body": _wrap_body(inner)}


# ── OdA (Ordine di Acquisto) ──────────────────────────────

def build_oda_email(fornitore_name: str, ordine_id: str, commessa_numero: str, company_name: str, importo_totale: float) -> dict:
    total_fmt = _fmt_eur(importo_totale)
    subject = f"Ordine n. {ordine_id} — Commessa {commessa_numero} — {company_name}"
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
    return {"subject": subject, "html_body": _wrap_body(inner, accent_color="#059669")}


# ── Conto Lavoro DDT ──────────────────────────────

def build_cl_email(fornitore_nome: str, tipo: str, ral: str, commessa_numero: str, company_name: str) -> dict:
    tipo_labels = {"verniciatura": "VERNICIATURA", "zincatura": "ZINCATURA A CALDO", "sabbiatura": "SABBIATURA", "altro": "LAVORAZIONE ESTERNA"}
    tipo_label = tipo_labels.get(tipo, tipo.upper())
    subject = f"DDT Conto Lavoro {tipo_label} — {company_name} — Rif. {commessa_numero}"
    inner = f"""
        <p style="color: #1e293b; font-size: 15px; line-height: 1.7; margin-top: 0;">
            Gentile <strong>{fornitore_nome}</strong>,
        </p>
        <p style="color: #475569; font-size: 15px; line-height: 1.7;">
            in allegato il DDT per lavorazione in conto terzi.
        </p>
        <div style="background: #f5f3ff; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="color: #475569; margin: 0; font-size: 14px;">
                <strong>Tipo:</strong> {tipo_label}<br/>
                <strong>Commessa:</strong> {commessa_numero}
                {"<br/><strong>RAL:</strong> " + ral if ral else ""}
            </p>
        </div>
        <p style="color: #475569; font-size: 14px; margin-bottom: 0;">
            Cordiali saluti,<br/>
            <strong>{company_name}</strong>
        </p>
    """
    return {"subject": subject, "html_body": _wrap_body(inner, accent_color="#7c3aed")}
