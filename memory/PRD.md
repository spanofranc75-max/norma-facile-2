# Norma Facile 2.0 - Product Requirements Document

## Original Problem Statement
Build Norma Facile 2.0 - a LegalTech SaaS for Italian legal professionals with:
- React Frontend + FastAPI Backend + MongoDB
- Modular monolith backend architecture
- Google OAuth & JWT authentication
- AI-powered document generation (OpenAI GPT-4o)
- Legal Assistant Chatbot
- Document storage in MongoDB

## User Personas
1. **Italian Lawyers** - Need quick legal document generation
2. **Law Firms** - Require document management and AI assistance
3. **Legal Professionals** - Looking for efficient legal tools

## Core Requirements (Static)
- Italian language UI
- Clean/Modern Light Theme (Navy Blue #0F172A, Slate Gray)
- Emergent-managed Google OAuth
- OpenAI GPT-4o integration (via Emergent LLM Key)
- Modular backend: core/, models/, routes/, services/

## What's Been Implemented (Phase 1 - Feb 27, 2026)

### Backend Architecture
- ✅ `/backend/main.py` - FastAPI app setup & mounting
- ✅ `/backend/core/` - Config, Database, Security modules
- ✅ `/backend/models/` - User, Document, Chat Pydantic schemas
- ✅ `/backend/routes/` - Auth, Documents, Chat routers
- ✅ `/backend/services/` - Placeholder for business logic

### Authentication Module
- ✅ Emergent Google OAuth integration
- ✅ Session management with httpOnly cookies
- ✅ User creation/update in MongoDB
- ✅ Protected routes with session verification
- ✅ `/api/auth/session` - Exchange session_id for user session
- ✅ `/api/auth/me` - Get current user
- ✅ `/api/auth/logout` - Logout user

### Frontend
- ✅ Landing page with Italian UI
- ✅ Auth callback handler
- ✅ Dashboard layout with sidebar
- ✅ Protected route component
- ✅ Design system (Libre Baskerville + Inter fonts)

## Prioritized Backlog

### P0 - Phase 2 (Next)
- [ ] Document generation with GPT-4o
- [ ] Legal chatbot assistant
- [ ] Document CRUD operations

### P1 - Phase 3
- [ ] Document templates library
- [ ] Chat history persistence
- [ ] Document export (PDF)

### P2 - Future
- [ ] Team collaboration features
- [ ] Advanced document search
- [ ] Usage analytics dashboard
- [ ] Subscription/billing integration

## Next Tasks List
1. Implement DocumentService with GPT-4o integration
2. Build Document Generator UI (split screen: form + preview)
3. Implement ChatService for legal assistant
4. Build Chat UI (ChatGPT-like interface)
5. Add document history/storage view
