# Norma Facile 2.0 — PRD

## Problema originale
Sistema ERP completo per azienda di carpenteria metallica. Gestione commesse, preventivi, fatture, DDT, approvvigionamento, produzione, conto lavoro, tracciabilità materiali EN 1090/EN 13241, generazione PDF, integrazione FattureInCloud, modulo contabile/finanziario.

## Lingua utente
Italiano

## Architettura
- **Frontend:** React + Shadcn/UI + TailwindCSS + Recharts (porta 3000)
- **Backend:** FastAPI + MongoDB + WeasyPrint + openpyxl (porta 8001)
- **Integrazioni:** Claude Sonnet 4, OpenAI GPT-4o Vision, Emergent Object Storage, Resend, FattureInCloud, Google Auth, react-pdf

## Funzionalità implementate

### Moduli core
- Gestione completa commesse, preventivi, fatture, DDT
- Approvvigionamento (RdP, OdA, arrivi materiale)
- Produzione (fasi, operatori, timeline)
- Conto lavoro (invio, rientro, verifica QC, NCR)
- Tracciabilità materiali EN 1090 (material_batches, lotti_cam)
- Generazione PDF: Super Fascicolo, Fascicolo Tecnico, DoP, DDT, NCR
- AI parsing certificati (OCR + analisi)

### Modulo contabile/finanziario
- **Import fatture SDI con rate multiple (FIXED 2026-03-08):**
  - Parsing completo di tutti i `<DettaglioPagamento>` con schema arricchito (scadenza_id, numero_rata, totale_rate, importo_residuo, stato, modalita_pagamento, origine)
  - Fallback Level 1: scadenze da XML
  - Fallback Level 2: condizioni pagamento fornitore (ricerca per P.IVA e CF)
  - Fallback Level 3: default 30gg dalla data fattura
  - Preview XML con scadenze calcolate + banner origine + duplicate detection
- Scadenziario unificato attive+passive con aging (0-30, 31-60, 61-90, >90gg)
- Cruscotto finanziario con DSO/DPO, fatturato per cliente/tipologia
- Export scadenziario XLSX (openpyxl) e PDF (WeasyPrint)
- Cash flow previsionale e consuntivo
- Riconciliazione bancaria (import CSV, matching transazioni)

### Stabilizzazione codebase (2026-03-08)
1. Atomic counter preventivi (tutti e 3 i path: create, from-distinta, clone)
2. Serializer MongoDB centralizzato (core/serializer.py) + fix _id:0 su get_commessa_or_404
3. 18 indici MongoDB su collection critiche
4. Paginazione su commesse, preventivi, DDT (page/per_page con metadata)
5. Search globale (endpoint + componente React con debounce, Ctrl+K, keyboard nav)
6. Morning Briefing dashboard (4 card: scadenze oggi/domani, ritardi, commesse ferme, azioni)

## Backlog prioritizzato

### P1 — Alta priorità
- Completare alert email giornalieri scadenze (template HTML, test invio Resend)

### P2 — Media priorità
- Impostazioni utente per alert email (opt-in, indirizzo, giorni preavviso)
- Firma digitale su PDF Perizia (tablet)
- Portale cliente read-only

### P3 — Bassa priorità / Futuro
- Analisi predittiva margini per preventivi
- Report PDF mensili automatizzati
- PWA per accesso offline
- Migrazione immagini Base64 -> object storage
- Refactoring CommessaOpsPanel.js

## File chiave
- `/app/backend/routes/fatture_ricevute.py` — Parser SDI XML (FIXED), import, preview, CRUD
- `/app/backend/services/payment_calculator.py` — Calcolo scadenze da condizioni pagamento
- `/app/backend/routes/search.py` — Search globale
- `/app/backend/routes/dashboard.py` — Morning Briefing + KPI
- `/app/backend/core/serializer.py` — Serializer MongoDB
- `/app/frontend/src/pages/FattureRicevutePage.js` — UI fatture ricevute con preview import
- `/app/frontend/src/components/GlobalSearchBar.js` — Barra ricerca globale
