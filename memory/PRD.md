# NormaFacile 2.0 — PRD

## Problema Originale
Gestionale per carpenteria metallica conforme EN 1090, EN 13241, ISO 3834. Struttura "Matrioska" per cantieri misti, vista officina blindata per operai, generazione automatica pacco documenti.

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

## Implementato

### Fork 1 (20/03/2026) — Cantieri Misti
- Voci di Lavoro backend + frontend (CRUD)
- CommessaOpsPanel: unione categorie
- Diario Adattivo: selettore voce + campi condizionali

### Fork 2 (20/03/2026) — Vista Officina
- 4 Ponti: Timer, Foto, Checklist, Blocco Dati
- PIN management, QR officina per voce
- Badge alert qualità in Dashboard

### Fork 3 (20/03/2026) — Pulsante Magico
- PDF unificato "Pacco Documenti Cantiere" con WeasyPrint
- Copertina + Indice + PARTE A (1090) + PARTE B (13241) + PARTE C (Generiche)
- Automazione verbale: checklist OK → CONFORME, NOK → NON CONFORME
- Filtro Beltrami: documenti filtrati per voce_id
- Firma tecnica con spazio firma manuale/digitale
- Test: 100% backend (14/14) + 100% frontend

### PROJECT_KNOWLEDGE.md aggiornato con:
- Logiche Smistatore Intelligente (certificati cumulativi Beltrami)
- DDT Multi-Commessa & Magazzino Scorte
- Regola Consumabili (Filo & Gas)
- Architettura Metadati + Indice Invertito

## Backlog Prioritizzato

### P1 — Prossimi
- **Fase 4: Smistatore Intelligente** — AI per certificati cumulativi, DDT multi-commessa, consumabili auto
- Split SettingsPage.js (>1700 righe)

### P2 — Importanti
- Split commesse.py (>1300 righe)
- Onboarding Wizard, Export Excel, RBAC granulare, Unificazione PDF

### P3 — Futuri
- Firme digitali, Portale clienti, Notifiche WhatsApp
