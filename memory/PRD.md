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
- 4-step wizard, DOP + CE Label + Manuale, Thermal Uw calculator, Confronta Serramenti

### Sicurezza Cantieri / POS (Phase 7)
- 3-step wizard, AI risk assessment (GPT-4o), POS PDF

### Workshop Dashboard (Phase 9)
- 4 KPIs, Quick Actions, Scadenze/Materiale/Fatture widgets

### Norma Core Engine (Phase 10)
- ThermalValidator, SafetyValidator, CEValidator, Draft 2025/2026 ENEA limits

### Catalogo Profili + Norma Router + Vendor API (Phase 11-12)
- Custom profiles CRUD, merged catalog, bulk price update
- 10 ProductTypes -> RegulationStandards, multi-key vendor system, NF-Standard JSON

### Preventivi Commerciali (Phase 13)
- Smart Quotes with thermal compliance, PDF with technical annex
- **Converti in Fattura:** One-click conversion PRV -> FT with all lines/client/notes imported
  - Auto-marks preventivo as "accettato", links to invoice
  - Blocks duplicate conversions (409), requires client (422)

## API Endpoints
- `/api/auth/`, `/api/clients/`, `/api/invoices/`, `/api/company/settings`
- `/api/rilievi/`, `/api/distinte/`
- `/api/certificazioni/` + `/thermal/` + `/router/`
- `/api/sicurezza/`
- `/api/dashboard/stats`
- `/api/catalogo/` + `/merged/all` + `/bulk-price-update`
- `/api/vendor/keys` + `/import_catalog` + `/catalogs` + `/thermal-profiles`
- `/api/preventivi/` — CRUD + check-compliance + PDF + convert-to-invoice

## DB Collections
- users, clients, invoices, rilievi, distinte, certificazioni, pos_documents
- company_settings, user_profiles, vendor_keys, vendor_catalogs, preventivi

## Prioritized Backlog

### P1
- [ ] Real "Importa da Rilievo" (parse sketch -> BOM)
- [ ] Advanced bar optimizer (bin-packing)
- [ ] SDI direct integration
- [ ] Recurring invoices / email reminders

### P2
- [ ] Team collaboration, advanced reporting, client portal, mobile app
