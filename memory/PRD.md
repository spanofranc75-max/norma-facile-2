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
- Confronto AI vs Manuale con endpoint /api/preventivatore/confronta

## Ultimo Completamento (21 Mar 2026)

**Blind Test corretto su feedback utente:**
- HEA 200 come pilastri 4m (non travi 12m) - CORRETTO
- Ore: metodo EUR/kg (1.05 EUR/kg speciale) → ~119h su 4200 kg (vs 110h manuale)
- Bulloneria: peso stimato (M16 ~0.5kg, M20 ~0.8kg) - CORRETTO
- Prompt AI migliorato: legge quote reali, distingue travi/pilastri
- Tabella ore speciale: 30h/ton (da 55h/ton)
- Confidence Score aggiornato: 95 Eccellente (-2.3% scostamento)
- Testing: iter_191 (15/15), iter_192 (17/17)

## Credenziali
- User: user_97c773827822
- Session: sXLRQVAMtJAFhjM60UrZAjE_8wtJUdJ4sQQpbS5SFsY
- Test: test_cal_2026

## Backlog
- (P1) Alerting intelligente costi reali > budget
- (P2) Unificazione PDF legacy
- (P2) Export Excel
- (P3) Portale clienti, RBAC granulare
