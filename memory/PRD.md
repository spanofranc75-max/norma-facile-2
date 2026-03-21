# NormaFacile 2.0 — PRD

## Problema Originale
ERP completo per carpenteria metallica con gestione EN 1090, EN 13241, ISO 3834. Include commesse, certificazioni, preventivi, DDT, fatturazione, produzione, qualifica saldatori, WPS/WPQR e analisi costi.

## Utenti Target
- Titolari/responsabili carpenteria metallica
- Responsabili qualita e produzione

## Architettura
- **Frontend**: React 18 + TailwindCSS + Shadcn/UI + Recharts
- **Backend**: FastAPI + Motor (MongoDB async)
- **AI**: emergentintegrations (GPT-4o Vision)
- **Auth**: Google OAuth (Emergent-managed)
- **PDF**: WeasyPrint

## Moduli Implementati

### Core
- Commesse, Clienti, Preventivi, DDT, Fatturazione
- Diario di Produzione, Fascicolo Tecnico CE
- Qualifica Saldatori + WPS/WPQR, Magazzino

### Moduli Avanzati
- **AI Vision Disegni**: Analisi automatica disegni con GPT-4o
- **Preventivatore Predittivo**: Wizard AI per stime automatiche
- **DoP Frazionata**, **SAL e Acconti**, **Conto Lavoro Avanzato**
- **KPI Dashboard**: Metriche + Confidence Score
- **Confronto AI vs Manuale**: Report delta riga per riga + insights
- **Calibrazione ML Predittiva**: Apprendimento automatico da progetti completati

### Ultimo Completamento (21 Mar 2026)

**Blind Test Preventivatore Predittivo:**
- Analisi autonoma disegno "Solaio Carpenteria A2" (Sasso Marconi)
- Materiali estratti: IPE 270, HEA 200, Piastre 15/20mm, Bulloneria M16/M20
- Prezzi storici DDT: S275 1.15/kg, Piastre 1.30/kg, Zinc 0.45/kg, Bulloni 4.50/kg
- Margini: Materiali 15%, Manodopera 40%, C/L 10%
- PV-2026-0045-AI generato (32.038 vs 14.536 manuale)
- Endpoint POST /api/preventivatore/confronta + pagina /confronto
- Testing: 15/15 backend + 100% frontend (iteration_191)

**Sistema ML Calibrazione Predittiva:**
- 10 progetti storici completati usati per training
- Fattori correttivi pesati per similarita (peso 50%, classe 25%, nodi 15%, tipo 10%)
- Accuracy Pre-ML: 89% -> Post-ML: 90.7% (+1.7%)
- API: /api/calibrazione/status, calcola-fattori, applica, feedback
- Integrato nel preventivatore: applica_calibrazione=true
- Pannello ML nella KPI Dashboard con grafico evoluzione
- Testing: 17/17 backend + 100% frontend (iteration_192)

## Credenziali Test
- User: spano.franc75@gmail.com (user_97c773827822)
- Session: sXLRQVAMtJAFhjM60UrZAjE_8wtJUdJ4sQQpbS5SFsY
- Test session: test_cal_2026
- Operatori: Ahmed (PIN 1234), Karim (PIN 5678)

## API Key Endpoints
- /api/preventivatore/confronta (POST) - Confronto AI vs Manuale
- /api/calibrazione/status (GET) - Stato calibrazione ML
- /api/calibrazione/calcola-fattori (POST) - Fattori per target
- /api/calibrazione/applica (POST) - Applica calibrazione a stima
- /api/calibrazione/feedback (POST) - Registra progetto completato

## Task Futuri (Backlog)
- (P1) Sistema alerting intelligente (costi reali > budget 10%)
- (P2) Unificazione 13 servizi PDF legacy
- (P2) Export Excel analisi costi
- (P3) Portale clienti read-only
- (P3) RBAC granulare
