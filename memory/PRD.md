# Norma Facile 2.0 — PRD

## Problema Originale
Applicazione gestionale per carpenteria metallica: gestione commesse, fatturazione, perizie, rilievi, preventivi, con integrazione FattureInCloud per fatturazione elettronica e SDI.

## Architettura
- **Frontend:** React + Tailwind + Shadcn/UI
- **Backend:** FastAPI + MongoDB (Motor)
- **Auth:** Emergent-managed Google Auth (cookie-based)
- **Storage:** S3-compatible Object Storage
- **Integrazioni:** FattureInCloud API v2, Resend, GPT-4o Vision

## Core Requirements
- Gestione completa ciclo commessa (preventivo → fattura → SDI)
- Rilievo Guidato con 6 tipologie, misure parametriche, 3D viewer, calcolo materiali, PDF
- Fatturazione elettronica con invio SDI via FattureInCloud
- Perizie con AI Vision analysis
- Dashboard cruscotto operativo

## Cosa è stato implementato

### Redesign PDF Grigio Chiaro — COMPLETATO 19/03/2026
- **Palette grigio chiaro completa**: Tutti i colori sostituiti con scala di grigi elegante
  - Header tabella: #E8E8E8 sfondo + #666666 testo (era navy/bianco)
  - Box TOTALE: #E0E0E0 sfondo (era navy scuro)
  - Bordi/accenti: #AAAAAA (era blu #2563EB)
  - Testo corpo: #555555, titoli: #666666, secondario: #888888
- **Logo proporzionale**: PIL calcola dimensioni corrette (bounding box 120x60), era forzato 150x50
- **Condizioni vendita**: Nessun blocco firma duplicato se già presente nel testo
- **CSS WeasyPrint aggiornato**: Stessa palette grigio per preventivi e DDT
- **Tutti i colori blu/navy/neri rimossi** da tutti i 3 generatori PDF
- 16/16 test passati (iteration 170)

### Fix PDF Monocromatico e Layout — 19/03/2026
- Fix errori di sintassi e import
- API Anteprima/Scarica funzionanti
- 15/15 test passati (iteration 169)

### Rilievo Guidato (Steps 1-8) — COMPLETATO 09/03/2026
- Backend: modello esteso, endpoint calcolo materiali per 6 tipologie
- Frontend: TipologiaSelector, FormMisure dinamico, RilievoViewer3D (Three.js)

### Ripristino PDF Fatture/Preventivi ReportLab — COMPLETATO 18/03/2026
- `pdf_invoice_modern.py` riscritto con ReportLab
- Font LiberationSans TTF per supporto Unicode

### Altre Feature Completate
- Fatturazione completa (FT, NC, proforma)
- Validazione pre-invio SDI
- Object Storage integration
- Gestione clienti/fornitori, Preventivi, DDT
- Modulo saldatori/certificazioni, Super Fascicolo
- Magazzino con tracciabilità
- Sistema backup asincrono

## Backlog Prioritizzato

### P0 — Nessuno attivo

### P1
- Conferma fix SDI in produzione
- Verifica sync fatture ricevute (sync-fic)
- Rimuovere logging diagnostico in routes/invoices.py

### P2
- RBAC (permessi/ruoli)
- Script migrazione Base64 → Object Storage
- Refactoring unificazione servizi PDF

### P3
- Firma digitale PDF Perizia
- Portale cliente read-only
- AI Copilot per preventivi
- Refactoring CommessaOpsPanel.js
- Refactoring RilievoEditorPage.js
