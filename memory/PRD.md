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
- **FEATURE: Dossier → Fascicolo Tecnico** - Endpoint `/dossier` ora genera il Fascicolo Tecnico professionale invece del vecchio log eventi.

## Issue Pendenti
- **P1**: Verifica end-to-end generazione dinamica PDF (DoP/CE) con dati materiali reali
- **P1**: Verifica flusso creazione DDT (nuovo dialog con numero editabile)
- **P2**: Gestione eccezioni generiche (`except Exception`) in tutto il backend
- **P2**: Cache frontend (utente deve fare hard refresh dopo deploy)

## Backlog Prioritizzato

### P0
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
