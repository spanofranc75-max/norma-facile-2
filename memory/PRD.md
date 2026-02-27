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
- Custom profiles, merged catalog, bulk price update, multi-key vendor system

### Preventivi Commerciali (Phase 13)
- Smart Quotes with thermal compliance, PDF with technical annex
- Converti in Fattura, Workflow Timeline (PRV->Accettato->FT->Pagata)

### Import Rilievo -> Distinta (Phase 14) — NEW
- **The Bridge:** Split-screen dialog in Distinta editor
- **Dimension Parser:** Extracts measurements from rilievo notes (H=2200, 1500x900, standalone mm) and sketch dimension fields
- **Interactive UI:** Left panel shows rilievo data with clickable dimension chips, right panel shows BOM rows
- **Apply Dimension:** Click chip -> applies value_mm to selected BOM row's length, or creates new row
- **Link Rilievo:** Connects rilievo to distinta, auto-sets client_id, appends reference note
- Endpoints: GET /rilievo-data/{id} (parse), POST /{id}/import-rilievo/{id} (link)

## API Endpoints
- `/api/auth/`, `/api/clients/`, `/api/invoices/`, `/api/company/settings`
- `/api/rilievi/`, `/api/distinte/` + `/rilievo-data/{id}` + `/{id}/import-rilievo/{id}`
- `/api/certificazioni/` + `/thermal/` + `/router/`
- `/api/sicurezza/`
- `/api/dashboard/stats`
- `/api/catalogo/`, `/api/vendor/`, `/api/preventivi/`

## Prioritized Backlog

### P1
- [ ] Advanced bar optimizer (bin-packing algorithm)
- [ ] SDI direct integration
- [ ] Recurring invoices / email reminders

### P2
- [ ] Team collaboration, advanced reporting, client portal, mobile app
