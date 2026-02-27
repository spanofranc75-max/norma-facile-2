# Norma Facile 2.0 - Product Requirements Document

## Original Problem Statement
Build Norma Facile 2.0 - a **CRM/ERP per Fabbri (Metalworkers)** with React + FastAPI + MongoDB.

## Core Architecture
- **Norma Core Engine** (`backend/core/engine/`) — Single Source of Truth
  - `climate_zones.py`, `thermal.py`, `safety.py`, `ce.py`, `router.py`
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

### Ottimizzatore di Taglio Avanzato (Phase 15) — NEW (2026-02-27)
- **FFD Algorithm:** First Fit Decreasing 1D bin-packing in `services/optimizer.py`
- **API Endpoints:** POST `/{id}/ottimizza-taglio`, GET `/{id}/ottimizza-taglio-pdf`
- **Frontend Modal:** Graphical bar visualization with colored cuts, waste indicators
- **Parameters:** Configurable bar length (default 6000mm) and blade kerf (default 3mm)
- **Per-profile sections:** Collapsible with badges (bars needed, cuts, waste %)
- **PDF Export:** "Scheda Taglio Ottimizzata" with visual bar drawings via ReportLab
- **Testing:** 100% pass (13/13 backend, all frontend verified)

## API Endpoints
- `/api/auth/`, `/api/clients/`, `/api/invoices/`, `/api/company/settings`
- `/api/rilievi/`, `/api/distinte/` + `/rilievo-data/{id}` + `/{id}/import-rilievo/{id}`
- `/api/distinte/{id}/ottimizza-taglio` (POST — run FFD optimizer)
- `/api/distinte/{id}/ottimizza-taglio-pdf` (GET — optimized cutting plan PDF)
- `/api/certificazioni/` + `/thermal/` + `/router/`
- `/api/sicurezza/`
- `/api/dashboard/stats`
- `/api/catalogo/`, `/api/vendor/`, `/api/preventivi/`

## Prioritized Backlog

### P1
- [x] Advanced bar optimizer (FFD bin-packing algorithm) — DONE 2026-02-27
- [ ] SDI direct integration
- [ ] Recurring invoices / email reminders

### P2
- [ ] Team collaboration, advanced reporting, client portal, mobile app
