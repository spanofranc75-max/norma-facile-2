# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale per carpenteria metallica conforme EN 1090, EN 13241, ISO 3834. L'utente ha richiesto la gestione di 3 categorie di lavoro con workflow distinti e la struttura "Matrioska" per cantieri misti.

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

## Struttura Matrioska — Cantieri Misti (IMPLEMENTATO)
- Una Commessa è un "Fascicolo di Cantiere" che può contenere multiple "Voci di Lavoro"
- Ogni Voce ha la propria categoria normativa (EN_1090, EN_13241, GENERICA)
- Il pannello operativo mostra le sezioni dell'UNIONE di tutte le categorie presenti
- Il Diario di Produzione chiede "Su quale voce stai lavorando?" con bottoni grandi e colorati
- Campi adattivi: EN 1090 → N. colata + WPS | EN 13241 → Note collaudo | GENERICA → solo ore
- Retrocompatibilità: commesse senza voci extra funzionano come prima

## Cosa è stato implementato

### Sessioni precedenti
- Calcolo margini corretto
- Fix deployment Railway con nixpacks.toml
- Backend refactoring: commessa_ops.py → 6 moduli
- Frontend refactoring: CommessaOpsPanel.js → 8 sotto-componenti
- Responsive 12 pagine
- Pulizia codice morto

### Sessione 20 Marzo 2026
- FASE 1 COMPLETATA: Categorie di Lavoro (3 bottoni, campi condizionali, banner normativa)
- FASE 1.5 COMPLETATA: Voci di Lavoro backend (API CRUD) + frontend (VociLavoroSection)
- FASE 2 COMPLETATA: Diario Produzione Adattivo (selettore voce, campi specifici per categoria)
- CommessaOpsPanel fix: usa UNIONE categorie (hasEN1090, hasEN13241, isOnlyGenerica)
- Test: 100% backend (19/19) + 100% frontend (iteration_178)

## Backlog Prioritizzato

### P0 — Completato
- ~~FASE 1: Categorie di Lavoro~~
- ~~FASE 1.5: Voci di Lavoro (Matrioska)~~
- ~~FASE 2: Diario Produzione Adattivo~~

### P1 — Prossimi
- FASE 3: "Pulsante Magico" per generare pacchetto documenti specifico per categoria (PDF/ZIP)
- Vista "Officina" semplificata per operai (mobile-first, QR + PIN)
- Split di SettingsPage.js (1.731 righe)

### P2 — Importanti
- Split commesse.py (1.330 righe)
- Onboarding Wizard, Unificazione servizi PDF, Export Excel, RBAC granulare

### P3 — Futuri
- Firme digitali su PDF, Portale clienti read-only, Notifiche WhatsApp
