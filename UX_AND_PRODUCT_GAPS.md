# UX AND PRODUCT GAPS — NormaFacile 2.0

> Punti in cui il processo e troppo complicato, poco chiaro, o migliorabile per l'utente

---

## UX-001: CommessaHubPage e troppo densa — 11+ sezioni in una pagina

- **Gravita**: Alta
- **Area**: UX / frontend
- **Dove si trova**: `/app/frontend/src/pages/CommessaHubPage.js` (1063 righe)
- **Perche e un problema**: La pagina hub della commessa carica 11 sotto-sezioni (CommessaOpsPanel, VociLavoro, CommessaComplianceBanner, RiesameTecnico, RegistroSaldatura, TracciabilitaMateriali, ControlloFinale, ReportIspezioni, RamiNormativi, ObbrighiCommessa, VerificaCommittenza). L'utente deve scrollare molto per trovare la sezione desiderata. Non c'e navigazione interna ne tab system per la parte inferiore.
- **Impatto reale**: L'utente si perde. Troppa informazione in un solo schermo. Difficile capire dove guardare prima.
- **Correzione consigliata**: 1) Aggiungere tab o navigazione laterale interna per le sezioni. 2) Collassare le sezioni meno usate per default. 3) Mettere in evidenza le azioni urgenti (obblighi bloccanti, gate rossi).
- **Effort stimato**: Medio

---

## UX-002: IstruttoriaPage — 1710 righe, 17 state variables

- **Gravita**: Alta
- **Area**: UX / frontend
- **Dove si trova**: `/app/frontend/src/pages/IstruttoriaPage.js`
- **Perche e un problema**: Il file e il piu grande del frontend. 17 `useState`, 31 hook calls. Include: analisi AI, risposte domande, segmentazione, review, fase 2, generazione commessa. Tutto in un singolo componente. L'utente deve navigare un flusso complesso (5+ step) senza una guida visiva chiara di dove si trova nel processo.
- **Impatto reale**: Utente confuso su quale step fare dopo. Rischio di saltare la conferma prima della segmentazione. UX pesante e poco guidata.
- **Correzione consigliata**: Refactorare in un wizard multi-step con stepper visivo: Analisi -> Domande -> Conferma -> Segmentazione -> Review -> Genera Commessa.
- **Effort stimato**: Alto

---

## UX-003: Nessun onboarding / primo utilizzo guidato

- **Gravita**: Alta
- **Area**: prodotto / UX
- **Dove si trova**: Assente nell'intera applicazione
- **Perche e un problema**: Un utente nuovo si trova davanti a una sidebar con 8 gruppi, 40+ link. Non c'e: 1) Tour guidato del primo utilizzo. 2) Suggerimento su dove iniziare. 3) Checklist "primi passi" (configura azienda -> crea primo cliente -> crea preventivo). 4) Empty states informativi sulle pagine vuote.
- **Impatto reale**: Alto tasso di abbandono per nuovi utenti. L'app e potente ma non comunica COME usarla.
- **Correzione consigliata**: 1) Wizard "Prima configurazione" (dati azienda, figure aziendali, primo cliente). 2) Banner "Prossimi passi" nella dashboard. 3) Empty states migliorati con CTA chiare.
- **Effort stimato**: Medio

---

## UX-004: 19 pagine senza design responsive

- **Gravita**: Media
- **Area**: UX / mobile
- **Dove si trova**: `ArchivioStoricoPage`, `CertificazioneWizardPage`, `CertificazioniPage`, `CoreEnginePage`, `DistintePage`, `FascicoloCantierePage`, `FattureRicevutePage`, `InvoiceEditorPage`, `ManualePage`, `PeriziaEditorPage`, `PeriziaListPage`, `PlanningPage`, `PosWizardPage`, `QualitySystemPage`, `RilieviPage`, `SettingsPage`, `SicurezzaPage`, `TracciabilitaPage`
- **Perche e un problema**: Queste pagine non hanno classi responsive (sm:/md:/lg:). Su tablet o smartphone risultano inutilizzabili o con layout rotto.
- **Impatto reale**: Il titolare di una carpenteria potrebbe voler controllare lo stato commesse da cantiere (tablet/smartphone). Senza responsive, l'app e desktop-only de facto.
- **Correzione consigliata**: Prioritizzare responsive per: SettingsPage (configurazione), SicurezzaPage (usata in cantiere), CertificazioniPage (consultazione).
- **Effort stimato**: Medio (2-3 ore per pagina)

