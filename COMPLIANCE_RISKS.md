# COMPLIANCE RISKS — NormaFacile 2.0

> Analisi rischi GDPR, AI, sicurezza, accessibilita e auditability

---

## CR-001: Credenziali Aruba (password) memorizzate in chiaro nel DB

- **Gravita**: Alta
- **Area**: sicurezza / compliance
- **Dove si trova**: `/app/backend/models/company.py` righe 85-87, collezione `company_settings`
- **Perche e un problema**: Il campo `aruba_password` viene memorizzato in chiaro nella collezione MongoDB. Qualsiasi accesso al DB (backup, data breach, accesso non autorizzato) espone la password Aruba SDI dell'utente.
- **Impatto reale**: Violazione delle best practice di sicurezza. Se il DB viene compromesso, le credenziali SDI dell'utente sono esposte.
- **Prova dal codice**: `models/company.py:86: aruba_password: Optional[str] = None` — salvato direttamente nel documento MongoDB senza encryption.
- **Correzione consigliata**: Cifrare `aruba_password` prima del salvataggio (AES-256 con chiave da env var). Oppure usare vault/secret manager.
- **Effort stimato**: Medio

---

## CR-002: Token FattureInCloud (FIC) in chiaro nel DB e in .env

- **Gravita**: Alta
- **Area**: sicurezza
- **Dove si trova**: `/app/backend/.env` riga `FIC_ACCESS_TOKEN=a/eyJ0eXAi...`, `/app/backend/models/company.py` riga 91
- **Perche e un problema**: Il token di accesso FattureInCloud e un JWT salvato sia in `.env` che nel DB `company_settings.fic_access_token`. E un bearer token con accesso completo ai dati finanziari dell'azienda.
- **Impatto reale**: Compromissione del token = accesso a tutti i dati contabili dell'azienda su FattureInCloud.
- **Prova dal codice**: `FIC_ACCESS_TOKEN=a/eyJ0eXAi...` in backend/.env.
- **Correzione consigliata**: Token FIC dovrebbe essere in un secret manager, non in .env versionato. Aggiungere .env a .gitignore (verificare).
- **Effort stimato**: Piccolo

---

## CR-003: Nessun rate limiting sugli endpoint AI

- **Gravita**: Alta
- **Area**: sicurezza / finanza
- **Dove si trova**: Endpoint AI: `/api/istruttoria/analizza-preventivo`, `/api/cantieri-sicurezza/{id}/ai-precompila`, `/api/committenza/analizza/{package_id}`, `/api/istruttoria/segmenta`, `/api/istruttoria/rispondi`, `/api/istruttoria/rispondi-contestuale`
- **Perche e un problema**: Ogni chiamata AI consuma token OpenAI a pagamento. Senza rate limiting, un utente malintenzionato o un bug frontend puo generare costi illimitati. Inoltre, un DoS sugli endpoint AI blocca il servizio per tutti.
- **Impatto reale**: Rischio finanziario diretto (costi API OpenAI) e rischio disponibilita.
- **Prova dal codice**: Nessun middleware `slowapi`, nessun check rate in nessun file.
- **Correzione consigliata**: Implementare rate limiting per-user (es. 10 call/min per endpoint AI, 100 call/min per API generali).
- **Effort stimato**: Medio

---

## CR-004: Disclaimer AI insufficienti nell'interfaccia operativa

- **Gravita**: Media
- **Area**: compliance AI / UX
- **Dove si trova**: Pagine operative (IstruttoriaPage, SchedaCantierePage, CommessaHubPage)
- **Perche e un problema**: NormaFacile genera: istruttorie normative AI, segmentazione automatica, precompilazione sicurezza AI, analisi committenza AI, generazione POS DOCX. Queste sono informazioni a valore legale/normativo. Il disclaimer esiste nella LandingPage e in /legal/disclaimer, ma NON e visibile nelle pagine operative dove l'utente usa attivamente i risultati AI. L'utente potrebbe fidarsi ciecamente di output AI errati in contesto EN 1090 / D.Lgs. 81/2008.
- **Impatto reale**: Rischio legale se un utente prende decisioni normative basandosi esclusivamente su output AI senza review umana, e qualcosa va storto.
- **Prova dal codice**: `grep -rn "disclaimer\|AI.*generato" pages/IstruttoriaPage.js` = 0 risultati. L'unico disclaimer e nella LandingPage e in /legal/disclaimer.
- **Correzione consigliata**: Aggiungere banner/badge visibile su ogni output AI ("Proposta AI - Verifica umana necessaria") su: risultati istruttoria, segmentazione, precompilazione sicurezza, analisi committenza, POS generato.
- **Effort stimato**: Piccolo (1-2 ore)

---

## CR-005: Nessuna distinzione UI tra stato "AI proposto" e "confermato dall'utente"

- **Gravita**: Media
- **Area**: compliance / auditability
- **Dove si trova**: Moduli istruttoria, segmentazione, sicurezza AI
- **Perche e un problema**: Nell'audit trail, esiste `actor_type` (user/system/ai), ma nel frontend la distinzione tra "dato proposto dall'AI" e "dato confermato dall'operatore" non e sempre evidente. Per compliance EN 1090 / ISO 3834, e necessario sapere CHI ha preso una decisione tecnica.
- **Impatto reale**: In caso di audit EN 1090, potrebbe essere difficile dimostrare che un operatore qualificato ha effettivamente verificato le scelte normative.
- **Prova dal codice**: I campi `confidence` (dedotto/confermato/incerto) esistono nel backend ma non sono sempre visibili nel frontend.
- **Correzione consigliata**: Rendere visibile lo stato confidence/origin su ogni dato AI. Badge "AI" vs "Confermato" chiaro.
- **Effort stimato**: Medio

