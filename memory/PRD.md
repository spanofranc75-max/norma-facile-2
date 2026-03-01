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

### Fix PDF Preview CL + Email Editing (Mar 2026)
- **Fix PDF Preview Conto Lavoro**: Il blob URL veniva invalidato dall'aggiunta di `?token=` — ora controlla se è blob URL prima di aggiungere il token
- **Modifica Testo Email**: Bottone "Modifica testo" nell'anteprima che permette di editare Oggetto e Corpo prima dell'invio
- **Backend aggiornato**: Tutti i 6 endpoint `send-email` (CL, RdP, OdA, Fattura, DDT, Preventivo) accettano `custom_subject` e `custom_body` opzionali
- Testing: 100% backend (9/9), 100% frontend (iteration_65)

### Fix Flusso Completo Fatturazione + Allega Modulo (Mar 2026)
- **BUG CRITICO FIXATO: Fatturazione vuota** — Il filtro anno usava regex `-2026-` che non matchava `FT-2026/0001` (separatore `/`). Corretto a `-2026[-/]`
- **BUG FIXATO: Fatture non collegate alla Commessa** — Quando si genera fattura progressiva dal preventivo, ora l'invoice viene auto-aggiunta a `moduli.fatture_ids` della commessa collegata
- **BUG FIXATO: "Allega Modulo" non funzionava** — Il dialog richiedeva di digitare l'ID interno a mano. Rifatto con dropdown automatico: selezionando il tipo (Fattura, Preventivo, DDT...), carica la lista documenti dell'utente via nuovo endpoint `GET /api/commesse/{id}/available-modules`
- **BUG FIXATO: Select dentro Dialog** — Sostituito Radix Select con native `<select>` nel dialog Allega Modulo
- Dati reali fixati: collegate le 2 fatture progressive alla commessa nel DB

### Dashboard Sostenibilita & CO2 (Phase 58 - Mar 2026)
- **Backend Potenziato**: Endpoint `GET /api/cam/report-aziendale` arricchito con KPI sostenibilita:
  - `alberi_equivalenti`: CO2 risparmiata / 22 kg CO2 per albero/anno (fonte EEA)
  - `indice_economia_circolare`: % media ponderata acciaio riciclato
  - `co2_per_commessa`: breakdown CO2 risparmiata per ogni commessa (per bar chart)
  - `trend_mensile`: aggregazione mensile peso/riciclato/CO2 (per area chart)
- **Frontend Dashboard**: Pagina `/report-cam` riscritta con:
  - 3 Hero Cards: Eco-Counter CO2, Effetto Foresta (alberi equivalenti), Indice Circolare (gauge Recharts)
  - KPI Strip: 5 mini-KPI (Acciaio Totale, Riciclato, Commesse, Lotti, Riduzione CO2)
  - 2 Grafici Recharts: AreaChart trend mensile CO2 + BarChart CO2 per commessa
  - Tabelle: Commesse, Fornitori, Metodi Produttivi (preservate)
  - Empty state con messaggio localizzato
- **Sidebar**: Label aggiornata a "Sostenibilita & CO2"
- Testing: 100% backend (10/10), 100% frontend (iteration_66)

### Tooltip su Bottoni Disabilitati (Phase 58b - Mar 2026)
- **Componente DisabledTooltip**: Wrapper riutilizzabile che spiega all'utente perche un bottone e disabilitato
- **Applicato su**: PreventivoEditorPage (Compliance), CommessaHubPage (Collega Modulo), CommessaOpsPanel (Crea DDT C/L)
- Nuovo file: `/app/frontend/src/components/DisabledTooltip.js`

### Green Certificate per Commessa (Phase 58c - Mar 2026)
- **Endpoint**: `GET /api/cam/green-certificate/{commessa_id}` genera PDF brandizzato di sostenibilita
- **PDF Professionale**: Bordo verde, logo aziendale, 4 KPI (CO2 risparmiata, alberi equivalenti, acciaio riciclato, indice circolare), tabella materiali con badge conformita CAM, sezione firma
- **Frontend**: Bottone "Green Certificate" nella sezione CAM del CommessaHub (visibile solo con lotti CAM)
- Nuovi file: `backend/services/pdf_green_certificate.py`
- Testing: 100% backend (6/6), 100% frontend (iteration_67)

### Bug Fix: AI Certificate Parsing (Phase 59 - Mar 2026)
- **Fix**: Installato `poppler-utils` (system dependency per `pdf2image`) — parsing certificati 3.1 PDF con AI tornato funzionante
- File: `/app/apt-packages.txt` creato per persistenza

