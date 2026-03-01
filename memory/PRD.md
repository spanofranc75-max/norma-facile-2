# Norma Facile 2.0 - PRD

## Problema Originale
SaaS per fabbri e carpenterie italiane. CRM, compliance e gestione operativa con architettura centrata sulla "Commessa" (Job Order).

## Architettura
- **Frontend:** React + Tailwind + Shadcn/UI
- **Backend:** FastAPI + MongoDB
- **Auth:** Emergent-managed Google OAuth
- **PDF:** WeasyPrint + pypdf
- **AI:** OpenAI GPT-4o Vision (certificati)
- **Fatturazione:** Fatture in Cloud (SDI)

## Funzionalita' Implementate

### Core
- Gestione Commesse, Preventivi, Clienti, Fornitori
- Procurement (RdP, OdA)
- DDT, Fatture, Note di Credito
- Distinte di taglio
- AI parsing certificati materiali (GPT-4o Vision)
- CAM compliance + CO2 savings
- Repository documenti centralizzato
- Compliance Dashboard

### Fascicolo Tecnico EN 1090
- 6 documenti singoli: DOP, Etichetta CE, Piano di Controllo, Rapporto VT, Registro Saldatura, Riesame Tecnico
- Auto-compilazione aggressiva (~90%)
- Firma digitale incorporata nei PDF

### Super Fascicolo Tecnico Unico (Mar 2026)
- PDF unico aggregato: Copertina + Indice + 5 Capitoli
- Include certificati 3.1 + certificati conto lavoro (rientro)
- Endpoint: GET /api/commesse/{cid}/fascicolo-tecnico-completo

### Rientro Conto Lavoro (NUOVO - Mar 2026)
- Workflow completo: inviato -> rientrato -> verificato
- Modale rientro con: data, DDT fornitore, peso rientrato, esito QC, upload certificato
- 3 esiti QC: conforme, non_conforme, conforme_con_riserva
- NCR PDF auto-generato per non conformita'
- Verifica auto-completa fase produzione correlata
- Certificato rientro linkato automaticamente al repository documenti e Super Fascicolo
- Endpoints: POST .../rientro, PATCH .../verifica, GET .../ncr-pdf

### Impostazioni - Tab Certificazioni
- EN 1090-1 + EN 13241 + Classe Esecuzione Default

### Bug Fix
- Select dropdown Radix UI: fix propagazione eventi

## Backlog

### P1
- Verifica utente integrazione Fatture in Cloud SDI
- Verifica parsing certificati AI

### P2
- Test end-to-end completo
- Bug preview PDF Conto Lavoro (DDT invio)
- Strategia seeding dati

### P3
- Miglioramenti Repository Documenti
- Export distinta taglio CSV per CNC
- Stato "SOSPESA" per commesse

### Futuro
- PWA offline, object storage, versioning, Stripe

## File Principali
- `/app/backend/routes/commessa_ops.py` - Rientro + Verifica + NCR endpoints
- `/app/backend/services/pdf_ncr.py` - NCR PDF generator (NUOVO)
- `/app/backend/services/pdf_super_fascicolo.py` - Super Fascicolo (include cert CL)
- `/app/frontend/src/components/CommessaOpsPanel.js` - UI Rientro modale
