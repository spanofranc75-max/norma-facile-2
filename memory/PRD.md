# Norma Facile 2.0 — PRD

## Problema Originale
Sistema ERP per carpenteria metallica (Steel Project Design Srls). Gestione commesse, preventivi, fatturazione, certificazioni EN 1090, perizie AI con ispezione fotografica, e ora gestione avanzata materiali/magazzino.

## Architettura
- **Backend**: FastAPI + MongoDB + Object Storage (Emergent)
- **Frontend**: React + Shadcn UI + TailwindCSS
- **Auth**: Emergent-managed Google OAuth
- **AI**: OpenAI GPT-4o Vision (Emergent LLM Key)
- **Email**: Resend
- **Fatturazione Elettronica**: FattureInCloud

## Funzionalità Implementate

### Core ERP
- Gestione clienti e fornitori
- Preventivi con numerazione sequenziale (riuso numeri eliminati)
- Fatturazione attiva/passiva con scadenziario
- Commesse con produzione, approvvigionamento, conto lavoro
- Dashboard finanziaria
- Catalogo articoli con storico prezzi

### Modulo Ispezione AI
- Perizia con foto + analisi AI (GPT-4o Vision)
- Generazione PDF professionale
- Proposte soluzioni AI
- Object Storage per immagini

### Analisi Margini Predittiva
- Servizio centralizzato aggregazione costi (margin_service.py)
- Dashboard margini in tempo reale
- Previsione AI margine finale per commesse in corso
- Costi: materiali, manodopera, fatture imputate, conto lavoro, OdA

### Gestione Avanzata Materiali (NUOVO - Mar 2026)
- **Prelievo da Magazzino**: Assegnazione materiale da giacenza ad una commessa con calcolo costo automatico (POST /api/commesse/{cid}/preleva-da-magazzino)
- **Annulla Imputazione Fattura**: Rimozione collegamento fattura→commessa con ripristino stato (POST /api/fatture-ricevute/{fr_id}/annulla-imputazione)
- **Utilizzo Parziale Materiale**: Al registrare un arrivo, specificare quantità effettivamente usata; il resto torna in giacenza magazzino (quantita_utilizzata su POST arrivi)
- **Colonna Giacenza**: Catalogo articoli mostra giacenza attuale

### Altre Funzionalità
- Backup intelligente con merge/upsert e wipe-and-replace
- Email rebrandate (Steel Project Design Srls)
- Qualifica saldatori e WPS
- Fascicolo tecnico CE
- Notifiche e scadenziario pagamenti

## Task Completati Ultima Sessione
- [x] Prelievo da magazzino → commessa
- [x] Annulla imputazione fattura ricevuta
- [x] Utilizzo parziale materiale con resto a magazzino
- [x] Colonna giacenza nella pagina articoli
- [x] Badge "Imputata" sulle fatture ricevute
- [x] Test automatici superati (backend 100%, frontend 95%)

## Backlog Prioritizzato

### P1 - Prossimi
- Firma digitale su PDF Perizia (tablet)
- Portale cliente read-only per tracking commesse

### P2 - Futuri
- Analisi margini predittiva per nuovi preventivi
- Report PDF mensili automatici
- PWA per accesso offline
- Migrare immagini Base64 a Object Storage
- Sostituire immagini generiche nel PDF perizia con foto reali

### Refactoring
- Scomporre MaterialiPage.js / CommessaOpsPanel.js (2700+ righe)
- Centralizzare utility (fmtEur, formatDateIT) in shared utils
- Ottimizzare gestione stato nei componenti complessi

## Vincoli Tecnici Critici
- `window.confirm()` è BLOCCATO nel sandbox → usare `useConfirm()` hook
- PDF preview: solo `react-pdf`, NO iframe/embed/blob/data URLs
- Select Radix UI: NO `value=""`, usare sentinella `__none__`
- Tutti i backend routes con prefisso `/api`
- MongoDB: sempre escludere `_id` nelle risposte
