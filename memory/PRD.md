# Norma Facile 2.0 - Product Requirements Document

## Original Problem Statement
Build Norma Facile 2.0 - a **CRM/ERP per Fabbri (Metalworkers)** with React + FastAPI + MongoDB.

## Core Architecture
- **Norma Core Engine** (`backend/core/engine/`) — Single Source of Truth
  - `climate_zones.py` — ClimateZone enum + ENEA limits (Draft 2025/2026)
  - `thermal.py` — ThermalValidator (EN ISO 10077-1)
  - `safety.py` — SafetyValidator (D.Lgs. 81/2008 POS)
  - `ce.py` — CEValidator (EN 1090-1, EN 13241, EN 14351-1)
  - `router.py` — NormaRouter (ProductType → RegulationStandard mapping)

## What's Been Implemented

### Phase 1-5 — Foundation (Feb 27, 2026)
- Auth (Google OAuth), Invoicing, Rilievi, Distinta Smart BOM, Industrial Blue Theme

### Phase 6 — Certificazioni CE + Smart CE Calculator (Feb 27, 2026)
- 4-step wizard, EN 1090-1 & EN 13241, DOP + CE Label + Manuale d'Uso PDF
- Thermal transmittance Uw (EN ISO 10077-1), Confronta Serramenti

### Phase 7 — Sicurezza Cantieri / POS (Feb 27, 2026)
- 3-step wizard, AI risk assessment (GPT-4o), POS PDF generation

### Phase 8 — Workshop Dashboard (Feb 27, 2026)
- 4 KPIs, Quick Actions, Scadenze/Materiale/Fatture widgets

### Phase 9 — Norma Core Engine (Feb 27, 2026)
- ThermalValidator, SafetyValidator, CEValidator, Draft 2025/2026 ENEA limits

### Phase 10 — Catalogo Profili Personalizzato (Feb 27, 2026)
- User custom profiles CRUD, merged catalog, bulk price update

### Phase 11 — Norma Router + Vendor API (Feb 27, 2026)
- **Norma Router:** Maps 10 ProductTypes to RegulationStandards
  - Cancello/Portone → EN 13241 (gates)
  - Finestra/Portafinestra → EN 14351-1 + ThermalValidator (windows)
  - Tettoia/Scala/Soppalco/Ringhiera/Pensilina/Recinzione → EN 1090-1 (structural)
  - Returns mandatory fields list per product type
- **Vendor API (NF-Standard):**
  - Multi-key system: each vendor gets unique API key (nf_vk_xxx)
  - Keys managed by user (create/list/revoke)
  - `POST /api/vendor/import_catalog` — Protected by X-Vendor-Key header
  - NF-Standard JSON: `{vendor, system, profiles: [{code, type, uf, weight, ...}]}`
  - Upsert: same vendor+system replaces existing catalog
  - Stored in `vendor_catalogs` collection (separate from user profiles)
- **Merged Thermal Profiles:** Dropdown combines Built-in + [Vendor] + [Custom]

## API Endpoints
- `/api/auth/` — Google OAuth
- `/api/clients/` — Client CRUD
- `/api/invoices/` — Invoice CRUD + PDF + XML
- `/api/company/settings` — Company settings
- `/api/rilievi/` — Rilievo CRUD + sketch + photo + PDF
- `/api/distinte/` — Distinta CRUD + profiles + bar calc
- `/api/certificazioni/` — CE CRUD + validation + PDF
- `/api/certificazioni/thermal/` — Thermal reference data + calculation
- `/api/certificazioni/router/product-types` — All product types (PUBLIC)
- `/api/certificazioni/router/{product_type}` — Route product to standards (PUBLIC)
- `/api/sicurezza/` — POS CRUD + AI risk + validation + suggest-dpi + PDF
- `/api/dashboard/stats` — Workshop dashboard aggregation
- `/api/catalogo/` — Custom profiles CRUD + merged/all + bulk-price-update
- `/api/vendor/keys` — Vendor API key management (CRUD)
- `/api/vendor/import_catalog` — NF-Standard catalog import (X-Vendor-Key)
- `/api/vendor/catalogs` — Browse vendor catalogs
- `/api/vendor/thermal-profiles` — Merged frame types for thermal calc

## DB Collections
- users, clients, invoices, rilievi, distinte, certificazioni, pos_documents
- company_settings, user_profiles, vendor_keys, vendor_catalogs

## Prioritized Backlog

### P1
- [ ] Real "Importa da Rilievo" (parse sketch → BOM)
- [ ] Advanced bar optimizer (bin-packing)
- [ ] SDI direct integration
- [ ] Recurring invoices / email reminders

### P2 - Future
- [ ] Team collaboration, advanced reporting, client portal, mobile app
