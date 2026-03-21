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
- Tracciabilita FPC completa (creazione progetto, dettaglio, controlli, CE)

### Sicurezza Operativa
- **Canale AZIENDA**: Documenti globali (DURC, Visura, White List, Patente a Crediti, DVR) con scadenze
- **Canale PERSONALE**: Risorse Umane (/operai) — anagrafica operai + 8 tipi attestato sicurezza
- **Matrice Scadenze** (/operai/matrice) — tabella pallini colorati (verde/giallo/rosso/grigio)
- **POS Wizard Step 4**: Selezione operai + warning attestati + documenti globali

### Verbale di Posa in Opera (21 Mar 2026)
- **Pagina mobile-first** `/verbale-posa/:commessaId` — uso diretto in cantiere
- **Lotti EN 1090 in evidenza**: Tabella blu con N. Colata, Tipo (Acciaio/Bulloneria), Cert. 3.1 in verde
- **Checklist tecnica**: 4 dichiarazioni pre-selezionate
- **Upload foto cantiere**: Drag-and-drop + camera access su mobile
- **Firma touch**: Canvas per firma cliente su tablet/cellulare
- **PDF professionale**: Header Steel Project Design, appendice lotti + DDT
- **Bottone "Invia a CIMS"**: Preparato (disabilitato), pronto per email integration
- **Accessibile da FPC Project** page tramite bottone dedicato
- Testing: Backend 14/14 (100%), Frontend 100% (iteration_197)

### Test Data - Commessa Loiano
- Commessa: com_loiano_cims_2026 (NF-2026-LOIANO) — C.I.M.S SCRL
- FPC Project: prj_ee66232bbe9d (EXC2)
- Lotti: A24-88731 (HEB 120, ArcelorMittal), B24-92145 (IPE 160, Riva), F24-00287 (Bulloni M16, Fontana)
- Workers: wld_022030bdcf (Marco Bianchi), wld_811fabf3a1 (Luca Rossi), wld_1282360dd4 (Andrea Verdi)

## Credenziali Test
- User: user_97c773827822
- Session: active_test_session_2026

## Backlog
- (P1) Integrazione email "Invia a CIMS" (SendGrid/Resend)
- (P1) Training automatico ML dal Diario di Produzione
- (P1) Alerting costi reali > budget
- (P2) Upload logo aziendale (per Verbale/POS/Preventivi)
- (P2) Unificazione PDF legacy, Export Excel
- (P3) Portale clienti, RBAC granulare, Drag-and-Drop AI
