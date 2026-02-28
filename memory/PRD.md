# NormaFacile 2.0 - Product Requirements Document

## Problema Originale
Applicazione full-stack per la gestione di certificazioni EN 1090 e EN 13241, preventivi, fatture, DDT, commesse e documentazione normativa per aziende del settore metalmeccanico (Fabbri).

## Dominio di Produzione
- Frontend: `https://www.1090normafacile.it`
- API: `https://api.1090normafacile.it`

## Architettura
- **Frontend**: React (CRA) + Shadcn UI + TailwindCSS
- **Backend**: FastAPI + Motor (MongoDB async)
- **Database**: MongoDB
- **Email**: Resend API (`fatture@steelprojectdesign.it`)
- **PDF**: WeasyPrint (template unificato)
- **AI**: GPT-4o Vision (Emergent LLM Key)
- **Auth**: Google OAuth (Emergent-managed)
- **SDI**: Aruba + FattureInCloud (moduli pronti)

## Configurazione Produzione (COMPLETATA - Phase 36)
- `backend/core/config.py`: Pydantic Settings centralizzato con tutte le variabili
- `backend/services/email_service.py`: Resend (welcome, invoice, DDT)
- `backend/services/aruba_sdi.py`: FatturaPA XML generator + Aruba API client
- `backend/services/fattureincloud_api.py`: FIC API v2 client completo
- `.env`: JWT_SECRET, RESEND_API_KEY, GOOGLE_CLIENT_ID/SECRET, CORS produzione
- Dipendenze aggiuntive: resend, APScheduler, qrcode, ezdxf, openpyxl
- Frontend: fabric, react-signature-canvas, react-dropzone, html2pdf.js, pdfjs-dist, date-fns, zod

## Moduli Implementati

### Foundation (Phase 1-5)
- Google OAuth, Invoicing, Rilievi, Distinta Smart BOM, Industrial Blue Theme

### Certificazioni CE + Smart CE Calculator (Phase 6/8)
- 4-step wizard, DOP + CE Label + Manuale, Thermal Uw, Confronta Serramenti

### Sicurezza Cantieri / POS (Phase 7)
- 3-step wizard, AI risk assessment (GPT-4o), POS PDF

### Workshop Dashboard (Phase 9) + UI Polish (Phase 16)
- Gradient KPI cards, Recharts BarChart, FAB "Nuovo", Fascicolo Cantiere

### Norma Core Engine + Catalogo + Vendor API (Phase 10-12)
- ThermalValidator, SafetyValidator, CEValidator, NormaRouter, Custom profiles

### Scheda Cliente/Fornitore + Tipi Pagamento (Phase 17)
- Tab-based form, Persone di Riferimento, Payment Types CRUD

### Preventivo Avanzato v2 — Invoicex Style (Phase 18)
- Sidebar Tabs, Line Items, Quick Fill, Totals block, Converti in Fattura

### DDT Module (Phase 19)
- 3 types, Invoicex-style editor, PDF, Converti DDT in Fattura

### Fornitori Module (Phase 20)
- Dedicated /fornitori page, shared backend with client_type filter

### Perizia Sinistro (Phase 21-21c)
- Damage assessment, AI photo analysis, Codici Danno Tags, Lettera Perito

### Sopralluogo Rapido Wizard (Phase 23)
- 5-step mobile-first wizard, GPS, Camera Smart, Diagnosi, Misure, Riepilogo

### Archivio Sinistri Dashboard (Phase 22)
- KPI cards, grafici, breakdown per tipo danno

### Sinistro Smart Algorithm (Phase 24)
- calc_voci_costo con formule EN 1090/13241

### Catalogo Articoli (Phase 25)
- CRUD, ricerca, storico prezzi, bulk import

### Tracciamento Pagamenti (Phase 25)
- Scadenze, pagamenti parziali/totali, KPI cards

### Fatture Ricevute + FatturaPA XML Import (Phase 26)
- Import XML, parser namespace-agnostic, matching fornitore per P.IVA

### Core Engine Normativo (Phase 27)
- NormaConfig data-driven, Calcolo Uw ISO 10077-1, Validazione regole dinamiche

### Generazione Fascicolo Automatica (Phase 28)
- DOP, Etichetta CE, Manuale d'Uso, PDF + ZIP

