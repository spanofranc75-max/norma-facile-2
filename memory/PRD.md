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
- Documenti globali (DURC, Visura, White List, Patente a Crediti, DVR) con scadenze persistenti (PATCH endpoint)
- Allegati Tecnici POS: Rumore, Vibrazioni, MMC con toggle "Includi nel POS"
- Risorse Umane + Matrice Scadenze + POS Wizard con selezione operai

### Dashboard Conformita Documentale (21 Mar 2026)
- Widget "Conformita Documentale" con pillole stato, alert 30gg, barre avanzamento commesse
- Scarica Fascicolo Aziendale (ZIP istantaneo)
- Validazione Preventiva Commessa (banner bloccante)
- Logo aziendale integrato nel PDF del Verbale di Posa

### Fix Preventivatore AI Predittivo (21 Mar 2026)
- Bug: lista preventivi mostrava anche quelli eliminati → filtro `status: {$ne: "eliminato"}`
- Bug: AI predittivo tutto a zero senza disegno → aggiunta "Stima Rapida Manuale"
- Backend: endpoint /calcola accetta `peso_kg_target` e genera materiale sintetico
- Frontend: Step 0 ora ha due percorsi: AI Vision upload OPPURE inserimento manuale peso+tipologia
- Calcolo realistico con prezzi storici (S275JR 1.15€/kg, zincatura 0.45€/kg), ore EUR/kg (1.00€/kg media)

### Verbale di Posa in Opera
- Pagina mobile-first, Lotti EN 1090, Checklist, Foto, Firma touch, PDF, Invia a CIMS (disabilitato)

### Test Data - Commessa Loiano
- Commessa: com_loiano_cims_2026 (NF-2026-LOIANO) — C.I.M.S SCRL
- FPC Project: prj_ee66232bbe9d (EXC2)

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
