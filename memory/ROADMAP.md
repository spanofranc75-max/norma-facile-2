# NormaFacile 2.0 — ROADMAP

## Legenda Priorità
- **P0**: Bloccante, da risolvere subito
- **P1**: Importante, prossimo sprint
- **P2**: Miglioramento significativo
- **P3**: Nice-to-have / futuro

---

## CRITICITÀ DA RISOLVERE (Stabilità)

### Backend — Debito Tecnico
- [ ] **P1** Spezzare `commessa_ops.py` (3.430 righe) in sotto-moduli:
  - `routes/approvvigionamento.py` (richieste preventivo, ordini, arrivi)
  - `routes/produzione.py` (fasi, init produzione)
  - `routes/conto_lavoro.py` (lavorazioni esterne)
  - `routes/repository_documenti.py` (upload, gestione file)
- [ ] **P1** Spezzare `fatture_ricevute.py` (2.448 righe) in:
  - `routes/fatture_ricevute.py` (CRUD)
  - `services/xml_parser.py` (parsing XML fatture)
  - `services/fic_sync.py` (sincronizzazione FattureInCloud)
- [ ] **P2** Unificare 13 servizi PDF in un `BasePDFService` condiviso (header, footer, stili, tabelle)
- [ ] **P2** Rimuovere placeholder vuoti: `chat.py`, `documents.py` (restituiscono 501)
- [ ] **P2** Rimuovere collezioni MongoDB vuote e inutilizzate: `vendor_catalogs`, `vendor_keys`, `user_profiles`, `catalogo_profili`
- [ ] **P3** Eliminare `pdf_template.py` (v1 obsoleto, sostituito da `pdf_template_v2.py`)

### Frontend — Debito Tecnico
- [ ] **P1** Spezzare `CommessaOpsPanel.js` (2.959 righe) in sotto-componenti:
  - `ApprovvigionamentoPanel.js`
  - `ProduzionePanel.js`
  - `ContoLavoroPanel.js`
  - `RepositoryDocumentiPanel.js`
  - `ConsegnePanel.js`
- [ ] **P1** Spezzare `SettingsPage.js` (1.731 righe) in tab separati
- [ ] **P2** Responsive per le restanti 19 pagine (33/52 già responsive)
- [ ] **P2** Aggiungere test frontend (attualmente 0 test)

### Database
- [ ] **P2** Verificare e completare indici sulle collezioni principali con query lente
- [ ] **P3** Script di migrazione per immagini Base64 legacy → object storage

### Auth & Sicurezza
- [ ] **P2** Semplificare dual-auth (Emergent + Google OAuth) — ogni modifica è fragile
- [ ] **P3** Sistema RBAC avanzato con permessi granulari per modulo

---

## IDEE E FUNZIONALITÀ FUTURE (Post-Stabilità)

### UX / Esperienza Utente
- [ ] **P1** **Vista "Officina" semplificata** — Pagina dedicata per operai: solo Diario Produzione + Fasi attive. Accesso diretto da mobile senza navigare 30 menu. Potrebbe essere il punto di ingresso dopo login per ruolo "officina"
- [ ] **P1** **Onboarding wizard** — Primo accesso guidato: "Crea la tua prima commessa in 3 minuti". Con dati pre-compilati di esempio cliccabili
- [ ] **P2** **Dark mode** — La sidebar è già dark, il contenuto è light. Toggle dark/light mode
- [ ] **P2** **Menu sidebar personalizzabile** — Possibilità di nascondere sezioni non usate, ordinare per flusso di lavoro
- [ ] **P3** **Demo interattiva** dalla landing page con dati finti navigabili

### Fiscale / Contabilità
- [ ] **P2** **Registro IVA formale** (acquisti/vendite) — oggi l'IVA è calcolata dalla somma fatture, manca il registro per il commercialista
- [ ] **P2** **Costo orario per mansione** — oggi c'è un unico costo orario aziendale. Un saldatore costa diverso da un montatore
- [ ] **P2** **Export mensile per commercialista** — PDF/Excel con IVA, fatturato, costi, margini automatico
- [ ] **P3** **Import cedolini** per costi reali del personale (oggi si usa il costo orario stimato)
- [ ] **P3** **Gestione ritenuta d'acconto** sulle fatture ricevute da professionisti
- [ ] **P3** **Riconciliazione bancaria** — la collezione `movimenti_bancari` esiste ma è vuota

### Normativo (EN 1090 / EN 13241 / ISO 3834)
- [ ] **P2** **Classe di esecuzione (EXC) che guida i requisiti** — EXC3 deve forzare controlli aggiuntivi che EXC2 non richiede
- [ ] **P2** **Popolare moduli normativi mai usati**: WPS (0 doc), saldatori (0 doc), FPC Projects (0 doc), distinte (0 doc), certificazioni CE (0 doc)
- [ ] **P3** **DUVRI** per cantieri con interferenze (subappalti)
- [ ] **P3** **Firme digitali** sui report PDF

### Integrazioni & Comunicazione
- [ ] **P2** **Notifiche WhatsApp** per scadenze (saldatori, strumenti, pagamenti) — tasso apertura 10x rispetto email
- [ ] **P3** **Collegamento Cassetto Fiscale** per check automatico stato fatture SDI
- [ ] **P3** **API pubblica** per integrazione con ERP esterni
- [ ] **P3** **Portale cliente read-only** — il cliente vede stato commessa, consegne, documenti

### Business & Monetizzazione
- [ ] **P2** **Pricing page** sulla landing:
  - Starter (1 utente, fatturazione + commesse): ~29€/mese
  - Pro (team, EN 1090, tracciabilità): ~79€/mese
  - Enterprise (FPC completo, CAM, multi-sede): ~149€/mese
- [ ] **P3** **PWA** (Progressive Web App) per installazione su smartphone officina

---

*Ultimo aggiornamento: 20 Marzo 2026*
