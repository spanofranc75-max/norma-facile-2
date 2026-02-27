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

## User Personas
1. **Italian Lawyers** - Need legal document generation and invoicing
2. **Law Firms** - Require document management, client database, and billing
3. **Surveyors/Technicians** - Need on-site measurement tools with sketch capabilities

## Core Requirements (Static)
- Italian language UI
- Clean/Modern Light Theme (Navy Blue, Slate Gray)
- Emergent-managed Google OAuth
- Modular backend: core/, models/, routes/, services/
- Tablet-first design for field work (Rilievi module)

## What's Been Implemented

### Phase 1 - Auth Skeleton (Feb 27, 2026)
- ✅ Backend modular architecture
- ✅ Emergent Google OAuth integration
- ✅ Session management with httpOnly cookies

### Phase 2 - Invoicing Module (Feb 27, 2026)
- ✅ Client CRUD (anagrafica)
- ✅ Invoice CRUD (Fattura, Preventivo, DDT, Nota di Credito)
- ✅ Invoicex-style editor with line items grid
- ✅ PDF generation (ReportLab)
- ✅ XML export (FatturaPA format for SDI)
- ✅ Tax calculations (Rivalsa, Cassa, Ritenuta)
- ✅ Document conversion (PRV→FT, DDT→FT)

### Phase 3 - Rilievi Module (Feb 27, 2026)
- ✅ **Rilievo CRUD** - Create, read, update, delete surveys
- ✅ **Sketch Pad** - Canvas drawing with react-canvas-draw
  - Upload background photo
  - Draw annotations on top
  - Color/thickness selection
  - Undo/clear functionality
  - Dimension input (L × H × P)
- ✅ **Photo Gallery** - Attach site photos with camera/upload
- ✅ **PDF Export** - Professional summary with sketches, photos, notes
- ✅ **Client Integration** - "Nuovo Rilievo" button from client page
- ✅ **Tablet-First UI** - Large buttons, touch-friendly tabs

## API Endpoints

### Invoicing
- `/api/clients/` - Client CRUD
- `/api/invoices/` - Invoice CRUD + status + convert
- `/api/invoices/{id}/pdf` - PDF download
- `/api/invoices/{id}/xml` - XML export
- `/api/company/settings` - Company/bank settings

### Rilievi
- `/api/rilievi/` - Rilievo CRUD
- `/api/rilievi/{id}/sketch` - Add sketch
- `/api/rilievi/{id}/photo` - Add photo
- `/api/rilievi/{id}/pdf` - PDF export

## Prioritized Backlog

### P0 - Phase 4 (Next)
- [ ] AI Document generation with GPT-4o
- [ ] Legal chatbot assistant
- [ ] Document templates library

### P1 - Phase 5
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
