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

### Sessioni precedenti
- Calcolo margini corretto (include costi manodopera da diario)
- Fix deployment Railway con nixpacks.toml
- Backend refactoring: commessa_ops.py → 6 moduli + wrapper (17/17 test)
- Dashboard, CommessaHubPage, DiarioProduzione, DashboardLayout resi responsive
- Indici DB ottimizzati (diario_produzione, operatori, sessions)

### Sessione corrente (20 Marzo 2026)
- **Frontend refactoring COMPLETATO**: CommessaOpsPanel.js da 2.964 → 161 righe
  - ApprovvigionamentoSection.js (568 righe)
  - ProduzioneSection.js (120 righe)
  - ConsegneSection.js (149 righe)
  - ContoLavoroSection.js (358 righe)
  - TracciabilitaSection.js (113 righe)
  - CAMSection.js (243 righe)
  - RepositoryDocumentiSection.js (369 righe)
  - Test: 100% (iteration_175)
- **Pulizia codice morto**: chat.py, documents.py + model eliminati
- **Responsive Fase 2 COMPLETATO**: 8 pagine rese mobile-friendly
  - PreventiviPage, ClientsPage, FornitoriPage, ArticoliPage
  - InvoicesPage, ScadenziarioPage, MarginAnalysisPage, CostControlPage
  - Pattern: flex-col sm:flex-row, hidden md:table-cell, overflow-x-auto, w-full sm:w-auto
  - Test: 100% desktop + mobile (iteration_176)

## Pagine già responsive (totale ~12)
Dashboard, CommessaHubPage, DiarioProduzione, DashboardLayout,
PreventiviPage, ClientsPage, FornitoriPage, ArticoliPage,
InvoicesPage, ScadenziarioPage, MarginAnalysisPage, CostControlPage

## Backlog Prioritizzato

### P1 — Urgenti
- Responsive per le restanti pagine (DDTEditorPage, DistintaEditorPage, PlanningPage, etc.)
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
