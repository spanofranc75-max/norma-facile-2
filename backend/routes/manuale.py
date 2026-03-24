"""
Manuale Utente — Generazione PDF professionale white-label.
GET  /api/manuale/contenuti   — Restituisce i capitoli del manuale (JSON)
GET  /api/manuale/genera-pdf  — Genera PDF impaginato con logo, FAQ, QR Code
"""
import io
import os
import base64
import logging
from datetime import datetime, timezone

import qrcode
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from weasyprint import HTML

from core.database import db
from core.security import get_current_user

router = APIRouter(prefix="/manuale", tags=["manuale"])
logger = logging.getLogger(__name__)


# ── Contenuti statici del manuale ──

CAPITOLI = [
    {
        "id": "intro",
        "titolo": "Introduzione",
        "icona": "info",
        "contenuto": """
<p>Benvenuto nel sistema gestionale per carpenteria metallica conforme alle normative <strong>EN 1090</strong>, <strong>EN 13241</strong> e <strong>ISO 3834</strong>.</p>
<p>Questo manuale descrive tutte le funzionalita del software, dalla gestione commerciale alla tracciabilita dei materiali, dalla sicurezza in cantiere alla generazione automatica di documenti tecnici.</p>
<h4>A chi e rivolto</h4>
<ul>
<li>Titolari e responsabili di officina</li>
<li>Responsabili commerciali e preventivisti</li>
<li>Responsabili della qualita e sicurezza</li>
<li>Operai e capi squadra (modulo Officina)</li>
</ul>
""",
    },
    {
        "id": "preventivi",
        "titolo": "Gestione Preventivi",
        "icona": "calculator",
        "contenuto": """
<h4>Creazione Preventivo Manuale</h4>
<ol>
<li>Dalla barra laterale, clicca su <strong>Commerciale → Preventivi</strong></li>
<li>Clicca <strong>Nuovo Preventivo</strong></li>
<li>Compila: cliente, oggetto, normativa di riferimento (EN 1090 / EN 13241), classe di esecuzione</li>
<li>Aggiungi le voci di lavoro con peso, prezzo unitario e margine</li>
<li>Clicca <strong>Salva</strong> per creare il preventivo in stato Bozza</li>
</ol>
<h4>Preventivatore Predittivo AI</h4>
<ol>
<li>Vai su <strong>Commerciale → AI Predittivo</strong></li>
<li><strong>Metodo 1 — Analisi Disegno:</strong> Carica un PDF o immagine del disegno tecnico. L'AI estrae automaticamente profili, piastre e bulloneria con relativi pesi</li>
<li><strong>Metodo 2 — Stima Rapida:</strong> Inserisci il peso stimato (kg) e la tipologia di struttura (leggera/media/complessa/speciale)</li>
<li>Il sistema calcola ore stimate (metodo parametrico + EUR/kg), costi materiali da prezzi storici, e margini differenziati</li>
<li>Clicca <strong>Genera Preventivo</strong> per creare il documento ufficiale</li>
</ol>
<h4>Margini Differenziati</h4>
<p>Il sistema applica margini separati per:</p>
<ul>
<li><strong>Materiali</strong> (default 25%): ricarico su acciaio, bulloneria, accessori</li>
<li><strong>Manodopera</strong> (default 30%): ricarico su ore officina e montaggio</li>
<li><strong>Conto Lavoro</strong> (default 20%): ricarico su zincatura, verniciatura, lavorazioni esterne</li>
</ul>
""",
    },
    {
        "id": "commesse",
        "titolo": "Gestione Commesse",
        "icona": "briefcase",
        "contenuto": """
<h4>Creazione Commessa</h4>
<ol>
<li>Dalla lista preventivi, clicca <strong>Accetta</strong> su un preventivo approvato</li>
<li>Il sistema crea automaticamente la commessa con tutti i dati del preventivo</li>
<li>In alternativa, vai su <strong>Produzione → Commesse</strong> e clicca <strong>Nuova Commessa</strong></li>
</ol>
<h4>Hub Commessa</h4>
<p>Ogni commessa ha un hub centrale con:</p>
<ul>
<li><strong>Banner Conformita:</strong> Verifica automatica che i documenti aziendali (DURC, Visura, etc.) siano validi per la durata dei lavori</li>
<li><strong>Voci di Lavoro:</strong> Dettaglio delle lavorazioni con stato avanzamento</li>
<li><strong>Diario di Produzione:</strong> Registrazione ore e attivita degli operai</li>
<li><strong>Pacco Documenti:</strong> Generazione automatica del fascicolo sicurezza ZIP</li>
</ul>
<h4>Validazione Preventiva</h4>
<p>All'apertura di una commessa, il sistema verifica automaticamente se tutti i documenti aziendali obbligatori sono presenti e validi. Se un documento e mancante o scaduto, viene mostrato un <strong>avviso rosso bloccante</strong> con il dettaglio dei problemi.</p>
""",
    },
    {
        "id": "sicurezza",
        "titolo": "Sicurezza e Documenti",
        "icona": "shield",
        "contenuto": """
<h4>Documenti Aziendali</h4>
<p>In <strong>Impostazioni → Documenti</strong> puoi gestire:</p>
<ul>
<li><strong>DURC</strong> — Documento Unico Regolarita Contributiva</li>
<li><strong>Visura Camerale</strong> — Visura CCIAA aggiornata</li>
<li><strong>White List</strong> — Iscrizione Prefettura</li>
<li><strong>Patente a Crediti</strong> — INAIL</li>
<li><strong>DVR</strong> — Documento Valutazione Rischi (D.Lgs 81/08)</li>
</ul>
<p>Per ogni documento puoi impostare la <strong>data di scadenza</strong> cliccando sull'icona del dischetto accanto al campo data. Il sistema mostra alert colorati:</p>
<ul>
<li><span style="color:green;">Verde</span> = Valido (oltre 30 giorni)</li>
<li><span style="color:orange;">Giallo</span> = In scadenza (entro 30 giorni)</li>
<li><span style="color:red;">Rosso</span> = Scaduto o critico (entro 15 giorni)</li>
</ul>
<h4>Allegati Tecnici POS</h4>
<p>Nella sezione <strong>Allegati Tecnici POS</strong> puoi caricare:</p>
<ul>
<li><strong>Valutazione Rumore</strong> — D.Lgs 81/08 Titolo VIII</li>
<li><strong>Valutazione Vibrazioni</strong> — D.Lgs 81/08</li>
<li><strong>Valutazione MMC</strong> — Movimentazione Manuale Carichi</li>
</ul>
<p>Ogni allegato ha un interruttore <strong>"Includi nel POS"</strong>. Gli allegati attivi vengono inseriti automaticamente nel pacchetto sicurezza ZIP di ogni commessa.</p>
<h4>Fascicolo Aziendale</h4>
<p>Dalla Dashboard, il pulsante <strong>Fascicolo</strong> scarica uno ZIP contenente tutti i documenti aziendali organizzati in cartelle.</p>
""",
    },
    {
        "id": "risorse_umane",
        "titolo": "Risorse Umane e Attestati",
        "icona": "users",
        "contenuto": """
<h4>Anagrafica Operai</h4>
<p>In <strong>Risorse Umane</strong> gestisci l'anagrafica di tutti gli operai con:</p>
<ul>
<li>Dati anagrafici e mansione</li>
<li>Patentini di saldatura (EN ISO 9606)</li>
<li>Attestati sicurezza: Formazione Base 81/08, Primo Soccorso, Antincendio, Lavori in Quota, PLE, Carrellista, Visita Medica, Formazione Specifica</li>
</ul>
<h4>Matrice Scadenze</h4>
<p>La pagina <strong>Matrice Scadenze</strong> mostra una tabella con pallini colorati per ogni operaio:</p>
<ul>
<li><span style="color:green;">●</span> Verde = Attestato valido</li>
<li><span style="color:orange;">●</span> Giallo = In scadenza</li>
<li><span style="color:red;">●</span> Rosso = Scaduto</li>
<li><span style="color:gray;">●</span> Grigio = Non presente</li>
</ul>
<h4>Integrazione POS</h4>
<p>Nel wizard POS (Step 4), puoi selezionare gli operai assegnati alla commessa. Il sistema controlla automaticamente che tutti gli attestati siano validi e li allega al pacchetto sicurezza.</p>
""",
    },
    {
        "id": "tracciabilita",
        "titolo": "Tracciabilita FPC (EN 1090)",
        "icona": "clipboard",
        "contenuto": """
<h4>Progetto FPC</h4>
<p>Il modulo <strong>Tracciabilita</strong> gestisce il controllo di produzione in fabbrica secondo EN 1090:</p>
<ol>
<li>Crea un progetto FPC collegato a una commessa</li>
<li>Definisci classe di esecuzione (EXC1-EXC4)</li>
<li>Registra i lotti di materiale con N. Colata e certificati 3.1</li>
<li>Esegui controlli qualita (visivi, dimensionali, NDT)</li>
</ol>
<h4>Verbale di Posa in Opera</h4>
<ol>
<li>Dalla pagina FPC del progetto, clicca <strong>Genera Verbale</strong></li>
<li>Compila: data installazione, metodo di montaggio, condizioni meteo</li>
<li>I lotti EN 1090 vengono inseriti automaticamente nel verbale</li>
<li>Aggiungi foto dal cantiere (drag-and-drop o scatto diretto)</li>
<li>Fai firmare il cliente direttamente sullo schermo del tablet</li>
<li>Clicca <strong>Genera PDF</strong> per il documento ufficiale</li>
</ol>
""",
    },
    {
        "id": "dashboard",
        "titolo": "Dashboard e KPI",
        "icona": "chart",
        "contenuto": """
<h4>Cruscotto Officina</h4>
<p>La Dashboard mostra in tempo reale:</p>
<ul>
<li><strong>KPI Principali:</strong> Fatturato, commesse attive, ore lavorate, efficienza</li>
<li><strong>Conformita Documentale:</strong> Stato di tutti i documenti aziendali con previsione a 30 giorni</li>
<li><strong>Barre Avanzamento:</strong> Percentuale di conformita per ogni commessa attiva</li>
<li><strong>Prossime Scadenze:</strong> Alert per documenti in scadenza</li>
</ul>
<h4>Dashboard KPI Avanzata</h4>
<p>In <strong>Dashboard KPI</strong> trovi grafici dettagliati su:</p>
<ul>
<li>Andamento fatturato mensile</li>
<li>Distribuzione costi (materiali vs manodopera vs conto lavoro)</li>
<li>Efficienza preventivi (tasso di conversione)</li>
<li>Confronto stime AI vs valori reali</li>
</ul>
""",
    },
]

