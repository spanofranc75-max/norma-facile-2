# Norma Facile 2.0 - Product Requirements Document

## Original Problem Statement
Build Norma Facile 2.0 - a **CRM/ERP per Fabbri (Metalworkers)** with React + FastAPI + MongoDB.

## Core Architecture
- **Norma Core Engine** (`backend/core/engine/`) — Single Source of Truth
  - `climate_zones.py` — ClimateZone enum + ENEA limits (Draft 2025/2026)
  - `thermal.py` — ThermalValidator (EN ISO 10077-1)
  - `safety.py` — SafetyValidator (D.Lgs. 81/2008 POS)
  - `ce.py` — CEValidator (EN 1090-1, EN 13241, EN 14351-1)
  - `router.py` — NormaRouter (ProductType -> RegulationStandard)

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

### Catalogo Profili Personalizzato (Phase 11)
- Custom profiles CRUD, merged catalog, bulk price update

### Norma Router + Vendor API (Phase 12)
- 10 ProductTypes -> RegulationStandards, multi-key vendor system, NF-Standard JSON

### Preventivi Commerciali (Phase 13) — NEW
- Smart Quotes with thermal compliance integration
- CRUD with auto-generated PRV-YYYY-NNNN numbers
- Line items with optional thermal_data (glass/frame/spacer/zone per line)
- "Verifica Compliance" button runs NormaCore ThermalValidator on all thermal lines
- Green/red compliance banner and detailed compliance table per line
- Technical Details drawer (Sheet) per line item for thermal config
- PDF: commercial offer + technical annex "Prestazioni Termiche Calcolate"
- Auto-calculated totals (subtotal, IVA, total)

## API Endpoints
- `/api/auth/`, `/api/clients/`, `/api/invoices/`, `/api/company/settings`
- `/api/rilievi/`, `/api/distinte/`
- `/api/certificazioni/` + `/thermal/` + `/router/`
- `/api/sicurezza/`
- `/api/dashboard/stats`
- `/api/catalogo/` + `/merged/all` + `/bulk-price-update`
- `/api/vendor/keys` + `/import_catalog` + `/catalogs` + `/thermal-profiles`
- `/api/preventivi/` — CRUD + check-compliance + PDF (NEW)

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
