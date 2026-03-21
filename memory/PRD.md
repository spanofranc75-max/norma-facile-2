# NormaFacile 2.0 — PRD

## Problema Originale
ERP completo per carpenteria metallica con gestione EN 1090, EN 13241, ISO 3834.

## Architettura
- **Frontend**: React 18 + TailwindCSS + Shadcn/UI + Recharts
- **Backend**: FastAPI + Motor (MongoDB async)
- **AI**: emergentintegrations (GPT-4o Vision)
- **Auth**: Google OAuth (Emergent-managed)
- **PDF**: WeasyPrint

## Moduli Implementati
- Core: Commesse, Clienti, Preventivi, DDT, Fatturazione, Diario Produzione, Fascicolo CE, WPS, Magazzino
- AI Vision Disegni, Preventivatore Predittivo, DoP Frazionata, SAL e Acconti, Conto Lavoro Avanzato
- KPI Dashboard + Calibrazione ML Predittiva
- Confronto AI vs Manuale, Analisi AI Page con editing pesi live
- Tracciabilita FPC completa (creazione progetto da preventivo, dettaglio, controlli, CE)

### Sicurezza Operativa
- **Canale AZIENDA**: Documenti globali (DURC, Visura, White List, Patente a Crediti, DVR) con scadenze
- **Canale PERSONALE**: Risorse Umane (/operai) — anagrafica operai + 8 tipi attestato sicurezza
- **Matrice Scadenze** (/operai/matrice) — tabella pallini colorati
- **POS Wizard Step 4**: Selezione operai + warning attestati

### Verbale di Posa in Opera (Completato 21 Mar 2026)
- **Pagina dinamica** `/verbale-posa/:commessaId` con caricamento automatico dati commessa
- **Materiali**: Tabella materiali dalla commessa con lotti EN 1090 (n. colata, dimensioni, cert 3.1)
- **Checklist tecnica**: 4 dichiarazioni pre-selezionate (regola d'arte, conformita, materiali, sicurezza)
- **Upload foto**: Drag-and-drop per 2-3 foto cantiere
- **Firma touch**: Canvas per firma grafica del cliente su tablet/cellulare
- **PDF professionale**: Nome `Verbale_Posa_CODICE_DATA.pdf`, header Steel Project Design, appendice lotti/DDT
- **Bottone "Invia a CIMS"**: Preparato (disabilitato), pronto per integrazione email
- Testing: Backend 13/13, Frontend 95%→100% (fix navigazione FPC)

## Credenziali Test
- User: user_97c773827822
- Session: active_test_session_2026
- FPC Project: prj_ee66232bbe9d (Loiano)
- Test commessa: com_e8c4810ad476 (NF-2026-000001)

## Route Principali
- /operai, /operai/matrice - Risorse Umane + Matrice Scadenze
- /tracciabilita - Tracciabilita EN 1090
- /tracciabilita/progetto/:id - Dettaglio FPC
- /verbale-posa/:commessaId - Verbale di Posa in Opera
- /settings (Documenti) - Documenti Azienda
- /pos/nuovo, /pos/:id - POS Wizard 4 step
- /analisi-ai/:id, /confronto, /kpi - AI + KPI

## Backlog
- (P1) Training automatico ML dal Diario di Produzione
- (P1) Alerting costi reali > budget
- (P1) Integrazione email per invio CIMS
- (P2) Unificazione PDF legacy, Export Excel
- (P2) Upload logo aziendale in Impostazioni (per Verbale/POS/Preventivi)
- (P3) Portale clienti, RBAC granulare, Drag-and-Drop AI
