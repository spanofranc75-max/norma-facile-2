# SPEC_PACCHETTI_DOCUMENTALI.md
## Pacchetti Documentali Intelligenti — NormaFacile 2.0

**Data**: 2026-03-22 | **Versione**: 1.0 — Spec MVP

---

## 1. Obiettivo

Quando la committenza chiede documenti (azienda, attestati dipendenti, mezzi, cantiere), il sistema deve:
1. Capire cosa serve
2. Verificare cosa c'e gia
3. Mostrare cosa manca o e scaduto
4. Preparare il pacchetto
5. Inviare email in un click
6. Tenere traccia di cosa e stato mandato

---

## 2. Famiglie Documenti

| Famiglia | Esempi |
|----------|--------|
| Azienda | DURC, Visura, Polizze, ISO, DVR |
| Persone/Dipendenti | Attestati formazione, PLE, Primo soccorso, Idoneita |
| Mezzi/Attrezzature | Verifiche periodiche, Libretti, Assicurazioni |
| Commessa/Cantiere | POS, Elenco lavoratori, Documenti sicurezza |

---

## 3. Modello Dati

### A. `lib_tipi_documento` — Libreria tipi documento

```json
{
  "code": "DURC",
  "label": "DURC",
  "category": "azienda",
  "entity_type": "azienda",
  "has_expiry": true,
  "validity_days": 120,
  "privacy_level": "cliente_condivisibile",
  "default_required_for": ["ingresso_cantiere", "qualifica_fornitore"],
  "active": true,
  "sort_order": 10
}
```

entity_type: `azienda | persona | mezzo | cantiere | commessa`
privacy_level: `cliente_condivisibile | interno | riservato | sensibile`

### B. `documenti_archivio` — Documenti reali caricati

```json
{
  "document_type_code": "ATTESTATO_PLE",
  "entity_type": "persona",
  "entity_id": "worker_01",
  "owner_label": "Mario Rossi",
  "title": "Attestato PLE Mario Rossi",
  "issue_date": "2025-01-10",
  "expiry_date": "2030-01-10",
  "status": "valido",
  "verified": true,
  "version": 1,
  "file_id": "file_123",
  "file_name": "attestato_ple_rossi.pdf",
  "mime_type": "application/pdf",
  "privacy_level": "cliente_condivisibile",
  "tags": ["ple", "formazione", "cantiere"],
  "source": "upload_manuale",
  "notes": ""
}
```

Stati documento: `valido | in_scadenza | scaduto | non_verificato | sostituito | archiviato`

### C. `pacchetti_template` — Template pacchetti standard

```json
{
  "code": "INGRESSO_CANTIERE_BASE",
  "label": "Ingresso cantiere base",
  "description": "Pacchetto documenti standard per avvio cantiere",
  "rules": [
    { "document_type_code": "DURC", "entity_type": "azienda", "required": true },
    { "document_type_code": "VISURA_CAMERALE", "entity_type": "azienda", "required": true },
    { "document_type_code": "POS", "entity_type": "cantiere", "required": true },
    { "document_type_code": "ATTESTATO_SICUREZZA", "entity_type": "persona", "required": true, "scope": "all_assigned_workers" }
  ],
  "active": true
}
```

### D. `pacchetti_documentali` — Pacchetto reale per commessa/cantiere

```json
{
  "commessa_id": "COM-2026-00125",
  "cantiere_id": "cs_001",
  "template_code": "INGRESSO_CANTIERE_BASE",
  "status": "draft",
  "requested_by": { "type": "committente", "name": "Maxima Srl" },
  "recipient": { "to": ["sicurezza@cliente.it"], "cc": ["ufficio@cliente.it"] },
  "items": [
    {
      "document_type_code": "DURC",
      "entity_type": "azienda",
      "entity_id": "company_01",
      "required": true,
      "document_id": "doc_100",
      "status": "attached",
      "blocking": false
    },
    {
      "document_type_code": "ATTESTATO_PLE",
      "entity_type": "persona",
      "entity_id": "worker_01",
      "required": true,
      "document_id": null,
      "status": "missing",
      "blocking": true
    }
  ],
  "summary": { "total_required": 12, "attached": 9, "missing": 2, "expired": 1 },
  "email_draft": {
    "subject": "Invio documentazione cantiere COM-2026-00125",
    "body": "In allegato la documentazione richiesta...",
    "attachments_ready": false
  }
}
```

Stati pacchetto: `draft | in_preparazione | pronto_invio | inviato | incompleto | annullato`

### E. `pacchetti_invii` — Log invii email

```json
{
  "package_id": "pack_001",
  "email_to": ["sicurezza@cliente.it"],
  "email_cc": ["ufficio@cliente.it"],
  "subject": "Invio documentazione cantiere COM-2026-00125",
  "document_ids": ["doc_100", "doc_101", "doc_102"],
  "attachment_count": 3,
  "status": "sent",
  "provider": "resend",
  "provider_message_id": "msg_123",
  "sent_by": "usr_01",
  "sent_at": "2026-03-22T11:00:00Z",
  "notes": ""
}
```

