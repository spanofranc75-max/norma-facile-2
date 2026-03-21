# NormaFacile 2.0 — PRD

## Problema Originale
ERP completo per carpenteria metallica con gestione EN 1090, EN 13241, ISO 3834.

## Architettura
- **Frontend**: React 18 + TailwindCSS + Shadcn/UI + Recharts
- **Backend**: FastAPI + Motor (MongoDB async)
- **AI**: emergentintegrations (GPT-4o Vision)
- **Auth**: Google OAuth (Emergent-managed)

## Moduli Implementati
- Core: Commesse, Clienti, Preventivi, DDT, Fatturazione, Diario Produzione, Fascicolo CE, Saldatori, WPS, Magazzino
- AI Vision Disegni, Preventivatore Predittivo, DoP Frazionata, SAL e Acconti, Conto Lavoro Avanzato
- KPI Dashboard + Calibrazione ML Predittiva
- Confronto AI vs Manuale
- Analisi AI Page con editing pesi live
- **Tracciabilita FPC completa** (creazione progetto da preventivo, dettaglio, controlli, CE)
- **Documenti Azienda** (DURC, Visura, White List, Patente a Crediti) nelle Impostazioni
- **Integrazione ZIP CSE** con documenti globali sicurezza

## Ultimo Completamento (21 Mar 2026)

**Bug Fix FPC + Feature Documenti Azienda:**
1. Bug FPC risolto: `batches.map is not a function` in FPCProjectPage.js — la risposta API `/api/fpc/batches` restituiva `{batches:[]}` invece di array diretto
2. Aggiunto bottone "Crea Progetto FPC" nella tab Progetti FPC con dialog per selezionare preventivo e classe di esecuzione
3. Creato progetto FPC Loiano (prj_ee66232bbe9d) da PRV-2026-0042 per CIMS SCRL
4. Implementata sezione Documenti Azienda nelle Impostazioni con 4 card: DURC, Visura, White List, Patente a Crediti
5. Integrati documenti globali sicurezza nel pacchetto ZIP CSE (sicurezza.py)
- Testing: 16/16 backend + 100% frontend (iteration_194)

## Credenziali Test
- User: user_97c773827822
- Session: sXLRQVAMtJAFhjM60UrZAjE_8wtJUdJ4sQQpbS5SFsY
- FPC Project: prj_ee66232bbe9d (Loiano)

## Route Principali
- /tracciabilita - Tracciabilita EN 1090 (Lotti, Saldatori, Progetti FPC)
- /tracciabilita/progetto/:projectId - Dettaglio progetto FPC
- /settings (tab Documenti) - Documenti Azienda DURC/Visura/WhiteList/Patente
- /analisi-ai/:prevId - Pagina Analisi AI con editing pesi
- /confronto?ai=X&man=Y - Report confronto AI vs Manuale
- /fpc -> redirect /tracciabilita
- /kpi - Dashboard KPI + Calibrazione ML

## Backlog
- (P1) Training automatico ML dal Diario di Produzione
- (P1) Alerting intelligente costi reali > budget
- (P2) Unificazione PDF legacy, Export Excel
- (P3) Portale clienti, RBAC granulare, Drag-and-Drop AI