### Registro DDT + Quick Fill + AI Foto Posa (Phase 29)
- KPI, filtri, quick fill fatture, validazione foto installazione

### Module Interconnection (Phase 30)
- Distinta->Preventivo, Preventivo->Fattura, Rilievo->POS

### Kanban Planning Cantieri (Phase 32)
- 7 colonne drag-and-drop, CRUD commesse

### Quality Score (Phase 33)
- Score 0-100, 4 livelli, radial progress bar, insights

### Bug Fix: Logo + Condizioni Vendita + Client Creation (Phase 34-35)
- Logo upload base64, condizioni vendita in PDF, fix form client

### EBITDA Dashboard + PDF Preview (Phase 35)
- Analisi finanziaria, KPI, grafici, tabella mensile, anteprima PDF inline

### Migrazione Configurazione Produzione (Phase 36)
- Config centralizzata, Email Resend, Aruba SDI, FattureInCloud API

### Email Sending + SDI Integration (Phase 37)
- Endpoint POST /api/invoices/{id}/send-email — genera PDF, invia via Resend con allegato
- Endpoint POST /api/invoices/{id}/send-sdi — genera XML FatturaPA, invia ad Aruba SDI
- Endpoint POST /api/ddt/{id}/send-email — genera PDF DDT, invia via Resend
- Endpoint POST /api/preventivi/{id}/send-email — genera PDF preventivo, invia via Resend
- Tracking email: email_sent, email_sent_to, email_sent_at in MongoDB
- Pulsanti "Email" in: InvoiceEditorPage, PreventivoEditorPage, DDTEditorPage
- Pulsante "Invia a SDI" in InvoiceEditorPage + InvoicesPage dropdown
- Validazione SDI: blocca bozze, verifica configurazione chiavi
- Testing: 16/16 backend, 100% frontend (iteration_44)

### Fix Indirizzo Tab + Storico Email Cliente (Phase 38)
- BUG FIX: Tab "Indirizzo" nel dialog cliente non mostrava i campi (form wrapper senza flex classes)
- Nuovo tab "Email Inviate" nella scheda cliente — storico completo email inviate
- Endpoint GET /api/clients/{id}/email-log — aggrega email da fatture, DDT, preventivi
- Testing: 100% backend e frontend (iteration_45)

### PDF Redesign Preventivo (Phase 39)
- Riscrittura completa del generatore PDF preventivi da ReportLab a WeasyPrint (HTML/CSS)
- Layout a due colonne: info azienda (sx) + cliente con bordo (dx)
- Titolo PREVENTIVO centrato con numero documento
- Metadati: DATA, Pagamento, Validita
- Tabella articoli 8 colonne: Codice, Descrizione, u.m., Quantita, Prezzo, Sconti, Importo, Iva
- Sezione note tecniche
- Dettaglio IVA con breakdown per aliquota + TOTALE IMPONIBILE + Totale IVA + Totale EUR
- Dati bancari
- Pagina condizioni di vendita con sezione accettazione e firma
- Formattazione numeri italiana (virgola decimale, punto migliaia)
- Gestione robusta valori None in tutti i campi
- Testing: 17/17 test passati (iteration_46)

### PDF Template Unification (Phase 40)
- Modulo condiviso `services/pdf_template.py` con CSS, header builder, totals builder
- Fatture: Riscrittura da ReportLab a WeasyPrint — layout unificato con IBAN/banca nel footer
- DDT: Riscrittura da ReportLab a WeasyPrint — layout unificato con info trasporto + firme mittente/vettore/destinatario
- Preventivo: Refactoring per usare il modulo condiviso
- Font/colori/margini identici su tutti e 3 i tipi di documento