---

## CR-006: Accessibilita web (WCAG) quasi assente

- **Gravita**: Media
- **Area**: compliance / accessibilita
- **Dove si trova**: Tutte le 70 pagine frontend
- **Perche e un problema**: 
  - 0/70 pagine con `aria-label`
  - Solo 3 pagine con gestione keyboard (tabIndex/onKeyDown)
  - 19/70 pagine senza classi responsive
  - Nessun skip-to-content link
  - Nessun screen reader support
- **Impatto reale**: L'app non e utilizzabile da utenti con disabilita. In Italia, il D.Lgs. 106/2018 estende l'obbligo di accessibilita alle aziende private con fatturato >500M. Anche se non obbligatorio oggi per il target di NormaFacile, e una best practice e un rischio reputazionale.
- **Prova dal codice**: `grep -rl "aria-label" pages/` = 0 file.
- **Correzione consigliata**: Livello minimo: aggiungere `aria-label` a tutti i pulsanti iconici, `role` ai contenitori principali, skip-to-content link. Livello avanzato: audit WCAG 2.1 AA.
- **Effort stimato**: Alto (progressivo)

---

## CR-007: Dati sensibili nei pacchetti documentali senza encryption

- **Gravita**: Media
- **Area**: GDPR / privacy
- **Dove si trova**: Collezione `documenti_archivio`, campo `privacy_level` ("sensibile", "cliente_condivisibile", "interno")
- **Perche e un problema**: I documenti classificati come "sensibile" (es. documenti identita, certificati medici per sicurezza cantiere) sono memorizzati con lo stesso livello di protezione dei documenti normali. Non c'e encryption at-rest specifica, non c'e access logging sui documenti sensibili, non c'e retention policy.
- **Impatto reale**: Violazione potenziale GDPR Art. 32 (misure tecniche adeguate). In caso di data breach, i documenti sensibili sono esposti come tutti gli altri.
- **Prova dal codice**: Il campo `privacy_level` e gestito come semplice label. Nessun encryption, nessun access log specifico.
- **Correzione consigliata**: 1) Encryption at-rest per documenti "sensibile". 2) Access log su ogni visualizzazione/download di doc sensibili. 3) Retention policy con cancellazione automatica.
- **Effort stimato**: Alto

---

## CR-008: Nessuna policy di retention dati

- **Gravita**: Media
- **Area**: GDPR
- **Dove si trova**: Intero sistema
- **Perche e un problema**: GDPR Art. 5(1)(e) richiede limitazione della conservazione. Il sistema non ha: 1) Scadenza automatica su dati personali. 2) Procedura di cancellazione su richiesta. 3) Anonimizzazione dopo periodo di retention. 4) Le 100 collezioni DB crescono senza limiti.
- **Impatto reale**: Accumulo indefinito di dati personali. Rischio sanzione GDPR.
- **Correzione consigliata**: Definire retention policy per ogni tipo di dato. Implementare job di cleanup automatico. Priorita: `activity_log`, `notification_logs`, `download_tokens`, `notifiche_smart`.
- **Effort stimato**: Alto

---

## CR-009: JWT secret hardcoded in .env

- **Gravita**: Media
- **Area**: sicurezza
- **Dove si trova**: `/app/backend/.env` riga `JWT_SECRET=normafacile-prod-secret-key-2026-steelproject`
- **Perche e un problema**: Il JWT secret e una stringa leggibile e prevedibile. Se il .env viene committato in un repo pubblico o esposto, tutti i JWT dell'applicazione possono essere forgiati.
- **Impatto reale**: Compromissione del secret = accesso completo a tutti gli account.
- **Prova dal codice**: `JWT_SECRET=normafacile-prod-secret-key-2026-steelproject` — troppo descrittivo e debole.
- **Correzione consigliata**: Generare un secret casuale (256+ bit), non includerlo nei commit, usare secret manager in produzione.
- **Effort stimato**: Piccolo

---

## CR-010: Audit trail non copre accessi a dati sensibili

- **Gravita**: Bassa
- **Area**: auditability / GDPR
- **Dove si trova**: `services/audit_trail.py`
- **Perche e un problema**: L'audit trail traccia azioni CRUD e AI, ma non traccia: 1) Accessi in lettura a documenti sensibili. 2) Export/download di dati. 3) Chi ha visualizzato cosa. Per GDPR compliance, gli accessi ai dati personali dovrebbero essere tracciabili.
- **Impatto reale**: Impossibile rispondere alla domanda "chi ha accesso a questo documento?" in caso di richiesta GDPR.
- **Correzione consigliata**: Aggiungere log di lettura per documenti con `privacy_level=sensibile` e per export dati.
- **Effort stimato**: Medio

---

## RIEPILOGO RISCHI

| ID | Titolo | Gravita | Area |
|----|--------|---------|------|
| CR-001 | Password Aruba in chiaro nel DB | Alta | Sicurezza |
| CR-002 | Token FIC in chiaro | Alta | Sicurezza |
| CR-003 | No rate limiting endpoint AI | Alta | Sicurezza/Finanza |
| CR-004 | Disclaimer AI insufficienti in UI | Media | Compliance AI |
| CR-005 | No distinzione AI/confermato in UI | Media | Auditability |
| CR-006 | Accessibilita WCAG assente | Media | Accessibilita |
| CR-007 | Doc sensibili senza encryption | Media | GDPR |
| CR-008 | Nessuna retention policy | Media | GDPR |
| CR-009 | JWT secret debole | Media | Sicurezza |
| CR-010 | Audit trail non copre letture | Bassa | Auditability |
