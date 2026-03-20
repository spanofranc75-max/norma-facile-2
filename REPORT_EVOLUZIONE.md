# NormaFacile 2.0 — Report Evoluzione Sistema

## Da dove siamo partiti → Dove siamo arrivati

| Area | PRIMA (v1.0) | DOPO (v2.0 — Sistema Nervoso) | Extra non richiesti |
|------|-------------|-------------------------------|---------------------|
| **Gestione DDT e Certificati** | Semplice archivio documenti: upload manuale, nessuna indicizzazione, ricerca per nome file | **Smistatore Intelligente AI Vision**: analisi multi-pagina con GPT-4o, estrazione automatica N. colata / materiale / dimensioni / acciaieria, matching automatico con voci di lavoro, gestione "scorte" per certificati non assegnati | Filtro Beltrami per DDT multi-commessa multi-pagina, analisi disegni tecnici con estrazione bulloneria automatica e proposta RdP |
| **Officina e Operai** | Registrazione ore manuale con foglio presenze, nessun controllo accessi | **Diario Produzione digitale** con PIN operatore, timer sessione START/STOP, **Safety Gate**: blocco preventivo se corsi D.Lgs 81/08 scaduti o patentini EN 1090 non validi (HTTP 403). Tracciabilita gas/filo per lotto e tipo | Scadenzario attrezzature con alert tarature scadute, checklist qualita auto-compilata, registrazione WPS e numero colata per sessione |
| **Montaggio e Cantiere** | Verbale cartaceo: firma su foglio, nessun dato tecnico strutturato | **Diario di Montaggio digitale a 6 step**: (1) Analisi DDT bulloneria, (2) Serraggio intelligente con **calcolo automatico coppia Nm** da tabella EN 14399, (3) Controllo fondazioni con foto obbligatorie, (4) Firma cliente digitale su tablet, (5) Modulo Varianti con foto documentazione, (6) Checklist sicurezza cantiere pre-lavoro | Blocco report finale se non confermato uso chiave dinamometrica, alert se attrezzatura non tarata, export CSE per Coordinatore Sicurezza |
| **Tracciabilita PNRR/DNSH** | Incubo burocratico: raccolta manuale certificati, compilazione fogli Excel | **Archivio DNSH automatico**: AI Vision estrae % materiale riciclato, certificazioni ambientali (EPD, ISO 14001), metodo produttivo (EAF/BOF) direttamente dai certificati 3.1. Capitolo dedicato nel Pacco Documenti | Dichiarazione CAM automatica con badge conformita, report green certificate PDF, integrazione con capitolo Sostenibilita del Pulsante Magico |
| **Flusso Dati (I Fili Conduttori)** | Moduli isolati: ogni sezione indipendente, nessun passaggio automatico di stato | **State Machine completa**: DDT fornitore analizzato → Voce "Pronto per Produzione". Rientro C/L → Fase completata automaticamente. Firma cliente → Targa CE + QR Code + Manutenzione programmata. Corso scaduto → Blocco diario. **DoP bloccata se C/L non rientrati**. SAL calcolato da ore reali diario | Circuito Conto Lavoro completo (DDT Out/In), DoP Frazionata con suffissi, modulo SAL e Acconti con fatturazione percentuale |
| **Post-Vendita** | "Consegna e dimentica": nessun follow-up, nessun tracciamento post-consegna | **Passaporto Digitale Prodotto**: firma cliente → generazione automatica Targa CE con QR Code, creazione scadenzario manutenzione 12/24 mesi, **Pacco Documenti "Pulsante Magico"** con 6 capitoli: Strutture, Cancelli, Relazione Tecnica, Montaggio, Trattamenti Superficiali, Sostenibilita | Archivio Storico con export ZIP per anno/cliente, notifiche email scadenze manutenzione |

---

## Dettaglio "Fili Conduttori" — La State Machine

```
DISEGNO CARICATO
    │
    ▼
[AI Vision Disegno] ──→ Lista Bulloneria ──→ Proposta RdP Automatica
    │
    ▼
ORDINE A FORNITORE ──→ DDT FORNITORE RICEVUTO
    │
    ▼
[Smistatore Intelligente] ──→ Certificati indicizzati per voce
    │                          Voce → "Pronto per Produzione"
    ▼
DIARIO PRODUZIONE
    │ ├─ [Safety Gate] Corsi scaduti? → BLOCCO 403
    │ ├─ Timer START/STOP con tracciabilita
    │ └─ Checklist Qualita → Verbale Collaudo
    │
    ▼
CONTO LAVORO (se necessario)
    │ ├─ DDT Out → Invio a terzista (zincatura/verniciatura)
    │ ├─ DDT In → Rientro + Upload Certificato Trattamento
    │ ├─ Verifica QC → Fase "Trattamenti Superficiali" completata
    │ └─ [BLOCCO] DoP non generabile se C/L non rientrati
    │
    ▼
MONTAGGIO IN CANTIERE
    │ ├─ [Safety Gate] Corsi/patentini scaduti? → BLOCCO 403
    │ ├─ Analisi DDT bulloneria con AI
    │ ├─ Calcolo coppia serraggio automatico (Nm)
    │ ├─ Foto giunti + ancoraggi obbligatorie
    │ ├─ Modulo Varianti con documentazione
    │ └─ Checklist Sicurezza Cantiere
    │
    ▼
FIRMA CLIENTE (Fine Lavori)
    │
    ├──→ Targa CE con QR Code (Passaporto Digitale)
    ├──→ Scadenzario Manutenzione (12/24 mesi)
    ├──→ SAL finale calcolato da ore reali
    └──→ "PULSANTE MAGICO" — Pacco Documenti Completo
              │
              ├─ CAP. 1: Strutture EN 1090
              ├─ CAP. 2: Cancelli EN 13241
              ├─ CAP. 3: Relazione Tecnica
              ├─ CAP. 4: Relazione di Montaggio
              ├─ CAP. 5: Trattamenti Superficiali
              └─ CAP. 6: Sostenibilita e DNSH
```

---

## Extra implementati oltre le richieste iniziali

1. **Archivio Storico** — Export ZIP strutturato per anno/cliente con tutti i documenti
2. **Scadenzario Attrezzature** — Gestione tarature con alert integrato nel diario
3. **Export CSE** — Pacchetto documenti per il Coordinatore Sicurezza Esecuzione
4. **Modulo Varianti** — Documentazione varianti in cantiere con foto obbligatorie
5. **Filtro Beltrami** — Gestione DDT multi-fornitore multi-commessa multi-pagina
6. **Analisi Disegni AI** — Estrazione automatica bulloneria da disegni tecnici con proposta RdP
7. **DoP Frazionata** — Generazione DoP multiple per la stessa commessa con suffissi (/A, /B)
8. **Circuito Conto Lavoro Completo** — DDT Out/In con certificati trattamento auto-agganciati
9. **Modulo SAL e Acconti** — Fatturazione progressiva basata sull'avanzamento reale
10. **Capitolo Trattamenti Superficiali** — Sezione dedicata nel Pulsante Magico con certificati zincatura/verniciatura

---

*Report generato il 20/03/2026 — NormaFacile 2.0 "Sistema Nervoso"*
