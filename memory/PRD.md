# Norma Facile 2.0 - ERP Carpenteria Metallica

## Problema Originale
Costruire un ERP completo per un'azienda di carpenteria metallica, "Norma Facile 2.0", con gestione preventivi, fatture, commesse, tracciabilità materiali, certificazioni EN 1090/EN 13241, e fatturazione elettronica.

## Architettura
- **Frontend**: React + Shadcn/UI + TailwindCSS (porta 3000)
- **Backend**: FastAPI + MongoDB (porta 8001)
- **Auth**: Google OAuth (Emergent-managed)
- **Integrazioni**: Fatture in Cloud, Resend (email), WeasyPrint (PDF)

## Funzionalità Implementate

### Core ERP
- Gestione clienti (persone fisiche e giuridiche)
- Preventivi con editor completo (righe, sconti, IVA, compliance termica)
- Fatturazione progressiva con workflow (bozza -> accettato -> fatturato -> saldato)
- Commesse con split per normativa mista
- DDT (Documenti di Trasporto)
- Scadenziario pagamenti automatico

### Gestione Pagamenti
- Tipi pagamento avanzati multi-rata (stile Invoicex)
- Simulazione pagamenti client-side
- Termine "A fine lavori"
- Generazione automatica scadenze all'emissione fattura

### Conti Bancari e SDI
- Gestione multi-conto corrente aziendale nelle impostazioni
- Selezione conto nel preventivo/fattura (dropdown "Ns. Conto per Pagamento")
- Dati fatturazione elettronica (SDI, natura giuridica, regime fiscale)

### Tracciabilità e Certificazioni
- FPC (Fascicolo Produzione in Cantiere)
- Certificazioni EN 1090 / EN 13241
- Qualifica saldatori
- Compliance termica (calcolo Uw)

### Altre Funzionalità
- Numerazione atomica preventivi/fatture (no duplicati)
- Migrazione dati da vecchia app
- Backup/Restore
- Gestione team con ruoli
- Notifiche email (scheduler giornaliero)
- Generazione PDF
- Anteprima email

## Bug Risolti (sessione corrente - 3 Marzo 2026)
- **P0 FIX: Dropdown conti bancari vuoto nell'editor preventivi** - L'endpoint API chiamato era errato (`/company/` invece di `/company/settings`). Fix applicato in `PreventivoEditorPage.js` linea 143.
- **P0 FIX: Errore 422 al salvataggio preventivo** - `sconto_2` (stringa vuota) non veniva convertito a float prima dell'invio. Riscritto il payload di salvataggio campo per campo (no più `...form` spread). Aggiunti validators difensivi backend su `QuoteLine` e `PreventivoCreate`.
- **P0 FIX: Salvataggio impostazioni bloccato da EmailStr** - I campi `email` e `pec` con stringa vuota facevano fallire TUTTO il salvataggio delle impostazioni (inclusi conti bancari). Rimosso `EmailStr` da `CompanySettingsUpdate` e aggiunto validator `empty_str_to_none`.
- **Enhancement: Conto predefinito** - Stellina ★ nel dropdown per il conto marcato come predefinito. Auto-selezione del conto predefinito per nuovi preventivi.
- **UI: Q.tà vuota** - Il campo quantità nelle nuove righe ora parte vuoto invece che con "1".
- **Enhancement: Errori 422 dettagliati** - Aggiunto exception handler globale che mostra il campo esatto che causa l'errore di validazione.
- **Feature: Riepilogo Pagamenti nel PDF** - Il PDF del preventivo ora include una tabella "Riepilogo Scadenze Pagamento" con date, quote % e importi calcolati automaticamente dal tipo di pagamento.
- **Feature: Dashboard Semaforo Commesse** - Widget nel cruscotto che mostra lo stato delle commesse attive con semaforo (rosso=ritardo, giallo=scadenza vicina, verde=in tempo). Ordinamento per urgenza.
- **Feature: Gestione Fasi di Produzione con Date Previste** - Ogni fase di produzione ora ha una `data_prevista` auto-calcolata dalla deadline. Indicatore di ritardo per-fase (rosso se in ritardo). Date editabili inline. Il semaforo bump a giallo se fasi in ritardo anche con deadline lontana.
- **Feature: Generazione WPS automatica EN 1090** - Knowledge base completa (7 processi, 6 gruppi materiale, filler, gas, preriscaldo EN 1011-2, interpass, CND%). Suggerisce automaticamente i parametri WPS e trova i saldatori qualificati. CRUD completo con auto-numerazione.
- **Fix: Formato numerazione fatture** - Cambiato da `FT-2026-001` a `N/YYYY` (es. `13/2026`) per allinearsi alle fatture esistenti.