FAQ = [
    {
        "domanda": "La data di scadenza non si salva. Cosa faccio?",
        "risposta": "Dopo aver inserito la data nel campo, clicca l'icona del <strong>dischetto</strong> (salva) accanto al campo. La data viene salvata solo quando premi il pulsante. Verifica che il documento sia stato prima caricato: non e possibile impostare una scadenza senza un file associato.",
    },
    {
        "domanda": "Come carico un nuovo patentino o attestato per un operaio?",
        "risposta": "Vai su <strong>Risorse Umane</strong>, seleziona l'operaio, clicca <strong>Aggiungi Qualifica</strong>. Scegli il tipo di attestato dal menu a tendina, compila la data di rilascio e scadenza, poi salva.",
    },
    {
        "domanda": "Perche il preventivo AI mostra tutto a zero?",
        "risposta": "Il preventivo AI necessita di materiali per calcolare i costi. Usa la <strong>Stima Rapida Manuale</strong>: inserisci il peso stimato in kg e la tipologia di struttura nello Step 1. In alternativa, carica un disegno tecnico chiaro (PDF o immagine) con le distinte materiali visibili.",
    },
    {
        "domanda": "Come includo gli allegati tecnici nel pacchetto sicurezza?",
        "risposta": "In <strong>Impostazioni → Documenti</strong>, scorri fino alla sezione <strong>Allegati Tecnici POS</strong>. Carica i file (Rumore, Vibrazioni, MMC) e assicurati che l'interruttore <strong>Includi nel POS</strong> sia attivo. I file verranno inseriti automaticamente nello ZIP.",
    },
    {
        "domanda": "Il banner rosso sulla commessa dice 'Conformita insufficiente'. Come risolvo?",
        "risposta": "Il banner mostra quali documenti sono mancanti o scaduti. Clicca <strong>Correggi documenti</strong> per andare direttamente alla pagina Impostazioni. Carica i documenti mancanti e imposta le date di scadenza corrette. Il banner diventa verde quando tutti i documenti sono validi.",
    },
    {
        "domanda": "Come genero il Verbale di Posa?",
        "risposta": "Apri la commessa, vai nella sezione FPC/Tracciabilita, e clicca <strong>Genera Verbale</strong>. Il modulo e ottimizzato per tablet: puoi compilare i dati, scattare foto dal cantiere, e far firmare il cliente direttamente sullo schermo.",
    },
    {
        "domanda": "Posso personalizzare il logo sui documenti?",
        "risposta": "Si. Vai su <strong>Impostazioni → Logo</strong> e carica il logo della tua azienda. Il logo apparira automaticamente su tutti i PDF generati (preventivi, verbali, manuali).",
    },
    {
        "domanda": "Come scarico il fascicolo aziendale completo?",
        "risposta": "Dalla <strong>Dashboard</strong>, nel widget Conformita Documentale, clicca il pulsante <strong>Fascicolo</strong>. Verra scaricato uno ZIP con tutti i documenti organizzati in cartelle (Documenti Azienda + Allegati POS).",
    },
]