### EN 1090 FPC System (Phase 41)
- **Registro Saldatori**: CRUD completo con qualifica ISO 9606-1, scadenza, allarme scadenza
- **Tracciabilita Materiali**: CRUD lotti con fornitore, tipo materiale, numero colata, certificato 3.1 (base64)
- **Progetti FPC**: Conversione preventivo->progetto con classe EXC obbligatoria (EXC1-EXC4)
- **Assegnazione materiali**: Link lotto->riga distinta con heat_number e material_type
- **Controlli FPC**: 7 checklist (dimensionale, visivo, certificati, WPS, superfici, marcatura)
- **CE Label**: Verifica requisiti (blockers) + generazione etichetta CE
- **Workflow completo**: Blocco generazione CE se materiali non collegati, saldatore non assegnato, controlli non completati
- **Frontend**: Pagina `/tracciabilita` con 3 tab + pagina dettaglio progetto FPC
- **Sidebar**: Link aggiunto sotto "Produzione"
- Testing: 27/27 backend, 100% frontend (iteration_47)

### One-Click Technical Dossier (Phase 42)
- Servizio `dossier_generator.py`: genera Fascicolo Tecnico completo in un unico PDF
- 6+ sezioni: Copertina, DoP (Dichiarazione di Prestazione), Etichetta CE, Riepilogo Tracciabilita Materiali, Qualifica Saldatore, Checklist Controlli FPC
- Certificati 3.1 (base64) decodificati e allegati automaticamente al fascicolo
- Merge PDF con pypdf (PdfWriter/PdfReader)
- Endpoint: GET /api/fpc/projects/{id}/dossier -> StreamingResponse PDF
- Frontend: Pulsante grande "Stampa Fascicolo Tecnico Completo" con loading spinner
- Gestione robusta: sezioni omesse se dati mancanti (saldatore, certificati)
- Testing: 22/22 backend, 100% frontend (iteration_48)

### Architecture Documentation (Phase 43)
- Creato `/app/memory/ARCHITECTURE_FPC_WORKFLOW.md` con mappa completa dei flussi
- Documenta tutte le connessioni tra moduli: Rilievo->Distinta->Preventivo->(Fattura/Commessa/FPC)->Fascicolo
- Schema DB completo con foreign key tra collection
- Caso d'uso end-to-end dal sopralluogo alla fatturazione
- Suggerimenti miglioramento: collegamento Commessa<->FPC, avanzamento Kanban automatico

### Progressive Invoicing - Acconto & SAL (Phase 44)
- Nuovo endpoint `POST /api/preventivi/{id}/progressive-invoice` con 3 modalita: Acconto %, SAL (righe o importo libero), Saldo Finale
- Endpoint `GET /api/preventivi/{id}/invoicing-status` per stato fatturazione (total_invoiced, remaining, linked_invoices)
- Tracciamento `total_invoiced`, `linked_invoices` su preventivi collection
- Campo `invoicing_progress` calcolato al volo nella lista preventivi
- Saldo Finale: include automaticamente righe negative "A detrarre acconto Ft. XXX"
- Validazione: rifiuta importi superiori al residuo, rifiuta se gia completamente fatturato
- Frontend: InvoiceGenerationModal con 3 scelte (Acconto/SAL/Saldo), progress bar, anteprima importo
- Frontend: Barra progresso "Fatturato: X%" nella lista preventivi
- Frontend: Timeline workflow aggiornata (Preventivo → Fatturazione → Completato)
- Testing: 15/15 backend, 100% frontend (iteration_49)

### Architettura Hub Commesse - Event-Driven (Phase 45)
- **Macchina a Stati**: 8 stati lifecycle (richiesta, bozza, rilievo_completato, firmato, in_produzione, fatturato, chiuso, sospesa)
- **Event Sourcing**: Ogni cambio stato tramite eventi con operatore, timestamp, note, payload
- **10 Transizioni**: COMMESSA_CREATA, RICHIESTA_PREVENTIVO, RILIEVO_COMPLETATO, FIRMA_CLIENTE, PREVENTIVO_ACCETTATO, AVVIO_PRODUZIONE, FATTURA_EMESSA, CHIUSURA_COMMESSA, SOSPENSIONE, RIATTIVAZIONE
- **Hub Moduli**: La commessa collega rilievo, distinta, preventivo, fatture[], ddt[], fpc_project, certificazione
- **API Hub View**: `GET /api/commesse/{id}/hub` ritorna commessa + tutti i moduli collegati fetchati dalle rispettive collection
- **Module Linking**: `POST /api/commesse/{id}/link-module` e unlink per collegare qualsiasi modulo
- **Dossier Unico**: `GET /api/commesse/{id}/dossier` genera PDF completo (copertina, anagrafica, timeline, preventivo, fatture, DDT, FPC, certificazione)
- **Backward Compatible**: Kanban drag-and-drop (campo `status`) resta funzionante, `stato` lifecycle opera in parallelo con sync automatico
- **Numerazione**: Formato `NF-YYYY-NNNNNN` per commesse
- **Cantiere**: Dati cantiere embedded (indirizzo, citta, contesto, ambiente)
- **Frontend Hub**: Pagina `/commesse/:id` con barra lifecycle, azioni contestuali, moduli collegati, timeline eventi
- **Frontend Kanban**: Click su card → pagina Hub, badge stato + numero su ogni card
- Testing: 18/18 backend, 100% frontend (iteration_50)

