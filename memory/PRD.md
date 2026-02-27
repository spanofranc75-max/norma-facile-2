# Norma Facile 2.0 - Product Requirements Document

## Original Problem Statement
Build Norma Facile 2.0 - a **CRM/ERP per Fabbri (Metalworkers)** with React + FastAPI + MongoDB.

## Core Architecture
- **Norma Core Engine** (`backend/core/engine/`) — Single Source of Truth for Italian building regulations
  - `climate_zones.py` — ClimateZone enum + ENEA limits (Draft 2025/2026)
  - `thermal.py` — ThermalValidator (EN ISO 10077-1)
  - `safety.py` — SafetyValidator (D.Lgs. 81/2008 POS)
  - `ce.py` — CEValidator (EN 1090-1, EN 13241, EN 14351-1)
- **Services** — Thin wrappers over Core Engine
- **Routes** — CRUD + orchestration, no business logic

## What's Been Implemented

### Phase 1-5 — Foundation (Feb 27, 2026)
- Auth (Google OAuth), Invoicing, Rilievi, Distinta Smart BOM, Industrial Blue Theme

### Phase 6 — Certificazioni CE (Feb 27, 2026)
- 4-step wizard (DOP + CE Label + Manuale d'Uso)
- EN 1090-1 & EN 13241 support

### Phase 7 — Sicurezza Cantieri / POS (Feb 27, 2026)
- 3-step wizard, AI risk assessment (GPT-4o), PDF generation

### Phase 8 — Smart CE Calculator (Feb 27, 2026)
- Thermal transmittance Uw (EN ISO 10077-1)
- 8 glass, 8 frame, 5 spacer types
- Zone compliance badges, Ecobonus validation

### Phase 9 — Workshop Dashboard (Feb 27, 2026)
- 4 KPIs, Quick Actions, Scadenze/Materiale/Fatture widgets

### Phase 10 — Confronta Serramenti (Feb 27, 2026)
- Side-by-side thermal config comparison with "Migliore" badge

### Phase 11 — Norma Core Engine Refactoring (Feb 27, 2026)
- Created `backend/core/engine/` as Single Source of Truth
- ThermalValidator, SafetyValidator, CEValidator classes
- Updated ENEA limits to Draft 2025/2026 (A/B: 2.6, C: 1.75, D: 1.67, E: 1.30, F: 1.00)
- CEValidator gates PDF generation (422 for incomplete certs)
- SafetyValidator auto-suggests DPI per risk selection
- New endpoints: validate cert, validate POS, suggest DPI
- services/thermal_calc.py → thin wrapper (backward compatible)

## API Endpoints
- `/api/auth/` — Google OAuth
- `/api/clients/` — Client CRUD
- `/api/invoices/` — Invoice CRUD + PDF + XML
- `/api/company/settings` — Company settings
- `/api/rilievi/` — Rilievo CRUD + sketch + photo + PDF
- `/api/distinte/` — Distinta CRUD + profiles + bar calc
- `/api/certificazioni/` — CE CRUD + PDF
- `/api/certificazioni/{id}/validate` — CE validation (NEW)
- `/api/certificazioni/thermal/reference-data` — Glass/frame/spacer data
- `/api/certificazioni/thermal/calculate` — Uw calculation
- `/api/sicurezza/` — POS CRUD + AI risk + PDF
- `/api/sicurezza/{id}/validate` — POS DPI validation (NEW)
- `/api/sicurezza/{id}/suggest-dpi` — Auto-suggest DPI (NEW)
- `/api/dashboard/stats` — Workshop dashboard aggregation

## Prioritized Backlog

### P0 - Next
- [ ] Custom profiles catalog (user adds own profiles to Distinta)

### P1
- [ ] Real "Importa da Rilievo" (parse sketch → BOM)
- [ ] Advanced bar optimizer (bin-packing)
- [ ] SDI direct integration
- [ ] Recurring invoices / email reminders

### P2 - Future
- [ ] Team collaboration
- [ ] Advanced reporting/analytics
- [ ] Client portal
- [ ] Mobile app

## Technical Stack
- **Backend:** FastAPI, MongoDB, ReportLab, uvicorn
- **Frontend:** React, TailwindCSS, Shadcn/UI, react-canvas-draw
- **Auth:** Emergent-managed Google OAuth
- **AI:** OpenAI GPT-4o via emergentintegrations
- **Theme:** Industrial Blue (#0055FF, #1E293B, #334155)
