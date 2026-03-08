# Norma Facile 2.0 — PRD

## Problema originale
Sistema ERP completo per azienda di carpenteria metallica. Gestione commesse, preventivi, fatture, DDT, approvvigionamento, produzione, conto lavoro, tracciabilita materiali EN 1090/EN 13241, generazione PDF, integrazione FattureInCloud, modulo contabile/finanziario.

## Lingua utente
Italiano

## Architettura
- **Frontend:** React + Shadcn/UI + TailwindCSS + Recharts (porta 3000)
- **Backend:** FastAPI + MongoDB + WeasyPrint + openpyxl (porta 8001)
- **Integrazioni:** Claude Sonnet 4, OpenAI GPT-4o Vision, Emergent Object Storage, Resend, FattureInCloud, Google Auth, react-pdf

## Funzionalita implementate

### Moduli core
- Gestione completa commesse, preventivi, fatture, DDT
- Approvvigionamento (RdP, OdA, arrivi materiale)
- Produzione (fasi, operatori, timeline)
- Conto lavoro (invio, rientro, verifica QC, NCR)
- Tracciabilita materiali EN 1090 (material_batches, lotti_cam)
- Generazione PDF: Super Fascicolo, Fascicolo Tecnico, DoP, DDT, NCR
- AI parsing certificati (OCR + analisi)

### Modulo contabile/finanziario (COMPLETATO 2026-03-08)
- Import fatture SDI: parsing multipli DettaglioPagamento, fallback 3 livelli, preview con scadenze
- Deduplicazione robusta: $or fingerprint + indice unique fr_id + lock anti-doppio-click
- Scadenziario unificato attive+passive con aging
- Cruscotto finanziario con DSO/DPO, fatturato per cliente/tipologia
- Export scadenziario XLSX/PDF
- Riconciliazione bancaria (import CSV, matching transazioni)
- Alert email scadenze (COMPLETATO): job schedulato 24h, template HTML, invio Resend, endpoint test manuale + preview

### Stabilizzazione codebase (2026-03-08)
1. Atomic counter preventivi (3 path: create, from-distinta, clone)
2. Serializer MongoDB centralizzato + fix _id:0
3. 18+ indici MongoDB + unique index fr_id
4. Paginazione su commesse, preventivi, DDT
5. Search globale (endpoint + componente React con debounce, Ctrl+K)
6. Morning Briefing dashboard (4 card)
7. Pulizia DB: duplicati rimossi, scadenze migrate, dati test eliminati
8. Backup DB per deploy produzione

### Audit Trail & Preferenze Notifiche (2026-03-08)
1. **Activity Audit Trail (P0)** - Sistema di logging per operazioni CRUD critiche
   - Servizio `services/audit_trail.py` con funzione `log_activity()` fire-and-forget
   - API `GET /api/activity-log` con paginazione e filtri (entity_type, action, user, date range, search)
   - API `GET /api/activity-log/stats` con statistiche (oggi, settimana, top users, top entities)
   - Pagina frontend `/registro-attivita` con tabella, filtri, statistiche
   - Integrato in: clienti, commesse, preventivi, fatture, DDT, fatture ricevute
   - Indici MongoDB su timestamp, entity_type, user_id, action
   - Voce sidebar sotto "Impostazioni > Registro Attivita"

2. **Preferenze Notifiche Email (P2)** - Configurazione utente per alert email
   - API `GET/PUT /api/notifications/preferences` per preferenze per-utente
   - Campi: email_alerts_enabled, alert_email, preavviso_giorni, alert_scadenze_pagamento, alert_qualita
   - Tab "Notifiche" nella pagina Impostazioni
   - Scheduler aggiornato per rispettare opt-out e email personalizzata

## Backlog prioritizzato

### P2 — Media priorita
- Firma digitale su PDF Perizia (tablet)
- Portale cliente read-only
- Strategia backup automatico DB

### P3 — Bassa priorita / Futuro
- Analisi predittiva margini per preventivi
- Report PDF mensili automatizzati
- PWA per accesso offline
- Migrazione immagini Base64 -> object storage
- Refactoring CommessaOpsPanel.js
- AI Copilot per preventivi
- Gantt Chart per pianificazione produzione
- Webhook per SDI (sostituzione upload manuale XML)
