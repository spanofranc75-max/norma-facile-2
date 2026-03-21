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

### Sicurezza Operativa & Conformita
- **Canale AZIENDA**: Documenti globali (DURC, Visura, White List, Patente a Crediti, DVR) con scadenze persistenti (PATCH endpoint)
- **Allegati Tecnici POS**: Rumore, Vibrazioni, MMC con toggle "Includi nel POS" — auto-inclusi nello ZIP (05_ALLEGATI_POS/)
- **Canale PERSONALE**: Risorse Umane (/operai) — anagrafica operai + 8 tipi attestato sicurezza
- **Matrice Scadenze** (/operai/matrice) — tabella pallini colorati (verde/giallo/rosso/grigio)
- **POS Wizard Step 4**: Selezione operai + warning attestati + documenti globali

### Dashboard Conformita Documentale (21 Mar 2026)
- **Widget "Conformita Documentale"**: Pillole stato doc, badge problemi, previsione 30gg, barre avanzamento per commessa
- **Scarica Fascicolo Aziendale**: ZIP istantaneo con tutti i documenti aziendali + allegati POS organizzati in cartelle
- **Validazione Preventiva Commessa**: Banner rosso bloccante sulla pagina commessa se documenti mancanti/scaduti/insufficienti per la durata lavori
- **Commessa Compliance Check**: API che verifica se i documenti coprono la deadline della commessa
- Testing: Backend 21/21 (100%), Frontend 100% (iteration_199)

### Logo Aziendale (21 Mar 2026)
- Logo upload in Impostazioni (base64 in company_settings.logo_url)
- Logo integrato nel PDF del Verbale di Posa (sostituisce testo "STEEL PROJECT DESIGN")
- Legge da entrambe le collection: settings e company_settings

### Verbale di Posa in Opera
- Pagina mobile-first `/verbale-posa/:commessaId` — uso diretto in cantiere
- Lotti EN 1090 in evidenza: Tabella blu con N. Colata, Tipo, Cert. 3.1
- Checklist tecnica, Upload foto cantiere, Firma touch, PDF professionale
- Bottone "Invia a CIMS": Preparato (disabilitato), pronto per email integration

### Fix Persistenza Date (21 Mar 2026)
- PATCH endpoint per aggiornare scadenza senza re-upload file
- Alert scadenze: Badge verde (valido), giallo (<30gg), rosso (<15gg/scaduto), pulse critico
- Testing: Backend 21/21, Frontend 100% (iteration_198)

### Test Data - Commessa Loiano
- Commessa: com_loiano_cims_2026 (NF-2026-LOIANO) — C.I.M.S SCRL
- FPC Project: prj_ee66232bbe9d (EXC2)
- Lotti: A24-88731 (HEB 120), B24-92145 (IPE 160), F24-00287 (Bulloni M16)

## Credenziali Test
- User: user_97c773827822 (spano.franc75@gmail.com)
- Session: test_session_2026_active

## Backlog
- (P1) Integrazione email "Invia a CIMS" (SendGrid/Resend)
- (P1) Training automatico ML dal Diario di Produzione
- (P1) Alerting costi reali > budget
- (P2) Unificazione PDF legacy, Export Excel
- (P2) PDF Compliance dalla Matrice Scadenze
- (P3) Portale clienti, RBAC granulare, Drag-and-Drop AI, QR Code su documenti
