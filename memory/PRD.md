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

### Gestione Audit & Non Conformità (Mar 2026)
- Pagina isolata /audit accessibile dalla sidebar (gruppo Certificazioni)
- Backend: /api/audits (CRUD audit con upload PDF verbale) + /api/ncs (CRUD NC indipendenti o collegate)
- Tab UI: [Registro Audit] + [Non Conformità]
- KPI Cards: NC Aperte, Audit Anno Corrente, Prossimo Audit, NC Chiuse
- Tipi audit: interno, esterno_ente, cliente
- Esiti audit: positivo, negativo, con_osservazioni
- NC con priorità (alta/media/bassa) e stati (aperta, in_lavorazione, chiusa)
- NC auto-numerate (NC-YYYY-NNN), collegabili a audit o standalone (reclami, errori)
- Workflow NC: apertura → analisi causa → azione correttiva → chiusura (con data e responsabile)
- Riapertura NC chiuse, eliminazione audit con scollegamento NC
- Calcolo giorni apertura NC
- Testato: 51/51 backend pytest + 20/20 frontend (iteration_91.json)

### Quality Hub Dashboard (Mar 2026)
- Dashboard riepilogativa /quality-hub — visione unificata di tutti gli alert qualità
- Banner alert con conteggio totale elementi che richiedono attenzione
- KPI Cards cliccabili: Saldatori, Apparecchiature, NC Aperte, Audit Anno, Documenti
- Sezione Patentini: lista patentini scaduti/in scadenza con badge stato
- Sezione Strumenti: lista tarature scadute/in scadenza
- Sezione NC Aperte: lista non conformità con priorità e giorni apertura
- Card prossimo audit programmato
- Backend: /api/quality-hub/summary (aggregazione dati da 5 collection)
- Testato: 26/26 backend + 16/16 frontend (iteration_92.json)

### Smart Assign: Integrazione Registri → Commessa (Mar 2026)
- Backend: /api/smart-assign/welders e /api/smart-assign/instruments (lookup con stato)
- Frontend FascicoloTecnicoSection: "Importa da Registro Saldatori" con select + alert stato patentino
- Auto-compilazione campi saldatore/punzone nel Registro Saldatura
- Qualifiche saldatore mostrate come badge con data scadenza
- Piano Controllo: select strumento dal registro con warning taratura scaduta
- Campo strumento ibrido: seleziona da registro OPPURE scrivi manualmente

### Fix Critico: babel-metadata-plugin (Mar 2026)
- Corretto bug null pointer in plugins/visual-edits/babel-metadata-plugin.js (linea 936)
- importPath.parentPath.parentPath era null per import top-level → null-safe check aggiunto
- Risolto: tutte le pagine con import lucide-react compilano correttamente

### Collegamento DDT ↔ Commesse (Mar 2026)
- Pagina DDT (/ddt): aggiunta colonna "Commessa" con numero commessa cliccabile (link a /commesse/:id)
- Editor DDT (/ddt/:id): aggiunto badge "Commessa NF-XXX" nell'header cliccabile
- Backend: arricchimento dati DDT con info commessa (numero, titolo) in lista e dettaglio
- Conto Lavoro: auto-creazione DDT in ddt_documents quando stato → "inviato" (con tipo "conto_lavoro")
- Backfill: script retroattivo per creare DDT per i conto lavoro già inviati/rientrati
- Zero modifiche allo schema commessa — solo aggiunta ddt_invio_id al conto lavoro

### Patentini Saldatori nel Super Fascicolo Tecnico (Mar 2026)
- Il "Fascicolo Tecnico Unico" (PDF) ora include automaticamente tutti i saldatori assegnati alla commessa
- Sorgenti saldatori: (1) `_source_welder_id` nel registro saldatura (Smart Assign), (2) `welder_id` dal progetto FPC
- Sezione 4.4: tabella riepilogativa con nome, punzone, stato qualifiche, dettaglio patentini (standard, processo, scadenza)
- Appendice B: auto-allegamento dei PDF patentini originali (solo qualifiche attive/in_scadenza con file)
- Calcolo stato qualifiche in tempo reale: attivo (>30gg), in_scadenza (<=30gg), scaduto
- Se nessun saldatore assegnato, mostra messaggio informativo senza errori
- Testato: 9/9 backend pytest (iteration_93.json)

