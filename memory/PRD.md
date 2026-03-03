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
- **P0 FIX: Errore 422 al salvataggio preventivo** - `sconto_2` (stringa vuota) non veniva convertito a float prima dell'invio. Aggiunto conversione frontend + validators difensivi backend su `QuoteLine` e `PreventivoCreate`.
- **Enhancement: Conto predefinito** - Stellina ★ nel dropdown per il conto marcato come predefinito. Auto-selezione del conto predefinito per nuovi preventivi.

## Issue Pendenti
- **P2**: Validazione Pydantic su dati migrati (response_model rimosso temporaneamente)
- **P2**: Cache frontend (utente deve fare hard refresh dopo deploy)

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
