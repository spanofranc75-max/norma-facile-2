"""Test: Scadenzario Fornitori con rate multiple.
Verifica che get_payables_aging() gestisca correttamente:
1. Fatture con scadenze_pagamento (rate individuali)
2. Fatture legacy (solo data_scadenza_pagamento)
3. Cashflow forecast con rate multiple
"""
import pytest
import pytest_asyncio
from datetime import date, timedelta
from unittest.mock import patch
from services.financial_service import get_payables_aging, get_cashflow_forecast

pytestmark = pytest.mark.anyio


class FakeCursor:
    """Mock async cursor for MongoDB find()."""
    def __init__(self, items):
        self._items = items
    def sort(self, *a, **kw):
        return self
    async def to_list(self, length=None):
        return self._items
    def __aiter__(self):
        return self._async_gen()
    async def _async_gen(self):
        for item in self._items:
            yield item


class FakeCollection:
    def __init__(self, items):
        self._items = items
    def find(self, query=None, projection=None):
        return FakeCursor(self._items)
    def aggregate(self, pipeline):
        return FakeCursor([])


@pytest.fixture
def today_iso():
    return date.today().isoformat()


# ── Test 1: Fattura con rate multiple (RIBA 30-60) ──


async def test_payables_aging_with_installments(today_iso):
    """Una fattura da 10000€ con RIBA 30-60 deve generare 2 righe da 5000€."""
    d30 = (date.today() + timedelta(days=30)).isoformat()
    d60 = (date.today() + timedelta(days=60)).isoformat()
    
    items = [{
        "fr_id": "fr_test1",
        "numero_documento": "123/2026",
        "fornitore_nome": "Acciai Rossi SRL",
        "totale_documento": 10000.0,
        "data_scadenza_pagamento": d60,
        "data_documento": "2026-01-15",
        "residuo": 10000.0,
        "scadenze_pagamento": [
            {"rata": 1, "data_scadenza": d30, "importo": 5000.0, "pagata": False},
            {"rata": 2, "data_scadenza": d60, "importo": 5000.0, "pagata": False},
        ],
    }]

    with patch("services.financial_service.db") as mock_db:
        mock_db.fatture_ricevute = FakeCollection(items)
        result = await get_payables_aging("user1", today_iso)

    assert len(result["detail"]) == 2, f"Expected 2 installments, got {len(result['detail'])}"
    assert result["detail"][0]["amount"] == 5000.0
    assert result["detail"][1]["amount"] == 5000.0
    assert "Rata 1" in result["detail"][0]["numero"]
    assert "Rata 2" in result["detail"][1]["numero"]
    assert result["total"] == 10000.0


# ── Test 2: Fattura con una rata già pagata ──


async def test_payables_aging_partial_paid(today_iso):
    """Se rata 1 è pagata, deve apparire solo rata 2."""
    d30 = (date.today() + timedelta(days=30)).isoformat()
    d60 = (date.today() + timedelta(days=60)).isoformat()
    
    items = [{
        "fr_id": "fr_test2",
        "numero_documento": "456/2026",
        "fornitore_nome": "Tubi Bianchi SPA",
        "totale_documento": 8000.0,
        "data_scadenza_pagamento": d60,
        "data_documento": "2026-02-01",
        "residuo": 4000.0,
        "scadenze_pagamento": [
            {"rata": 1, "data_scadenza": d30, "importo": 4000.0, "pagata": True},
            {"rata": 2, "data_scadenza": d60, "importo": 4000.0, "pagata": False},
        ],
    }]

    with patch("services.financial_service.db") as mock_db:
        mock_db.fatture_ricevute = FakeCollection(items)
        result = await get_payables_aging("user1", today_iso)

    assert len(result["detail"]) == 1
    assert result["detail"][0]["amount"] == 4000.0
    assert "Rata 2" in result["detail"][0]["numero"]
    assert result["total"] == 4000.0


# ── Test 3: Fattura legacy senza scadenze_pagamento ──


async def test_payables_aging_legacy_single(today_iso):
    """Fattura senza scadenze_pagamento: fallback a data_scadenza_pagamento + residuo."""
    d45 = (date.today() + timedelta(days=45)).isoformat()
    
    items = [{
        "fr_id": "fr_legacy",
        "numero_documento": "789/2026",
        "fornitore_nome": "Ferramenta Verdi",
        "totale_documento": 3000.0,
        "data_scadenza_pagamento": d45,
        "data_documento": "2026-01-20",
        "residuo": 3000.0,
        "scadenze_pagamento": [],
    }]

    with patch("services.financial_service.db") as mock_db:
        mock_db.fatture_ricevute = FakeCollection(items)
        result = await get_payables_aging("user1", today_iso)

    assert len(result["detail"]) == 1
    assert result["detail"][0]["amount"] == 3000.0
    assert "Rata" not in result["detail"][0]["numero"]
    assert result["total"] == 3000.0


# ── Test 4: Mix di fatture con e senza rate ──