## Bug Risolti (sessione 3 Marzo 2026 - Fork)
- **Feature: Logica "Fine Mese + N Giorni"** - Aggiunto campo `extra_days` al modello `PaymentTypeBase` e alla UI. Permette termini come "30gg FM+10" (30 giorni dalla data fattura, fine mese + 10 giorni). Logica applicata in: backend simulate, frontend dialog (campo condizionale visibile solo con FM attivo), simulazione client-side e calcolo automatico scadenza in InvoiceEditorPage.
- **Fix: Errore 400 Invio SDI** - L'endpoint `send-sdi` ora legge le credenziali FIC anche dalle variabili d'ambiente (fallback). Fix mapping data fattura (`issue_date` invece di `created_at`).
- **Feature: Restyling Scadenziario stile Invoicex** - Riscrittura completa della pagina con layout tabellare tradizionale: barra KPI riassuntiva, filtri (Fornitori/Clienti, date, ricerca, solo da pagare), tabella con colonne ordinabili (Data Scad., Pagata, Importo, Da Pagare, Documento, Data Doc., Pagamento, Fornitore, Stato), footer con totali, colori amber per scaduti leggibili.

- **Feature: Importazione Intelligente Righe Fattura + Magazzino + Margini** - Nuovo servizio `invoice_line_processor.py` con smart matching articoli (codice/descrizione), calcolo PMP (Prezzo Medio Ponderato), creazione/aggiornamento articoli a magazzino. Assegnazione per-riga (Magazzino/Commessa/Spese Generali) con endpoint `assign-rows`. Analisi Margini: confronto preventivo vs costi reali per commessa con alert verde/giallo/rosso.

- **Feature: Controllo di Gestione Avanzato (Costo Orario Pieno)** - Nuovo servizio `cost_calculator.py` per calcolo costo orario reale aziendale: (Stipendi + Contributi + Overhead) / Ore Lavorabili. Pagina "Configurazione Finanziaria" con il "Numero Magico" (costo orario pieno) e form configurazione. Log ore per commessa. Analisi Margini aggiornata con barre separate Materiali (ambra) + Personale (viola) e alert a 4 livelli (verde >20%, giallo 10-20%, arancione <10%, rosso <0%).

## Bug Risolti (sessione 4 Marzo 2026 - Fork 2)
- **P0 FIX: Logica Matching Tracciabilità Materiali** - La funzione `_extract_profile_base` in `commessa_ops.py` generava chiavi troppo generiche per profili piatti/tubo/angolari (es. FLAT 120X12 e FLAT 120X7 entrambi mappati a "PIATTO120"). Fix: aggiunto collasso spazi intorno a X (`120 X 12` → `120X12`), migliorato parsing codici prodotto. Step C del matching reso più restrittivo: rimosso matching generico per sottostringhe/dimensioni, sostituito con match famiglia+dimensioni identiche. 26 unit test in `test_profile_matching.py`, tutti passano.
- **P0 FIX DEFINITIVO: Bug Creazione Cliente/Fornitore** - Ripristinata validazione Pydantic sugli endpoint POST/PUT di `clients.py`. I modelli `ClientCreate`/`ClientUpdate` ora usano `model_validator(mode='before')` per gestire automaticamente valori `null` dal frontend (li rimuove e usa i default Pydantic). `ConfigDict(extra="ignore")` per ignorare campi sconosciuti. Migliorata gestione errori 422 in `apiRequest.js` per mostrare messaggi specifici (campo + messaggio) invece di JSON raw. 18 test CRUD in `test_iteration119_client_crud.py`, tutti passano.
- **BUG FIX CRITICO: Ri-analisi certificato non puliva vecchi dati** - Quando si ri-analizzava un certificato dopo il fix del matching, i vecchi material_batches e lotti_cam della precedente analisi errata rimanevano nel database. Ora la ri-analisi elimina PRIMA tutti i dati vecchi (material_batches, lotti_cam, archivio) collegati al documento, poi ri-crea solo i match corretti. Blindato con 32 test (26 profili + 6 OdA matching) e commenti DO NOT TOUCH.
- **FEATURE: Pacchetto Consegna Completo (DDT + DoP + CE)** - Riscrittura completa del flusso consegna:
  - **DDT**: Rimossa cornice dati cliente, dati completi cliente (indirizzo, P.IVA, CF, PEC, SDI), numero DDT editabile, numerazione separata conto lavoro (CL-YYYY-NNNN vs DDT-YYYY-NNNN), righe dal preventivo con checkbox selezione voci.
  - **DoP**: Auto-popola certificato EN 1090 n., nome/cognome (firmatario), luogo e data, firma dalle impostazioni azienda.
  - **CE**: Certificato n. dalle impostazioni, "Caratteristiche strutturali: Disegni forniti dal committente redatti dall'Ing. {nome} TAV. n. {numero}", "Costruzione: in accordo alla specifica del cliente disegno TAV. n. {numero}, EN 1090-2".

