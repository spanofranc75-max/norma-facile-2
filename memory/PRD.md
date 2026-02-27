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
- Photo Gallery
- PDF Export
- Client Integration
- Tablet-First UI

### Phase 4 - Distinta Materiali Smart BOM (Feb 27, 2026)
- BOM CRUD with auto-calculated weight and surface
- Standard metal profiles database (43 profiles: Tubolari, Piatti, Angolari, Tondi)
- Profile selection dropdown with auto-fill weight_per_meter and surface_per_meter
- Smart calculations: Row Weight = Length(m) x Qty x weight_per_meter
- Smart calculations: Row Surface = Length(m) x Qty x surface_per_meter
- "Calcola Barre" - bar optimization (6m standard bars with waste calculation)
- "Stampa Lista Taglio" - PDF cutting list for workshop
- Footer: Total Weight (kg), Total Surface (mq), Total Cost
- Import from Rilievo (mock)

### Phase 5 - Industrial Blue Theme (Feb 27, 2026)
- Primary buttons: #0055FF (Electric Blue), flat, no shadows
- Sidebar/Table headers: #1E293B (Slate 800)
- Cards: white bg, border-gray-200, bg-blue-50 header sections
- Data numbers: font-mono, blue #0055FF
- Typography: Inter/Roboto (font-sans), NO serif fonts

### Phase 6 - Certificazioni CE (Feb 27, 2026)
- Full CRUD for certifications (DOP / CE Label / Manuale d'Uso e Manutenzione)
- Support for EN 1090-1 (Structural) and EN 13241 (Gates/Doors)
- 3-step wizard: Project → Standard → Technical Specs
- PDF generation: DOP + CE Label + Manuale d'Uso e Manutenzione (3 pages)
- Auto-generated declaration numbers

### Phase 7 - Sicurezza Cantieri / POS Generator (Feb 27, 2026)
- Predefined risk database: 13 risks, 14 machines, 13 DPI for metalworkers
- 3-step wizard: Cantiere → Lavorazioni → Macchine & DPI
- AI-powered risk assessment via GPT-4o (Emergent LLM Key)
- POS PDF generation (8 sections: cover, company, site, risks, machines, DPI, AI assessment, emergencies)
- Auto-fill committente from client selection
- Landing page rebranded to "CRM per Fabbri" — "Il Ferro, Organizzato"

## API Endpoints
- `/api/auth/` - Google OAuth
- `/api/clients/` - Client CRUD
- `/api/invoices/` - Invoice CRUD + status + convert
- `/api/invoices/{id}/pdf` - PDF download
- `/api/invoices/{id}/xml` - XML export
- `/api/company/settings` - Company/bank settings
- `/api/rilievi/` - Rilievo CRUD
- `/api/rilievi/{id}/sketch` - Add sketch
- `/api/rilievi/{id}/photo` - Add photo
- `/api/rilievi/{id}/pdf` - PDF export
- `/api/distinte/` - Distinta CRUD
- `/api/distinte/profiles` - Standard metal profiles catalog
- `/api/distinte/{id}/calcola-barre` - Bar optimization
- `/api/certificazioni/` - Certificazioni CE CRUD
- `/api/certificazioni/{id}/fascicolo-pdf` - DOP + CE Label + Manuale d'Uso PDF
- `/api/sicurezza/` - POS CRUD
- `/api/sicurezza/rischi` - Risk/Machine/DPI reference data
- `/api/sicurezza/{id}/genera-rischi` - AI risk assessment (GPT-4o)
- `/api/sicurezza/{id}/pdf` - POS PDF download

## Prioritized Backlog

### P0 - Next
- [ ] Custom profiles catalog (user can add their own profiles)
- [ ] Dashboard redesign for metalworkers (recent BOMs, weight stats)
- [ ] Landing page update to reflect "CRM per Fabbri" identity

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
- **Hosting:** Kubernetes (preview environment)
- **Theme:** Industrial Blue (#0055FF, #1E293B, #334155)
