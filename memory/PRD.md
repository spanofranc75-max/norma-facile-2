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
- Sopralluoghi AI con report e foto
- Rilievi misure con sketch pad e PDF
- Perizie sinistro con codici danno e report

### Modulo contabile/finanziario
- Import fatture SDI con deduplicazione robusta
- Scadenziario unificato attive+passive con aging
- Cruscotto finanziario con DSO/DPO
- Export XLSX/PDF
- Riconciliazione bancaria
- Alert email scadenze (job schedulato 24h)

### Stabilizzazione codebase
1. Atomic counter preventivi
2. Serializer MongoDB centralizzato
3. 18+ indici MongoDB + unique index fr_id
4. Paginazione su commesse, preventivi, DDT
5. Search globale (Ctrl+K)
6. Morning Briefing dashboard
7. Pulizia DB e backup produzione

### Audit Trail & Preferenze Notifiche (2026-03-08)
1. **Activity Audit Trail (P0)** — Sistema di logging per operazioni CRUD critiche
   - Servizio `services/audit_trail.py` con `log_activity()` fire-and-forget
   - API `GET /api/activity-log` con paginazione e filtri
   - API `GET /api/activity-log/stats` con statistiche
   - Pagina frontend `/registro-attivita`
   - Integrato in: clienti, commesse, preventivi, fatture, DDT, fatture ricevute, sopralluoghi, rilievi, perizie
   - 4 indici MongoDB per performance

2. **Preferenze Notifiche Email (P2)** — Configurazione utente per alert email
   - API `GET/PUT /api/notifications/preferences`
   - Tab "Notifiche" nella pagina Impostazioni
   - Scheduler aggiornato per rispettare opt-out e email personalizzata

3. **Backup Automatico Giornaliero (P2)** — Strategia backup automatizzata
   - Job schedulato nel loop scheduler (24h)
   - Conserva ultimi 7 backup automatici con cleanup
   - API `GET /api/admin/backup/history` per storico
   - UI nella tab Backup con sezione storico e badge Auto/Manuale

## Backlog prioritizzato

### P2 — Media priorita
- Firma digitale su PDF Perizia (tablet)
- Portale cliente read-only

### P3 — Bassa priorita / Futuro
- Analisi predittiva margini per preventivi
- Report PDF mensili automatizzati
- PWA per accesso offline
- Migrazione immagini Base64 -> object storage
- Refactoring CommessaOpsPanel.js
- AI Copilot per preventivi
- Gantt Chart per pianificazione produzione
- Webhook per SDI
