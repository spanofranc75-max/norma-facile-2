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

### RdP e OdA con Righe Dettagliate (Phase 48)
- **RdP Dialog Avanzato**: Tabella righe con Descrizione, Quantità, U.M., ☑️ Cert. 3.1 richiesto
- **OdA Dialog Avanzato**: Tabella righe con Descrizione, Quantità, U.M., Prezzo Unitario, Importo calcolato, ☑️ Cert. 3.1
- **Totale OdA Automatico**: Calcolo in tempo reale del totale ordine dalla somma delle righe
- **Riferimento Commessa**: Numero commessa sempre visibile nell'intestazione dei dialog
- **Backend Models**: `RigaRdP` e `RigaOdA` Pydantic con `richiede_cert_31: bool`
- **Validazione**: Almeno una riga con descrizione richiesta per inviare
- **Add/Remove Lines**: Bottoni per aggiungere/rimuovere righe dinamicamente
- Testing: 12/12 backend, 100% frontend (iteration_54)

### PDF Preview + Email Workflow per Procurement (Phase 49)
- **PDF Generator**: Nuovo servizio `/app/backend/services/pdf_procurement.py` per RdP e OdA
- **Anteprima PDF**: Modal con iframe per visualizzare il PDF prima di inviare
- **API PDF**: `GET /api/commesse/{id}/approvvigionamento/richieste/{rdp_id}/pdf` e `.../ordini/{ordine_id}/pdf`
- **Invio Email**: `POST .../send-email` genera PDF, invia via Resend al fornitore, traccia lo stato
- **Status Badge**: Verde "Inviata" se `email_sent=true`, Rosso "Bozza" se `email_sent=false`
- **Email Tracking**: Campi `email_sent`, `email_sent_to`, `email_sent_at` su ogni RdP/OdA
- **Template Email**: Email professionale con riferimento commessa e dettaglio materiali
- **PDF Professionale**: Layout a due colonne, tabella righe con badge Cert. 3.1, riferimento cantiere
- Testing: 12/12 backend, 100% frontend (iteration_55)

### Arrivo Materiali Intelligente + Normativa Preventivo (Phase 50)
- **Logo nei PDF**: RdP e OdA includono il logo aziendale se presente in company_settings
- **Normativa in Preventivo**: Campo "EN_1090", "EN_13241" o nessuna per determinare i requisiti di tracciabilità fin dall'inizio
- **Registrazione Arrivo Avanzata**: Form con DDT fornitore, data, fornitore (combobox), e tabella materiali dettagliata
- **Materiali con Dettaglio**: Ogni materiale ha descrizione, quantità, U.M., riferimento ordine (per smistamento multi-commessa), checkbox Cert. 3.1
- **Collegamento Certificati**: Endpoint `PUT .../materiale/{idx}/certificato` per collegare certificato (numero colata, qualità) a singolo materiale
- **Auto-Tracciabilità EN 1090**: Se commessa è EN 1090 e viene collegato un certificato, auto-registrazione in material_batches
- **UX Migliorata**: Bottone "Emetti Ordine" richiede descrizione compilata (non solo placeholder)
- Testing: 12/12 backend, 100% frontend (iteration_56)

### Crea OdA da RdP + UI Certificati con AI OCR (Phase 51)
- **Crea OdA da RdP Accettata**: Bottone "Crea OdA" su RdP con stato 'accettata' che pre-compila l'ordine con le stesse righe della richiesta
- **Pre-compilazione Intelligente**: Fornitore, descrizione, quantità, u.m., richiede_cert_31 copiati automaticamente — solo i prezzi da inserire
- **Riferimento RdP**: Note dell'OdA contengono automaticamente "Rif. RdP: xxx" per tracciabilità
- **UI Collegamento Certificati**: Dialog "Collega Certificati ai Materiali" accessibile dagli arrivi con materiali che richiedono Cert. 3.1
- **Tabella Materiali con Stato**: Mostra materiali con badge 3.1, stato collegamento (verde "Collegato" o rosso "Non collegato")
- **Upload con AI OCR**: Caricamento PDF certificato → analisi GPT-4o Vision → estrazione automatica numero colata, qualità, fornitore → collegamento a materiale + tracciabilità EN 1090
- **Toast Informativi**: "OdA pre-compilato dalla RdP - aggiungi i prezzi e invia!"
- Testing: 100% backend, 100% frontend (iteration_57)

