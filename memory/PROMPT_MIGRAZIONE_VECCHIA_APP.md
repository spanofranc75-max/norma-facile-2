# PROMPT PER AGENTE EMERGENT — EXPORT DATI PER MIGRAZIONE

## OBIETTIVO
Devi creare **un unico endpoint API** che esporta tutti i dati per la migrazione verso la nuova app Norma Facile 2.0.

## ENDPOINT DA CREARE

### `GET /api/export/migrazione-completa`

Questo endpoint deve restituire un JSON con **4 sezioni**. Non serve autenticazione (è un export one-time).

```json
{
  "preventivi": [...],
  "fatture_vendita": [...],
  "fatture_acquisto": [...],
  "anagrafica": [...]
}
```

---

## 1. PREVENTIVI (`preventivi`)

Per ogni preventivo, esporta questi campi ESATTI con questi nomi:

```json
{
  "number": "PRV-2024/0001",
  "client_business_name": "Nome Cliente SRL",
  "client_partita_iva": "IT12345678901",
  "client_codice_fiscale": "RSTMRC80A01H501Z",
  "client_codice_sdi": "ABC1234",
  "client_pec": "cliente@pec.it",
  "client_address": "Via Roma 1",
  "client_cap": "00100",
  "client_city": "Roma",
  "client_province": "RM",
  "subject": "Oggetto del preventivo",
  "date": "2024-06-15",
  "validity_days": 30,
  "status": "accettato",
  "payment_type": "Bonifico 30gg",
  "notes": "Note visibili al cliente",
  "sconto_globale": 0,
  "acconto": 0,
  "lines": [
    {
      "description": "Carpenteria metallica per capannone",
      "codice_articolo": "CARP-001",
      "quantity": 1.0,
      "unit": "kg",
      "unit_price": 2.50,
      "sconto_1": 0,
      "sconto_2": 0,
      "vat_rate": "22",
      "notes": ""
    }
  ],
  "totals": {
    "subtotal": 2500.00,
    "sconto_globale_value": 0,
    "imponibile": 2500.00,
    "iva": 550.00,
    "total": 3050.00
  }
}
```

**IMPORTANTE**: Includi TUTTI i preventivi, anche quelli vecchi/rifiutati. Lo stato deve essere uno di: `bozza`, `inviato`, `accettato`, `rifiutato`, `scaduto`.

---

## 2. FATTURE DI VENDITA (`fatture_vendita`)

Fatture attive già trasmesse allo SDI. Per ogni fattura:

```json
{
  "document_type": "FT",
  "document_number": "FT-2024-001",
  "client_business_name": "Nome Cliente SRL",
  "client_partita_iva": "IT12345678901",
  "client_codice_fiscale": "RSTMRC80A01H501Z",
  "client_codice_sdi": "ABC1234",
  "client_pec": "cliente@pec.it",
  "client_address": "Via Roma 1",
  "client_cap": "00100",
  "client_city": "Roma",
  "client_province": "RM",
  "issue_date": "2024-06-20",
  "due_date": "2024-07-20",
  "status": "emessa",
  "sdi_status": "consegnata",
  "sdi_id": "IT01234567890_ABCDE",
  "payment_method": "bonifico",
  "payment_terms": "30gg",
  "lines": [
    {
      "code": "CARP-001",
      "description": "Carpenteria metallica",
      "quantity": 100.0,
      "unit_price": 25.00,
      "discount_percent": 0.0,
      "vat_rate": "22",
      "line_total": 2500.00,
      "vat_amount": 550.00
    }
  ],
  "totals": {
    "subtotal": 2500.00,
    "total_vat": 550.00,
    "total_document": 3050.00,
    "total_to_pay": 3050.00
  },
  "tax_settings": {
    "apply_rivalsa_inps": false,
    "rivalsa_inps_rate": 4.0,
    "apply_cassa": false,
    "cassa_type": "",
    "cassa_rate": 4.0,
    "apply_ritenuta": false,
    "ritenuta_rate": 20.0
  },
  "notes": "",
  "linked_preventivo_number": "PRV-2024/0001"
}
```

