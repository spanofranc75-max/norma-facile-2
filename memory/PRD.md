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
- 4-step wizard, EN 1090-1 & EN 13241, DOP + CE Label + Manuale d'Uso PDF

### Phase 7 — Sicurezza Cantieri / POS (Feb 27, 2026)
- 3-step wizard, AI risk assessment (GPT-4o), POS PDF generation

### Phase 8 — Smart CE Calculator (Feb 27, 2026)
- Thermal transmittance Uw (EN ISO 10077-1), 8 glass/8 frame/5 spacer types, 6 zones

### Phase 9 — Workshop Dashboard (Feb 27, 2026)
- 4 KPIs, Quick Actions, Scadenze/Materiale/Fatture widgets

### Phase 10 — Confronta Serramenti (Feb 27, 2026)
- Side-by-side thermal config comparison with "Migliore" badge

### Phase 11 — Norma Core Engine (Feb 27, 2026)
- ThermalValidator, SafetyValidator, CEValidator as Single Source of Truth
- Draft 2025/2026 ENEA limits, PDF generation blocked for incomplete certs (422)

### Phase 12 — Catalogo Profili Personalizzato (Feb 27, 2026)
- User custom profiles CRUD (code, description, category, weight/surface/price per meter, supplier)
- Categories: Ferro, Alluminio, Accessori, Verniciatura, Altro
- Searchable merged catalog (43 standard + custom profiles)
- Bulk price update (increase/decrease all by X%, optional category filter)
- Integration with Distinta module via `/api/catalogo/merged/all`
- Frontend: Table view, search, category/source filters, add/edit/delete dialogs

## API Endpoints
- `/api/auth/` — Google OAuth
- `/api/clients/` — Client CRUD
- `/api/invoices/` — Invoice CRUD + PDF + XML
- `/api/company/settings` — Company settings
- `/api/rilievi/` — Rilievo CRUD + sketch + photo + PDF
- `/api/distinte/` — Distinta CRUD + profiles + bar calc
- `/api/certificazioni/` — CE CRUD + validation + PDF
- `/api/certificazioni/thermal/` — Thermal reference data + calculation
- `/api/sicurezza/` — POS CRUD + AI risk + validation + suggest-dpi + PDF
- `/api/dashboard/stats` — Workshop dashboard aggregation
- `/api/catalogo/` — Custom profiles CRUD
- `/api/catalogo/merged/all` — Merged catalog (standard + custom)
- `/api/catalogo/bulk-price-update` — Bulk price update

## Prioritized Backlog

### P0 - Next
- [ ] Norma Router (ProductType → RegulationStandard mapping)
- [ ] Vendor API (NF-Standard JSON import for manufacturers)

### P1
- [ ] Real "Importa da Rilievo" (parse sketch → BOM)
- [ ] Advanced bar optimizer (bin-packing)
- [ ] SDI direct integration
- [ ] Recurring invoices / email reminders

### P2 - Future
- [ ] Team collaboration
- [ ] Advanced reporting/analytics
- [ ] Client portal, Mobile app

## Technical Stack
- **Backend:** FastAPI, MongoDB, ReportLab, uvicorn
- **Frontend:** React, TailwindCSS, Shadcn/UI, react-canvas-draw
- **Auth:** Emergent-managed Google OAuth
- **AI:** OpenAI GPT-4o via emergentintegrations
- **Theme:** Industrial Blue (#0055FF, #1E293B, #334155)
