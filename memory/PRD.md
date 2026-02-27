# Norma Facile 2.0 - Product Requirements Document

## Original Problem Statement
Build Norma Facile 2.0 - a LegalTech SaaS for Italian legal professionals with:
- React Frontend + FastAPI Backend + MongoDB
- Modular monolith backend architecture
- Google OAuth & JWT authentication
- AI-powered document generation (OpenAI GPT-4o) - Pending
- Legal Assistant Chatbot - Pending
- **Invoicing Module (Invoicex-style)** - COMPLETE
- **Rilievo Misure (On-Site Survey Tool)** - COMPLETE
- **Distinta Materiali (BOM)** - COMPLETE (skeleton)
- **Industrial Blue UI Theme** - COMPLETE

## User Personas
1. **Italian Lawyers** - Need legal document generation and invoicing
2. **Law Firms** - Require document management, client database, and billing
3. **Surveyors/Technicians** - Need on-site measurement tools with sketch capabilities

## Core Requirements (Static)
- Italian language UI
- "Industrial Blue" Theme: Primary #0055FF, Sidebar #1E293B, Text #334155
- Emergent-managed Google OAuth
- Modular backend: core/, models/, routes/, services/
- Tablet-first design for field work (Rilievi module)

## What's Been Implemented

### Phase 1 - Auth Skeleton (Feb 27, 2026)
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

### Phase 4 - Distinta Materiali (Feb 27, 2026)
- BOM CRUD (skeleton)
- Materials table editor
- Auto-calculating totals
- Import from Rilievo (mock)

### Phase 5 - Industrial Blue Theme (Feb 27, 2026)
- Primary buttons: #0055FF (Electric Blue)
- Sidebar/Table headers: #1E293B (Slate 800)
- Active nav items: #0055FF blue highlight
- Flat blue buttons, white cards with thin borders
- Dark industrial table headers with white text
- Font: Inter/Roboto
- Applied consistently across ALL pages

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

## Prioritized Backlog

### P0 - Next
- [ ] AI Document generation with GPT-4o
- [ ] Legal chatbot assistant
- [ ] Document templates library

### P1
- [ ] BOM module enhancements (smart calculation, material catalog, import from rilievo)
- [ ] BOM PDF export
- [ ] SDI direct integration
- [ ] Recurring invoices
- [ ] Email reminders for overdue invoices

### P2 - Future
- [ ] Team collaboration
- [ ] Advanced reporting/analytics
- [ ] Client portal
- [ ] Mobile app (React Native)

## Technical Stack
- **Backend:** FastAPI, MongoDB, ReportLab (PDF), uvicorn
- **Frontend:** React, TailwindCSS, Shadcn/UI, react-canvas-draw
- **Auth:** Emergent-managed Google OAuth
- **Hosting:** Kubernetes (preview environment)
- **Theme:** Industrial Blue (#0055FF, #1E293B, #334155)
