# Norma Facile 2.0 — PRD

## Problema Originale
Sistema ERP per carpenteria metallica (Steel Project Design Srls). Gestione commesse, preventivi, fatturazione, certificazioni EN 1090, perizie AI con ispezione fotografica, gestione avanzata materiali/magazzino.

## REGOLA FONDAMENTALE FATTURAZIONE
**Si lavora SEMPRE sull'IMPONIBILE. L'IVA si aggiunge SOLO alla fine.**
- Percentuali acconto: calcolate sull'imponibile
- SAL: importi basati sulle righe (line_total = imponibile per riga)
- Saldo: residuo calcolato sull'imponibile
- Mai calcolare percentuali sul totale con IVA

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
- Fatturazione progressiva (acconto %, SAL, saldo) — **FIX CRITICO Mar 2026: calcoli basati su imponibile**
- Commesse con produzione, approvvigionamento, conto lavoro
- Dashboard finanziaria
- Catalogo articoli con storico prezzi e giacenza

### Modulo Ispezione AI
- Perizia con foto + analisi AI (GPT-4o Vision)
- Generazione PDF professionale
- Proposte soluzioni AI
- Object Storage per immagini

### Analisi Margini Predittiva
- Servizio centralizzato aggregazione costi (margin_service.py)
- Dashboard margini in tempo reale
- Previsione AI margine finale per commesse in corso

### Gestione Avanzata Materiali (Mar 2026)
- Prelievo da Magazzino → Commessa
- Annulla Imputazione Fattura Ricevuta
- Utilizzo Parziale Materiale con resto a magazzino
- Colonna Giacenza nel catalogo articoli

### Altre Funzionalità
- Backup intelligente con merge/upsert e wipe-and-replace
- Email rebrandate (Steel Project Design Srls)
- Qualifica saldatori e WPS
- Fascicolo tecnico CE
- Notifiche e scadenziario pagamenti

## Bug Fix Critici
- **[Mar 2026] DOPPIA IVA su fattura progressiva**: Acconto % calcolava la percentuale sul totale CON IVA invece che sull'imponibile. Corretto in preventivi.py (backend) e InvoiceGenerationModal.js (frontend).

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
- Scomporre CommessaOpsPanel.js (2800+ righe)
- Centralizzare utility (fmtEur, formatDateIT) in shared utils

## Vincoli Tecnici Critici
- `window.confirm()` è BLOCCATO nel sandbox → usare `useConfirm()` hook
- PDF preview: solo `react-pdf`, NO iframe/embed/blob/data URLs
- Select Radix UI: NO `value=""`, usare sentinella `__none__`
- Tutti i backend routes con prefisso `/api`
- MongoDB: sempre escludere `_id` nelle risposte
