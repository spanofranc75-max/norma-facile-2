# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale per carpenteria metallica conforme EN 1090, EN 13241, ISO 3834. Struttura "Matrioska" per cantieri misti, vista officina blindata per operai, generazione automatica pacco documenti, smistatore intelligente certificati.

## Utenti Target
- **Titolare**: Gestione completa, costi, preventivi, pacco documenti
- **Responsabile produzione**: Diario, fasi, operatori
- **Responsabile qualità**: Fascicolo tecnico, certificati, tracciabilità
- **Operai officina**: Vista blindata (/officina) con timer, foto, checklist

## Architettura
- Frontend: React + TailwindCSS + Shadcn/UI
- Backend: FastAPI + MongoDB
- Auth: Google OAuth (admin) + PIN 4 cifre (operai)
- PDF: WeasyPrint + pypdf
- AI: emergentintegrations (GPT-4o Vision per analisi certificati)

## Implementato

### Fork 1 — Cantieri Misti
- Voci di Lavoro CRUD + CommessaOpsPanel unione categorie
- Diario Adattivo con selettore voce colorato

### Fork 2 — Vista Officina
- 4 Ponti: Timer START/PAUSA/STOP, Foto smart routing, Checklist 👍/👎, Blocco Dati
- PIN management, QR officina, Badge alert qualità

### Fork 3 — Pulsante Magico + Smistatore Intelligente
- **Pacco Documenti PDF** con struttura a Capitoli:
  - CAP. 1: STRUTTURE (EN 1090) — DoP, Certificati 3.1, WPS, Foto, Verbale
  - CAP. 2: CANCELLI (EN 13241) — Dichiarazione Conformità, Foto Sicurezze, Verbale
  - CAP. 3: RELAZIONE TECNICA — Riepilogo ore e materiali
- **Automazione verbali**: checklist OK → ESITO POSITIVO, NOK → ESITO NEGATIVO
- **Filtro Beltrami**: doc_page_index per certificati analizzati dall'AI
- **Firma tecnica** con disclaimer automatico + spazio firma manuale
- **Smistatore Intelligente** (`services/smistatore_intelligente.py`):
  - Analisi AI Vision pagina per pagina (GPT-4o)
  - Matching per numero colata con lotti materiale
  - Regola consumabili: filo ≥1.0mm → EN_1090, <1.0mm → EN_13241, gas → EN_1090
  - Indice invertito `doc_page_index` per ritaglio certificati
  - API: POST /api/smistatore/analyze/{doc_id}, GET /api/smistatore/index/{id}, GET /api/smistatore/scorte
- Test: 100% backend (26/26 — iteration_181)

## Backlog Prioritizzato

### P1 — Prossimi
- Integrazione frontend Smistatore (bottone "Analizza" nel repository documenti)
- Split SettingsPage.js (>1700 righe)
- DDT Multi-Commessa & Magazzino Scorte

### P2 — Importanti
- Split commesse.py (>1300 righe)
- Onboarding Wizard, Export Excel, RBAC granulare

### P3 — Futuri
- Firme digitali su PDF, Portale clienti, Notifiche WhatsApp
