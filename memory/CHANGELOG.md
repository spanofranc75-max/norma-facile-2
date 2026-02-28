# Norma Facile 2.0 - Changelog

## 2026-02-28 - Phase 41: EN 1090 FPC System
- Sistema completo Factory Production Control per tracciabilità EN 1090
- Registro Saldatori con qualifiche ISO 9606-1 e allarme scadenza
- Tracciabilità Materiali: lotti con numero colata, tipo materiale, certificato 3.1 (base64)
- Progetti FPC: conversione preventivo→progetto con classe EXC obbligatoria
- Assegnazione materiali a righe distinta con heat_number
- 7 controlli FPC (dimensionale, visivo, certificati, WPS, superfici, marcatura)
- Generazione etichetta CE con verifica blockers
- Frontend: /tracciabilita (3 tab) + /tracciabilita/progetto/:id
- Sidebar: link "Tracciabilità EN 1090" sotto Produzione
- Testing: 27/27 backend, 100% frontend (iteration_47)

## 2026-02-28 - Phase 40: PDF Template Unification
- Modulo condiviso `services/pdf_template.py` (CSS, header, totals, conditions)
- Fatture PDF riscritte da ReportLab a WeasyPrint con layout unificato
- DDT PDF riscritti da ReportLab a WeasyPrint con info trasporto + firme
- Preventivo refactored per usare modulo condiviso
- Font/colori/margini identici su tutti i documenti

## 2026-02-28 - Phase 39: PDF Preventivo Redesign
- Riscrittura completa generatore PDF preventivi (ReportLab → WeasyPrint HTML/CSS)
- Layout match esatto del PDF esempio utente (Steel Project Design Srls)
- Intestazione a 2 colonne: azienda (sx) + cliente con bordo (dx)
- Titolo PREVENTIVO centrato + numero documento
- Metadati: DATA, Pagamento, Validità, Nota di riferimento
- Tabella articoli 8 colonne con formattazione numeri italiana
- Dettaglio IVA breakdown + TOTALE IMPONIBILE + Totale IVA + Totale €
- Dati bancari + Condizioni di vendita + Sezione accettazione/firma
- Fix gestione valori None in tutti i campi dati
- Testing: 17/17 test passati (iteration_46)

## 2026-02-28 - Phase 38: Fix Indirizzo Tab + Storico Email
- BUG FIX: Tab "Indirizzo" nel dialog cliente non mostrava i campi
- Nuovo tab "Email Inviate" nella scheda cliente
- Endpoint GET /api/clients/{id}/email-log
- Testing: 100% (iteration_45)

## 2026-02-28 - Phase 37: Email Sending + SDI Integration
- Endpoint send-email per fatture, DDT, preventivi (Resend API)
- Endpoint send-sdi per fatture (validazione, in attesa chiavi)
- Pulsanti UI in tutti gli editor documenti
- Testing: 16/16 backend, 100% frontend (iteration_44)

## 2026-02-28 - Phase 36: Migrazione Configurazione Produzione
- Config centralizzata Pydantic Settings
- Resend email service migrato
- Aruba SDI + FattureInCloud API moduli pronti
- Tutte le variabili .env migrate dall'app vecchia
