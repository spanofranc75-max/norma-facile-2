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
- Import fatture SDI con DettaglioPagamento multipli
- Scadenziario unificato attive+passive con aging (0-30, 31-60, 61-90, >90gg)
- Cruscotto finanziario con DSO/DPO, fatturato per cliente/tipologia
- Export scadenziario XLSX (openpyxl) e PDF (WeasyPrint)
- Cash flow previsionale e consuntivo
- Posizione debitoria/creditoria
- IVA trimestrale
- Riconciliazione bancaria (import CSV, matching transazioni)

### Correzioni e miglioramenti
- Counter atomico commesse (find_one_and_update su counters)
- Fix "preventivi riapparenti" su planning board (hidden_from_planning)
- Schema material_batches unificato + migrazione dati
- Fix crea_consegna -> push ddt_id su commessa
- Fix download DDT iframe (downloadPdfBlob)
- Alert email scadenze: skeleton backend implementato (IN PROGRESS)

## Backlog prioritizzato

### P0 — Critici
- Fix parser SDI XML per rate multiple (DettaglioPagamento multipli) e fallback condizioni pagamento fornitore

### P1 — Alta priorità
- Completare alert email giornalieri scadenze (template HTML, test invio Resend)
- Fix numerazione preventivi duplicati (atomic counter come commesse)

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
