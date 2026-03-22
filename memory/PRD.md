# NormaFacile 2.0 — PRD

## Problema Originale
ERP per carpenteria metallica con focus su conformità EN 1090-1 e viabilità commerciale come prodotto startup. Multi-normativa (EN 1090, EN 13241, Generica) con gestione commesse, tracciabilità materiali, saldatura, ispezioni, e generazione documentazione (DOP, CE Label).

## Utente Target
Carpenterie metalliche italiane, certificazione EN 1090, contratti PNRR.

## Funzionalità Implementate

### Core EN 1090 (Completo)
- Commesse CRUD con voci lavoro multi-normativa
- FPC: lotti materiale con tracciabilità colata -> cert 3.1 -> DDT
- Registro saldatura con WPS e qualifiche saldatori
- Riesame Tecnico (gate pre-produzione) con 12 check automatici
- Ispezioni, Controllo Finale, Fascicolo Tecnico
- DOP frazionata e automatica con PDF professionale

### CAM — Criteri Ambientali Minimi (Completato 21/03/2026)
- Campi CAM su material_batches: peso_kg, percentuale_riciclato, metodo_produttivo, distanza_trasporto_km, certificazione_epd, ente_certificatore_epd
- Calcolo conformità CAM da material_batches (bridge FPC <-> CAM senza duplicazione)
- CAM Alert pre-generazione: endpoint /api/cam/alert/{cid} con livello danger/success/warning e suggerimenti actionable
- Form frontend batch con sezione CAM dedicata (Peso, % Riciclato, Metodo Produttivo, Distanza)
- Colonne Peso e % Riciclato nella tabella rintracciabilità

### PDF Executive Professional (Completato 21/03/2026)
- DOP EN 1090 (4 pagine):
  - Intestazione professionale con barra gradient blu scuro e dati aziendali
  - Tabella prestazioni ZA.1-ZA.7 arricchita da Riesame Tecnico (no NPD: ZA.3 mostra WPS/saldatori, ZA.4 n. certificati, ZA.5-ZA.7 dati reali da Riesame)
  - Tracciabilità materiali con zebra striping e N. Colata monospace
  - Verifiche condizionali: Riesame, Registro Saldatura (con righe esempio), Ispezioni VT/Dim, Controllo Finale — sezioni vuote nascoste
  - Allegato CAM PNRR con badge DM 256/2022, 4 summary boxes, tabella dettaglio, riferimenti CO2
  - Dichiarazione Conformità con box gradient e firma nominativa
  - Timbro Professionale Circolare: "VERIFICATO CONFORME" + nome azienda + FPC + città/data
- Etichetta CE: formato 148x105mm, badge EN 1090-1, pronta stampa adesivo
- Dichiarazione CAM PNRR: badge "Art. 57 D.Lgs. 36/2023", dettaglio con fornitore/colata/distanza
- Scheda Rintracciabilità Totale: A4 landscape, 12 colonne, catena completa, legenda tecnica
- Banner CAM Alert nel CommessaHub: rosso (danger), verde (success), arancio (warning) con suggerimenti

### Multi-Normativa (Completo)
- Executive Dashboard con vista EN 1090 / EN 13241 / Generica
- normativa_tipo su voci_lavoro
- Riesame Tecnico Selettivo: check condizionali per normativa (completato 22/03/2026)
  - CHECKS_DEFINITION con campo `normativa` per ogni check
  - Filtraggio automatico basato su normativa_tipo delle voci lavoro della commessa
  - Check non applicabili marcati N/A con `applicabile: false` e motivo esclusione
  - Approvazione valida solo check applicabili (non-applicable auto-superati)
  - PDF con badge normative attive e riepilogo applicabili/N/A
  - Frontend: check N/A grayed out, strikethrough, icona "—", badge normativa nell'header

### Moduli Aggiuntivi (Completato)
- Scadenziario Manutenzioni Digitalizzato, Verbali ITT
- Sopralluoghi, Perizie, Preventivatore con AI
- DDT, Fatturazione attiva/passiva, Analisi finanziaria
- Notifiche (base), QR Code, Team management

### Safety Gate CAM (Completato 22/03/2026)
- Endpoint /api/dashboard/executive arricchito con campo cam_safety_gate
- Calcolo aggregato % riciclato su tutte le commesse attive con material_batches
- Alert "RISCHIO NON CONFORMITA" nella Dashboard Executive se % < 75%
- Badge per-commessa con link diretto alle commesse sotto soglia
- Avviso CAM proattivo nel Preventivatore (Step 3) per normativa EN_1090

### PDF Restyling Audit-Proof (Completato 22/03/2026)
- Footer DOP migliorato: "DoP {num} — Commessa {num}" + "Pag. X di Y"
- Dichiarazione CAM: verdetto CONFORME/NON CONFORME con stamp "ESITO VERIFICA"
- Quadro normativo arricchito: DM 23/06/2022 n.256, GU n.183, Art. 57 D.Lgs. 36/2023
- Footer CAM: "Dichiarazione CAM — DM 23/06/2022" + numerazione pagine