@router.get("/contenuti")
async def get_contenuti_manuale(user: dict = Depends(get_current_user)):
    """Restituisce i capitoli e FAQ del manuale."""
    return {
        "capitoli": [{"id": c["id"], "titolo": c["titolo"], "icona": c["icona"]} for c in CAPITOLI],
        "faq": FAQ,
        "versione": "2.0",
    }


@router.get("/genera-pdf")
async def genera_manuale_pdf(user: dict = Depends(get_current_user)):
    """Genera il Manuale Utente PDF professionale con logo white-label e QR Code."""

    # Load company settings for white-label — always filter by user_id
    cs = await db.company_settings.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}

    company_name = cs.get("business_name") or cs.get("ragione_sociale") or ""
    if not company_name:
        company_name = user.get("name", "La Tua Azienda")
    company_addr = cs.get("address", "")
    company_piva = cs.get("partita_iva", "")

    logo_url = cs.get("logo_url", "")
    if logo_url and logo_url.startswith("data:image"):
        logo_html = f'<img src="{logo_url}" class="logo-img" />'
    else:
        logo_html = f'<div class="logo-text">{company_name.upper()}</div>'

    # Generate QR Code
    app_url = os.environ.get("APP_URL", "https://normafacile.it")
    qr_url = f"{app_url}/portale-cliente"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#1E293B", back_color="white")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_b64 = base64.b64encode(qr_buffer.getvalue()).decode("utf-8")
    qr_data_uri = f"data:image/png;base64,{qr_b64}"

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%d/%m/%Y")

    # Build HTML
    chapters_html = ""
    for i, ch in enumerate(CAPITOLI, 1):
        chapters_html += f"""
        <div class="chapter" style="page-break-before: {'always' if i > 1 else 'auto'};">
            <div class="chapter-header">
                <span class="chapter-num">Capitolo {i}</span>
                <h2>{ch['titolo']}</h2>
            </div>
            <div class="chapter-body">{ch['contenuto']}</div>
        </div>
        """

    # FAQ section
    faq_rows = ""
    for j, fq in enumerate(FAQ, 1):
        faq_rows += f"""
        <tr>
            <td class="faq-num">{j}</td>
            <td class="faq-q">{fq['domanda']}</td>
            <td class="faq-a">{fq['risposta']}</td>
        </tr>
        """

    # Table of contents
    toc_items = ""
    for i, ch in enumerate(CAPITOLI, 1):
        toc_items += f'<div class="toc-item"><span class="toc-num">{i}.</span> {ch["titolo"]}</div>'
    toc_items += f'<div class="toc-item"><span class="toc-num">{len(CAPITOLI)+1}.</span> Guida alla Risoluzione Problemi</div>'

    html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<style>
