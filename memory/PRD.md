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
1. **Copertina**: Logo + tachimetro SVG conformità (semicircolare, 3 livelli colore) + dati sopralluogo + foto hero sfumata
2. **Box Riepilogo**: Conformità%, Rischi Critici, Rischi Medi, Dispositivi Mancanti, Interventi Previsti
3. **Descrizione Generale**: Box con analisi AI
4. **Documentazione Fotografica**: Griglia 2 colonne con didascalie
5. **Schede Criticità Pro**: Layout 2 colonne (problema+foto SX | soluzione+immagine esempio DX) con barra laterale colorata per gravità, badge norma, tipo rischio
6. **Dispositivi Sicurezza**: Presenti (verde) vs Mancanti (rosso) con checkmark/cross
7. **Materiali e Interventi**: Tabella professionale con priorità (obbligatorio/consigliato) e totale
8. **Note e Firme**: Area note AI + tecnico, doppia firma (tecnico + cliente)
9. **Sezioni numerate** (01, 02, 03...) con header navy

### Libreria Immagini Soluzione
- 4 immagini PNG in `/app/backend/services/ref_images/`: costa.png, encoder.png, fotocellula.png, rete.png
- Matching via keyword: costa, fotocellula, rete, encoder (+ sinonimi: motore→encoder, limitatore→encoder, fotocellule→fotocellula)
- Cache in memoria per performance

## Feature Completate (sessione 5 Marzo 2026 - Fork 8)

### PDF Perizia Pro - Restyling Completo
- **Tachimetro SVG semicircolare** sulla copertina con 3 livelli colore (rosso <35%, ambra 35-65%, verde >65%)
- **Schede criticità a 2 colonne**: problema+foto SX | soluzione+immagine esempio DX
- **Immagini soluzione** dalla libreria statica (costa, fotocellula, rete, encoder) matchate per keyword
- **Box riepilogo** con contatori: Conformità%, Rischi Critici, Rischi Medi, Dispositivi Mancanti, Interventi
- **Sezioni numerate** (01-05) con header navy professionale
- 28/28 test passati (iteration_139)

### Quick Create Cliente + Restyling PDF v2
- **Modale "Nuovo Cliente Rapido"** nel wizard sopralluogo step 1: bottone "+ Nuovo" accanto alla dropdown cliente, modale con Nome (obbligatorio), Indirizzo, Telefono, Email. Al salvataggio seleziona automaticamente il cliente creato.
- **Griglia foto 2x2** senza placeholder vuoti per numero dispari di foto
- **Prezzi smart** nella tabella materiali: "Da Quotare" per prezzi a 0, totale solo se almeno un prezzo > 0
- **Header professionale** nelle pagine contenuto: barra Blu Notte con logo grande + "RELAZIONE TECNICA DI SOPRALLUOGO" + numero documento
- 20/20 test passati (iteration_140)

### Sistema Email Perizia Professionale (5 Mar 2026)
- **Template dinamico**: 3 livelli in base a conformità%: URGENTE (<40%, Art. 2051 C.C., Rischio Penale/Assicurativo), ATTENZIONE (40-65%), Normale (>65%)
- **Anteprima completa**: Pannello con Oggetto + Corpo editabili, "Scarica PDF (Anteprima)" per revisione prima dell'invio
- **Backend**: Accetta subject/body personalizzati dal frontend, fallback a default se vuoti
- 39/39 test passati (iteration_144)

### Migliorie Professionali PDF Perizia v3 (5 Mar 2026)
- **AI Prompt**: Varianti autonome (no "include Variante A"), campo `rischi_residui`, campo `stima_manodopera`
- **PDF Registro Manutenzione**: Obbligo Libretto Impianto, manutenzioni semestrali
- **PDF Check-list Post-Intervento**: 8 test specifici (forze impatto, coste, fotocellule, finecorsa, arresto emergenza, encoder, lampeggiante, Dichiarazione)
- **PDF Rischi Residui**: Sezione warning ambra dopo le varianti
- **PDF Manodopera**: Stima ore/tecnici nel footer di ogni variante
- **Immagini**: Label aggiornata "Soluzione tipo (sostituibile con foto proprie installazioni)"
- 18/18 test passati (iteration_143)

### Bug Fix: Crash Dettaglio Fattura da Preventivo (5 Mar 2026)
- **Causa**: Le funzioni `create_invoice_from_preventivo` (invoices.py) e `create_progressive_invoice` (preventivi.py) creavano un oggetto `totals` incompleto, senza `vat_breakdown`, `total_to_pay`, `rivalsa_inps`, `cassa`, `ritenuta`.
- **Frontend** `InvoiceEditorPage.js` riga 904 fa `Object.entries(totals.vat_breakdown)` che crashava.
- **Fix**: Entrambe le funzioni ora generano un `totals` completo e coerente con `InvoiceTotals`. Corretta anche la fattura 19/2026 (Merighi Giancarlo) già nel DB.
- Verificato via API e screenshot: pagina caricata correttamente con tutti i totali.