---

## UX-005: Dashboard — troppi KPI senza prioritizzazione

- **Gravita**: Media
- **Area**: UX / prodotto
- **Dove si trova**: Dashboard principale, Executive Dashboard, Dashboard Cantiere
- **Perche e un problema**: Esistono 3 dashboard diverse (dashboard, executive, cantiere-multilivello) che mostrano molti KPI. Il titolare deve capire QUALE dashboard guardare e COSA e urgente. Non c'e un "colpo d'occhio" unico che dica: "Oggi ci sono 3 cose urgenti".
- **Impatto reale**: Il valore della dashboard come strumento decisionale e diluito dalla quantita di informazioni.
- **Correzione consigliata**: 1) Unificare in una vista principale con 3 aree: Urgenze (rosso), Attenzione (giallo), Tutto OK (verde). 2) Card "Azioni da fare oggi" in cima alla dashboard principale.
- **Effort stimato**: Medio

---

## UX-006: Navigazione CommessaHub -> Moduli sorgente frammentata

- **Gravita**: Media
- **Area**: UX
- **Dove si trova**: `CommessaHubPage` / `ObbrighiCommessaSection`
- **Perche e un problema**: Il registro obblighi mostra la fonte (Evidence Gate, POS, Committenza, ecc.) ma i link per "andare alla fonte" non sono sempre presenti o funzionanti. L'utente vede un obbligo bloccante ma non sa come risolverlo senza navigare manualmente alla sezione corretta.
- **Impatto reale**: Frustrazione utente. Passaggi manuali che potrebbero essere un click.
- **Correzione consigliata**: Aggiungere link "Vai alla fonte" su ogni obbligo che porta direttamente alla sezione/pagina dove risolvere il problema.
- **Effort stimato**: Piccolo

---

## UX-007: Stato "bozza" vs "definitivo" non chiaro su documenti generati

- **Gravita**: Media
- **Area**: prodotto / UX
- **Dove si trova**: POS DOCX, email pacchetti, certificazioni CE
- **Perche e un problema**: Il POS generato e una "bozza modificabile" (lo dice il bottone), ma una volta scaricato e nella lista storico generazioni, non c'e distinzione chiara tra bozza e versione definitiva. Lo stesso per i pacchetti documentali: un pacchetto inviato e diverso da uno in preparazione, ma la UI li mostra nello stesso modo.
- **Impatto reale**: Rischio di inviare una bozza come documento definitivo. Confusione su quale sia la versione corrente.
- **Correzione consigliata**: Aggiungere stato esplicito (Bozza/In review/Definitivo) a POS, pacchetti, certificazioni. Badge colorato visibile.
- **Effort stimato**: Piccolo-Medio

---

## UX-008: Sidebar troppo lunga — 40+ voci

- **Gravita**: Bassa
- **Area**: UX
- **Dove si trova**: `DashboardLayout.js` — NAV_GROUPS
- **Perche e un problema**: La sidebar ha 8 gruppi con 40+ link totali. Anche con i gruppi accordion, la navigazione e densa. Un utente con ruolo `ufficio_tecnico` vede quasi tutto. Non c'e modo di personalizzare la sidebar o nascondere sezioni poco usate.
- **Impatto reale**: Overload cognitivo. Le voci importanti si perdono tra quelle secondarie.
- **Correzione consigliata**: 1) "Preferiti" pinnabili in cima alla sidebar. 2) Sezione "Recenti" con le ultime 3-5 pagine visitate. 3) Possibilita di nascondere gruppi non usati.
- **Effort stimato**: Medio

---

## UX-009: Feedback utente post-azioni AI inconsistente