@page {{
    size: A4;
    margin: 20mm 18mm 25mm 18mm;
    @bottom-center {{
        content: counter(page) " / " counter(pages);
        font-size: 8pt;
        color: #94A3B8;
        font-family: 'Helvetica Neue', Arial, sans-serif;
    }}
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: 'Helvetica Neue', Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.6;
    color: #1E293B;
}}
.logo-img {{ max-height: 48px; max-width: 200px; object-fit: contain; }}
.logo-text {{
    font-size: 20pt; font-weight: 800; color: #0055FF;
    letter-spacing: 2px;
}}

/* COVER */
.cover {{
    page-break-after: always;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    min-height: 240mm;
    text-align: center;
}}
.cover-logo {{ margin-bottom: 30mm; }}
.cover h1 {{
    font-size: 28pt; color: #1E293B; font-weight: 800;
    letter-spacing: 1px; margin-bottom: 4mm;
}}
.cover .subtitle {{
    font-size: 12pt; color: #64748B; margin-bottom: 20mm;
}}
.cover .meta {{
    font-size: 9pt; color: #94A3B8;
    border-top: 1px solid #E2E8F0;
    padding-top: 5mm; margin-top: 10mm;
}}

/* TOC */
.toc {{ page-break-after: always; padding-top: 10mm; }}
.toc h2 {{
    font-size: 16pt; color: #1E293B; margin-bottom: 8mm;
    border-bottom: 2px solid #0055FF; padding-bottom: 3mm;
}}
.toc-item {{
    padding: 3mm 0; border-bottom: 1px dotted #CBD5E1;
    font-size: 11pt; color: #334155;
}}
.toc-num {{ font-weight: 700; color: #0055FF; margin-right: 3mm; }}

/* CHAPTERS */
.chapter-header {{
    background: #F8FAFC; border-left: 4px solid #0055FF;
    padding: 4mm 5mm; margin-bottom: 5mm;
}}
.chapter-num {{
    font-size: 8pt; color: #0055FF; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px;
}}
.chapter-header h2 {{
    font-size: 15pt; color: #1E293B; margin-top: 1mm;
}}
.chapter-body {{
    padding: 0 2mm;
}}
.chapter-body h4 {{
    font-size: 11pt; color: #0055FF; margin: 5mm 0 2mm 0;
    font-weight: 700;
}}
.chapter-body p {{ margin-bottom: 3mm; }}
.chapter-body ul, .chapter-body ol {{
    margin: 2mm 0 4mm 6mm;
}}
.chapter-body li {{ margin-bottom: 1.5mm; }}

/* FAQ TABLE */
.faq-section {{ page-break-before: always; }}
.faq-section h2 {{
    font-size: 15pt; color: #1E293B; margin-bottom: 5mm;
    border-left: 4px solid #F59E0B; padding-left: 5mm;
    background: #FFFBEB; padding: 4mm 5mm;
}}
.faq-table {{
    width: 100%; border-collapse: collapse; margin-top: 5mm;
    font-size: 9pt;
}}
.faq-table th {{
    background: #1E293B; color: white;
    padding: 3mm; text-align: left; font-size: 8pt;
    text-transform: uppercase; letter-spacing: 0.5px;
}}
.faq-table td {{
    padding: 3mm; border-bottom: 1px solid #E2E8F0;
    vertical-align: top;
}}
.faq-table tr:nth-child(even) {{ background: #F8FAFC; }}
.faq-num {{ width: 8mm; text-align: center; font-weight: 700; color: #0055FF; }}
.faq-q {{ width: 55mm; font-weight: 600; color: #334155; }}
.faq-a {{ color: #475569; }}

/* QR PAGE */
.qr-page {{
    page-break-before: always;
    text-align: center;
    padding-top: 50mm;
}}
.qr-page h2 {{
    font-size: 16pt; color: #1E293B; margin-bottom: 8mm;
}}
.qr-page .qr-box {{
    display: inline-block;
    border: 2px solid #E2E8F0;
    border-radius: 4mm;
    padding: 5mm;
    margin: 5mm 0;
}}
.qr-page .qr-box img {{ width: 50mm; height: 50mm; }}
.qr-page .qr-label {{
    font-size: 10pt; color: #64748B; margin-top: 5mm;
}}
.qr-page .qr-url {{
    font-size: 8pt; color: #94A3B8; margin-top: 2mm;
    font-family: monospace;
}}
.qr-page .footer-note {{
    margin-top: 30mm;
    font-size: 8pt; color: #CBD5E1;
    border-top: 1px solid #E2E8F0;
    padding-top: 5mm;
}}
</style>
</head>
<body>

<!-- COPERTINA -->
<div class="cover">
    <div class="cover-logo">{logo_html}</div>
    <h1>Manuale Utente</h1>
    <div class="subtitle">Gestionale Carpenteria Metallica — EN 1090 / EN 13241 / ISO 3834</div>
    <div class="subtitle" style="font-size:10pt;">Versione 2.0</div>
    <div class="meta">
        {company_name}<br>
        {company_addr}{(' | P.IVA ' + company_piva) if company_piva else ''}<br>
        Documento generato il {date_str}
    </div>
</div>

<!-- INDICE -->
<div class="toc">
    <h2>Indice dei Contenuti</h2>
    {toc_items}
</div>

<!-- CAPITOLI -->
{chapters_html}

<!-- FAQ -->
<div class="faq-section">
    <h2>Guida alla Risoluzione Problemi</h2>
    <table class="faq-table">
        <thead>
            <tr>
                <th>#</th>
                <th>Problema</th>
                <th>Soluzione</th>
            </tr>
        </thead>
        <tbody>
            {faq_rows}
        </tbody>
    </table>
</div>

<!-- QR CODE -->
<div class="qr-page">
    <div class="cover-logo">{logo_html}</div>
    <h2>Portale Documenti Online</h2>
    <p style="font-size:10pt;color:#64748B;margin-bottom:5mm;">
        Inquadra il QR Code per accedere al portale documenti
    </p>
    <div class="qr-box">
        <img src="{qr_data_uri}" />
    </div>
    <div class="qr-label">Scansiona con la fotocamera del tuo smartphone</div>
    <div class="qr-url">{qr_url}</div>
    <div class="footer-note">
        &copy; {now.year} {company_name} — Tutti i diritti riservati<br>
        Generato automaticamente dal sistema gestionale v2.0
    </div>
</div>

</body>
</html>"""

    pdf_bytes = HTML(string=html_content).write_pdf()
    pdf_buffer = io.BytesIO(pdf_bytes)
    pdf_buffer.seek(0)

    fname = f"Manuale_Utente_{company_name.replace(' ', '_')}_{now.strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
