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

### Modulo contabile/finanziario (COMPLETATO 2026-03-08)
- Import fatture SDI: parsing multipli DettaglioPagamento, fallback 3 livelli, preview con scadenze
- Deduplicazione robusta: $or fingerprint + indice unique fr_id + lock anti-doppio-click
- Scadenziario unificato attive+passive con aging
- Cruscotto finanziario con DSO/DPO, fatturato per cliente/tipologia
- Export scadenziario XLSX/PDF
- Riconciliazione bancaria (import CSV, matching transazioni)
- **Alert email scadenze (COMPLETATO)**: job schedulato 24h, template HTML, invio Resend, endpoint test manuale + preview

### Stabilizzazione codebase (2026-03-08)
1. Atomic counter preventivi (3 path: create, from-distinta, clone)
2. Serializer MongoDB centralizzato + fix _id:0
3. 18+ indici MongoDB + unique index fr_id
4. Paginazione su commesse, preventivi, DDT
5. Search globale (endpoint + componente React con debounce, Ctrl+K)
6. Morning Briefing dashboard (4 card)
7. Pulizia DB: duplicati rimossi, scadenze migrate, dati test eliminati
8. Backup DB per deploy produzione

## Backlog prioritizzato

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
