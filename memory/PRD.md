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
- Auto-compilazione aggressiva (~90%) da Commessa, Preventivo, Impostazioni, Material Batches
- Mandatario = cliente dall'intestazione preventivo
- Firma digitale incorporata nei PDF
- Timeline produzione sincronizzata

### Super Fascicolo Tecnico Unico (NUOVO - Mar 2026)
- PDF unico aggregato con Copertina + Indice + 5 capitoli:
  - Cap 1: Dati Generali (Dossier Commessa)
  - Cap 2: Riesame Tecnico & ITT
  - Cap 3: Tracciabilita' Materiali & Sostenibilita' (Lotti + CAM + Green Cert + Appendice A: Cert 3.1)
  - Cap 4: Processo di Saldatura (PCQ + Registro + VT + Appendice B: Patentini)
  - Cap 5: Marcatura CE (DoP + Etichetta CE)
- Endpoint: GET /api/commesse/{cid}/fascicolo-tecnico-completo
- Service: /app/backend/services/pdf_super_fascicolo.py
- Header/Footer coerenti con logo e numero commessa su ogni pagina

### Impostazioni - Tab Certificazioni
- EN 1090-1: Numero certificazione + Classe Esecuzione Default (EXC1-EXC4)
- EN 13241: Numero certificazione
- Dati Ente Certificatore

### Integrazioni
- Fatture in Cloud (SDI) - richiede credenziali utente
- Resend (email transazionali)
- Google Auth (Emergent-managed)

### Bug Fix
- Select dropdown Radix UI: fix propagazione eventi con onPointerDownOutside e onCloseAutoFocus

## Backlog

### P1
- Verifica utente integrazione Fatture in Cloud SDI
- Verifica parsing certificati AI

### P2
- Test end-to-end completo flusso applicativo
- Bug preview PDF Conto Lavoro
- Strategia seeding dati

### P3
- Miglioramenti Repository Documenti
- Export distinta taglio CSV per CNC
- Stato "SOSPESA" per commesse

### Futuro
- PWA offline mode
- Migrazione object storage certificati
- Versioning fatture/fascicolo
- Stripe pagamenti

## File Principali
- `/app/backend/services/pdf_super_fascicolo.py` - Super Fascicolo Tecnico Unico (NUOVO)
- `/app/backend/routes/commessa_ops.py` - Endpoint fascicolo-tecnico-completo (NUOVO)
- `/app/backend/routes/fascicolo_tecnico.py` - Auto-compilazione aggressiva
- `/app/backend/services/pdf_fascicolo_tecnico.py` - Generazione PDF singoli
- `/app/backend/models/company.py` - Modello impostazioni
- `/app/frontend/src/pages/SettingsPage.js` - Tab Certificazioni
- `/app/frontend/src/components/FascicoloTecnicoSection.js` - UI Fascicolo + bottone Scarica PDF Unico
- `/app/frontend/src/components/ui/select.jsx` - Fix bug Radix Select
