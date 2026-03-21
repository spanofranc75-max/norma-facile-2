# NormaFacile 2.0 — PRD

## Problema Originale
ERP completo per carpenteria metallica con gestione EN 1090, EN 13241, ISO 3834.

## Architettura
- **Frontend**: React 18 + TailwindCSS + Shadcn/UI + Recharts
- **Backend**: FastAPI + Motor (MongoDB async)
- **AI**: emergentintegrations (GPT-4o Vision)
- **Auth**: Google OAuth (Emergent-managed)

## Moduli Implementati
- Core: Commesse, Clienti, Preventivi, DDT, Fatturazione, Diario Produzione, Fascicolo CE, WPS, Magazzino
- AI Vision Disegni, Preventivatore Predittivo, DoP Frazionata, SAL e Acconti, Conto Lavoro Avanzato
- KPI Dashboard + Calibrazione ML Predittiva
- Confronto AI vs Manuale, Analisi AI Page con editing pesi live
- Tracciabilita FPC completa (creazione progetto da preventivo, dettaglio, controlli, CE)

### Sicurezza Operativa (Completato 21 Mar 2026)
- **Canale AZIENDA**: Documenti globali (DURC, Visura, White List, Patente a Crediti, DVR) in Impostazioni → Documenti
- **Canale PERSONALE**: Risorse Umane (/operai) — anagrafica operai unificata con cassetti attestati sicurezza:
  - Patentino Saldatura, Formazione Base 81/08, Formazione Specifica Rischio Alto
  - Primo Soccorso, Antincendio, Lavori in Quota, PLE, Idoneita Sanitaria
- **Matrice Scadenze** (/operai/matrice) — tabella operai × attestati con pallini colorati (verde/giallo/rosso/grigio)
- **POS Wizard Step 4**: Selezione operai per cantiere con warning attestati + documenti azienda globali
- **Integrazione ZIP CSE**: Documenti globali inclusi automaticamente

## Credenziali Test
- User: user_97c773827822
- Session: active_test_session_2026
- FPC Project: prj_ee66232bbe9d (Loiano)
- Workers: wld_022030bdcf (Marco Bianchi), wld_811fabf3a1 (Luca Rossi), wld_1282360dd4 (Andrea Verdi)

## Route Principali
- /operai - Risorse Umane (anagrafica operai + attestati)
- /operai/matrice - Matrice Scadenze Aziendale
- /tracciabilita - Tracciabilita EN 1090 (Lotti, Saldatori, Progetti FPC)
- /tracciabilita/progetto/:projectId - Dettaglio progetto FPC
- /settings (tab Documenti) - Documenti Azienda DURC/Visura/WhiteList/Patente/DVR
- /pos/nuovo, /pos/:posId - POS Wizard 4 step con selezione operai
- /analisi-ai/:prevId - Analisi AI con editing pesi
- /confronto - Report confronto AI vs Manuale
- /kpi - Dashboard KPI + Calibrazione ML

## Backlog
- (P1) Training automatico ML dal Diario di Produzione
- (P1) Alerting intelligente costi reali > budget
- (P2) Unificazione PDF legacy, Export Excel
- (P3) Portale clienti, RBAC granulare, Drag-and-Drop AI