## Bug Risolti (sessione 5 Marzo 2026 - Fork 3)
- **P0 FIX DEFINITIVO: Cascade Delete CAM/Tracciabilità** - Il bug ricorrente dove eliminando un certificato la sezione CAM non si aggiornava era causato dal FRONTEND: `handleDeleteDoc` in `CommessaOpsPanel.js` chiamava solo `fetchData()` ma NON `fetchCamData()`. Il backend cascade delete (3 strategie: source_doc_id, colata numbers, nuke orphans) funzionava correttamente. Fix: aggiunto `fetchCamData(); onRefresh?.()` al handler. Toast ora mostra dettagli cascade. 10 test di regressione passati (5 pytest + 5 API contracts).
- **FIX: Pulizia orfani database** - Rimossi 4 record orfani (2 lotti_cam + 2 material_batches) da documenti eliminati in sessioni precedenti.
- **FIX: poppler-utils** - Installato permanentemente (presente in apt-packages.txt).

## Feature Completate (sessione 5 Marzo 2026 - Fork 3)
- **P0 FEATURE: Super Fascicolo Tecnico con copertina professionale** - Creato template HTML professionale in `/app/backend/templates/pdf/cover_page.html`. Cover page include: logo azienda, badge EN 1090, titolo "FASCICOLO TECNICO / Dossier di Fabbricazione e Controllo", box dati commessa dinamico, indice contenuti dinamico (mostra N certificati e N patentini), area firma RWC, footer con P.IVA. Generatore aggiornato per merge certificati dal Repository Documenti + fallback material_batches. 14/14 test passati + 5/5 regressione cascade delete.
- **FEATURE: Colori righe preventivi** - Righe colorate in base allo stato effettivo: Accettato=ambra, In Lavorazione=blu, Chiuso=verde. Backend arricchisce la lista con `commessa_stato` dalla commessa collegata.
- **FEATURE: Commessa Generica** - Nuovo endpoint `POST /commesse/from-preventivo/{id}/generica` crea commesse senza numero NF-XXXX (usa GEN-PRV-XXXX), con flag `generica=true`. Dropdown nel PreventivoEditor con 2 opzioni: "Commessa Normata" e "Commessa Generica". Badge "GEN" nel Planning Kanban.
- **FEATURE: Rimozione scadenze dal preventivo PDF** - Rimossa la sezione "RIEPILOGO SCADENZE PAGAMENTO" dal PDF preventivo.
- **FEATURE: Popolamento dati dinamico Fascicolo Tecnico** - Fix 4 sezioni PDF:
  - CAM: pesi "N.D." al posto di "0.0 kg" con catena fallback (cam_lotti → material_batches → arrivi → N.D.)
  - Green Certificate: "N.D." per CO2 quando pesi non disponibili
  - PCQ: arricchimento fasi da commessa.produzione (date, operatori, esiti)
  - Registro Saldatura: auto-popola da saldatori assegnati e WPS
  - DoP/CE: dati materiale reali da `_get_material_properties(cam_lotti)` — "S275JR+AR" invece di default generico
  - Durabilità: check anche su conto_lavoro per trattamenti superficiali
  13/13 test passati.
- **FEATURE: Restyling totale fattura PDF** - Nuovo generatore `pdf_invoice_modern.py`: header con logo grande + company a destra, sezione "DESTINATARIO" senza bordi, tabella padding generoso, coordinate bancarie SX / totali DX, scadenza prominente in box blu, font Helvetica. 9/9 test passati.
- **FEATURE: Colori preventivi accentuati** - Righe con colori più forti e border-l-4: Accettato=ambra, In Lavorazione=sky blue, Chiuso=emerald.
- **FEATURE: Modulo RdP (Richiesta Preventivo Fornitore)** - Flusso completo: selezione articoli → scelta fornitore → genera RdP PDF → registra risposta fornitore → applica prezzi con ricarico configurabile (default 30%) → aggiorna preventivo automaticamente → converte in OdA nella commessa collegata. Backend: 7 endpoint in `/app/backend/routes/rdp.py`. Frontend: pannello `RdpPanel.js` integrato nel PreventivoEditorPage. PDF: "RICHIESTA DI OFFERTA" professionale con spazio risposta fornitore. 14/14 test passati.
  13/13 test passati.

