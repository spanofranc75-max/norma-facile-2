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

### Rilievo Guidato (Steps 1-8) — COMPLETATO 09/03/2026
- Backend: modello esteso (tipologia, misure, elementi, vista_3d_config)
- Endpoint `POST /api/rilievi/{id}/calcola-materiali` per 6 tipologie
- Frontend: TipologiaSelector, FormMisure dinamico, RilievoViewer3D (Three.js)
- Screenshot 3D → upload come foto
- **PDF aggiornato**: sezioni Tipologia, Misure Rilevate, Vista 3D, Lista Materiali Calcolata
- Test e2e per tutte 6 tipologie: PASSATO

### Fix Critico SDI — 09/03/2026
- `default=str` aggiunto a `json.dumps` in `fattureincloud_api.py` (riga 67)
- Risolve crash su tipi non JSON-serializzabili

### Altre Feature Completate (sessioni precedenti)
- Fatturazione completa (FT, NC, proforma)
- Validazione pre-invio SDI
- PDF worker fix (CDN path)
- Object Storage integration
- Gestione clienti/fornitori
- Preventivi con varianti
- DDT e consegne
- Modulo saldatori/certificazioni
- Super Fascicolo
- Magazzino con tracciabilità

### Ripristino PDF Fatture/Preventivi ReportLab — COMPLETATO 18/03/2026
- `pdf_invoice_modern.py` riscritto da zero con ReportLab (era WeasyPrint)
- Font: LiberationSans TTF per supporto Unicode completo (€, •, à, è, —)
- Layout: logo+azienda, separatore blu, titolo centrato, box meta grigi, cliente con bordo blu, tabella navy, totali con box navy, banca/scadenze con bordo blu, footer certificazioni
- Scadenze pagamento integrate nel PDF
- Condizioni vendita per Preventivi (pagina 2)
- 9/9 test pytest passati

## Backlog Prioritizzato

### P0 — Nessuno attivo

### P1
- Conferma fix SDI in produzione
- Rimuovere logging diagnostico in `routes/invoices.py`

### P2
- Permessi/Ruoli Granulari (RBAC)
- Script migrazione Base64 → Object Storage

### P3
- Firma digitale PDF Perizia
- Portale cliente read-only
- AI Copilot per preventivi
- Refactoring CommessaOpsPanel.js (monolite)
- Refactoring RilievoEditorPage.js (1200+ righe)
