# Norma Facile 2.0 — PRD

## Problema originale
Sistema ERP completo per azienda di carpenteria metallica. Gestione commesse, preventivi, fatture, DDT, approvvigionamento, produzione, conto lavoro, tracciabilità materiali EN 1090, generazione PDF (Super Fascicolo, Fascicolo Tecnico, DoP), integrazione FattureInCloud, portale AI.

## Lingua utente
Italiano

## Architettura
- **Frontend:** React + Shadcn/UI + TailwindCSS (porta 3000)
- **Backend:** FastAPI + MongoDB (porta 8001)
- **Integrazioni:** Claude Sonnet 4, OpenAI GPT-4o Vision, Emergent Object Storage, Resend, FattureInCloud, Google Auth, react-pdf

## Funzionalità implementate
- Gestione completa commesse, preventivi, fatture, DDT
- Approvvigionamento (RdP, OdA, arrivi materiale)
- Produzione (fasi, operatori, timeline)
- Conto lavoro (invio, rientro, verifica QC, NCR)
- Tracciabilità materiali EN 1090 (material_batches, lotti_cam)
- Generazione PDF: Super Fascicolo, Fascicolo Tecnico, DoP, DDT, NCR
- AI parsing certificati (OCR + analisi)
- Download PDF iframe-safe (downloadPdfBlob con token temporaneo)
- Prelievo da magazzino con tracciabilità automatica
- Sistema notifiche, dashboard cruscotto, gestione clienti/fornitori

## Completato in questa sessione (2026-03-08)
1. **Tracciabilità materiali da magazzino (P0)** — Endpoint `preleva-da-magazzino` ora crea automaticamente `material_batch` e `lotto_cam` quando l'articolo prelevato ha metadati certificato (numero_colata/heat_number).
2. **Fix download PDF DDTEditorPage (Bug ricorrente)** — Sostituito `window.open` con `downloadPdfBlob` per compatibilità iframe.

## Backlog prioritizzato

### P0 (Completati)
- ~~Tracciabilità materiali da magazzino~~
- ~~Fix download PDF DDTEditorPage~~

### P1
- Allineamento schema `material_batches` (unificare campi tra confirm-profili e link_certificato_to_materiale)
- Firma digitale su PDF Perizia (tablet)
- Sostituzione immagini generiche PDF AI con foto reali installazioni

### P2
- Portale cliente read-only
- Analisi predittiva margini per preventivi
- Report PDF mensili automatizzati
- PWA per accesso offline
- Migrazione immagini Base64 → object storage
- Refactoring CommessaOpsPanel.js (componente monolitico)
