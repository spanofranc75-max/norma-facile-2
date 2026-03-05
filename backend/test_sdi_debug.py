"""
Debug SDI: simula l'invio per le fatture dell'utente reale.
"""
import asyncio, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REAL_USER_ID = "user_97c773827822"

async def main():
    from motor.motor_asyncio import AsyncIOMotorClient
    from dotenv import load_dotenv
    load_dotenv()
    
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    
    from services.fattureincloud_api import (
        get_fic_client, map_fattura_to_fic,
        validate_invoice_for_sdi, extract_fic_error_message,
    )
    
    # Real user company settings
    company = await db.company_settings.find_one({"user_id": REAL_USER_ID}, {"_id": 0}) or {}
    print(f"=== Company Settings (user: {REAL_USER_ID}) ===")
    print(f"  P.IVA: {company.get('partita_iva', 'N/D')}")
    print(f"  CF: {company.get('codice_fiscale', 'N/D')}")
    print(f"  Indirizzo: {company.get('address', 'N/D')}")
    print(f"  CAP: {company.get('cap', 'N/D')}, Citta: {company.get('city', 'N/D')}")
    
    fic_token = company.get("fic_access_token") or os.environ.get("FIC_ACCESS_TOKEN")
    fic_company_id = company.get("fic_company_id") or os.environ.get("FIC_COMPANY_ID")
    print(f"  FIC Token: {'✅' if fic_token else '❌'}")
    print(f"  FIC Company ID: {fic_company_id or '❌'}")
    print()
    
    # Real user invoices in emessa status
    invoices = await db.invoices.find(
        {"user_id": REAL_USER_ID, "status": "emessa", "document_type": "FT"},
        {"_id": 0}
    ).sort("document_number", -1).to_list(10)
    
    print(f"=== {len(invoices)} fatture 'emessa' per utente reale ===\n")
    
    for inv in invoices:
        doc_num = inv.get("document_number", "?")
        inv_id = inv.get("invoice_id")
        
        print(f"{'='*60}")
        print(f"📄 FATTURA {doc_num} (ID: {inv_id})")
        
        # Lines summary
        lines = inv.get("lines", [])
        total_netto = sum(l.get("line_total", 0) for l in lines)
        total_iva = sum(l.get("vat_amount", 0) for l in lines)
        print(f"   Righe: {len(lines)}, Netto: {total_netto:.2f}€, IVA: {total_iva:.2f}€, Lordo: {total_netto + total_iva:.2f}€")
        print(f"   FIC doc ID esistente: {inv.get('fic_document_id', 'Nessuno')}")
        
        for i, l in enumerate(lines):
            neg = " ⚠️ NEGATIVO" if l.get("unit_price", 0) < 0 or l.get("line_total", 0) < 0 else ""
            print(f"   Riga {i+1}: {l.get('description','')[:70]}... | {l.get('quantity',0)} x {l.get('unit_price',0):.2f}€ = {l.get('line_total',0):.2f}€ (IVA {l.get('vat_rate','?')}%){neg}")
        
        # Client
        client_doc = await db.clients.find_one({"client_id": inv.get("client_id")}, {"_id": 0}) or {}
        print(f"\n   👤 Cliente: {client_doc.get('business_name', '???')}")
        print(f"      P.IVA: {client_doc.get('partita_iva', 'N/D')} | CF: {client_doc.get('codice_fiscale', 'N/D')}")
        print(f"      SDI: {client_doc.get('codice_sdi', 'N/D')} | PEC: {client_doc.get('pec', 'N/D')}")
        
        # STEP 1: Validation
        print(f"\n   🔍 VALIDAZIONE:")
        errors = validate_invoice_for_sdi(inv, client_doc, company)
        if errors:
            for e in errors:
                print(f"   ❌ {e}")
            print()
            continue
        print(f"   ✅ Validazione OK")
        
        # STEP 2: Map to FIC
        print(f"\n   📦 MAPPING FIC:")
        try:
            fic_data = map_fattura_to_fic(inv, client_doc)
            # Show payload with key fields
            print(f"   type: {fic_data.get('data', {}).get('type')}")
            print(f"   number: {fic_data.get('data', {}).get('number')}")
            print(f"   date: {fic_data.get('data', {}).get('date')}")
            entity = fic_data.get('data', {}).get('entity', {})
            print(f"   entity.name: {entity.get('name')}")
            print(f"   entity.vat_number: {entity.get('vat_number')}")
            items = fic_data.get('data', {}).get('items_list', [])
            print(f"   items_list ({len(items)} righe):")
            for j, item in enumerate(items):
                print(f"      [{j}] qty={item.get('qty')} price={item.get('net_price')} vat={item.get('vat', {}).get('id', '?')} desc={str(item.get('name', ''))[:50]}...")
            
            # Full payload for reference
            print(f"\n   --- FULL FIC PAYLOAD ---")
            print(json.dumps(fic_data, indent=2, default=str))
            print(f"   --- END PAYLOAD ---")
        except Exception as e:
            print(f"   ❌ ERRORE MAPPING: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        # STEP 3: Call FIC
        if not fic_token or not fic_company_id:
            print(f"\n   ⚠️ No FIC credentials, skip API call")
            continue
        
        fic = get_fic_client(access_token=fic_token, company_id=int(fic_company_id))
        fic_doc_id = inv.get("fic_document_id")
        
        print(f"\n   🌐 CHIAMATA FIC API:")
        if not fic_doc_id:
            try:
                import httpx
                result = await fic.create_issued_invoice(fic_data)
                fic_doc_id = result.get("data", {}).get("id")
                print(f"   ✅ Creato su FIC: ID = {fic_doc_id}")
            except Exception as e:
                if hasattr(e, 'response'):
                    print(f"   ❌ ERRORE CREATE ({e.response.status_code}):")
                    print(f"   --- ERROR RESPONSE BODY ---")
                    print(f"   {e.response.text}")
                    print(f"   --- FINE ---")
                else:
                    print(f"   ❌ {type(e).__name__}: {e}")
                continue
        else:
            print(f"   Doc gia' su FIC: {fic_doc_id}")
        
        # STEP 4: SDI
        print(f"\n   📡 INVIO SDI:")
        try:
            import httpx
            sdi_result = await fic.send_to_sdi(fic_doc_id)
            print(f"   ✅ SDI OK: {json.dumps(sdi_result, indent=2, default=str)[:300]}")
        except Exception as e:
            if hasattr(e, 'response'):
                print(f"   ❌ ERRORE SDI ({e.response.status_code}):")
                print(f"   --- ERROR RESPONSE BODY ---")
                print(f"   {e.response.text}")
                print(f"   --- FINE ---")
            else:
                print(f"   ❌ {type(e).__name__}: {e}")
        print()

if __name__ == "__main__":
    asyncio.run(main())