### Feature: Perizia AI Multi-Normativa (6 Mar 2026)
- **Frontend**: Aggiunto selettore Card Grid per tipologia perizia nello Step 1 del Wizard (Cancelli EN 12453, Barriere D.M. 236/89, Strutture NTC 2018). Placeholder, istruzioni foto e testo AI dinamici.
- **Backend (vision_analysis.py)**: 3 system prompt specializzati per GPT-4o con competenze normative specifiche e JSON output schema condiviso.
- **Backend (pdf_perizia_sopralluogo.py)**: Template PDF dinamico — titolo copertina, norme citate, note legali, checklist post-intervento si adattano al tipo di perizia.
- **Model**: Aggiunto campo `tipo_perizia` a SopralluogoCreate/Update.

### Feature: Duplica Preventivo / Clone Quote (6 Mar 2026)
- **Backend**: Endpoint `POST /api/preventivi/{id}/clone` — clona preventivo con nuovo ID, numero progressivo, data odierna, status `bozza`, reset `converted_commessa_id` e `total_invoiced`
- **Frontend Editor**: Bottone "Crea Copia" nella toolbar (PreventivoEditorPage) — redirect automatico al nuovo preventivo
- **Frontend Lista**: Icona Copy in ogni riga (PreventiviPage) — clone rapido dalla lista
- 20/20 test backend + tutti i test UI passati (iteration_148)

### Feature: Perizia AI Parapetti & Ringhiere (6 Mar 2026)
- **Nuova 4a categoria**: "Parapetti & Ringhiere" (UNI 11678 / NTC 2018) aggiunta al modulo AI Inspection
- **Prompt AI specializzato**: Verifica altezza (100cm/110cm), scalabilita, tipo vetro (stratificato vs monolitico), fissaggi/morsetti, aperture >10cm (sfera), corrosione, bordo inferiore
- **PDF configurato**: Titolo copertina, norme legali (UNI 11678, NTC 2018 par. 3.1.4, UNI 7697, UNI EN 12600), checklist post-intervento specifica
- **Frontend**: 4a card nel selettore con icona Fence, placeholder e istruzioni contestuali per parapetti
- 17/17 test passati (iteration_147)

### Bug Fix: Errore 400 salvataggio fattura emessa (6 Mar 2026)
- **Causa**: Il backend bloccava QUALSIASI modifica su fatture non in bozza (riga 479 invoices.py). Il frontend inviava tutto il payload (incluse lines) anche per modifiche ai soli metadati.
- **Fix Backend**: Logica granulare — metadati (termini pagamento, scadenza, note) aggiornabili su tutti gli status; modifiche strutturali (righe, impostazioni fiscali, numero, cliente) bloccate su non-bozza.
- **Fix Frontend**: `handleSave` invia solo campi metadati per fatture non in bozza.

### Chiusura Diretta Commessa (6 Mar 2026)
- **Backend**: Nuovo endpoint `POST /api/commesse/{id}/complete-simple` — chiude una commessa direttamente saltando certificazione e produzione
- **Frontend**: Bottone "Chiudi senza certificazione" nel CommessaHubPage, visibile per stati attivi (richiesta, bozza, rilievo_completato, firmato, in_produzione, fatturato)
- **Dialog di conferma** con nota opzionale, evento `CHIUSURA_DIRETTA` registrato nella timeline
- 14/14 test passati (iteration_146)

### P0 (Completati)
- ~~Crash pagina dettaglio fattura da preventivo~~ COMPLETATO (5 Mar 2026)
- ~~Termini pagamento spariti in fatturazione~~ COMPLETATO (6 Mar 2026)
- ~~Errore 400 salvataggio fattura emessa~~ COMPLETATO (6 Mar 2026)
- ~~Restyling PDF Perizia Pro con tachimetro Risk Score~~ COMPLETATO (5 Mar 2026)
- ~~Preventivi accettati nella Planning Board~~ COMPLETATO
- ~~Error handling SDI~~ COMPLETATO
- ~~Modulo Sopralluoghi & Perizie~~ COMPLETATO
- ~~Chiusura diretta commessa senza certificazione~~ COMPLETATO (6 Mar 2026)

### P1
- **Firma digitale su tablet** — Permettere al cliente di firmare il PDF perizia su tablet
- **Bug condizioni pagamento** — Verificare condizioni pagamento cancellate alla chiusura form fornitore (non riprodotto)
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

## File Chiave
- `/app/backend/services/pdf_perizia_sopralluogo.py` - Generatore PDF Perizia Pro
- `/app/backend/services/ref_images_library.py` - Libreria immagini soluzione
- `/app/backend/routes/sopralluogo.py` - API sopralluoghi (CRUD + analisi AI + PDF)
- `/app/frontend/src/pages/SopralluogoWizardPage.js` - Wizard frontend
- `/app/frontend/src/pages/SopralluoghiPage.js` - Lista sopralluoghi

## Note Tecniche
- Contatori atomici MongoDB per numerazione documenti
- Autenticazione session-based (`credentials: 'include'`)
- L'utente comunica esclusivamente in italiano
- WeasyPrint per PDF con SVG inline (tachimetro) + CSS @page per intestazioni
- GPT-4o Vision per analisi sicurezza cancelli
- Object Storage Emergent per foto sopralluoghi