### Campi Normativa Commesse (Phase 59 - Mar 2026)
- Aggiunti campi `classe_exc` (EXC1-EXC4) e `tipologia_chiusura` (cancello, ringhiera, porta, scala, struttura, recinzione, pensilina, altro) a `CommessaCreate`/`CommessaUpdate`
- Badge visibili nel CommessaHubPage, selettori nel form creazione PlanningPage

### Fix Dashboard Fatturato (Phase 59 - Mar 2026)
- Corretto calcolo mesi nel grafico fatturato: sostituito `timedelta(days=30)` con aritmetica mesi precisa
- Feb 2026 ora correttamente visibile con 5 fatture emesse per EUR 3.877,75

### Fix Importo Email Preventivo (Phase 59 - Mar 2026)
- Email preview/send per preventivi ora legge `totals.total` (non `totals.total_document` che non esiste nei preventivi)

### Workflow Fatture: Emetti → SDI (Phase 59 - Mar 2026)
- Bottone "Emetti" in InvoiceEditorPage e dropdown InvoicesPage (bozza → emessa)
- Bottone "Invia SDI" visibile solo per documenti emessi (non bozze)
- Opzione "Segna Pagata" per fatture emesse
- Fix: rimosso vincolo `ge=0` su `unit_price` per supportare note di credito
- Testing: 100% backend (12/12), 100% frontend (iteration_68)

### Workflow SDI Aruba Completo (Phase 59b - Mar 2026)
- **Backend SDI Riscritto**: `aruba_sdi.py` ora legge credenziali dal DB (`company_settings.aruba_username/password/sandbox`), non piu dal `.env`
- **3 Endpoint SDI**: `POST send-sdi` (genera XML + invia), `GET stato-sdi` (verifica stato), `POST genera-xml` (generazione XML)
- **Frontend Impostazioni**: Nuovo tab "Integrazioni" in Settings con campi Aruba username/password/sandbox
- **Workflow UI Completo**: Emetti (bozza→emessa) → Invia SDI → Verifica Stato con bottoni condizionali
- **Modello Aggiornato**: `CompanySettings` e `CompanySettingsUpdate` con campi `aruba_*`
- Testing: 100% backend (11/11), 100% frontend (iteration_69)

### Fix AI Certificate Processing + Migrazione SDI a Fatture in Cloud (Phase 60 - Mar 2026)
- **BUG CRITICO FIXATO: AI Certificate Processing inconsistente** — Profili senza match OdA/RdP/DDT venivano archiviati (`tipo="archivio"`) e non creavano lotti CAM/material_batches.
  - **Root cause**: Condizione `if tipo != "archivio"` + mancanza di fallback alla commessa corrente
  - **FIX**: Aggiunto fallback (riga 1498-1503): profili senza match procurement → assegnati alla commessa corrente. Condizione cambiata a `if colata and matched_commessa_id:`
  - **Logica smart matching PRESERVATA**: 1) Match esatto via OdA/RdP/DDT 2) Match parziale 3) Cross-commessa assignment + copia certificato 4) Fallback alla commessa corrente se nessun match trovato
  - **Logging dettagliato**: ogni step del matching è ora loggato per debug futuro
- **Migrazione SDI da Aruba a Fatture in Cloud**: Endpoint `send-sdi` e `stato-sdi` ora usano `FattureInCloudClient` (API v2)
- **Backend**: `invoices.py` aggiornato, credenziali lette da `company_settings.fic_company_id` e `fic_access_token`
- **Modello**: Aggiunti `fic_company_id`, `fic_access_token` a `CompanySettings` e `CompanySettingsUpdate`
- **Frontend Impostazioni**: Tab "Integrazioni" aggiornata con campi Fatture in Cloud (Company ID, Access Token)
- Testing: 100% backend (13/13 iteration_72), 100% backend (10/10 iteration_70)

### Scheda Rintracciabilità Materiali EN 1090 (Phase 61 - Mar 2026)
- **Nuova funzionalità: PDF Scheda Rintracciabilità** — Genera PDF MOD.07 EN 1090 con WeasyPrint (landscape A4) da dati material_batches
- **Preventivo arricchito**: Aggiunti campi `numero_disegno` e `ingegnere_disegno` per collegare disegni tecnici
- **Material Batches arricchiti**: Nuovi campi `posizione`, `n_pezzi`, `numero_certificato`, `ddt_numero`, `disegno_numero`
- **Smart Matching migliorato**: Nuovo `_extract_profile_base()` estrae tipo profilo base (es. "IPE100") per matching affidabile tra OdA e certificati
- **Cascade Delete potenziata**: Ora elimina lotti CAM orfani tramite numeri colata dal metadata del certificato
- **Endpoint**: `GET /api/commesse/{cid}/scheda-rintracciabilita-pdf`
- **Frontend**: Bottone "Scheda Rintracciabilità PDF" nella sezione Tracciabilità + campi extra visualizzati
- Testing: 100% backend (12/12), 100% frontend (iteration_73)