### Bug Fix: Dashboard Sostenibilità vuota (Mar 2026)
- **Problema:** La pagina Sostenibilità & CO2 mostrava "Nessun dato CAM" nonostante 2 lotti CAM presenti nelle commesse
- **Causa Root:** Il filtro per anno usava confronto stringa (`"$gte": "2026-01-01"`) ma `created_at` era salvato come `datetime` object → risultato sempre 0
- **Secondo bug:** Il trend mensile faceva `isinstance(created, str)` ignorando i datetime → grafici mensili vuoti
- **Fix:** Query `$or` per gestire entrambi i tipi (datetime e string), trend mensile gestisce entrambi i formati
- Ora la dashboard mostra: 4.731 kg acciaio, 80% riciclato, 2 lotti conformi CAM

### Bug Fix: Dashboard — Conformità EN 1090 vuota (Mar 2026)
- **Problema:** Widget "Conformità EN 1090" mostrava "Nessuna commessa" nonostante 2 commesse EN 1090 lavorate
- **Causa:** Filtro cercava solo stato `confermata/in_produzione`, ma le commesse reali erano `fatturato/chiuso`
- **Fix:** Ora include tutte le commesse (escluse bozze) che hanno dati nel fascicolo tecnico o classe_esecuzione
- Testato: 14/14 (iteration_94.json)

### Bug Fix: Dashboard — Quality Score ingiusto (Mar 2026)
- **Problema:** Punteggio 19/100 "Apprendista" perché 65 punti erano legati a rilievi/POS/CE che l'utente non usa
- **Causa:** Categorie fisse (Sicurezza 30pt, CE 25pt, Foto 10pt) penalizzavano chi non fa cantieri
- **Fix:** Score adattivo — solo categorie rilevanti al workflow dell'utente. Nuove: Commesse & Produzione, Sistema Qualità. Normalizzato a 100
- Risultato: score realistico 47/100 "Artigiano in Crescita" per lo stesso utente

### Stabilizzazione (Mar 2026)
- Test di stabilizzazione completo: 23/23 backend + frontend Playwright
- Tutti i fix della sessione verificati senza regressioni (iteration_95.json)
- Score qualità realistico: 72/100 "Artigiano Esperto"

### Modulo Scadenziario & Imputazione Costi (Mar 2026)
- **Scadenziario Dashboard** (`/scadenziario`): aggrega scadenze pagamenti, patentini, tarature, consegne
- **KPI**: pagamenti scaduti, pagamenti mese, totale acquisti anno, inbox da processare
- **Imputazione Costi**: assegna fatture ricevute a commessa (costi_reali) o magazzino (aggiorna giacenze + prezzo medio ponderato)
- **FIC Sync**: endpoint pronto per sync FattureInCloud (attende token valido)
- **Frontend**: pagina completa con KPIs, inbox, filtri tipo/stato, timeline raggruppata per mese
- **Sidebar**: Scadenziario + Fatture Ricevute spostati in "Acquisti & Magazzino"
- Testato: 23/23 backend + frontend Playwright (iteration_96.json)

### Migrazione Dati da Vecchia App (Mar 2026)
- Endpoint `POST /api/migrazione/importa`: scarica dati dalla vecchia Norma Facile e importa
- Importati: 39 anagrafiche, 31 preventivi, 12 fatture vendita, 47 fatture acquisto
- Deduplicazione automatica per P.IVA/numero documento
- Idempotente: re-run sicuro, salta i duplicati
- Collegamento automatico clienti/fornitori tramite P.IVA
- Scadenziario ora mostra 20 scadenze pagamento + 47 fatture da processare

### Modulo EN 13241 Cancelli & EN 12453 Automazioni (Mar 2026)
- Flusso parallelo a EN 1090: certificazione cancelli con DoP, Etichetta CE, Registro Manutenzione, Dichiarazione CE
- Dati prestazionali: classe vento, permeabilità aria, resistenza termica, sicurezza apertura
- Automazione (motorizzati): analisi rischi (8 rischi default R01-R08), prove di forza con auto-compliance (< 400N dinamica, < 150N statica)
- Componenti: motore, fotocellule, costa sensibile, centralina, telecomando
- Sistema a cascata: supporto per Fac, Rolling Center, BFT etc.
- Frontend: pannello integrato nella commessa con 3 sezioni (Prestazioni, Sicurezza, Documenti)
- 4 PDF generati: DoP, Etichetta CE, Registro Manutenzione, Dichiarazione CE Macchine
- Testato: 14/14 backend pytest (iteration_97.json)

## Backlog
- P1: Fatture in Cloud SDI (necessita credenziali utente), verifica parsing AI
- P2: Test e2e completo, seeding dati, coesione flusso
- P3: CSV per CNC, stato SOSPESA, miglioramenti repository documenti
- Futuro: PWA, object storage, versioning, Stripe
- Refactoring: CommessaOpsPanel.js troppo grande, da dividere
