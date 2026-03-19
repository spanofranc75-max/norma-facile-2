# Norma Facile 2.0 — PRD

## Problema Originale
Applicazione gestionale per carpenteria metallica (CRM/ERP per Fabbri).
L'app era instabile dopo migrazione a Vercel (frontend) e Railway (backend).

## Architettura
- Frontend: React (Emergent Preview) | Backend: FastAPI + MongoDB (Emergent)
- Preview URL: https://facile-email-fix.preview.emergentagent.com

## Implementato

### Fix Caratteri Corrotti (19/03/2026)
- `PreventivoEditorPage.js` aveva triple-encoding UTF-8 su caratteri italiani (à, è, ò) e em-dash
- Fix applicato con libreria `ftfy` su tutta la pagina preventivo
- Corretto: "ValiditÃÂÃÂ" → "Validità", "Q.tÃÂÃÂ" → "Q.tà", "puÃÂÃÂ²" → "può", "EXC1 ÃÂÃÂ..." → "EXC1 —"
- Lint zero errori dopo il fix

### Fix Bug P0: Invio Email RdP/OdA (19/03/2026)
- `try/except` nella generazione PDF con messaggi di errore specifici invece di 500 generico
- Supporto CC aggiunto a `send_rdp_email` e `send_oda_email` in `email_service.py`
- `credentials: 'include'` aggiunto alle fetch di `EmailPreviewDialog.js` (preview + send)
- Fix endpoint: CC ora passato correttamente anche senza custom_subject/body
- **Testato: 19/19 test passati (100%)**

### CUP/CIG/CUC + Rimozione Impostazioni Fiscali
- Campi CUP, CIG, CUC aggiunti nel form fattura e preventivo
- Propagazione automatica da preventivo a fattura
- CUP/CIG/CUC visibili nei PDF
- Rimossa sezione Impostazioni Fiscali legacy

### Destinatari Multipli Email + Rubrica
- Campo CC nel dialog EmailPreviewDialog con rubrica contatti rapida
- Backend: tutti gli endpoint (fatture, preventivi, DDT, RdP, OdA) accettano CC
- Contatti suggeriti dal database cliente (PEC, email, referenti)

### Fix sync-fic FattureInCloud
- Token aggiornato + error handling 401 + rimosso filtro data incompatibile API v2

### Layout PDF Unificato + Fix Viewer
- Header unificato, palette grigia, logo proporzionale, pdfjs-dist aggiornato

### Numerazione Commesse Separata
- Contatori separati per EN_1090, EN_13241 e generiche
- Commesse generiche usano il numero del preventivo

### Indicatori Email Inviata RdP/OdA
- Icona check-mark su RdP/OdA già inviati
- Possibilità di reinvio

## Backlog
### P1
- Verifica completa utente di tutte le feature recenti in produzione

### P2
- Unificazione servizi PDF (pdf_invoice_modern.py + pdf_template.py)
- Sistema RBAC
- Migrazione immagini legacy Base64

### P3
- Firma digitale PDF, Portale cliente, AI Copilot
