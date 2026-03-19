# Norma Facile 2.0 — PRD

## Problema Originale
Applicazione gestionale per carpenteria metallica.

## Architettura
- Frontend: React (Vercel) | Backend: FastAPI + MongoDB Atlas (Railway)

## Implementato — 19/03/2026

### Layout PDF Unificato (commit cf4dbdb)
- **Tutti i documenti** (Fattura, Preventivo, DDT) hanno la stessa struttura:
  - Logo + Azienda a SINISTRA | Cliente a DESTRA (stessa riga)
  - Titolo + Numero centrato
  - Tabella articoli con header grigio chiaro #E8E8E8
  - Totali con box grigio #E0E0E0
- **DDT riscritto**: ReportLab diretto, pagina singola, numero DDT, cliente visibile, dati trasporto compatti
- **Fattura**: cliente spostato nell'header (era sotto come blocco separato)

### Fix PDF Viewer (commit aab6f27)
- pdfjs-dist aggiornato a 5.4.296 (match react-pdf@10.4.1)
- Worker URL corretto (unpkg.com)

### Palette Grigio Chiaro (commit b1e53f8)
- Zero colori navy/blu/neri
- Logo proporzionale con PIL

## Backlog
### P1
- Verifica visiva dopo deploy Railway/Vercel
- Test sync fatture ricevute

### P2
- RBAC, Migrazione Base64, Unificazione servizi PDF

### P3
- Firma digitale, Portale cliente, AI Copilot