Stati invio: `draft | queued | sent | failed`

### F. `profili_documentali_committente` (opzionale, post-MVP)

```json
{
  "committente_name": "Grande Azienda X",
  "default_package_template": "QUALIFICA_FORNITORE_BIGCO",
  "always_required": ["DURC", "VISURA_CAMERALE", "POS", "ATTESTATO_SICUREZZA"],
  "notes": "Richiede anche elenco mezzi e documenti accesso portale",
  "active": true
}
```

---

## 4. Regole Logiche Motore Pacchetto

| # | Regola |
|---|--------|
| 1 | Cerca documento piu recente valido per tipo+entita |
| 2 | Priorita: verified=true > piu recente > escludi scaduto |
| 3 | Se item required e missing/expired -> pacchetto non pronto_invio senza override |
| 4 | Se template ha scope=all_assigned_workers -> genera item per ogni lavoratore assegnato |
| 5 | Stessa logica per mezzi assegnati |
| 6 | Non inviare mai documenti scaduti/mancanti/sensibili senza conferma |
| 7 | Ogni pacchetto deve avere checklist tracciata |
| 8 | Ogni invio deve essere loggato |
| 9 | Documenti devono avere scadenza e stato, non solo file |
| 10 | Il sistema deve sapere a chi appartiene ogni documento |

---

## 5. Classificazione Privacy

| Livello | Esempio |
|---------|---------|
| cliente_condivisibile | DURC, attestato PLE |
| interno | procedure interne |
| riservato | carta identita |
| sensibile | idoneita sanitaria |

---

## 6. Endpoint MVP

### Tipi documento
- `GET /api/documenti/tipi`

### Archivio documenti
- `POST /api/documenti`
- `GET /api/documenti`
- `PATCH /api/documenti/{id}`
- `GET /api/documenti/{id}`

### Pacchetti
- `POST /api/pacchetti-documentali`
- `POST /api/pacchetti-documentali/{id}/genera-da-template`
- `GET /api/pacchetti-documentali/{id}`
- `PATCH /api/pacchetti-documentali/{id}`
- `POST /api/pacchetti-documentali/{id}/prepara-invio`
- `POST /api/pacchetti-documentali/{id}/invia-email`

### Log invii
- `GET /api/pacchetti-documentali/{id}/invii`

---

## 7. Casi d'Uso MVP

### Ingresso cantiere
DURC, visura, POS, elenco lavoratori, attestati base, idoneita, mezzi

### Qualifica fornitore (grande azienda)
DURC, polizze, ISO, organigramma, DVR/estratti, attestati, documenti sicurezza

### Documenti personale operativo
Attestati formazione, PLE, primo soccorso, antincendio, idoneita

### Documenti mezzi
Verifiche, libretti, assicurazioni, documenti PLE/gru/carrelli

---

## 8. Flussi Utente

### Flusso 1 — Manuale
apri commessa -> "Nuovo pacchetto" -> scegli template -> sistema cerca documenti -> mostra presenti/mancanti/scaduti -> "Prepara email" -> verifica -> "Invia"

### Flusso 2 — Da cantiere
apri scheda cantiere -> "Prepara dossier cantiere" -> sistema prende docs azienda + operatori + mezzi + POS -> compone pacchetto -> invio

### Flusso 3 — Da richiesta cliente (futuro, con AI)
carica mail/PDF -> sistema propone checklist -> conferma -> cerca documenti -> prepara

---

## 9. Schermate MVP

| # | Schermata | Contenuto |
|---|-----------|-----------|
| 1 | Archivio Documenti | Filtri: azienda/dipendente/mezzo/cantiere/tipo/stato/scadenza |
| 2 | Nuovo Pacchetto | Commessa, destinatario, tipo, template, note |
| 3 | Checklist Pacchetto | 3 colonne: Richiesto / Trovato / Problemi |
| 4 | Preview Invio | Oggetto, testo mail, allegati, warning privacy/scadenze |
| 5 | Storico Invii | A chi, quando, per quale commessa, quali documenti, esito |

---

## 10. Roadmap Implementazione

| Fase | Descrizione | Dipendenze |
|------|-------------|------------|
| D1 | Libreria tipi documento + archivio documenti | Object Storage |
| D2 | Template pacchetti + generazione checklist | D1 |
| D3 | Matching automatico documenti validi | D1 |
| D4 | UI pacchetto documentale | D2, D3 |
| D5 | Invio email + log | D4, Resend |
| D6 | Profili documentali committente | D5 |

---

## 11. Integrazione con Moduli Esistenti

| Modulo | Integrazione |
|--------|-------------|
| Sicurezza | Dal cantiere: operatori, mezzi, POS, documenti sicurezza |
| Committenza | Legge richiesta cliente/contratto -> checklist (futuro) |
| Dashboard | Mostra: pacchetto pronto/incompleto, scadenze, invii |
