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
- **Sidebar Tabs:** Riferimento (sconto globale, acconto), Pagamento (condizioni, IBAN, banca), Destinazione merce, Note
- **Line Items Enhanced:** Codice articolo, Sconto 1%, Sconto 2% (cascading), Prezzo netto calcolato, UdM dropdown (pz/m/mq/kg/h/corpo)
- **Quick Fill:** Selezione cliente auto-compila: payment_type, IBAN, banca, destinazione merce dall'anagrafica
- **Totals Dettagliati:** Totale senza IVA → Sconto globale → Imponibile → Totale IVA → TOTALE → Acconto → DA PAGARE
- **Converti in Fattura v2:** Porta sconti, prezzo netto, tipo pagamento nella fattura
- **Backend:** calc_line con sconti cascata, calc_totals(lines, sconto_globale, acconto), payment_type mapping per enum fattura
- **Testing:** Backend 22/22, Frontend 100%

## Ottimizzatore di Taglio (Phase 15)
- FFD Algorithm, API + PDF export, frontend modal

## Import Rilievo -> Distinta (Phase 14)
- Split-screen bridge UI

## API Endpoints
- `/api/auth/`, `/api/clients/`, `/api/invoices/`, `/api/company/settings`
- `/api/rilievi/`, `/api/distinte/` + optimizer endpoints
- `/api/certificazioni/` + `/thermal/` + `/router/`
- `/api/sicurezza/`, `/api/dashboard/stats`, `/api/dashboard/fascicolo/{client_id}`
- `/api/catalogo/`, `/api/vendor/`, `/api/preventivi/`
- `/api/payment-types/` (CRUD + `seed-defaults`)

## Prioritized Backlog

### P0 — In Progress
- [x] Quick Fill: preventivi auto-popola da cliente — DONE
- [ ] Quick Fill: fatture auto-popola da cliente (stesso pattern)

### P1
- [ ] SDI direct integration
- [ ] Recurring invoices / email reminders

### P2
- [ ] Team collaboration, advanced reporting, client portal, mobile app