- **Gravita**: Bassa
- **Area**: UX
- **Dove si trova**: Istruttoria AI, Sicurezza AI, Committenza AI
- **Perche e un problema**: Dopo un'operazione AI (analisi, precompilazione, segmentazione), il feedback varia: a volte c'e un banner verde, a volte un toast, a volte solo l'aggiornamento dei dati. Non c'e un pattern consistente. Il tempo di attesa AI (10-30 secondi) non ha sempre un loading spinner adeguato.
- **Impatto reale**: L'utente non e sicuro se l'AI ha terminato o sta ancora elaborando.
- **Correzione consigliata**: Pattern unificato: 1) Loading overlay con messaggi progressivi per operazioni AI. 2) Banner risultato con summary (N obblighi trovati, N rischi attivati, ecc.). 3) Azione successiva suggerita.
- **Effort stimato**: Piccolo

---

## UX-010: Accessibilita zero

- **Gravita**: Media
- **Area**: accessibilita / UX
- **Dove si trova**: Tutte le pagine
- **Perche e un problema**: 
  - 0 `aria-label` su 70 pagine
  - Solo 3 pagine con gestione tastiera
  - Nessun skip-to-content
  - Colori di contrasto non verificati
  - Nessun focus visible sugli elementi interattivi in molte pagine
- **Impatto reale**: Inutilizzabile per utenti con disabilita visive o motorie.
- **Correzione consigliata**: Livello minimo: `aria-label` su tutti i bottoni iconici e input, focus visible su tutti gli elementi interattivi, skip-to-content link.
- **Effort stimato**: Medio (progressivo)

---

## UX-011: Pacchetti documentali — flusso upload pesante

- **Gravita**: Bassa
- **Area**: UX
- **Dove si trova**: `PacchettiDocumentaliPage.js` tab Archivio
- **Perche e un problema**: Per caricare un documento, l'utente deve: selezionare tipo, compilare entity_type, owner_label, title, date, file. Molti campi. Per un'azienda che carica 20+ documenti alla volta (ingresso cantiere), il processo e lento.
- **Impatto reale**: Frizione sull'operazione piu frequente del modulo pacchetti.
- **Correzione consigliata**: 1) Upload bulk (drag & drop multiplo). 2) Auto-detect tipo documento dal nome file. 3) Pre-fill date e entity_type dal contesto.
- **Effort stimato**: Medio

---

## UX-012: Notifiche — nessun filtro per gravita o tipo

- **Gravita**: Bassa
- **Area**: UX
- **Dove si trova**: `NotificationsPage.js`, drawer notifiche
- **Perche e un problema**: Nella pagina notifiche e nel drawer, tutte le notifiche sono mostrate in ordine cronologico senza filtri. Un utente con molte notifiche non puo filtrare per "solo critiche" o "solo relative alla commessa X".
- **Impatto reale**: Le notifiche critiche si perdono tra quelle informative.
- **Correzione consigliata**: Aggiungere filtri: gravita (critica/alta/media/bassa), tipo, commessa.
- **Effort stimato**: Piccolo

---

## RIEPILOGO

| ID | Titolo | Gravita | Effort |
|----|--------|---------|--------|
| UX-001 | CommessaHubPage troppo densa | Alta | Medio |
| UX-002 | IstruttoriaPage monolitica | Alta | Alto |
| UX-003 | Nessun onboarding | Alta | Medio |
| UX-004 | 19 pagine non responsive | Media | Medio |
| UX-005 | Dashboard senza prioritizzazione | Media | Medio |
| UX-006 | Link "vai alla fonte" mancanti | Media | Piccolo |
| UX-007 | Stato bozza/definitivo non chiaro | Media | Piccolo-Medio |
| UX-008 | Sidebar troppo lunga | Bassa | Medio |
| UX-009 | Feedback AI inconsistente | Bassa | Piccolo |
| UX-010 | Accessibilita zero | Media | Medio |
| UX-011 | Upload pacchetti pesante | Bassa | Medio |
| UX-012 | Notifiche senza filtri | Bassa | Piccolo |
