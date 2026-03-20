# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale per carpenteria metallica conforme EN 1090, EN 13241, ISO 3834. Struttura "Matrioska" per cantieri misti, con vista officina blindata per operai.

## Utenti Target
- **Titolare carpenteria**: Gestione completa commesse, costi, preventivi
- **Responsabile produzione**: Diario produzione, fasi, operatori
- **Responsabile qualità**: Fascicolo tecnico, certificati, tracciabilità
- **Operai officina**: Vista blindata (/officina) con timer, foto, checklist

## Architettura
- **Frontend**: React + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **Auth**: Google OAuth (admin) + PIN 4 cifre (operai)
- **Hosting**: Railway (backend) + Vercel (frontend)

## 3 Categorie di Lavoro (IMPLEMENTATO)
### A. STRUTTURALE (EN 1090) → Tracciabilità, WPS, DoP, CE
### B. CANCELLO (EN 13241) → Kit sicurezza, collaudo, manuale
### C. GENERICA (No CE) → Solo ore e materiali

## Struttura Matrioska — Cantieri Misti (IMPLEMENTATO)
- Commessa contiene multiple Voci di Lavoro
- Pannello operativo mostra UNIONE di tutte le categorie
- Diario adattivo con selettore voce colorato
- Retrocompatibilità con commesse mono-categoria

## Vista Officina — 4 Ponti (IMPLEMENTATO 20/03/2026)
### PONTE 1: DIARIO (Timer)
- 3 bottoni grandi: START (verde), PAUSA (giallo), STOP (rosso)
- Timer visivo che scorre, nessun numero di costo visibile
- STOP → salva automaticamente minuti nel diario produzione della commessa
- Stato timer persistito in DB (sopravvive a refresh browser)

### PONTE 2: FOTO (Certificati/Collaudi)
- Singolo bottone FOTO grande circolare
- Routing intelligente basato su voce attiva:
  - EN 1090 → tipo "certificato_31" (Repository certificati 3.1)
  - EN 13241 → tipo "foto" (Fascicolo tecnico)
  - GENERICA → tipo "foto" (Repository documenti)
- Nome file chiaro: FOTO_{normativa}_{numero_commessa}_{timestamp}.jpg

### PONTE 3: QUALITÀ (Checklist)
- Icone + 👍/👎 per ogni punto di controllo
- EN 1090: Saldature Pulite, Dimensioni OK, Materiale OK
- EN 13241: Sicurezze OK, Movimento OK
- GENERICA: Lavoro Completato
- 👎 → crea alert automatico per Admin (badge rosso dashboard)

### PONTE 4: BLOCCO DATI
- Operaio intrappolato in /officina — nessuna navigazione
- Nessun menu, nessun link a fatture/clienti/fornitori
- Accesso: QR Code + PIN 4 cifre
- QR generabile dalla CommessaHubPage per commessa o voce specifica

## Implementato — Cronologia

### Pre-fork
- Calcolo margini, deployment Railway, backend refactoring
- Frontend refactoring CommessaOpsPanel (8 sotto-componenti)
- Responsive 12 pagine, pulizia codice morto

### Fork 1 (20/03/2026)
- Categorie di lavoro, Voci di Lavoro (Matrioska)
- Diario Produzione Adattivo (selettore voce, campi condizionali)
- CommessaOpsPanel: usa UNIONE categorie

### Fork 2 (20/03/2026) — Corrente
- Vista Officina completa con 4 Ponti
- Backend: /api/officina/* (PIN, timer, foto, checklist, alerts)
- Frontend: OfficinaPage.js (tema dark, mobile-first)
- PIN management inline nel DiarioProduzione
- QR dialog aggiornato con link officina per voce
- Badge alert qualità nella Dashboard admin

## Backlog Prioritizzato

### P1 — Prossimi
- FASE 3: "Pulsante Magico" — generazione pacchetto documenti per cantiere (PDF/ZIP)
- Split SettingsPage.js (>1700 righe)

### P2 — Importanti
- Split commesse.py (>1300 righe)
- Onboarding Wizard, Unificazione servizi PDF, Export Excel
- RBAC granulare

### P3 — Futuri
- Firme digitali su PDF, Portale clienti read-only
- Notifiche WhatsApp scadenze

## DB Collections
- `commesse`, `voci_lavoro`, `diario_produzione`, `operatori`
- `commessa_documents`, `officina_timers`, `officina_checklist`, `officina_alerts`