## Feature Completate (sessione 4 Marzo 2026 - Fork 4)
- **P0 FEATURE: Preventivi Accettati nella Planning Board** - Modificato endpoint `GET /api/commesse/board/view` per includere i preventivi con status "accettato" che non hanno una commessa collegata. Appaiono nella colonna "Nuove Commesse" con stile visivo distinto: bordo tratteggiato verde, badge "Preventivo Accettato", icona FileText. NON sono trascinabili. Click naviga a `/preventivi/edit/{id}`. Header mostra conteggio separato commesse + preventivi accettati. Pulsante "Crea Commessa" direttamente sulla card per creare la commessa con un click e navigare al suo hub. 10/10 test passati.

- **P0 FIX: Integrazione Ciclo Passivo nel Cruscotto Finanziario** - Corretto uso campi fatture_ricevute: `imposta` (non `totale_iva`), `data_scadenza_pagamento` (non `data_scadenza`), `payment_status`. Creato `financial_service.py` con funzioni aggregate per ciclo attivo+passivo. Aggiunto: Flusso Cassa Reale (6 mesi), Aging Fornitori, IVA Vendite vs IVA Acquisti (Bilancino IVA), Scadenzario completo con debiti fornitori e badge scaduti. 26/26 test passati.

## Bug Risolti (sessione 5 Marzo 2026 - Fork 5)
- **P0 FIX: Scadenzario Fornitori non splitta le rate** - Root cause multipla:
  1. Nessuna FR aveva `scadenze_pagamento` popolato
  2. Il matching fornitori P.IVA/CF non verificava la corrispondenza dei nomi (es. Bertolini FR collegata ad ALD Automotive per P.IVA condivisa)
  3. Il matching CF accettava match senza verifica nome (CF di ALD = P.IVA di Bertolini nel XML)
  4. Le query cashflow/receivables escludevano fatture con `payment_status: None`
  Fix applicati:
  - `financial_service.py`: `get_payables_aging()` e `get_cashflow_forecast()` usano `scadenze_pagamento` per rate individuali; query ampliate per includere `payment_status: None`
  - `fatture_ricevute.py` (`recalc-scadenze`): completamente riscritto con 3 fasi:
    - **Phase 0**: Verifica link esistenti e corregge mismatch (BERTOLINI: ALD→BERTOLINI)
    - **Phase 1**: Link FR non collegate via P.IVA+nome, CF+nome, nome word-based
    - **Phase 2**: Calcolo rate da tipo pagamento fornitore
  - P.IVA/CF matching ora verifica corrispondenza nome prima di accettare
  - `payment_calculator.py`: Fix critico "fine mese": il calcolo aggiungeva giorni letterali (31/01+30=02/03→fine marzo) invece di usare mesi di calendario (31/01 + 1 mese → fine febbraio). La convenzione italiana "30/60 gg FM" significa N/30 mesi dopo la data fattura, scadenza a fine mese. Esempio: DINELLI 31/01 RB30/60FM → era 31/03+30/04, ora corretto a 28/02+31/03.

## Bug Risolti (sessione 5 Marzo 2026 - Fork 6)
- **P0 FIX: UI "Segna come Pagata" (InvoicesPage.js)** - Riscrittura completa dello styling condizionale nella tabella fatture:
  - Colonna "Da Pagare" rinominata in "Residuo" per allinearsi alla terminologia utente
  - Righe pagate: sfondo verde chiaro (`bg-emerald-50/40`) per distinzione visiva immediata
  - Colonna "Pagato": verde bold per fatture pagate, verde chiaro per parziali, grigio neutro per "-"
  - Colonna "Residuo": rosso solo quando importo > 0, grigio neutro per "-" quando saldato
  - Pulsante "Pagata?" migliorato: più grande, ombra, bordo più forte per visibilità
  - 11/11 test backend passati (`test_iteration133_mark_as_paid.py`)

