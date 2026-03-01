# Norma Facile 2.0 - PRD

## Problema Originale
SaaS per fabbri e carpenterie italiane. CRM, compliance e gestione operativa centrata sulla "Commessa".

## Architettura
- Frontend: React + Tailwind + Shadcn/UI
- Backend: FastAPI + MongoDB
- Auth: Emergent-managed Google OAuth
- PDF: WeasyPrint + pypdf
- AI: OpenAI GPT-4o Vision

## Funzionalita' Implementate

### Core
- Commesse, Preventivi, Clienti, Fornitori, Procurement, DDT, Fatture
- AI parsing certificati, CAM compliance + CO2, Repository documenti, Dashboard

### Fascicolo Tecnico EN 1090
- 6 documenti singoli + Super Fascicolo Unico (PDF 5 capitoli)
- Auto-compilazione aggressiva (~90%)

### Rientro Conto Lavoro
- Workflow: inviato -> rientrato -> verificato
- Modale rientro, NCR PDF, auto-fase, cert nel fascicolo

### Tempi Produzione
- started_at, completed_at, operator_name (opzionali, backward compat)
- Modale completamento con date + operatore

### Consegne al Cliente
- Sezione "Consegne al Cliente" nella commessa
- POST /api/commesse/{cid}/consegne: crea DDT pre-compilato con materiali dalla commessa
- GET /api/commesse/{cid}/consegne/{id}/pacchetto-pdf: PDF unico DDT + DoP + Etichetta CE

### Impostazioni
- Tab Certificazioni: EN 1090-1 + EN 13241 + Classe Esecuzione Default + Ente Certificatore

### Archivio Documentale Aziendale (Mar 2026)
- Pagina isolata /sistema-qualita accessibile dalla sidebar (gruppo Certificazioni)
- Backend: /api/company/documents/ (CRUD completo con upload file)
- Categorie: Manuali Qualita, Procedure, Certificazioni, Template, Normative, Organigramma, Altro
- UI: Shadcn Table con header scuro (bg-[#1E293B]), toolbar Card (Search + Select), Badge colorate
- Upload con dialog (drop zone, titolo, categoria, tag), download, delete con conferma
- File salvati su disco locale (/app/backend/uploads/company_docs/)
- Design coerente con Norma Facile 2.0 (stile identico a ArticoliPage)
- Testato: 14/14 frontend test passati (iteration_87.json)

## Bug Fix Critici (Mar 2026)

### P0: Bug Loop/Reload Editor Preventivi - RISOLTO
- **Problema:** Digitando in campi come "Tempi di Consegna" o "Ing. Disegno", la pagina entrava in loop mostrando spinner e perdendo tutti i dati del form
- **Causa Root:** ErrorBoundary wrappava l'intera app (BrowserRouter + AuthProvider). Quando errori DOM venivano catturati (es. da estensioni browser come Grammarly), l'ErrorBoundary faceva remount di tutto, incluso AuthProvider che resettava loading=true e user=null
- **Fix applicati:**
  1. ErrorBoundary spostato sotto AuthProvider (App.js) - lo stato auth non viene mai resettato
  2. ProtectedRoute usa sessionStorage ('nf_was_authenticated') per sopravvivere ai remount
  3. PreventivoEditorPage ha auto-save su sessionStorage con debounce 300ms
- **Testato:** 8/8 test passati con testing agent (iteration_85.json)

## Backlog
- P1: Fatture in Cloud SDI (necessita credenziali utente), verifica parsing AI
- P2: Test e2e completo, seeding dati, coesione flusso
- P3: CSV per CNC, stato SOSPESA, miglioramenti repository documenti
- Futuro: PWA, object storage, versioning, Stripe
- Refactoring: CommessaOpsPanel.js troppo grande, da dividere