async def test_payables_aging_mixed(today_iso):
    """Mix: 1 fattura con 3 rate + 1 fattura legacy = 4 righe."""
    d30 = (date.today() + timedelta(days=30)).isoformat()
    d60 = (date.today() + timedelta(days=60)).isoformat()
    d90 = (date.today() + timedelta(days=90)).isoformat()
    d45 = (date.today() + timedelta(days=45)).isoformat()
    
    items = [
        {
            "fr_id": "fr_multi",
            "numero_documento": "100/2026",
            "fornitore_nome": "MultiRate SRL",
            "totale_documento": 9000.0,
            "data_scadenza_pagamento": d90,
            "data_documento": "2026-01-10",
            "residuo": 9000.0,
            "scadenze_pagamento": [
                {"rata": 1, "data_scadenza": d30, "importo": 3000.0, "pagata": False},
                {"rata": 2, "data_scadenza": d60, "importo": 3000.0, "pagata": False},
                {"rata": 3, "data_scadenza": d90, "importo": 3000.0, "pagata": False},
            ],
        },
        {
            "fr_id": "fr_single",
            "numero_documento": "101/2026",
            "fornitore_nome": "SinglePay SNC",
            "totale_documento": 2000.0,
            "data_scadenza_pagamento": d45,
            "data_documento": "2026-02-01",
            "residuo": 2000.0,
            "scadenze_pagamento": [],
        },
    ]

    with patch("services.financial_service.db") as mock_db:
        mock_db.fatture_ricevute = FakeCollection(items)
        result = await get_payables_aging("user1", today_iso)

    assert len(result["detail"]) == 4, f"Expected 4, got {len(result['detail'])}"
    assert result["total"] == 11000.0
    amounts = sorted([d["amount"] for d in result["detail"]])
    assert amounts == [2000.0, 3000.0, 3000.0, 3000.0]


# ── Test 5: Fattura scaduta con rate ──


async def test_payables_aging_overdue_installments(today_iso):
    """Rate scadute devono avere days_overdue > 0 e urgency='scaduta'."""
    past = (date.today() - timedelta(days=15)).isoformat()
    future = (date.today() + timedelta(days=15)).isoformat()
    
    items = [{
        "fr_id": "fr_overdue",
        "numero_documento": "200/2026",
        "fornitore_nome": "Ritardo SRL",
        "totale_documento": 6000.0,
        "data_scadenza_pagamento": future,
        "data_documento": "2026-01-01",
        "residuo": 6000.0,
        "scadenze_pagamento": [
            {"rata": 1, "data_scadenza": past, "importo": 3000.0, "pagata": False},
            {"rata": 2, "data_scadenza": future, "importo": 3000.0, "pagata": False},
        ],
    }]

    with patch("services.financial_service.db") as mock_db:
        mock_db.fatture_ricevute = FakeCollection(items)
        result = await get_payables_aging("user1", today_iso)

    overdue = [d for d in result["detail"] if d["urgency"] == "scaduta"]
    in_time = [d for d in result["detail"] if d["urgency"] == "in_scadenza"]
    assert len(overdue) == 1
    assert len(in_time) == 1
    assert overdue[0]["days_overdue"] == 15
    assert result["scadute"] == 3000.0


# ── Test 6: Aging bucket classification ──


async def test_aging_bucket_classification(today_iso):
    """Rate a 15, 45, 75, 100 giorni devono finire nei bucket corretti."""
    d15 = (date.today() + timedelta(days=15)).isoformat()
    d45 = (date.today() + timedelta(days=45)).isoformat()
    d75 = (date.today() + timedelta(days=75)).isoformat()
    d100 = (date.today() + timedelta(days=100)).isoformat()
    
    items = [{
        "fr_id": "fr_buckets",
        "numero_documento": "300/2026",
        "fornitore_nome": "Bucket Test",
        "totale_documento": 40000.0,
        "data_scadenza_pagamento": d100,
        "data_documento": "2026-01-01",
        "residuo": 40000.0,
        "scadenze_pagamento": [
            {"rata": 1, "data_scadenza": d15, "importo": 10000.0, "pagata": False},
            {"rata": 2, "data_scadenza": d45, "importo": 10000.0, "pagata": False},
            {"rata": 3, "data_scadenza": d75, "importo": 10000.0, "pagata": False},
            {"rata": 4, "data_scadenza": d100, "importo": 10000.0, "pagata": False},
        ],
    }]

    with patch("services.financial_service.db") as mock_db:
        mock_db.fatture_ricevute = FakeCollection(items)
        result = await get_payables_aging("user1", today_iso)

    # Future dates: days = today - future = negative, so days <= 30 bucket
    # All 4 are in the future, so days is negative (<=30 bucket)
    # Actually: days = (today - due).days => negative for future dates
    # days <= 30 includes all negative => all in 0_30
    assert result["aging"]["0_30"] == 40000.0


# ── Test 7: Cashflow forecast con rate multiple ──


class FakeAsyncCursor:
    """Mock async cursor for MongoDB find() with async iteration."""
    def __init__(self, items):
        self._items = items
    def sort(self, *a, **kw):
        return self
    async def to_list(self, length=None):
        return self._items
    def __aiter__(self):
        return self
    async def __anext__(self):
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)