**IMPORTANTE**: 
- Includi lo stato SDI se disponibile (`consegnata`, `accettata`, `rifiutata`, `scartata`)
- Includi l'ID SDI se disponibile
- Se la fattura deriva da un preventivo, includi il numero del preventivo in `linked_preventivo_number`

---

## 3. FATTURE DI ACQUISTO (`fatture_acquisto`)

Fatture passive ricevute dallo SDI. Per ogni fattura:

```json
{
  "fornitore_nome": "Acciaierie Beltrame SPA",
  "fornitore_partita_iva": "IT98765432101",
  "fornitore_codice_fiscale": "98765432101",
  "fornitore_address": "Via dell'Industria 10",
  "fornitore_cap": "36100",
  "fornitore_city": "Vicenza",
  "fornitore_province": "VI",
  "tipo_documento": "TD01",
  "numero_documento": "2024/1234",
  "data_documento": "2024-06-10",
  "data_ricezione": "2024-06-12",
  "sdi_id": "IT98765432101_FGHIJ",
  "status": "registrata",
  "payment_status": "pagata",
  "data_scadenza_pagamento": "2024-07-10",
  "modalita_pagamento": "Bonifico",
  "condizioni_pagamento": "30gg DFFM",
  "linee": [
    {
      "numero_linea": 1,
      "codice_articolo": "IPE-200",
      "descrizione": "Profilato IPE 200x100x5.6 S275JR",
      "quantita": 500.0,
      "unita_misura": "kg",
      "prezzo_unitario": 1.20,
      "sconto_percent": 0,
      "aliquota_iva": "22",
      "importo": 600.00
    }
  ],
  "imponibile": 600.00,
  "imposta": 132.00,
  "totale_documento": 732.00,
  "totale_pagato": 732.00,
  "residuo": 0.00,
  "pagamenti": [
    {
      "data": "2024-07-08",
      "importo": 732.00,
      "metodo": "Bonifico",
      "note": ""
    }
  ],
  "notes": ""
}
```

**IMPORTANTE**:
- Includi lo storico pagamenti se disponibile
- Includi la data scadenza pagamento — è fondamentale per lo scadenziario
- Se l'XML SDI originale è salvato in base64, includi il campo `xml_base64` (opzionale)

---

## 4. ANAGRAFICA CLIENTI/FORNITORI (`anagrafica`)

Unifica clienti e fornitori in un'unica lista. Per ogni soggetto:

```json
{
  "tipo": "cliente",
  "business_name": "Nome SRL",
  "client_type": "azienda",
  "codice_fiscale": "RSTMRC80A01H501Z",
  "partita_iva": "IT12345678901",
  "codice_sdi": "ABC1234",
  "pec": "nome@pec.it",
  "address": "Via Roma 1",
  "cap": "00100",
  "city": "Roma",
  "province": "RM",
  "country": "IT",
  "phone": "+39 06 1234567",
  "email": "info@nome.it",
  "notes": "Cliente storico"
}
```

`tipo` deve essere: `cliente`, `fornitore`, o `entrambi`.
`client_type` deve essere: `azienda`, `professionista`, o `privato`.

---

## NOTE TECNICHE

1. **L'endpoint non deve richiedere autenticazione** — è per un export one-time
2. **Restituisci TUTTI i record**, senza limiti di paginazione
3. Se un campo non è disponibile, usa stringa vuota `""` (non `null`)
4. Le date devono essere in formato `YYYY-MM-DD`
5. I numeri devono essere numeri (non stringhe)
6. L'endpoint deve rispondere in meno di 60 secondi

## ESEMPIO DI RISPOSTA FINALE

```json
{
  "export_date": "2024-06-25T10:30:00Z",
  "app_name": "Norma Facile (vecchia)",
  "totals": {
    "preventivi": 45,
    "fatture_vendita": 32,
    "fatture_acquisto": 78,
    "anagrafica": 56
  },
  "preventivi": [...],
  "fatture_vendita": [...],
  "fatture_acquisto": [...],
  "anagrafica": [...]
}
```

Crea l'endpoint e dimmi quando è pronto. L'URL sarà usato dalla nuova app per importare automaticamente tutti i dati.
