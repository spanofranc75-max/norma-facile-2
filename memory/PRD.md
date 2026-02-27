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

### Workshop Dashboard (Phase 9)
- 4 KPIs, Quick Actions, Scadenze/Materiale/Fatture widgets

### Norma Core Engine + Catalogo + Vendor API (Phase 10-12)
- ThermalValidator, SafetyValidator, CEValidator, NormaRouter
- Custom profiles, merged catalog, bulk price update, multi-key vendor system

### Preventivi Commerciali (Phase 13)
- Smart Quotes with thermal compliance, PDF with technical annex
- Converti in Fattura, Workflow Timeline (PRV->Accettato->FT->Pagata)

### Import Rilievo -> Distinta (Phase 14)
- The Bridge: Split-screen dialog, dimension parser, interactive UI

### Ottimizzatore di Taglio Avanzato (Phase 15)
- FFD Algorithm, API + PDF export, frontend modal with bar visualization

### UI/UX Polish Phase — "Arredamento" (Phase 16)
- Dashboard: Gradient KPI cards, Recharts BarChart "Fatturato Mensile", FAB "Nuovo"
- Fascicolo Cantiere: `/fascicolo/:clientId` timeline + document grid
- Empty States: SVG illustrations + CTA across all list pages

### Scheda Cliente/Fornitore + Tipi Pagamento (Phase 17) — 2026-02-27
- **Tipi Pagamento CRUD:** New module `/impostazioni/pagamenti` with:
  - Full CRUD table with installment checkbox grid (Imm, 30, 60, 90...360 gg, FM, IVA30)
  - Tipo: BON/RIB/CON/ELE, Codice, Descrizione, Spese incasso, Banca necessaria
  - "Carica Predefiniti" button seeds 11 standard Italian payment types (BB30, BB60, BB30-60, RB30, etc.)
- **Client Model Expanded:** client_type (Cliente/Fornitore/Cliente-Fornitore), persona_fisica, titolo/cognome/nome, codice_sdi, PEC, cellulare, fax, sito_web, contacts array, payment_type_id, IBAN, banca
- **Tab-based Client Form:** 5 tabs (Anagrafica, Indirizzo, Contatti, Pagamento, Note)
- **Persone di Riferimento:** Sub-table with tipo, nome, telefono, email + document email preferences (Preventivi, Fatture, Solleciti, Ordini, DDT)
- **Payment Type Linking:** Client's Pagamento tab links to CRUD payment types
- **Backward Compatible:** Old client_type values (azienda/privato/pa) still work
- **Testing:** Backend 20/20, Frontend 100% verified

## API Endpoints
- `/api/auth/`, `/api/clients/`, `/api/invoices/`, `/api/company/settings`
- `/api/rilievi/`, `/api/distinte/` + optimizer endpoints
- `/api/certificazioni/` + `/thermal/` + `/router/`
- `/api/sicurezza/`
- `/api/dashboard/stats`, `/api/dashboard/fascicolo/{client_id}`
- `/api/catalogo/`, `/api/vendor/`, `/api/preventivi/`
- `/api/payment-types/` (CRUD + `seed-defaults`)

## Prioritized Backlog

### P0 — Next Steps
- [ ] Propagazione dati cliente/pagamento nei Preventivi e Fatture (auto-fill condizioni pagamento)

### P1
- [ ] SDI direct integration
- [ ] Recurring invoices / email reminders

### P2
- [ ] Team collaboration, advanced reporting, client portal, mobile app