- **FEATURE: Restyling Template Fattura PDF (pdf_invoice_modern.py)** - Riprogettazione completa del layout:
  - Header: divider Blu Notte #0F172A
  - Cliente: "Spettabile Cliente" senza box/bordi, layout arioso
  - Tabella: header scuro #0F172A con testo bianco, padding 10px per leggibilità
  - Footer SX: "Dati Pagamento" con Condizioni di Pagamento, Banca, IBAN, BIC visibili
  - Footer DX: Totale 18pt bold, scadenza in ROSSO (#b91c1c) evidenziata
  - Note legali: "Riserva di proprietà ex art. 1523 C.C. — Interessi moratori ex D.Lgs 231/02"
  - Footer normativo: "Azienda Certificata EN 1090-1 EXC2 • ISO 3834-2 • Centro di Trasformazione Acciaio"
  - Rimossa variabile inutilizzata `netto_row`

- **FEATURE: Anteprima Live PDF nell'Editor Fattura** - Split-view con generazione PDF in tempo reale:
  - Backend: nuovo endpoint `POST /api/invoices/preview-pdf` genera PDF dai dati form correnti senza salvare
  - Frontend: componente `LivePDFPreview.js` con pannello laterale toggle (45% width)
  - Bottone "Anteprima Live" nell'header editor con icona PanelRightOpen
  - Pannello espandibile a fullscreen, bottone Aggiorna manuale, chiusura X
  - 10/10 test backend passati (`test_iteration134_preview_pdf.py`)

- **FIX: Condizioni di Vendita solo nel Preventivo** - Le condizioni generali di vendita (pagina 2 del PDF) ora appaiono SOLO per documenti di tipo PRV (Preventivo), NON nelle Fatture (FT), Note di Credito (NC), DDT. Verificato con test PDF: FT=1 pagina, PRV=2 pagine con condizioni.

- **FEATURE: Cleanup UX Tabella Fatture** - Pulizia completa della lista fatture:
  - Rimosso bottone "Pagata?" dalla colonna Stato (era brutto e confondeva)
  - Colonna Stato ora mostra SOLO badge colorati: Emessa (blu), Inviata SDI (giallo), Pagata (verde), Scaduta (rosso)
  - Nuova voce "Registra Incasso" nel menu azioni (3 puntini) per marcare fatture come pagate
  - Visibile per tutte le fatture non-bozza che non sono già pagate (incluse fatture vecchie di migrazione)
  - Funziona anche per fatture senza sdi_id (storiche importate)

## Issue Pendenti
- **P1**: Bug condizioni pagamento cancellate alla chiusura form fornitore senza salvare
- **P1**: Verifica end-to-end generazione dinamica PDF (DoP/CE) con dati materiali reali
- **P1**: Verifica flusso creazione DDT (nuovo dialog con numero editabile)
- **P2**: Gestione eccezioni generiche (`except Exception`) in tutto il backend
- **P2**: Cache frontend (utente deve fare hard refresh dopo deploy)

## Backlog Prioritizzato

### P0
- ~~Preventivi accettati nella Planning Board~~ COMPLETATO
- Conversione RdP in Ordine di Acquisto (OdA)
- Firma digitale su tablet (QR code per fasi produzione)

### P1
- Verifica end-to-end flusso DDT creazione (utente deve testare)
- Robustezza estrazione AI da PDF (strategia fallback multi-modello)
- Portale cliente read-only per tracking commesse
- Aggiungere firma immagine al DoP

### P2
- Gestione eccezioni generiche in tutto il backend
- Configurazione NAS come repository documenti
- Refactoring PreventivoEditorPage.js (1000+ righe)

### Futuri
- Analisi margini predittiva
- Calendario produzione / Gantt
- OCR per DDT fornitori
- Report PDF mensili automatici
- PWA per accesso offline
- Migrazione storage certificati (da Base64 a object storage)

## File Chiave
- `/app/frontend/src/pages/PreventivoEditorPage.js` - Editor preventivi
- `/app/frontend/src/pages/SettingsPage.js` - Impostazioni aziendali
- `/app/backend/routes/company.py` - API impostazioni aziendali
- `/app/backend/routes/preventivi.py` - API preventivi
- `/app/backend/routes/invoices.py` - API fatture
- `/app/backend/models/company.py` - Modelli impostazioni

## Note Tecniche
- Contatori atomici MongoDB per numerazione documenti (`counters` collection)
- Autenticazione session-based (`credentials: 'include'`)
- Dropdown nativi HTML per evitare bug z-index di Radix UI
- L'utente comunica esclusivamente in italiano
