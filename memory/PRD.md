# Norma Facile 2.0 - Product Requirements Document

## Original Problem Statement
Build Norma Facile 2.0 - a **CRM/ERP per Fabbri (Metalworkers)** with:
- React Frontend + FastAPI Backend + MongoDB
- Modular monolith backend architecture
- Google OAuth & JWT authentication
- Invoicing Module (Invoicex-style for Italian market)
- On-Site Survey Tool ("Rilievo Misure") for field measurements
- Smart Bill of Materials ("Distinta Materiali") with auto-calculated weight/surface
- "Industrial Blue" UI theme for a "Precision Engineering" aesthetic

## User Personas
1. **Fabbri / Metalworkers** - Need BOM calculations, cutting lists, weight/surface tracking
2. **Small Metal Workshops** - Require client management, invoicing, and project tracking
3. **Field Technicians** - Need on-site measurement tools with sketch capabilities

## Core Requirements (Static)
- Italian language UI
- "Industrial Blue" Theme: Primary #0055FF, Sidebar #1E293B, Text #334155
- Emergent-managed Google OAuth
- Modular backend: core/, models/, routes/, services/
- Tablet-first design for field work (Rilievi module)

## What's Been Implemented

### Phase 1 - Auth (Feb 27, 2026)
- Backend modular architecture
- Emergent Google OAuth integration
- Session management with httpOnly cookies

### Phase 2 - Invoicing Module (Feb 27, 2026)
- Client CRUD (anagrafica)
- Invoice CRUD (Fattura, Preventivo, DDT, Nota di Credito)
- Invoicex-style editor with line items grid
- PDF generation (ReportLab)
- XML export (FatturaPA format for SDI)
- Tax calculations (Rivalsa, Cassa, Ritenuta)
- Document conversion (PRV->FT, DDT->FT)

### Phase 3 - Rilievi Module (Feb 27, 2026)
- Rilievo CRUD
- Sketch Pad with react-canvas-draw
- Photo Gallery, PDF Export, Client Integration, Tablet-First UI

### Phase 4 - Distinta Materiali Smart BOM (Feb 27, 2026)
- BOM CRUD with auto-calculated weight and surface
- Standard metal profiles database (43 profiles)
- "Calcola Barre" bar optimization, "Stampa Lista Taglio" PDF cutting list
- Footer: Total Weight (kg), Total Surface (mq), Total Cost

### Phase 5 - Industrial Blue Theme (Feb 27, 2026)
- Primary #0055FF, Sidebar #1E293B, Cards white with blue headers

### Phase 6 - Certificazioni CE (Feb 27, 2026)
- Full CRUD (DOP / CE Label / Manuale d'Uso e Manutenzione)
- EN 1090-1 (Structural) and EN 13241 (Gates/Doors)
- 3-step wizard + PDF generation

### Phase 7 - Sicurezza Cantieri / POS Generator (Feb 27, 2026)
- 13 risks, 14 machines, 13 DPI database
- 3-step wizard with AI risk assessment (GPT-4o)
- POS PDF generation

### Phase 8 - Smart CE Calculator (Feb 27, 2026)
- Thermal transmittance (Uw) per EN ISO 10077-1
- 8 glass types, 8 frame types, 5 spacer types, 6 climate zones
- 4th step in Certificazioni wizard with real-time calculation
- Red/green Ecobonus eligibility display, zone compliance badges
- Thermal data included in generated PDF

### Phase 9 - Workshop Dashboard "Cruscotto Officina" (Feb 27, 2026)
- 4 KPI cards: Ferro in Lavorazione (kg), Cantieri Attivi, POS Generati, Fatturato Mese
- Quick Actions: Nuovo Rilievo, Nuova Distinta, Stampa POS
- Widgets: Prossime Scadenze, Materiale da Ordinare (bars needed), Documenti Recenti
- Backend aggregation endpoint: /api/dashboard/stats

### Phase 10 - Confronta Serramenti (Feb 27, 2026)
- Save multiple thermal configs for side-by-side comparison
- Comparison table with Uw values, glass/frame/spacer details
- Best configuration highlighted with "Migliore" badge
- Ecobonus eligibility per configuration

## API Endpoints
- `/api/auth/` - Google OAuth
- `/api/clients/` - Client CRUD
- `/api/invoices/` - Invoice CRUD + status + convert + PDF + XML
- `/api/company/settings` - Company/bank settings
- `/api/rilievi/` - Rilievo CRUD + sketch + photo + PDF
- `/api/distinte/` - Distinta CRUD + profiles + bar calculation
- `/api/certificazioni/` - Certificazioni CE CRUD + PDF
- `/api/certificazioni/thermal/reference-data` - Glass/frame/spacer data
- `/api/certificazioni/thermal/calculate` - Uw calculation
- `/api/sicurezza/` - POS CRUD + AI risk assessment + PDF
- `/api/dashboard/stats` - Workshop dashboard aggregation

## Prioritized Backlog

### P0 - Next
- [ ] Custom profiles catalog (user can add their own profiles)

### P1
- [ ] Real "Importa da Rilievo" (parse sketch dimensions into BOM items)
- [ ] Advanced bar optimizer (bin-packing algorithm)
- [ ] SDI direct integration
- [ ] Recurring invoices
- [ ] Email reminders for overdue invoices

### P2 - Future
- [ ] Team collaboration
- [ ] Advanced reporting/analytics (monthly weight, cost trends)
- [ ] Client portal
- [ ] Mobile app (React Native)

## Technical Stack
- **Backend:** FastAPI, MongoDB, ReportLab (PDF), uvicorn
- **Frontend:** React, TailwindCSS, Shadcn/UI, react-canvas-draw
- **Auth:** Emergent-managed Google OAuth
- **AI:** OpenAI GPT-4o via emergentintegrations library
- **Hosting:** Kubernetes (preview environment)
- **Theme:** Industrial Blue (#0055FF, #1E293B, #334155)