### Pacco Documenti RINA (Completato 22/03/2026)
- Endpoint GET /api/fascicolo-tecnico/{cid}/pacco-rina
- ZIP organizzato e numerato: 01_DOP, 02_CE, 03_CAM, 04_Rintracciabilità, 05_Riesame + 00_INDICE.txt
- Gestione errori per documenti non generabili (errori elencati nell'indice)
- Bottone "Pacco RINA" nella CommessaHub (rosso, prominente)

### Ponte Perizie → Preventivatore (Completato 22/03/2026)
- Endpoint POST /api/perizie/{id}/genera-preventivo
- Trasferimento automatico voci_costo perizia → righe preventivo
- Calcolo automatico normativa da tipo_danno (strutturale→EN_1090, automatismi→EN_13241)
- Link bidirezionale perizia↔preventivo (perizia.preventivo_id + preventivo.perizia_source)
- Bottone "Genera Preventivo da Perizia" nel Riepilogo della PeriziaEditorPage
- Log activity e navigazione diretta al preventivo creato

### Sistema Notifiche Proattive (Completato 22/03/2026)
- 3 tipi di check: Qualifiche Saldatori, Tarature Strumenti, Scadenze ITT
- 4 livelli di urgenza: Alert (30gg), Urgente (7gg), Critico (1gg), Scaduto (<0)
- Email template potenziato con badge colore per urgenza + sezione ITT dedicata
- Subject email dinamico con conteggio scadenze critiche
- Invio reale tramite Resend (API key configurata)
- Destinatario: utenti admin/ufficio_tecnico (da _get_notification_recipients)

### Report CAM Mensile (Completato 22/03/2026)
- Endpoint GET /api/cam/report-mensile/pdf
- KPI: % riciclato globale, peso totale acciaio, n. conformi/non conformi
- Tabella dettaglio per commessa con esito CONFORME/NON CONFORME
- Trend mensile ultimi 6 mesi con barre colorate e soglia tratteggiata
- Proiezione trimestrale automatica basata su media delta mensile
- Riferimenti normativi (DM 23/06/2022, Art. 57 D.Lgs. 36/2023)
- Bottone "Report CAM Mensile (PDF)" nella Dashboard Executive

### Motore di Istruttoria Automatica da Preventivo — Fase 1 (Completato 22/03/2026)
**Il cambio di paradigma: da generatore documentale a copilota tecnico-normativo.**

- **Livello 1A — Estrazione Tecnica** (GPT-4o):
  - Estrae: elementi strutturali, materiali, profili, spessori, saldature, trattamenti, montaggio, destinazione uso
  - Ogni dato ha stato: dedotto/confermato/mancante/incerto + fonte nel testo + confidenza
  - Rileva ambiguita e parole chiave di rischio

- **Livello 1B — Classificazione Normativa** (GPT-4o + Rules):
  - Classifica: EN 1090 / EN 13241 / Generica / Mista con motivazione
  - **Profilo tecnico specifico per normativa** (corretto: EXC solo per EN 1090):
    - EN 1090: tipo=exc, valore=EXC1-4
    - EN 13241: tipo=categorie_prestazione (resistenza vento, permeabilita aria, etc.)
    - Generica: tipo=complessita (bassa/media/alta)
  - Rule engine deterministico auto-corregge se AI assegna EXC a EN 13241

- **Override Umano Tracciato**:
  - Endpoint POST /api/istruttoria/{id}/revisione
  - Salva: valore_ai, valore_umano, corretto_da, corretto_il, motivazione_correzione
  - Checkpoint conferma obbligatorio (POST /api/istruttoria/{id}/conferma) prima di Fase 2

- **Frontend IstruttoriaPage** con:
  - Card classificazione + profilo tecnico + stato conoscenza
  - Elementi estratti con badge stato
  - Domande residue INTERATTIVE: Textarea per ogni domanda, pulsante "Salva Risposte", badge "Risposto", info autore/data
  - Sezione revisioni umane (valore AI barrato → valore umano verde)
  - Barra conferma con checkpoint pre-Fase 2

- **Risposte Domande Residue** (Completato 22/03/2026):
  - Endpoint POST /api/istruttoria/{id}/rispondi per salvare risposte utente
  - Merge risposte (non sovrascrive), validazione payload, gestione errori
  - Frontend: Textarea per ogni domanda, pre-popolate con risposte salvate
  - Badge "Risposto" verde + autore/data per risposte esistenti
  - Contatore risposte/domande totali nell'header sezione

- **Redesign P0.1 — Da analisi a cockpit operativo** (Completato 22/03/2026):
  - Card "Esito Istruttoria" dominante con normativa, profilo, confidenza, motivazione AI
  - Progress bar: N/M conferme date con feedback visivo
  - Domande residue con bottoni rapidi contestuali (risposte suggerite per dominio: montaggio, zincatura, tolleranze, saldatura, materiali)
  - Toggle behavior sui bottoni + textarea per risposta personalizzata
  - Badge "Proposta AI" / "Confermata" per distinzione visiva
  - CTA contestuale: verde "Conferma Istruttoria" quando tutto risposto, grigio "Conferma Comunque" altrimenti
  - Dettaglio tecnico collapsible (chiuso di default)
  - Punti incerti consolidati in unico box

## Backlog Prioritizzato

### P1
- (Completati: Ponte Perizie, Notifiche Proattive, Report CAM Mensile)

### P2
4. Architettura Multi-Tenant: tenant_id su tutte le collection
5. Training ML: Modello di stima dal Diario Produzione
6. Alerting Intelligente: Notifica sforamento costi

### P3
7. Unificazione PDF legacy (13 servizi)
8. Portale Clienti (read-only)
9. RBAC avanzato, QR Code migliorati
10. Split file grandi (SettingsPage.js, commesse.py)

## Architettura
- Frontend: React + ShadCN/UI, porta 3000
- Backend: FastAPI + MongoDB (test_database), porta 8001
- PDF: WeasyPrint
- AI: emergentintegrations + GPT-4o Vision
- Auth: Google OAuth con sessioni cookie
