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

### Fascicolo Tecnico EN 1090 (P0 - completato)
- 6 documenti: DOP, Etichetta CE, Piano di Controllo, Rapporto VT, Registro Saldatura, Riesame Tecnico
- Auto-compilazione aggressiva (~90%) da Commessa, Preventivo, Impostazioni, Material Batches
- Mandatario = cliente dall'intestazione preventivo
- Firma digitale incorporata nei PDF
- Fascicolo Tecnico Completo (PDF combinato)
- Timeline produzione sincronizzata

### Impostazioni - Tab Certificazioni (nuovo Feb 2026)
- EN 1090-1: Numero certificazione + Classe Esecuzione Default (EXC1-EXC4)
- EN 13241: Numero certificazione
- Dati Ente Certificatore: responsabile, ruolo, ente, numero ente
- Questi dati alimentano l'auto-compilazione del Fascicolo Tecnico

### Integrazioni
- Fatture in Cloud (SDI) - richiede credenziali utente
- Resend (email transazionali)
- Google Auth (Emergent-managed)

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

## Schema DB Chiave
- **company_settings:** + classe_esecuzione_default, certificato_en13241_numero
- **commesse:** fascicolo_tecnico (embedded), fasi_produzione
- **preventivi:** client_id, numero_disegno, classe_esecuzione, giorni_consegna
- **material_batches:** material_type, dimensions, spessore, acciaieria

## File Principali
- `/app/backend/routes/fascicolo_tecnico.py` - Auto-compilazione aggressiva
- `/app/backend/services/pdf_fascicolo_tecnico.py` - Generazione PDF
- `/app/backend/models/company.py` - Modello impostazioni
- `/app/frontend/src/pages/SettingsPage.js` - Tab Certificazioni
- `/app/frontend/src/components/FascicoloTecnicoSection.js` - UI Fascicolo