### Fascicolo Tecnico EN 1090 — 4 Documenti PDF (Phase 62 - Mar 2026)
- **DOP (Dichiarazione di Prestazione)**: PDF auto-compilato con tabella prestazioni EN 1090-2:2024, dati azienda/commessa/mandatario
- **CE (Marcatura CE)**: PDF con marchio CE, ente notificato, certificato, classe esecuzione, tabella caratteristiche
- **Piano di Controllo Qualità (MOD. 02)**: PDF landscape con 16 fasi predefinite (ricezione, taglio, saldatura, VT, CND, verniciatura, montaggio...), checkbox Pos/Neg, date, firme. Dati editabili via PUT
- **Rapporto VT (MOD. 06)**: PDF esame visivo con checkbox condizioni visione/superficie/ispezione/attrezzatura, tabella oggetti controllati con esiti
- **Architettura aperta**: Dati salvati in `commessa.fascicolo_tecnico`, fasi Piano Controllo personalizzabili
- **Preventivo arricchito**: Campi `numero_disegno` e `ingegnere_disegno` propagati ai documenti
- **Endpoints**: GET/PUT `/api/fascicolo-tecnico/{cid}` + 4 endpoint PDF (`/dop-pdf`, `/ce-pdf`, `/piano-controllo-pdf`, `/rapporto-vt-pdf`)
- **Frontend**: 4 card con bottoni PDF nella sezione "Fascicolo Tecnico EN 1090" del CommessaOpsPanel
- Testing: 100% backend (14/14), 100% frontend (iteration_74)

### Fascicolo Tecnico EN 1090 — Completamento 6 Documenti + Form Editabili (Phase 63 - Mar 2026)
- **Registro di Saldatura (MOD. 04)**: PDF landscape con tabella gerarchica saldature (20 colonne), gruppi VISUAL TEST, CND, RIPARAZIONE. Struttura fedele all'originale.
- **Riesame Tecnico (MOD. 01)**: PDF 2 pagine con checklist 28 requisiti (Si/No/N.A.), sezione Fattibilità (PROCEDERE/NON PROCEDERE), tabella ITT 10 caratteristiche.
- **Template PDF riscritti**: Tutti i 6 PDF (DOP, CE, Piano Controllo, Rapporto VT, Registro Saldatura, Riesame Tecnico) riscritti con layout fedele ai documenti originali. Header standard con logo/titolo/mod, bordi neri, font Calibri.
- **Etichetta CE fedele**: Bordo singolo, marchio CE grande centrato, campi label:value senza tabella, identica all'originale.
- **Form editabili**: Nuovo componente `FascicoloTecnicoSection.js` con dialog di editing per ciascun documento. Form specifici: DopEditForm, CeEditForm, PianoEditForm, VtEditForm, RegistroEditForm, RiesameEditForm.
- **Saldature dinamiche**: Aggiunta/rimozione righe saldatura nel Registro, con campi per tutti i 20 parametri.
- **Requisiti editabili**: Checklist Riesame con radio Si/No/N.A. per ogni requisito + campo note.
- **Fasi personalizzabili**: Toggle applicabile/non-applicabile per fasi Piano di Controllo con esito e data.
- **Endpoints**: 2 nuovi → `/registro-saldatura-pdf`, `/riesame-tecnico-pdf`
- **Frontend**: 6 card con bottoni "Compila" (apre editor) e "PDF" (scarica). Componente estratto dal panel principale.
- Testing: 100% backend (20/20 - iteration_75)

### Auto-compilazione PDF + Acciaieria + Firma Digitale (Phase 64 - Mar 2026)
- **Classe di Esecuzione nel Preventivo**: Nuovo campo `classe_esecuzione` (EXC1-EXC4) nel modello e editor preventivo. Auto-propagato a tutti i PDF del Fascicolo Tecnico.
- **Auto-compilazione da Preventivo**: `_get_context` ora recupera dal preventivo: cliente, classe esecuzione, n. disegno, ingegnere (redatto da). Tutti i 6 PDF e la Scheda Rintracciabilità li mostrano automaticamente.
- **Colonna Acciaieria**: Aggiunta alla Scheda Rintracciabilità Materiali (colonna "Acciaieria" nel PDF + campo editabile inline nel frontend).
- **Fornitore da OdA**: Il Fornitore nella Scheda Rintracciabilità viene ora cercato anche dagli Ordini di Acquisto (OdA) collegati alla commessa, non solo dal batch.
- **PATCH Material Batches**: Nuovo endpoint `PATCH /api/commesse/{cid}/material-batches/{batch_id}` per aggiornare acciaieria, fornitore, DDT, posizione, n. pezzi, n. certificato.
- **Firma Digitale**: Upload immagine PNG/JPG nelle Impostazioni Aziendali (tab Logo). Base64 salvato in `company_settings.firma_digitale`. Firma inserita automaticamente nelle aree firma di tutti i PDF (DOP, Piano Controllo, Rapporto VT, Registro Saldatura, Riesame Tecnico).
- **Logo nei PDF**: Tutti i PDF ora mostrano il logo aziendale nell'intestazione (se caricato).
- Testing: 100% backend (15/15 - iteration_76)

