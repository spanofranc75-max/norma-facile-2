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
- AI parsing certificati materiali, CAM compliance + CO2, Repository documenti, Compliance Dashboard

### Fascicolo Tecnico EN 1090
- 6 documenti singoli + Super Fascicolo Tecnico Unico (PDF aggregato 5 capitoli)
- Auto-compilazione aggressiva (~90%)

### Rientro Conto Lavoro (Mar 2026)
- Workflow: inviato -> rientrato -> verificato
- Modale rientro: data, DDT forn., peso, QC, upload certificato
- NCR PDF auto per non conformita', verifica auto-completa fase produzione

### Tempi Produzione (NUOVO - Mar 2026)
- Campi opzionali: started_at, completed_at, operator_name
- Modale conferma completamento con date precompilate
- Badge date/operatore accanto allo stato completato
- Backward compatible: vecchi campi data_inizio/data_fine preservati
- PDF Fascicolo usa completed_at con fallback sicuro

### Impostazioni
- Tab Certificazioni: EN 1090-1 + EN 13241 + Classe Esecuzione Default

## Backlog
- P1: Fatture in Cloud SDI, verifica parsing AI
- P2: Test e2e, bug preview PDF CL, seeding dati
- P3: Repository miglioramenti, CSV per CNC, stato SOSPESA
- Futuro: PWA, object storage, versioning, Stripe
