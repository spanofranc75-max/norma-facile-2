# Norma Facile 2.0 - ERP Carpenteria Metallica

## Problema Originale
Costruire un ERP completo per un'azienda di carpenteria metallica, "Norma Facile 2.0", con gestione preventivi, fatture, commesse, tracciabilità materiali, certificazioni EN 1090/EN 13241, e fatturazione elettronica.

## Architettura
- **Frontend**: React + Shadcn/UI + TailwindCSS (porta 3000)
- **Backend**: FastAPI + MongoDB (porta 8001)
- **Auth**: Google OAuth (Emergent-managed)
- **Integrazioni**: Fatture in Cloud, Resend (email), WeasyPrint (PDF), GPT-4o Vision, Object Storage Emergent

## Modulo Sopralluoghi & Messa a Norma AI

### Architettura
- **Backend**: `/app/backend/routes/sopralluogo.py` (API), `/app/backend/services/vision_analysis.py` (GPT-4o Vision), `/app/backend/services/object_storage.py` (Emergent Object Storage)
- **Frontend**: `/app/frontend/src/pages/SopralluogoWizardPage.js` (Wizard 4 step), `/app/frontend/src/pages/SopralluoghiPage.js` (Lista)
- **PDF Pro**: `/app/backend/services/pdf_perizia_sopralluogo.py` (generatore PDF professionale)
- **Immagini Soluzione**: `/app/backend/services/ref_images_library.py` + `/app/backend/services/ref_images/`
- **Collections MongoDB**: `sopralluoghi`, `articoli_perizia`

### PDF Perizia Pro Design
1. **Copertina**: Logo + tachimetro SVG conformità + dati sopralluogo + foto hero sfumata
2. **Box Riepilogo**: Conformità%, Rischi Critici/Medi, Dispositivi Mancanti, Interventi
3. **Descrizione Generale**: Box con analisi AI
4. **Documentazione Fotografica**: Griglia 2 colonne con didascalie
5. **Schede Criticità Pro**: Layout 2 colonne con barra laterale colorata per gravità
6. **Dispositivi Sicurezza**: Presenti (verde) vs Mancanti (rosso)
7. **Materiali e Interventi**: Tabella professionale con priorità
8. **Note e Firme**: Area note AI + tecnico, doppia firma
9. **Sezioni numerate** (01-05) con header navy

## Feature Completate (7 Mar 2026 - Fork 9)

### Ripristino Intelligente Backup (7 Mar 2026)
- **Backend**: `POST /api/admin/backup/restore` ora accetta parametro `mode` (Form field):
  - `mode=merge` (default): Upsert — record esistenti aggiornati, nuovi inseriti, nessun duplicato
  - `mode=wipe`: Sostituzione Totale — tutti i dati utente cancellati prima dell'importazione
  - Validazione: `mode` invalido ritorna 400
- **Frontend**: Dialog scelta modalità con 2 opzioni chiare (Unisci/Aggiorna vs Sostituzione Totale)
  - `data-testid="restore-mode-dialog"`, `btn-restore-merge`, `btn-restore-wipe`, `btn-restore-cancel`
  - Conferma aggiuntiva per modalità wipe (irreversibile)
  - Risultato mostra record eliminati/inseriti/aggiornati per collezione
- **9/9 test backend passati** (iteration_151)

### Fix window.confirm residui (7 Mar 2026)
- Migrato `CommessaOpsPanel.js` (2 occorrenze: elimina lotti CAM)
- Migrato `RdpPanel.js` (1 occorrenza: elimina RdP)
- Migrato `DeployTab` in SettingsPage.js
- **Zero `window.confirm()` rimasti** nel codebase (solo commenti in ConfirmProvider)

### Fix Bug Condizioni Pagamento Fornitore (7 Mar 2026)
- **FornitoriPage.js**: `handleOpenDialog` ora fetch dettagli completi via `GET /api/clients/{id}` prima di popolare il form
- **ClientsPage.js**: Stessa correzione applicata — garantisce che tutti i campi (pagamento, IBAN, banca) siano caricati
- Previene perdita dati quando i dati della lista non includono tutti i campi

## Feature Completate (Sessioni Precedenti)

### PDF Perizia Pro - Restyling Completo (5 Mar 2026)
- Tachimetro SVG semicircolare, schede criticità 2 colonne, immagini soluzione, box riepilogo
- 28/28 test passati (iteration_139)

### Quick Create Cliente + Restyling PDF v2 (5 Mar 2026)
- Modale "Nuovo Cliente Rapido", griglia foto 2x2, prezzi smart
- 20/20 test passati (iteration_140)

### Sistema Email Perizia Professionale (5 Mar 2026)
- Template dinamico 3 livelli, anteprima completa editabile
- 39/39 test passati (iteration_144)

### Perizia AI Multi-Normativa (6 Mar 2026)
- Cancelli EN 12453, Barriere D.M. 236/89, Strutture NTC 2018, Parapetti UNI 11678
- Frontend: selettore card grid, prompt AI specializzati, PDF dinamico

### Bug Fix DEFINITIVO: Emetti + Elimina + confirm bloccati (6 Mar 2026)
- ConfirmProvider globale con AlertDialog, sostituito window.confirm in 16+ file

### Bug Fix DEFINITIVO: Anteprima PDF (6 Mar 2026)
- react-pdf con rendering client-side su canvas

