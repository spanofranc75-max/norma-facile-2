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
- Backend: /api/company/documents/ (CRUD completo con upload file + versioning)
- Categorie: Manuali Qualita, Procedure, Certificazioni, Template, Normative, Organigramma, Altro
- UI: Shadcn Table con header scuro (bg-[#1E293B]), toolbar Card (Search + Select), Badge colorate
- **Versioning documenti**: Upload nuova revisione (POST /{id}/revision), storico versioni (GET /{id}/versions), download versione specifica (GET /{id}/versions/{num}/download)
- Colonna "Rev." nella tabella con badge cliccabile per documenti multi-versione
- Dialog "Storico Revisioni" con tabella versioni + download per ciascuna
- Dialog "Nuova Revisione" con archiviazione automatica versione corrente
- Delete elimina tutte le versioni (file + metadati)
- File salvati su disco locale (/app/backend/uploads/company_docs/)
- Testato: 12/12 backend + 15/15 frontend (iteration_88.json)

### Registro Apparecchiature & Strumenti (Mar 2026)
- Pagina isolata /strumenti accessibile dalla sidebar (gruppo Certificazioni)
- Backend: /api/instruments/ (CRUD con calcolo automatico stato scadenza)
- Tipi: Strumenti di Misura, Saldatrici, Macchinari, Altro
- Calcolo automatico computed_status: attivo (>30gg), in_scadenza (<=30gg), scaduto (<0gg)
- Stats bar: Totali, Attivi, In Scadenza, Scaduti, Manutenzione, Fuori Uso
- Card grid con bordo colorato per tipo, badge stato, barra scadenza con giorni rimanenti
- Filtri: tipo, stato, ricerca (nome, matricola, marca)
- Dialog creazione/modifica con sezione taratura (date, intervallo mesi)
- Testato: 22/22 backend pytest + 15/15 frontend (iteration_89.json)

## Bug Fix Critici (Mar 2026)

### P0: Bug Loop/Reload Editor Preventivi - RISOLTO
- **Problema:** Digitando in campi come "Tempi di Consegna" o "Ing. Disegno", la pagina entrava in loop mostrando spinner e perdendo tutti i dati del form
- **Causa Root:** ErrorBoundary wrappava l'intera app (BrowserRouter + AuthProvider). Quando errori DOM venivano catturati (es. da estensioni browser come Grammarly), l'ErrorBoundary faceva remount di tutto, incluso AuthProvider che resettava loading=true e user=null
- **Fix applicati:**
  1. ErrorBoundary spostato sotto AuthProvider (App.js) - lo stato auth non viene mai resettato
  2. ProtectedRoute usa sessionStorage ('nf_was_authenticated') per sopravvivere ai remount
  3. PreventivoEditorPage ha auto-save su sessionStorage con debounce 300ms
- **Testato:** 8/8 test passati con testing agent (iteration_85.json)

### Registro Saldatori & Patentini (Mar 2026)
- Pagina isolata /saldatori accessibile dalla sidebar (gruppo Certificazioni)
- Backend: /api/welders/ (CRUD saldatori + qualifiche con upload file PDF)
- Layout master-detail: sidebar lista saldatori + pannello dettaglio con tabella patentini
- Calcolo automatico stato patentino: attivo (>30gg), in_scadenza (<=30gg), scaduto (<0gg)
- Overall status saldatore: ok, warning, expired, no_qual
- Stats bar: Saldatori totali, Qualificati, Attenzione, Patentini Tot.
- Dialog creazione/modifica saldatore (nome, punzone, ruolo, telefono, email, data assunzione)
- Dialog aggiunta patentino (norma ISO 9606, processo, materiale, spessori, posizione, scadenza, PDF)
- Ricerca per nome/punzone nella sidebar
- Validazione backend: nome e punzone non possono essere vuoti
- File patentini salvati su disco locale (/app/backend/uploads/welder_certs/)
- Testato: 31/33 backend pytest + 17/17 frontend (iteration_90.json)

## Backlog
- P1: Integrare patentini saldatori nel "Super Fascicolo Tecnico" (auto-allegare PDF validi per saldatori della commessa)
- P1: Fatture in Cloud SDI (necessita credenziali utente), verifica parsing AI
- P2: Test e2e completo, seeding dati, coesione flusso
- P3: CSV per CNC, stato SOSPESA, miglioramenti repository documenti
- Futuro: PWA, object storage, versioning, Stripe
- Refactoring: CommessaOpsPanel.js troppo grande, da dividere