### Flusso Operativo Commessa Completo (Phase 46)
- **Approvvigionamento**: Richiesta Preventivo Fornitore (RdP) → Ricezione → Accettazione → Ordine Fornitore (OdA) → Conferma → Arrivo Materiale → Verifica
- **Produzione**: 6 fasi sequenziali tracciabili (Taglio → Foratura → Assemblaggio → Saldatura → Pulizia → Preparazione Superfici) con stato da_fare/in_corso/completato, operatore, date, progress bar
- **Conto Lavoro**: Invio a terzista (verniciatura/zincatura/sabbiatura) → DDT c/L → Rientro → Verifica certificati — workflow 5 stati
- **Repository Documenti**: Upload/download/delete file per commessa (certificati 3.1, conferme ordine, disegni, certificati verniciatura/zincatura, DDT, foto, altro) — collection separata commessa_documents
- **AI OCR Certificati 3.1**: GPT-4o Vision analizza PDF certificato ed estrae: N. Colata, Fornitore, Qualita acciaio, Normativa, Dimensioni, Composizione chimica, Proprieta meccaniche — auto-registra nel registro material_batches
- **Accetta Preventivo**: Bottone sulla toolbar del preventivo, abilita fatturazione progressiva solo dopo accettazione
- **Event Sourcing**: Ogni operazione pushes evento nella timeline commessa (RDP_INVIATA, ORDINE_EMESSO, MATERIALE_ARRIVATO, FASE_IN_CORSO, CL_CREATO, DOCUMENTO_CARICATO, CERTIFICATO_ANALIZZATO, ecc.)
- Testing: 24/24 backend, 100% frontend (iteration_52)

### Auto-Suggerimento Fornitori (Phase 47)
- **Combobox Riutilizzabile**: Nuovo componente `/app/frontend/src/components/ui/combobox.jsx` con ricerca in tempo reale (Command + Popover pattern)
- **CommessaOpsPanel**: Dialogs RdP, OdA, Conto Lavoro aggiornati con Combobox per selezione fornitore da anagrafica
- **ArticoliPage**: Dialog Nuovo Articolo aggiornato con Combobox per associazione fornitore
- **Backend Filter**: GET `/api/clients/?client_type=fornitore` include sia 'fornitore' che 'cliente_fornitore'
- **Data Association**: `fornitore_id` e `fornitore_nome` salvati correttamente in richieste, ordini, conto lavoro, articoli
- Testing: 10/10 backend, 100% frontend (iteration_53)

## Issue Pendenti
- **P1**: Login post-deploy fallisce (caching PWA/Service Worker)
- **P2**: Account test non funziona da UI

## Task Futuri
- [ ] P0: Finalizzare Dashboard EBITDA (calcoli finanziari + grafici)
- [ ] P1: Modal Anteprima PDF per tutti i documenti
- [ ] P1: Attivazione SDI (chiavi API Aruba)
- [ ] Collegamento diretto Commessa <-> Progetto FPC
- [ ] Esportazione CSV distinta di taglio per CNC
- [ ] Estensione Distinta Facile (grata 2 ante, cancello scorrevole)
- [ ] Categoria "CANCELLI" al listino prezzi
- [ ] Migrazione dati EN 13241
- [ ] Versioning fatture
- [ ] Integrazione Stripe (pagamenti online)
- [ ] Automazione invio credenziali
- [ ] Modalita offline (PWA)
- [ ] Firma Elettronica Avanzata (FEA)
- [ ] App Mobile Nativa