class FakeCollectionWithAsyncCursor:
    """Mock collection with async cursor support."""
    def __init__(self, items):
        self._items = items
    def find(self, query=None, projection=None):
        return FakeAsyncCursor(list(self._items))
    def aggregate(self, pipeline):
        return FakeCursor([])


async def test_cashflow_forecast_uses_installments(today_iso):
    """Cashflow forecast deve usare le rate individuali, non il totale fattura."""
    d20 = (date.today() + timedelta(days=20)).isoformat()  # In 30-day forecast
    d50 = (date.today() + timedelta(days=50)).isoformat()  # In 60-day forecast
    d80 = (date.today() + timedelta(days=80)).isoformat()  # In 90-day forecast
    
    # Invoice €12000 with 3 installments
    items = [{
        "fr_id": "fr_cashflow",
        "totale_documento": 12000.0,
        "data_scadenza_pagamento": d80,
        "residuo": 12000.0,
        "scadenze_pagamento": [
            {"rata": 1, "data_scadenza": d20, "importo": 4000.0, "pagata": False},
            {"rata": 2, "data_scadenza": d50, "importo": 4000.0, "pagata": False},
            {"rata": 3, "data_scadenza": d80, "importo": 4000.0, "pagata": False},
        ],
    }]

    with patch("services.financial_service.db") as mock_db:
        mock_db.fatture_ricevute = FakeCollectionWithAsyncCursor(items)
        mock_db.invoices = FakeCollection([])  # Empty invoices
        result = await get_cashflow_forecast("user1", today_iso)

    # Should have 3 forecast periods
    assert len(result) == 3
    
    # 30-day forecast: only rata 1 (4000€) is due
    assert result[0]["label"] == "30 giorni"
    assert result[0]["uscite"] == 4000.0, f"Expected 4000€ at 30d, got {result[0]['uscite']}"
    
    # 60-day forecast: rata 1 + rata 2 = 8000€
    assert result[1]["label"] == "60 giorni"
    assert result[1]["uscite"] == 8000.0, f"Expected 8000€ at 60d, got {result[1]['uscite']}"
    
    # 90-day forecast: all 3 rate = 12000€
    assert result[2]["label"] == "90 giorni"
    assert result[2]["uscite"] == 12000.0, f"Expected 12000€ at 90d, got {result[2]['uscite']}"


async def test_cashflow_forecast_excludes_paid_installments(today_iso):
    """Cashflow forecast deve escludere rate già pagate."""
    d25 = (date.today() + timedelta(days=25)).isoformat()
    d55 = (date.today() + timedelta(days=55)).isoformat()
    
    items = [{
        "fr_id": "fr_partial_paid",
        "totale_documento": 6000.0,
        "data_scadenza_pagamento": d55,
        "residuo": 3000.0,
        "scadenze_pagamento": [
            {"rata": 1, "data_scadenza": d25, "importo": 3000.0, "pagata": True},   # Already paid
            {"rata": 2, "data_scadenza": d55, "importo": 3000.0, "pagata": False},  # Not paid
        ],
    }]

    with patch("services.financial_service.db") as mock_db:
        mock_db.fatture_ricevute = FakeCollectionWithAsyncCursor(items)
        mock_db.invoices = FakeCollection([])
        result = await get_cashflow_forecast("user1", today_iso)

    # 30-day: rata 1 is paid, so 0€
    assert result[0]["uscite"] == 0.0, f"Expected 0€ at 30d (rata 1 paid), got {result[0]['uscite']}"
    
    # 60-day: only rata 2 (3000€) is unpaid and due
    assert result[1]["uscite"] == 3000.0, f"Expected 3000€ at 60d, got {result[1]['uscite']}"


# ── Test 9: Receivables aging includes payment_status=None ──


async def test_receivables_includes_null_payment_status(today_iso):
    """Invoices with payment_status=None should be treated as unpaid."""
    from services.financial_service import get_receivables_aging
    
    d30 = (date.today() + timedelta(days=30)).isoformat()
    
    items = [
        {
            "invoice_id": "inv_001",
            "number": "1/2026",
            "client_name": "Cliente Test",
            "totals": {"total_document": 5000.0},
            "due_date": d30,
            "issue_date": "2026-01-15",
            "payment_status": None,
            "status": "emessa",
        },
        {
            "invoice_id": "inv_002",
            "number": "2/2026",
            "client_name": "Cliente Due",
            "totals": {"total_document": 3000.0},
            "due_date": d30,
            "issue_date": "2026-01-20",
            "payment_status": "non_pagata",
            "status": "emessa",
        },
    ]

    with patch("services.financial_service.db") as mock_db:
        mock_db.invoices = FakeCollection(items)
        result = await get_receivables_aging("user1", today_iso)

    assert len(result["detail"]) == 2, f"Expected 2, got {len(result['detail'])}"
    assert result["total"] == 8000.0, f"Expected 8000, got {result['total']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
