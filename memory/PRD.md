# Norma Facile 2.0 - Product Requirements Document

## Original Problem Statement
Build Norma Facile 2.0 - a **CRM/ERP per Fabbri (Metalworkers)** with React + FastAPI + MongoDB.

## Core Architecture
- **Norma Core Engine** (`backend/core/engine/`) — Single Source of Truth
  - `climate_zones.py`, `thermal.py`, `safety.py`, `ce.py`, `router.py`

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
- Custom profiles CRUD, merged catalog, bulk price update
- Multi-key vendor system, NF-Standard JSON import

### Preventivi Commerciali (Phase 13)
- Smart Quotes with thermal compliance, PDF with technical annex
- Converti in Fattura (PRV -> FT one-click conversion)
- **Workflow Timeline:** Visual 4-step progress bar (Preventivo -> Accettato -> Fattura -> Pagata) with clickable invoice link and real-time status propagation

## API Endpoints
- `/api/auth/`, `/api/clients/`, `/api/invoices/`, `/api/company/settings`
- `/api/rilievi/`, `/api/distinte/`
- `/api/certificazioni/` + `/thermal/` + `/router/`
- `/api/sicurezza/`
- `/api/dashboard/stats`
- `/api/catalogo/` + `/merged/all` + `/bulk-price-update`
- `/api/vendor/keys` + `/import_catalog` + `/catalogs` + `/thermal-profiles`
- `/api/preventivi/` — CRUD + check-compliance + PDF + convert-to-invoice

## Prioritized Backlog

### P1
- [ ] Real "Importa da Rilievo" (parse sketch -> BOM)
- [ ] Advanced bar optimizer (bin-packing)
- [ ] SDI direct integration
- [ ] Recurring invoices / email reminders

### P2
- [ ] Team collaboration, advanced reporting, client portal, mobile app
