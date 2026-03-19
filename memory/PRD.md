# Norma Facile 2.0 — PRD

## Problema Originale
Applicazione gestionale per carpenteria metallica (CRM/ERP per Fabbri).
L'app era instabile dopo migrazione a Vercel (frontend) e Railway (backend).
Obiettivo principale: stabilizzare e standardizzare la generazione PDF.

## Architettura
- Frontend: React (Vercel) | Backend: FastAPI + MongoDB Atlas (Railway)
- Repo: spanofranc75-max/norma-facile-2 (GitHub)
- Directory produzione: /tmp/norma-facile-2-push/

## Implementato

### Destinatari Multipli Email (commit 5029e7d - 19/03/2026)
- Campo CC nel dialog EmailPreviewDialog per aggiungere destinatari aggiuntivi
- Supporto per input multipli (separati da virgola o invio)
- Validazione email, prevenzione duplicati
- Backend: tutti e 3 gli endpoint (fatture, preventivi, DDT) accettano parametro `cc`
- Email service Resend aggiornato con supporto CC
- Tracking destinatari multipli nel database

### Fix sync-fic FattureInCloud (commits 199697f, 278211d, 23acf97 - 19/03/2026)
- Token FattureInCloud aggiornato con nuovo token valido
- Error handling migliorato: messaggio chiaro per token scaduto (401)
- Rimosso filtro data `filter[date][from]` incompatibile con API v2 FattureInCloud (causava 422)

### Layout PDF Unificato (commit cf4dbdb)
- Tutti i documenti (Fattura, Preventivo, DDT) con stessa struttura header
- DDT riscritto con ReportLab
- Palette grigio chiaro professionale
- Logo proporzionale con PIL

### Fix PDF Viewer (commit aab6f27)
- pdfjs-dist aggiornato a 5.4.296
- Worker URL corretto

## Backlog
### P1
- Verifica visiva PDF dopo deploy Railway/Vercel

### P2
- Unificazione servizi PDF (pdf_invoice_modern.py + pdf_template.py)
- Sistema RBAC (controllo accessi basato su ruoli)
- Migrazione immagini legacy Base64

### P3
- Firma digitale sui report PDF
- Portale cliente in sola lettura
- AI Copilot
