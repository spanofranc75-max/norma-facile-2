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
- **Import fatture SDI (FIXED 2026-03-08):**
  - Parsing completo di tutti i `<DettaglioPagamento>` con schema arricchito
  - Fallback 3 livelli: XML → condizioni fornitore → default 30gg
  - Preview XML con scadenze calcolate + banner origine + duplicate detection
  - **Deduplicazione robusta**: $or (numero+piva+data | piva+data+totale) + indice unique su fr_id
  - Response batch con `dettaglio_saltate` e riepilogo
  - Fix applicato a: import-xml, import-xml-batch, preview-xml, sync-fic
- Scadenziario unificato attive+passive con aging
- Cruscotto finanziario con DSO/DPO, fatturato per cliente/tipologia
- Export scadenziario XLSX/PDF
- Riconciliazione bancaria (import CSV, matching transazioni)

### Stabilizzazione codebase (2026-03-08)
1. Atomic counter preventivi (3 path: create, from-distinta, clone)
2. Serializer MongoDB centralizzato + fix _id:0 su get_commessa_or_404
3. 18+ indici MongoDB su collection critiche + unique index fr_id
4. Paginazione su commesse, preventivi, DDT
5. Search globale (endpoint + componente React con debounce, Ctrl+K)
6. Morning Briefing dashboard (4 card)

### Data cleanup (2026-03-08)
- Rimossi 144+37 duplicati fatture ricevute (da 218 → 54 uniche)
- Migrato 21 scadenze dal vecchio al nuovo schema
- Fix dedup sync FIC con fingerprint robusto

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
