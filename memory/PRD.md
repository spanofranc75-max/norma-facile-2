# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale per carpenteria metallica conforme EN 1090, EN 13241, ISO 3834. L'utente ha richiesto un'analisi approfondita dell'app seguita da stabilizzazione e refactoring del codice critico.

## Utenti Target
- **Titolare carpenteria**: Gestione completa commesse, costi, preventivi
- **Responsabile produzione**: Diario produzione, fasi, operatori
- **Responsabile qualità**: Fascicolo tecnico, certificati, tracciabilità EN 1090
- **Operai officina**: Accesso semplificato al diario di produzione

## Architettura
- **Frontend**: React + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **Auth**: Google OAuth + JWT
- **Hosting**: Railway (backend) + Vercel (frontend)
- **AI**: Emergent LLM Key per analisi certificati

## Cosa è stato implementato

### Sessione precedente
- Calcolo margini corretto (include costi manodopera da diario)
- Fix deployment Railway con nixpacks.toml
- Dashboard, CommessaHubPage, DiarioProduzione resi responsive
- Indici DB ottimizzati (diario_produzione, operatori, sessions)

### Sessione corrente (20 Marzo 2026)
- **Backend refactoring completato** (sessione precedente): commessa_ops.py → 6 moduli + wrapper
- **Frontend refactoring COMPLETATO**: CommessaOpsPanel.js da 2.964 righe a 161 righe (orchestratore)
  - ApprovvigionamentoSection.js (568 righe) — RdP, OdA, Arrivi, Prelievo, CertLink
  - ProduzioneSection.js (120 righe) — Fasi produzione + Diario
  - ConsegneSection.js (149 righe) — DDT + DoP + CE
  - ContoLavoroSection.js (358 righe) — Verniciatura, Zincatura, Sabbiatura
  - TracciabilitaSection.js (113 righe) — Tracciabilità EN 1090
  - CAMSection.js (243 righe) — Criteri Ambientali Minimi DM 256/2022
  - RepositoryDocumentiSection.js (369 righe) — Upload documenti + AI parsing
- **Pulizia codice morto COMPLETATA**: Eliminati placeholder chat.py, documents.py, relativi models e registrazioni router
- Test di regressione: 100% frontend + 100% backend (10/10)

## Backlog Prioritizzato

### P1 — Urgenti
- Responsive per le restanti 19 pagine dell'app
- Vista "Officina" semplificata per operai
- Split di SettingsPage.js (1.731 righe)

### P2 — Importanti
- Onboarding Wizard per nuovi utenti
- Unificazione 13 servizi PDF in un servizio unico
- Export Excel per analisi costi
- RBAC granulare (ruoli personalizzati)

### P3 — Futuri
- Firme digitali su PDF
- Portale clienti read-only
- Notifiche WhatsApp scadenze
