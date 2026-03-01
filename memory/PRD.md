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

### Consegne al Cliente (NUOVO - Mar 2026)
- Sezione "Consegne al Cliente" nella commessa
- POST /api/commesse/{cid}/consegne: crea DDT pre-compilato con materiali dalla commessa
- GET /api/commesse/{cid}/consegne/{id}/pacchetto-pdf: PDF unico DDT + DoP + Etichetta CE
- DDT creato in ddt_documents con link commessa_id
- Bottone "DDT + DoP + CE" per download pacchetto completo
- Bottone "Modifica DDT" per aprire editor DDT

### Impostazioni
- Tab Certificazioni: EN 1090-1 + EN 13241 + Classe Esecuzione Default + Ente Certificatore

## Backlog
- P1: Fatture in Cloud SDI, verifica parsing AI
- P2: Test e2e, seeding dati
- P3: CSV per CNC, stato SOSPESA, repository miglioramenti
- Futuro: PWA, object storage, versioning, Stripe
