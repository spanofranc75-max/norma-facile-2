# NormaFacile 2.0 — PRD

## Problema Originale
ERP completo per carpenteria metallica con gestione EN 1090, EN 13241, ISO 3834. Francesco vuole vendere l'app in abbonamento ad altri colleghi.

## Architettura
- **Frontend**: React 18 + TailwindCSS + Shadcn/UI + Recharts
- **Backend**: FastAPI + Motor (MongoDB async)
- **AI**: emergentintegrations (GPT-4o Vision)
- **Auth**: Google OAuth (Emergent-managed)
- **PDF**: WeasyPrint + qrcode (QR Code generation)

## Moduli Implementati
- Core: Commesse, Clienti, Preventivi, DDT, Fatturazione, Diario Produzione, Fascicolo CE, WPS, Magazzino
- AI Vision Disegni, Preventivatore Predittivo (+ Stima Rapida Manuale), DoP Frazionata, SAL e Acconti
- KPI Dashboard + Calibrazione ML Predittiva + Confronto AI vs Manuale
- Tracciabilita FPC completa (creazione progetto, dettaglio, controlli, CE)

### Sicurezza Operativa & Conformita
- Documenti globali (DURC, Visura, White List, Patente a Crediti, DVR) con scadenze persistenti
- Allegati Tecnici POS (Rumore, Vibrazioni, MMC) con toggle "Includi nel POS"
- Dashboard Conformita Documentale + Fascicolo Aziendale ZIP + Validazione Preventiva Commessa
- Risorse Umane + Matrice Scadenze + POS Wizard

### Verbale di Posa in Opera
- Mobile-first, Lotti EN 1090, Checklist, Foto, Firma touch, PDF con logo dinamico

### Manuale Utente PDF (21 Mar 2026)
- **Pagina "Guida all'Uso"** (/manuale) nel menu laterale: 7 capitoli navigabili con accordion
- **Sezione FAQ** con ricerca: 8 domande frequenti basate sui bug reali risolti
- **PDF professionale**: Copertina con logo, Indice, 7 Capitoli, Tabella FAQ, QR Code finale
- **White-label**: Il PDF usa il logo dell'azienda da company_settings (personalizzabile per ogni abbonato)
- **QR Code**: Nell'ultima pagina, punta al portale clienti
- Backend: `/api/manuale/contenuti` (JSON) + `/api/manuale/genera-pdf` (PDF 178KB)
- Testing: Backend 12/12, Frontend 100% (iteration_200)

### Fix AI Predittivo (21 Mar 2026)
- Stima Rapida Manuale: peso + tipologia → calcolo istantaneo senza disegno
- Filtro preventivi eliminati dalla lista

## Credenziali Test
- User: user_97c773827822 (spano.franc75@gmail.com)
- Session: test_session_2026_active

## Backlog
- (P1) Integrazione email "Invia a CIMS" (SendGrid/Resend)
- (P1) Training automatico ML dal Diario di Produzione
- (P1) Alerting costi reali > budget
- (P2) Unificazione PDF legacy, Export Excel
- (P2) PDF Compliance dalla Matrice Scadenze
- (P3) Portale clienti, RBAC granulare, QR Code su documenti
