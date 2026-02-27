# Norma Facile 2.0 - Product Requirements Document

## Original Problem Statement
Build Norma Facile 2.0 - a **CRM/ERP per Fabbri (Metalworkers)** with React + FastAPI + MongoDB.

## Core Architecture
- **Norma Core Engine** (`backend/core/engine/`) — Single Source of Truth
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

### Ottimizzatore di Taglio Avanzato (Phase 15) — 2026-02-27
- FFD Algorithm (First Fit Decreasing 1D bin-packing)
- API: POST /{id}/ottimizza-taglio, GET /{id}/ottimizza-taglio-pdf
- Frontend modal with graphical bar visualization + PDF export

### UI/UX Polish Phase — "Arredamento" (Phase 16) — 2026-02-27
- **Dashboard Upgrade:** Gradient KPI cards (blue/amber/emerald/violet), Recharts BarChart "Fatturato Mensile" (6 months), custom tooltip
- **Quick Action FAB:** Floating action button bottom-right, expands to [Rilievo, Preventivo, Cliente] with slide-in animation
- **Fascicolo Cantiere:** New page `/fascicolo/:clientId` with vertical timeline (type-colored dots: rilievo/distinta/preventivo/fattura/certificazione), document grid (5 gradient count cards)
- **Empty States:** Reusable `EmptyState` component with per-module SVG illustrations (clients/invoices/rilievi/distinte/preventivi/fascicolo), friendly CTA buttons "Crea il primo [X]"
- **Backend:** `/api/dashboard/stats` now returns `fatturato_mensile` (6 months aggregation), `/api/dashboard/fascicolo/:clientId` aggregates all client documents

## API Endpoints
- `/api/auth/`, `/api/clients/`, `/api/invoices/`, `/api/company/settings`
- `/api/rilievi/`, `/api/distinte/` + optimizer endpoints
- `/api/certificazioni/` + `/thermal/` + `/router/`
- `/api/sicurezza/`
- `/api/dashboard/stats` (GET — KPIs + fatturato_mensile chart data)
- `/api/dashboard/fascicolo/{client_id}` (GET — project dossier timeline + documents)
- `/api/catalogo/`, `/api/vendor/`, `/api/preventivi/`

## Prioritized Backlog

### P1
- [x] Advanced bar optimizer (FFD bin-packing) — DONE
- [x] UI/UX Polish Phase (Dashboard, Empty States, Fascicolo) — DONE
- [ ] SDI direct integration
- [ ] Recurring invoices / email reminders

### P2
- [ ] Team collaboration, advanced reporting, client portal, mobile app
