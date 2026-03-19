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

### Layout PDF Unificato (commit cf4dbdb - 19/03/2026)
- Tutti i documenti (Fattura, Preventivo, DDT) hanno la stessa struttura:
  - Logo + Azienda a SINISTRA | Cliente a DESTRA (stessa riga)
  - Titolo + Numero centrato
  - Tabella articoli con header grigio chiaro #E8E8E8
  - Totali con box grigio #E0E0E0
- DDT riscritto: ReportLab diretto, pagina singola, numero DDT, cliente visibile
- Fattura: cliente spostato nell'header

### Fix PDF Viewer (commit aab6f27 - 19/03/2026)
- pdfjs-dist aggiornato a 5.4.296 (match react-pdf@10.4.1)
- Worker URL corretto (unpkg.com)

### Palette Grigio Chiaro (commit b1e53f8 - 19/03/2026)
- Zero colori navy/blu/neri, tutto grigio professionale
- Logo proporzionale con PIL

### Fix Error Handling sync-fic (commit 199697f - 19/03/2026)
- Gestione specifica errore 401 (token scaduto) con messaggio chiaro
- L'utente riceve istruzioni su come generare nuovo token FattureInCloud
- Gestione errore 403 (permessi) aggiunta

## In Corso / Bloccati
### P0 - Token FattureInCloud scaduto
- L'endpoint /api/fatture-ricevute/sync-fic restituisce 401
- BLOCCATO: serve un nuovo token API dall'utente
- Error handling migliorato: messaggio chiaro

### P1 - Verifica PDF post-deploy
- Layout unificato pushato, in attesa verifica utente su Railway

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