### Auto-compilazione Intelligente + Fascicolo Completo + Timeline (Phase 65 - Mar 2026)
- **Auto-compilazione 70%**: Il GET `/api/fascicolo-tecnico/{cid}` ora restituisce `_auto_fields` (lista campi auto-compilati da preventivo/commessa) e `_timeline` (fasi produzione). I campi auto: client_name, commessa_numero, commessa_title, disegno_numero, disegno_riferimento, redatto_da, classe_esecuzione, materiale, profilato, materiali_saldabilita.
- **Evidenziazione campi mancanti**: Frontend con `SmartField` — badge "AUTO" (verde) per campi auto-compilati, "DA COMPILARE" (ambra) per campi vuoti richiesti. Ogni card mostra indicatore completamento (es. "12/18") con bordo emerald/amber.
- **Timeline Produzione**: Striscia visiva con segmenti colorati (verde=completato, blu=in_corso, grigio=da_fare) sincronizzata da `fasi_produzione` della commessa. Le date delle fasi produzione auto-compilano le date del Piano di Controllo.
- **Genera Fascicolo Tecnico Completo**: Bottone "Genera Fascicolo Tecnico Completo" → dialog con checkboxes per selezionare documenti + bottoni "Tutti/Nessuno". Endpoint `GET /api/fascicolo-tecnico/{cid}/fascicolo-completo-pdf?docs=dop,ce,...` combina PDF selezionati con pypdf.
- **Tempi di Consegna**: Nuovo campo `giorni_consegna` nel preventivo (es. 30 giorni) — mostrato nell'editor con input numerico.
- Testing: 100% backend (18/18 - iteration_77), frontend verificato Playwright

### Dashboard Compliance + Fix Dropdown + Repository Filtri (Phase 66 - Mar 2026)
- **Dashboard Compliance EN 1090**: Nuovo widget nella home che mostra lo stato di completamento del fascicolo tecnico per ogni commessa attiva (confermata/in_produzione). Barra di progresso colorata (rosso <50%, ambra 50-80%, verde >80%), pillole per ogni documento (DOP/CE/Piano/VT/Registro/Riesame), click per navigare alla commessa. Ordinamento: incomplete per prime.
- **Fix Dropdown Radix UI nelle Modali**: Risolto bug ricorrente — aggiunto `onPointerDownOutside` handler nel DialogContent per prevenire chiusura quando si clicca su Select portal. SelectContent z-index alzato a `z-[100]` (sopra Dialog z-50).
- **Repository Documenti con Filtri**: Filtro per tipo documento (appare con >3 documenti) usando attributo `data-doc-type`. Filtraggio istantaneo client-side.
- **Endpoint**: `GET /api/dashboard/compliance-en1090` — ritorna commesse con compliance_pct, docs status (filled/total/complete per tipo), prod_progress.
- Testing: 100% backend (12/12 - iteration_78), frontend verificato Playwright

## Issue Pendenti
- **P2**: Radix UI Select/Popover dentro Dialog (workaround nativo attivo)
- **P2**: Verifica utente parsing AI certificati (richiede test manuale dall'utente)

## Task Futuri
- [ ] P1: Verifica integrazione Fatture in Cloud SDI (richiede credenziali utente)
- [ ] P1: Repository Documenti UI — nuova tab nel CommessaHub per gestire tutti i documenti
- [ ] P2: Fix Radix UI dropdown dentro modal (root cause investigation)
- [ ] P2: Data Seeding/Migrazione dati di test
- [ ] Collegamento diretto Commessa <-> Progetto FPC
- [ ] Esportazione CSV distinta di taglio per CNC
- [ ] Estensione Distinta Facile (grata 2 ante, cancello scorrevole)
- [ ] Categoria "CANCELLI" al listino prezzi
- [ ] Migrazione dati EN 13241
- [ ] Versioning fatture e fascicoli tecnici
- [ ] Integrazione Stripe (pagamenti online)
- [ ] Firma Elettronica Avanzata (FEA) per PDF
- [ ] Modalita offline (PWA)
- [ ] App Mobile Nativa
- [ ] Stato "SOSPESA" per commesse
