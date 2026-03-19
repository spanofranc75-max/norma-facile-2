# Norma Facile 2.0 — PRD

## Problema Originale
Applicazione gestionale per carpenteria metallica: gestione commesse, fatturazione, perizie, rilievi, preventivi, con integrazione FattureInCloud per fatturazione elettronica e SDI.

## Architettura
- **Frontend:** React + Tailwind + Shadcn/UI (Vercel)
- **Backend:** FastAPI + MongoDB Atlas (Railway)
- **Auth:** JWT cookie-based
- **Integrazioni:** FattureInCloud API v2, Resend, S3-compatible Storage

## Cosa è stato implementato

### Fix PDF Produzione — Grigio Chiaro — 19/03/2026
- Pushed commit `b1e53f8` al repo `spanofranc75-max/norma-facile-2`
- **Palette grigio chiaro** applicata a `pdf_invoice_modern.py` e `pdf_template.py`
- **Logo proporzionale** con PIL (era 150x50 fisso, ora bounding box 120x60)
- **Header tabella**: sfondo #E8E8E8 + testo #666666 (era bianco su #0F172A)
- **TOTALE box**: sfondo #E0E0E0 (era bianco su navy scuro)
- **Bordi**: #AAAAAA e #D5D5D5 (era #2563EB blu)
- **Testo**: #555555 corpo, #666666 titoli, #888888 secondario
- Zero colori navy/blu/neri nei 3 generatori PDF

### Completamenti precedenti
- Rilievo Guidato (6 tipologie, 3D viewer, calcolo materiali)
- Fatturazione completa (FT, NC, proforma)
- Fix critico SDI (json.dumps default=str)
- Object Storage, gestione clienti/fornitori, preventivi, DDT
- Modulo saldatori, Super Fascicolo, Magazzino

## Backlog Prioritizzato

### P1
- Conferma visiva PDF in produzione dopo deploy Railway
- Verifica sync fatture ricevute (sync-fic)

### P2
- RBAC (permessi/ruoli)
- Migrazione Base64 → Object Storage
- Refactoring unificazione servizi PDF

### P3
- Firma digitale PDF Perizia
- Portale cliente read-only
- AI Copilot per preventivi
