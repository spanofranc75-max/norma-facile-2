# NormaFacile 2.0 — PRD

## Problema Originale
ERP completo per carpenteria metallica con gestione EN 1090, EN 13241, ISO 3834. Include commesse, certificazioni, preventivi, DDT, fatturazione, produzione, qualifica saldatori, WPS/WPQR e analisi costi.

## Utenti Target
- Titolari/responsabili carpenteria metallica
- Responsabili qualità e produzione

## Requisiti Core
- Gestione commesse con fascicolo tecnico CE
- Tracciabilità materiali EN 10204
- Qualifica saldatori e WPS
- Preventivazione automatica e manuale
- DDT e fatturazione elettronica
- Diario di produzione
- Certificazioni e DoP

## Architettura
- **Frontend**: React 18 + TailwindCSS + Shadcn/UI + Recharts
- **Backend**: FastAPI + Motor (MongoDB async)
- **AI**: emergentintegrations (GPT-4o Vision)
- **Auth**: Google OAuth (Emergent-managed)
- **PDF**: WeasyPrint

## Moduli Implementati

### Core (Completati)
- Gestione Commesse, Clienti, Preventivi
- DDT (vendita/acquisto/conto lavoro)
- Fatturazione attiva/passiva
- Diario di Produzione con timer
- Fascicolo Tecnico CE
- Qualifica Saldatori + WPS/WPQR
- Magazzino con tracciabilità lotti

### Moduli Avanzati (Completati)
- **AI Vision Disegni**: Analisi automatica disegni tecnici con GPT-4o
- **Preventivatore Predittivo**: Wizard AI che analizza disegni → estrae materiali → calcola costi → genera preventivo
- **DoP Frazionata**: Generazione dichiarazioni di prestazione per lotti parziali
- **SAL e Acconti**: Gestione stati avanzamento lavori
- **Conto Lavoro Avanzato**: Certificati trattamento automatici
- **KPI Dashboard**: Metriche e Confidence Score (Recharts)
- **Confronto AI vs Manuale**: Report dettagliato con delta riga per riga, confidence score, insights AI

### Ultimo Completamento (21 Mar 2026)
- **Blind Test Preventivatore Predittivo**:
  - Analisi autonoma disegno "Solaio Carpenteria A2" (Sasso Marconi)
  - Estrazione materiali: IPE 270, HEA 200, Piastre 15/20mm, Bulloneria M16/M20
  - Calcolo costi con prezzi storici DDT (S275: 1.15€/kg, Piastre: 1.30€/kg, Zinc: 0.45€/kg, Bulloni: 4.50€/kg)
  - Margini applicati: Materiali 15%, Manodopera 40%, C/L 10%
  - Preventivo AI PV-2026-0045-AI generato (€32.038,38 vs Manuale €14.535,64)
  - Endpoint POST /api/preventivatore/confronta creato e testato
  - Frontend /confronto con gauge, KPI cards, tabella categorie, tabella righe, osservazioni AI
  - Testing: 15/15 backend + 100% frontend (iteration_191)

## Credenziali Test
- User: spano.franc75@gmail.com (user_97c773827822)
- Session: ryz-fOEx6ZwaCAXAV6zySsdMQjiayNpQgmkGzvO2wHI
- Test session: test_blind_2026
- Operatori: Ahmed (PIN 1234), Karim (PIN 5678)

## Task Futuri (Backlog)
- (P1) Sistema alerting intelligente (costi reali > budget 10%)
- (P2) Unificazione 13 servizi PDF legacy
- (P2) Export Excel analisi costi
- (P3) Portale clienti read-only
- (P3) RBAC granulare