### Template PDF Unificato V2 - Steel Project Design Style (Phase 52)
- **Nuovo Template**: `/app/backend/services/pdf_template_v2.py` con formato professionale unificato
- **Header a Due Colonne**: Logo + Azienda (sinistra) | "Spett.le" + Destinatario (destra)
- **Linea Blu Separatrice**: Separatore visivo tra header e contenuto
- **Titolo Centrato Blu**: "RICHIESTA DI PREVENTIVO N. RDA-xxx" o "ORDINE DI ACQUISTO N. ODA-xxx"
- **Box Info**: DATA | RIF. COMMESSA con etichette e valori
- **Tabella Professionale**: Header blu scuro (#1e3a5f), righe alternate, colonne allineate
- **Alert Box Giallo**: "CERTIFICATO RICHIESTO: Si richiede certificato materiale tipo 3.1 (EN 10204)"
- **Info Box Giallo Chiaro**: Per note aggiuntive
- **Footer Professionale**: "In attesa di Vs. cortese riscontro, porgiamo distinti saluti." + Nome Azienda + Contatti
- **Helper Functions**: `build_header()`, `build_info_boxes()`, `build_footer()` riutilizzabili per tutti i documenti
- Testing: 100% backend (iteration_58)

### Tracciabilità Materiali con AI OCR (Phase 53)
- **Bottone "Analizza AI" Esteso**: Appare su qualsiasi PDF (certificato_31, altro, ddt_fornitore) non ancora analizzato
- **Dati Estratti Visibili**: Card verde con Colata, Qualità, Fornitore, Normativa mostrata direttamente nel Repository
- **Sezione "Tracciabilità Materiali"**: Nuova sezione che aggrega tutti i materiali tracciati per la commessa
- **Doppia Fonte**: Mostra sia i record da `material_batches` (EN 1090) sia i documenti con `metadata_estratti`
- **Layout Professionale**: Grid 2x4 con etichette e valori per ogni materiale tracciato
- **Empty State**: Messaggio chiaro "Nessun materiale tracciato - Carica un certificato e clicca Analizza AI"
- **Bug Fix**: Corretto endpoint `/material-batches` → `/fpc/batches`
- Testing: 100% backend, 100% frontend (iteration_59)

### Modulo CAM - Criteri Ambientali Minimi (Phase 54)
- **Conformità Ambientale DM 256/2022**: Modulo completo per gestione conformità CAM per carpenteria metallica
- **Backend CRUD Lotti CAM**: Collection `lotti_cam` con dati materiale, % riciclato, metodo produttivo, certificazione
- **Calcolo Conformità Automatico**: Soglie per forno elettrico non legato (75%), legato (60%), ciclo integrale (12%)
- **AI OCR Potenziato**: Prompt GPT-4o Vision aggiornato per estrarre anche percentuale_riciclato, metodo_produttivo, certificazione_ambientale dai certificati 3.1
- **Import da Certificato AI**: Endpoint `/api/cam/import-da-certificato/{doc_id}` crea lotto CAM dai dati estratti
- **Dichiarazione CAM PDF**: Documento ufficiale con header azienda, tabella materiali, calcolo totale, esito conformità, riferimenti normativi, sezione firma
- **Frontend Sezione CAM**: Pannello collassabile nel CommessaHub con: sommario conformità (verde/rosso), lista lotti, dialog aggiunta/modifica, import da certificati, download PDF
- **Soglie Pubbliche**: Endpoint `/api/cam/soglie` restituisce regolamento completo
- Nuovi file: `backend/routes/cam.py`, `backend/models/cam.py`, `backend/services/pdf_cam_declaration.py`
- Testing: 100% backend, 100% frontend (iteration_60)

### Report CAM Multi-Commessa + CO2 (Phase 55)
- **Report Aziendale Sostenibilità**: Aggregazione multi-commessa di tutti i lotti CAM per periodo/anno
- **Calcolo CO2 Risparmiata**: Fattori World Steel Association (EAF=0.67 tCO2/t vs BOF=2.33 tCO2/t)
- **Endpoint API**: `GET /api/cam/report-aziendale?anno={year}` + `GET /api/cam/report-aziendale/pdf?anno={year}`
- **PDF Bilancio Sostenibilità**: Documento professionale con hero section, KPI grid, CO2 box, tabelle commesse/fornitori/metodi, footer normativo, sezione firma
- **Frontend Pagina `/report-cam`**: KPI cards (acciaio totale/riciclato, commesse conformi, CO2), hero card CO2, tabelle breakdown per commessa e fornitore, filtro anno, download PDF
- **Sidebar**: Link "Report CAM / CO2" aggiunto sotto gruppo "Certificazioni"
- Nuovi file: `frontend/src/pages/ReportCAMPage.js`, `backend/services/pdf_cam_report.py`
- Testing: 100% backend (17/17), 100% frontend (iteration_61)

### AI OCR Intelligente Multi-Profilo (Phase 56)
- **Prompt AI multi-profilo**: GPT-4o Vision ora estrae TUTTI i profili dal certificato 3.1 come array (non solo il primo)
- **Matching intelligente**: Incrocio automatico con OdA, RdP, DDT arrivi di TUTTE le commesse dell'utente
  - Profili che matchano la commessa corrente → CAM lotto + material_batch creati automaticamente
  - Profili che matchano altre commesse → certificato copiato automaticamente, CAM lotto creato nella commessa giusta
  - Profili non matchati → archiviati in `archivio_certificati` per recupero futuro
- **Normalizzazione profili**: IPE 100 = ipe100 = IPE100 (case/space insensitive)
- **Archivio Certificati**: `GET /api/cam/archivio-certificati` + `POST /api/cam/archivio-certificati/{colata}/assegna`
- **Frontend**: Toast informativi per tipo match, card multi-profilo con box blu, ri-analisi disponibile
- **Bug fix poppler**: Installato `poppler-utils` per conversione PDF→immagine
- **Bug fix response.text**: Fixato parsing risposta emergentintegrations (stringa diretta, non oggetto)
- Testing: 100% backend (8/8), 100% frontend (iteration_62)

### DDT Conto Lavoro Completo (Phase 57)
- **Dialog CL Avanzato**: Form completo con Tipo, Fornitore (dropdown da anagrafica), RAL (visibile per verniciatura), Causale Trasporto, Tabella Righe (descrizione, qtà, u.m., peso kg) con add/remove, Note
- **PDF DDT Conto Lavoro**: Generazione PDF professionale con header azienda/destinatario, tabella materiali, totale peso, box RAL, firme mittente/destinatario
- **Invio Email CL**: Endpoint per invio DDT via Resend con allegato PDF al fornitore (ricerca email da client_id, PEC, email, contacts)
- **Lista CL Migliorata**: Ogni C/L mostra tipo, fornitore, RAL, n. materiali, peso totale, status badge, bottoni PDF/Email
- **Transizioni Stato**: da_inviare → inviato → in_lavorazione → rientrato → verificato
- **Bug Fix Backend**: Aggiunto `send_email_with_attachment` a email_service.py, fixato CSS PDF (aggiunto COMMON_CSS), fixato query fornitore (`client_id` vs `id`), fixato metodo HTTP endpoint preview-pdf (POST→GET)
- Testing: 100% backend (11/11), 100% frontend (iteration_63)

### Anteprima Email per TUTTI gli Invii (Feb 2026)
- **EmailPreviewDialog**: Componente riutilizzabile che mostra destinatario, oggetto, corpo HTML in iframe, badge allegato, bottoni "Invia" e "Annulla"
- **6 Endpoint Backend `GET .../preview-email`**: RdP, OdA, Conto Lavoro (commessa_ops.py), Fattura (invoices.py), DDT (ddt.py), Preventivo (preventivi.py)
- **Frontend Integrato**: Tutti i 6 bottoni "Email" (CommessaOpsPanel, InvoiceEditorPage, InvoicesPage, DDTEditorPage, PreventivoEditorPage) ora aprono l'anteprima prima dell'invio
- **Email Preview Builder**: `/app/backend/services/email_preview.py` — template HTML coerenti per ogni tipo di documento
- Testing: 100% backend (14/14 pytest), 100% frontend (iteration_64)

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
