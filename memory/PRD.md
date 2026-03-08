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

## Completato in questa sessione (2026-03-08)

### Tracciabilità e correzioni
1. Tracciabilità magazzino EN 1090 nel `preleva-da-magazzino`
2. Fix `normativa_tipo` in `link_certificato_to_materiale` (riga 488)
3. Counter atomico commesse (`find_one_and_update` su `counters`)
4. `$push moduli.ddt_ids` alla creazione consegna
5. Guard EN_13241 condizionale su `CommessaOpsPanel`
6. Auth Bearer su `GateCertificationPanel` downloads
7. `hide-from-planning` per preventivi + cascade su delete commessa
8. Fix download DDT iframe (`downloadPdfBlob`)
9. Fix `cert.get()` fallback con `or "—"` su gate_certification
10. Fix `handleDelete` Planning distingue preventivi da commesse

### Modulo contabile
11. Backend aging buckets (pagamenti + incassi) nel scadenziario/dashboard
12. Frontend ScadenziarioPage: vista unificata, filtri stato/tipo/periodo, aging colori, mark paid
13. Backend DSO/DPO + fatturato per cliente + fatturato per tipologia nel cruscotto
14. Frontend EBITDAPage: tab "Analisi" con DSO/DPO/fatturato/posizione debitoria
15. Export scadenziario XLSX con stili colori e totali
16. Export scadenziario PDF landscape con WeasyPrint

## Backlog prioritizzato

### P1
- Allineamento schema `material_batches` (unificare campi tra confirm-profili e link_certificato_to_materiale)
- Firma digitale su PDF Perizia (tablet)
- Riconciliazione bancaria → scadenza

### P2
- Portale cliente read-only
- Sostituzione immagini generiche PDF AI con foto reali
- Analisi predittiva margini per preventivi
- Report PDF mensili automatizzati
- PWA per accesso offline
- Migrazione immagini Base64 → object storage
- Refactoring CommessaOpsPanel.js (componente monolitico)