### Duplica Preventivo / Clone Quote (6 Mar 2026)
- `POST /api/preventivi/{id}/clone`, bottoni in editor e lista
- 20/20 test passati (iteration_148)

### Chiusura Diretta Commessa (6 Mar 2026)
- `POST /api/commesse/{id}/complete-simple`
- 14/14 test passati (iteration_146)

## Backlog Prioritizzato

### Fix Numerazione Preventivi Non Continua (7 Mar 2026)

### Rebranding Email — Da "NormaFacile" a Nome Azienda (7 Mar 2026)
- **Mittente dinamico**: Email inviate come `Steel Project Design Srls <fatture@steelprojectdesign.it>` (legge `business_name` da `company_settings` DB, fallback su `SENDER_NAME` env)
- **Oggetto professionale**: "Invio Fattura n. 15/2026 da Steel Project Design Srls" (prima: "Fattura n. 15/2026 - NormaFacile")
- **Template HTML rebrandato**: Header con nome azienda su sfondo navy, footer "Questa email è stata inviata da [Azienda] tramite il sistema gestionale", testi più cordiali
- **8 funzioni email aggiornate**: welcome, invoice, DDT, RdP, OdA, perizia, conto lavoro, generic
- **Tutti i caller aggiornati**: `invoices.py`, `ddt.py`, `preventivi.py`, `sopralluogo.py`, `commessa_ops.py` passano `user_id` per lookup dinamico
- **Zero riferimenti "NormaFacile" nel servizio email**
- **Causa**: Il contatore atomico `document_counters` incrementava sempre, anche per preventivi poi cancellati. Risultato: PRV-0053 come max con solo 44 preventivi nel DB.
- **Fix Backend (create/clone)**: Prima di generare un nuovo numero, il sistema ora confronta il contatore con il max numero reale nel DB. Se il contatore è "avanti" (per cancellazioni), lo resetta al max esistente prima di incrementare.
- **Fix Backend (delete)**: Dopo l'eliminazione, ricalcola il contatore basandosi sul max numero reale via aggregazione MongoDB.
- **Fix Frontend**: Header ora mostra `total` dal DB (non `array.length`). Limite API aumentato da 50 a 500 per mostrare tutti i preventivi.
- **10/10 test passati** (iteration_152)

### Fix Scadenziario e Cruscotto Finanziario (7 Mar 2026)
- **Causa**: Le fatture senza `scadenze_pagamento` erano invisibili allo scadenziario. Query `payment_status` mancavano valori null.
- **Fix**: Sezione 5b nello scadenziario include fatture senza scadenze usando `due_date`. Query cambiate a `$nin:['pagata']`. Nuovo endpoint `POST /api/invoices/sync-scadenze`.
- **13/13 test passati** (iteration_153)

### P0 (Completati)
- ~~Scadenziario e Cruscotto Finanziario~~ COMPLETATO (7 Mar 2026)
- ~~Ripristino Intelligente Backup~~ COMPLETATO (7 Mar 2026)
- ~~Numerazione Preventivi Non Continua~~ COMPLETATO (7 Mar 2026)
- ~~Crash pagina dettaglio fattura da preventivo~~ COMPLETATO (5 Mar 2026)
- ~~Termini pagamento spariti in fatturazione~~ COMPLETATO (6 Mar 2026)
- ~~Errore 400 salvataggio fattura emessa~~ COMPLETATO (6 Mar 2026)
- ~~Bug condizioni pagamento fornitore~~ COMPLETATO (7 Mar 2026)
- ~~Modulo Sopralluoghi & Perizie~~ COMPLETATO

### P1
- **Firma digitale su tablet** — Permettere al cliente di firmare il PDF perizia su tablet
- Verifica end-to-end flusso DDT creazione
- Portale cliente read-only per tracking commesse

### P2
- Gestione eccezioni generiche nel backend
- Refactoring PreventivoEditorPage.js (1000+ righe)

### Futuri
- Analisi margini predittiva
- Calendario produzione / Gantt
- Report PDF mensili automatici
- PWA per accesso offline
- Migrazione storage certificati da Base64 a object storage
- OCR per DDT fornitori
- Sostituire immagini generiche nel PDF perizia con foto reali installazioni

## File Chiave
- `/app/backend/routes/backup.py` — Backup/Restore con merge/wipe
- `/app/backend/services/pdf_perizia_sopralluogo.py` — Generatore PDF Perizia Pro
- `/app/backend/routes/sopralluogo.py` — API sopralluoghi
- `/app/frontend/src/pages/SettingsPage.js` — Impostazioni con Backup tab
- `/app/frontend/src/components/ConfirmProvider.js` — Dialog conferma globale
- `/app/frontend/src/pages/FornitoriPage.js` — Gestione fornitori
- `/app/frontend/src/pages/ClientsPage.js` — Gestione clienti

## Note Tecniche
- Contatori atomici MongoDB per numerazione documenti
- Autenticazione session-based (`credentials: 'include'`)
- L'utente comunica esclusivamente in italiano
- WeasyPrint per PDF con SVG inline
- GPT-4o Vision per analisi sicurezza
- Object Storage Emergent per foto sopralluoghi
- react-pdf per preview PDF client-side (unica soluzione funzionante in sandbox)
- useConfirm() hook per conferme (window.confirm bloccato in sandbox iframe)
