# NormaFacile 2.0 — CHANGELOG

## 2026-03-23 — Hardening & Stabilizzazione

### Hardening tecnico
- TD-001/002/004/005/009/010: fix critici DB, sicurezza, stabilita
- CR-001/002: code review e cleanup
- Data Integrity Check: tool admin con endpoint /run, /latest, /history
- +22 indici MongoDB su 15 collezioni (totale: 49)

### UX
- UX-001: CommessaHubPage semplificata (bug CostRow fixato via testing agent)
- UX-003: Onboarding primo utilizzo (checklist + SmartEmptyState)
- IntegrityWidget sulla Dashboard admin (semaforo DB health)

### Validation Sprint
- 22/22 test superati: 12 PDF + 1 DOCX + storage + tokens + error handling + SDI
- Confermato: SDI/FattureInCloud e core e attivo

## 2026-03-23 — Business Sprint

### Demo Mode
- POST /api/demo/login (cookie-based), POST /api/demo/reset, GET /api/demo/status
- 28 documenti seed in 10 collezioni: 3 commesse, 2 clienti, 3 preventivi, 7 obblighi, 1 cantiere
- Demo Guard: email e SDI simulati, nessuna azione esterna reale
- Banner ambra sticky, bottone "Prova la Demo" su landing
- Testing: 100% (17/17 backend + 5/5 frontend) — iteration_250

### Content Engine M1+M2
- Backend: CRUD sorgenti, generazione idee AI, bozze AI, coda editoriale, stats
- Frontend: /contenuti con 4 tab (Sorgenti, Idee, Bozze, Coda Editoriale)
- Nav: "Contenuti" sidebar admin-only
- 11 sorgenti seed reali con campi: code, category, value_claim, proof_points, suggested_formats
- Seed upsert: aggiorna sorgenti esistenti (non solo inserisce)
- Testing: 100% (16/16 backend + 100% frontend) — iteration_251

### Calibrazione prompt AI Content Engine
- 3 benchmark reali inseriti nel system message come riferimento stilistico:
  1. Registro Obblighi — problema operativo / controllo
  2. POS dinamico — trasformazione concreta prima/dopo
  3. Dashboard Cantiere — visione manageriale / executive
- Stile calibrato: frasi corte, lessico da cantiere, prodotto dopo il problema, CTA conversazionale
- Prompt idee: hook concreti, esempi buoni/cattivi
- Prompt bozze LinkedIn: struttura obbligatoria 6 passi + 3 benchmark completi come few-shot
- 3 bozze test rigenerate con qualita sensibilmente superiore

### Caso Studio Quantificato
- Pagina pubblica /caso-studio (no login, asset commerciale)
- 5 sezioni: Contesto, Problema prima, Cosa fa NormaFacile, Risultati, Cosa cambia
- 4 metriche prudenziali PRIMA/DOPO con disclaimer "stime operative interne — caso pilota"
- CTA: Prova la Demo + Torna alla Home
- Sorgente SRC_CASO_STUDIO_QUANTIFICATO nel Content Engine (11 totali)
- Testing: 100% (15/15 frontend) — iteration_252

### Copy to Clipboard
- DraftDetail: Copia tutto, Titolo, Corpo, CTA, Hashtag
- Toast feedback via sonner ("Copiato!")
- Hover copy su corpo testo e CTA
