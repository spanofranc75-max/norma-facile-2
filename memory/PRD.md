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
- **Analisi AI Page** con editing pesi live (NUOVO)

## Ultimo Completamento (21 Mar 2026)

**Tre correzioni richieste dall'utente:**
1. Bottone "Analisi AI" aggiunto nella toolbar di ogni preventivo → naviga a /analisi-ai/:prevId
2. Pagina Analisi AI con editing pesi in tempo reale: click sul peso → campo input → aggiornamento live di tutti i costi (KPI cards, riepilogo, totali)
3. Bug FPC corretto: /fpc redirect a /tracciabilita (era "No routes matched")
- PUT /api/preventivi/:id aggiornato per accettare peso_totale_kg, ore_stimate, predittivo_data
- Testing: 16/16 backend + 100% frontend (iteration_193)

## Credenziali Test
- User: user_97c773827822
- Session: sXLRQVAMtJAFhjM60UrZAjE_8wtJUdJ4sQQpbS5SFsY
- Test: test_cal_2026

## Route Principali
- /analisi-ai/:prevId - Pagina Analisi AI con editing pesi
- /confronto?ai=X&man=Y - Report confronto AI vs Manuale
- /fpc → redirect /tracciabilita - Tracciabilita EN 1090
- /kpi - Dashboard KPI + Calibrazione ML

## Backlog
- (P1) Alerting intelligente costi reali > budget
- (P2) Unificazione PDF legacy, Export Excel
- (P3) Portale clienti, RBAC granulare
