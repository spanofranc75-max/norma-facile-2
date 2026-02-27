# Norma Facile 2.0 - Product Requirements Document

## Original Problem Statement
Build Norma Facile 2.0 - a **CRM/ERP per Fabbri (Metalworkers)** with React + FastAPI + MongoDB.

## Core Architecture
- **Norma Core Engine** (`backend/core/engine/`) — Business logic
- **Optimizer Service** (`backend/services/optimizer.py`) — FFD bin-packing

## Implemented Modules

### Foundation (Phase 1-5)
- Google OAuth, Invoicing, Rilievi, Distinta Smart BOM, Industrial Blue Theme

### Certificazioni CE + Smart CE Calculator (Phase 6/8)
- 4-step wizard, DOP + CE Label + Manuale, Thermal Uw, Confronta Serramenti

### Sicurezza Cantieri / POS (Phase 7)
- 3-step wizard, AI risk assessment (GPT-4o), POS PDF

### Workshop Dashboard (Phase 9) + UI Polish (Phase 16)
- Gradient KPI cards, Recharts BarChart "Fatturato Mensile", FAB "Nuovo"
- Fascicolo Cantiere, Empty States SVG

### Norma Core Engine + Catalogo + Vendor API (Phase 10-12)
- ThermalValidator, SafetyValidator, CEValidator, NormaRouter
- Custom profiles, merged catalog, vendor system

### Scheda Cliente/Fornitore + Tipi Pagamento (Phase 17)
- Tab-based client form (Anagrafica, Indirizzo, Contatti, Pagamento, Note)
- Persone di Riferimento with document email preferences
- Payment Types CRUD with installment checkbox grid
- Client_type: Cliente / Fornitore / Cliente-Fornitore

### Preventivo Avanzato v2 — Invoicex Style (Phase 18) — 2026-02-27
- Sidebar Tabs: Riferimento, Pagamento, Destinazione merce, Note
- Line Items Enhanced with cascading discounts
- Quick Fill from client data
- Totals block: subtotal, sconto globale, imponibile, IVA, totale, acconto, da pagare
- Converti in Fattura v2

## Ottimizzatore di Taglio (Phase 15)
- FFD Algorithm, API + PDF export, frontend modal

## Import Rilievo -> Distinta (Phase 14)
- Split-screen bridge UI

### DDT (Documento di Trasporto) Module (Phase 19) — 2026-02-27
- 3 types: Vendita (DDT-), Conto Lavoro (CL-), Rientro (RCL-)
- Invoicex-style editor with 4 sidebar tabs (Trasporto, Destinazione, Pagamento, Note)
- Line items with cascading discounts (sconto_1, sconto_2)
- Auto-causale based on DDT type
- PDF generation with stampa_prezzi toggle
- **Converti DDT in Fattura**: one-click conversion mapping lines, client, totals → creates invoice in bozza
  - DDT status → fatturato, bidirectional link (converted_to / converted_from)
  - "Vai alla Fattura" button after conversion
  - Duplicate conversion protection (409)
- Testing: 20/20 + 18/18 backend, 100% frontend

### Fornitori (Suppliers) Module (Phase 20) — 2026-02-27
- Dedicated /fornitori page with same tab-based UI as Clienti
- Uses existing /api/clients/ endpoint with client_type=fornitore filter
- Backend filter: $in query includes both 'fornitore' and 'cliente_fornitore'
- Sidebar: separate "Clienti" and "Fornitori" nav items
- Dialog: 5 tabs (Anagrafica, Indirizzo, Contatti, Pagamento, Note)
- Contact persons with document preferences (DDT, Preventivi, Fatture, etc.)
- Testing: 16/16 backend, 100% frontend

### Perizia Sinistro (Damage Assessment) Module (Phase 21) — 2026-02-27
- Professional damage assessment tool for insurance claims on fences/gates
- 3 damage types: Strutturale (EN 1090), Estetico, Automatismi (EN 12453)
- Map picker (react-leaflet + OpenStreetMap) with reverse geocoding
- Multi-photo upload (max 5) with GPT-4o Vision AI analysis
- Auto-generated cost items based on damage type:
  - Strutturale: 6 voci (smontaggio, fornitura +20% fuori serie, trasporto, installazione, oneri normativi DoP, smaltimento)
  - Estetico: 3 voci (smontaggio, carteggiatura/verniciatura, smaltimento)
  - Automatismi: 4 voci (smontaggio, componenti, collaudo EN 12453, smaltimento)
- Editable cost table with real-time total recalculation + "Ricalcola" server-side
- Professional PDF: Stato di Fatto, Computo Metrico Estimativo, Nota Tecnica per il Perito
- Endpoints: CRUD + /analyze-photos + /recalc + /pdf
- Testing: 22/22 backend, 100% frontend

- `/api/perizie/` (CRUD + analyze-photos + recalc + PDF)

## API Endpoints
- `/api/auth/`, `/api/clients/` (with client_type filter), `/api/invoices/`, `/api/company/settings`
- `/api/rilievi/`, `/api/distinte/` + optimizer endpoints
- `/api/certificazioni/` + `/thermal/` + `/router/`
- `/api/sicurezza/`, `/api/dashboard/stats`, `/api/dashboard/fascicolo/{client_id}`
- `/api/catalogo/`, `/api/vendor/`, `/api/preventivi/`
- `/api/payment-types/` (CRUD + `seed-defaults`)
- `/api/ddt/` (CRUD + PDF + causali + convert-to-invoice)

## Prioritized Backlog

### P0 — Completed
- [x] DDT Module — DONE (Phase 19)
- [x] Fornitori Module — DONE (Phase 20)
- [x] Perizia Sinistro Module — DONE (Phase 21)

### P1
- [ ] Registro DDT (numerazione automatica e reportistica mensile spedizioni)
- [ ] Quick Fill: fatture auto-popola da cliente (stesso pattern preventivi)
- [ ] SDI direct integration
- [ ] Recurring invoices / email reminders

### P2
- [ ] Team collaboration, advanced reporting, client portal, mobile app
