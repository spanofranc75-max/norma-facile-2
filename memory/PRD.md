# NormaFacile 2.0 — PRD

## Problema Originale
ERP completo per carpenteria metallica con gestione EN 1090, EN 13241, ISO 3834. Francesco vuole vendere l'app in abbonamento SaaS.

## Architettura
- **Frontend**: React 18 + TailwindCSS + Shadcn/UI + Recharts
- **Backend**: FastAPI + Motor (MongoDB async)
- **AI**: emergentintegrations (GPT-4o Vision)
- **Auth**: Google OAuth (Emergent-managed)
- **PDF**: WeasyPrint + qrcode
- **Multi-normativa**: voci_lavoro con normativa_tipo per riga (EN_1090, EN_13241, GENERICA)

## Moduli Implementati

### Flusso EN 1090 completo (testato con stress test RINA)
1. Perizia AI → Preventivo → Commessa EN_1090 EXC2
2. Riesame Tecnico (12 checks auto, safety gate bloccante)
3. Registro Saldatura + Tracciabilita Materiali
4. Controllo Finale + Report Ispezioni VT/DIM
5. DOP + Etichetta CE automatica
6. Scadenziario Manutenzioni + Verbali ITT

### Dashboard Executive Multi-Normativa (21 Mar 2026)
- `GET /api/dashboard/executive` — vista aggregata 3 settori
- **EN 1090**: indice rischio normativo, audit-ready count, riesame/ispezioni/controllo/DOP status
- **EN 13241**: stesse metriche per chiusure
- **GENERICA**: efficienza produttiva dalle fasi_produzione
- **Commesse miste**: voci_lavoro con normative diverse → commessa appare in piu settori con badge MISTA
- **Scadenze imminenti**: patentini + tarature + ITT aggregati con urgenza colorata
- **Frontend**: `/executive` — 3 sezioni settore, KPI cards, alert scadenze, click→CommessaHub
- Test: iteration 211 — 20/20 backend + 100% frontend

### Sopralluoghi + Perizie + Preventivatore (testati iteration 210)
- 36/36 endpoint testati — CRUD, PDF, genera-preventivo, accetta→commessa
- AI endpoints (GPT-4o Vision) verificati con dati esistenti

## Test Eseguiti
- Iteration 206: DOP/CE — 12/12
- Iteration 207: Scadenziario/ITT — 19/19
- Iteration 208: E2E integration (10 flussi) — 34/34
- Iteration 209: STRESS TEST RINA (4 scenari) — 28/28
- Iteration 210: Sopralluoghi/Perizie/Preventivatore — 36/36
- Iteration 211: Executive Dashboard Multi-Normativa — 20/20

## Backlog

### P1 — Prossimi (dalla richiesta utente)
- Riesame Tecnico Selettivo: attivare check solo per righe normate (EN 1090/13241), bypassare per generiche
- Verbali Prova EN 13241: forze cancello, fotocellule, bordi sensibili
- Sistema Notifiche Proattive: email 30gg/7gg/scadenza per patentini/tarature
- Ponte Perizie → Preventivatore: flusso automatico dati AI perizia → righe preventivo

### P2 — Miglioramenti
- Multi-Tenant: tenant_id su ogni collection + middleware isolamento
- Training ML dal Diario Produzione
- Alerting costi > budget

### P3 — Backlog Generale
- Unificazione PDF legacy, Portale clienti, RBAC, QR Code, Export Excel
- Split file grandi (SettingsPage.js, commesse.py)
