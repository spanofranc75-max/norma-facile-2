# Norma Facile 2.0 - Product Requirements Document

## Original Problem Statement
Build Norma Facile 2.0 - a LegalTech SaaS for Italian legal professionals with:
- React Frontend + FastAPI Backend + MongoDB
- Modular monolith backend architecture
- Google OAuth & JWT authentication
- AI-powered document generation (OpenAI GPT-4o) - Phase 2
- Legal Assistant Chatbot - Phase 2
- **Invoicing Module (Invoicex-style)** - IMPLEMENTED

## User Personas
1. **Italian Lawyers** - Need quick legal document generation and invoicing
2. **Law Firms** - Require document management, client database, and billing
3. **Legal Professionals** - Looking for efficient legal tools and compliance

## Core Requirements (Static)
- Italian language UI
- Clean/Modern Light Theme (Navy Blue #0F172A, Slate Gray)
- Emergent-managed Google OAuth
- OpenAI GPT-4o integration (via Emergent LLM Key)
- Modular backend: core/, models/, routes/, services/
- Invoicex-style invoicing with PDF/XML export

## What's Been Implemented

### Phase 1 - Auth Skeleton (Feb 27, 2026)
- ✅ Backend modular architecture
- ✅ Emergent Google OAuth integration
- ✅ Session management with httpOnly cookies
- ✅ Protected routes

### Phase 2 - Invoicing Module (Feb 27, 2026)

#### Backend
- ✅ **Client CRUD** - `/api/clients/` - Full anagrafica management
- ✅ **Invoice CRUD** - `/api/invoices/` - Create, read, update, delete
- ✅ **PDF Generation** - `/api/invoices/{id}/pdf` - Professional Italian PDF
- ✅ **XML Export** - `/api/invoices/{id}/xml` - FatturaPA format for SDI
- ✅ **Document Conversion** - `/api/invoices/convert` - PRV→FT, DDT→FT
- ✅ **Status Tracking** - Manual status workflow (Bozza→Emessa→Pagata)
- ✅ **Company Settings** - `/api/company/settings` - Header/bank info
- ✅ **Auto Numbering** - TYPE-YEAR-NUMBER format (FT-2026-001)
- ✅ **Tax Calculations** - Rivalsa INPS, Cassa Previdenza, Ritenuta d'acconto

#### Frontend
- ✅ **Clients Page** - Table with search, CRUD dialogs
- ✅ **Invoices List** - Filters by type/status/year, action menu
- ✅ **Invoice Editor** - Invoicex-style dense form with:
  - Header (type, dates, client, payment terms)
  - Line items grid (code, description, qty, price, discount, VAT)
  - Tax settings checkboxes (Rivalsa, Cassa, Ritenuta)
  - Live totals calculation (Imponibile, IVA breakdown, Totale)
- ✅ **Settings Page** - Company data and bank details
- ✅ **Dashboard** - Stats cards, recent invoices

## Prioritized Backlog

### P0 - Phase 3 (Next)
- [ ] AI Document generation with GPT-4o
- [ ] Legal chatbot assistant
- [ ] Document templates library

### P1 - Phase 4
- [ ] SDI direct integration (Agenzia Entrate)
- [ ] Recurring invoices
- [ ] Multi-currency support

### P2 - Future
- [ ] Team collaboration
- [ ] Advanced reporting/analytics
- [ ] Email reminders for overdue invoices
- [ ] Client portal

## Technical Notes
- PDF Generation: ReportLab (server-side, vector quality)
- XML Format: FatturaPA v1.2 (Italian e-invoicing standard)
- Numbering: Auto-increment per type/year, resets annually
- Tax Logic: Flexible Rivalsa/Cassa/Ritenuta with configurable rates

## Next Tasks List
1. Implement DocumentService with GPT-4o for legal docs
2. Build Chat UI for legal assistant
3. Add SDI submission status polling
4. Create invoice email sending feature
