# Norma Facile 2.0 — PRD

## Problema Originale
Applicazione gestionale per carpenteria metallica: gestione commesse, fatturazione, perizie, rilievi, preventivi, con integrazione FattureInCloud per fatturazione elettronica e SDI.

## Architettura
- **Frontend:** React + Tailwind + Shadcn/UI (Vercel)
- **Backend:** FastAPI + MongoDB Atlas (Railway)
- **Auth:** JWT cookie-based
- **Integrazioni:** FattureInCloud API v2, Resend, S3-compatible Storage

## Cosa è stato implementato

### Fix PDF Produzione — 19/03/2026
**Commit `b1e53f8` - Palette grigio chiaro:**
- Palette monocromatica grigio chiaro per pdf_invoice_modern.py e pdf_template.py
- Logo proporzionale con PIL (era forzato 150x50)
- Header tabella: sfondo #E8E8E8, testo #666666
- TOTALE box: sfondo #E0E0E0
- Bordi: #AAAAAA, testo: #555555

**Commit `aab6f27` - PDF viewer + DDT testo:**
- Fix pdf.js version mismatch (pdfjs-dist 3.11.174 → 5.4.296 per react-pdf@10.4.1)
- DDT: font tabella 8.5pt (era 7.5pt), padding migliore, etichette trasporto 8pt
- Template base: font 8.5pt per leggibilità
- Worker URL aggiornato (unpkg.com)

### Completamenti precedenti
- Rilievo Guidato (6 tipologie, 3D, calcolo materiali)
- Fatturazione completa (FT, NC, proforma)
- Fix critico SDI, Object Storage, clienti/fornitori
- Preventivi, DDT, saldatori, Super Fascicolo, Magazzino

## Backlog Prioritizzato

### P1
- Verifica visiva PDF dopo deploy Railway/Vercel
- Verifica sync fatture ricevute (sync-fic)

### P2
- RBAC (permessi/ruoli)
- Migrazione Base64 → Object Storage
- Refactoring unificazione servizi PDF

### P3
- Firma digitale PDF
- Portale cliente read-only
- AI Copilot preventivi
