# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale per carpenteria metallica conforme EN 1090, EN 13241, ISO 3834. L'utente ha richiesto la gestione di 3 categorie di lavoro con workflow distinti.

## Utenti Target
- **Titolare carpenteria**: Gestione completa commesse, costi, preventivi
- **Responsabile produzione**: Diario produzione, fasi, operatori
- **Responsabile qualità**: Fascicolo tecnico, certificati, tracciabilità EN 1090
- **Operai officina**: Accesso semplificato al diario di produzione

## Architettura
- **Frontend**: React + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **Auth**: Google OAuth + JWT (via Emergent)
- **Hosting**: Railway (backend) + Vercel (frontend)
- **AI**: Emergent LLM Key per analisi certificati

## 3 Categorie di Lavoro (IMPLEMENTATO)
### A. STRUTTURALE (EN 1090)
- Tracciabilità lotti ferro (3.1), patentini saldatori, WPS
- Controllo qualità, DoP, Etichetta CE
- Sezioni: Tutte (Approvvigionamento, Produzione, Consegne, Conto Lavoro, Tracciabilità, CAM, Fascicolo Tecnico, Repository)

### B. CANCELLO (EN 13241)
- Kit sicurezza, foto fotocellule/coste
- Verbale collaudo forze, Manuale d'Uso
- Sezioni: Approvvigionamento, Produzione, Consegne, Conto Lavoro, Certificazione Cancello, Repository

### C. GENERICA (No Marcatura)
- Solo gestione ore e materiali
- Nessun obbligo burocratico
- Sezioni: Solo Produzione, Conto Lavoro, Repository

## Cosa è stato implementato

### Sessioni precedenti
- Calcolo margini corretto
- Fix deployment Railway con nixpacks.toml
- Backend refactoring: commessa_ops.py → 6 moduli
- Frontend refactoring: CommessaOpsPanel.js → 8 sotto-componenti
- Responsive 12 pagine
- Pulizia codice morto

### Sessione corrente (20 Marzo 2026)
- **FASE 1 COMPLETATA: Categorie di Lavoro**
  - 3 bottoni grandi nel modal creazione commessa (Strutturale/Cancello/Generica)
  - Campi condizionali: Classe EXC per EN 1090, Tipologia per EN 13241, solo info per Generica
  - CommessaOpsPanel nasconde sezioni non pertinenti alla categoria
  - Banner normativa nel hub commessa per tutte e 3 le categorie
  - NORMATIVA_CONFIG aggiornato con GENERICA
  - Test: 100% backend (13/13) + 100% frontend (iteration_177)

## Backlog Prioritizzato

### P0 — Prossime fasi del flusso categorie
- FASE 2: Diario Produzione adattivo (certificati per EN 1090, foto collaudo per EN 13241, solo ore per GENERICA)
- FASE 3: "Pulsante Magico" per generare pacchetto documenti specifico per categoria

### P1 — Urgenti
- Responsive per le restanti pagine
- Vista "Officina" semplificata per operai
- Split di SettingsPage.js (1.731 righe)

### P2 — Importanti
- Onboarding Wizard, Unificazione servizi PDF, Export Excel, RBAC granulare

### P3 — Futuri
- Firme digitali, Portale clienti, Notifiche WhatsApp
