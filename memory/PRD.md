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

## Issue Pendenti
- **P2**: Validazione Pydantic su dati migrati (response_model rimosso temporaneamente)
- **P2**: Cache frontend (utente deve fare hard refresh dopo deploy)

## Bug Risolti (sessione 4 Marzo 2026 - Fork)
- **P0 FIX: Duplicazione dati nel Restore Backup** - La funzione `restore_backup` in `backup.py` usava logica "trova → salta se esiste", causando duplicati quando il PK mancava e non aggiornando mai i record modificati. Riscritta con `update_one(..., upsert=True)` per ogni documento. Aggiunta chiave PK per `company_settings` (user_id) e `catalogo_profili` (codice). La response ora restituisce `total_inserted`, `total_updated`, `total_errors`. Frontend aggiornato per riflettere la nuova logica. Test backend 100% (10/10 pytest).
- **BUG FIX: Errore 400 creazione Fornitore** - Il check duplicati P.IVA non distingueva tra tipi (cliente/fornitore), bloccando la creazione anche per tipi diversi. Ora: stesso tipo → 400 con nome record esistente; tipo diverso → 409 con suggerimento di conversione a "Cliente/Fornitore". Aggiunta pulizia stringhe vuote → null per campi opzionali in FornitoriPage.js (allineamento con ClientsPage.js). Aggiunto endpoint POST `/clients/{id}/promote` per conversione tipo.

## Backlog Prioritizzato

### P0
- Firma digitale su tablet (QR code per fasi produzione)

### P1
- Dashboard "semaforo" lavori in tempo reale

### P2
- Generazione automatica WPS per EN 1090
- Refactoring PreventivoEditorPage.js (1000+ righe -> componenti più piccoli)

### Futuri
- Portale cliente read-only
- Analisi margini predittiva
- Calendario produzione / Gantt
- OCR per DDT fornitori
- Report PDF mensili automatici
- PWA per accesso offline
- Migrazione storage certificati (da Base64 a object storage)
- Versioning documenti
- Funzionalità "Restore from Backup"

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
