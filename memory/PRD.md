# Norma Facile 2.0 — PRD

## Problema Originale
Applicazione gestionale per carpenteria metallica (CRM/ERP per Fabbri).
L'app era instabile dopo migrazione a Vercel (frontend) e Railway (backend).

## Architettura
- Frontend: React (Vercel) | Backend: FastAPI + MongoDB Atlas (Railway)
- Repo: spanofranc75-max/norma-facile-2 (GitHub)

## Implementato

### CUP/CIG/CUC + Rimozione Impostazioni Fiscali (commit 526f3ba - 19/03/2026)
- Campi CUP, CIG, CUC aggiunti nel form fattura e preventivo
- Propagazione automatica da preventivo a fattura (QuickFill + create_from_preventivo)
- CUP/CIG/CUC visibili nei PDF (fattura con ReportLab, preventivo con HTML)
- Rimossa sezione Impostazioni Fiscali (Rivalsa INPS, Cassa Previdenza, Ritenuta d'Acconto) 
- Mantenute Note Documento e ripristinato InvoiceEditorPage.js (era troncato)

### Destinatari Multipli Email + Rubrica (commit e932f80 - 19/03/2026)
- Campo CC nel dialog EmailPreviewDialog con rubrica contatti rapida
- Backend: tutti e 3 gli endpoint (fatture, preventivi, DDT) accettano CC
- Contatti suggeriti dal database cliente (PEC, email, referenti)

### Fix sync-fic FattureInCloud (commits 199697f, 278211d, 23acf97 - 19/03/2026)
- Token aggiornato + error handling 401 + rimosso filtro data incompatibile API v2

### Layout PDF Unificato + Fix Viewer (commits precedenti)
- Header unificato, palette grigia, logo proporzionale, pdfjs-dist aggiornato

## Backlog
### P1
- Verifica visiva CUP/CIG/CUC e CC in produzione dopo deploy

### P2
- Unificazione servizi PDF (pdf_invoice_modern.py + pdf_template.py)
- Sistema RBAC
- Migrazione immagini legacy Base64

### P3
- Firma digitale PDF, Portale cliente, AI Copilot
