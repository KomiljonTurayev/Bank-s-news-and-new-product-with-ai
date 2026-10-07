"""`/api/health`ning manba-ma'nodagi holati: bitta tirik manba
qolganlarining uzilganini yashirmasligi kerak."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api import app
from app.connectors.registry import CONNECTORS
from app.models import BankRate
from app.routers import meta as meta_router


# --- monitoring: bitta tirik manba qolganlarini yashirmasin ----------------


def _rate(session, source, fetched_at):
    session.add(
        BankRate(
            bank_code=source.bank_code,
            product_type=source.product_type,
            segment=source.segment,
            data={"value": 1.0},
            fetched_at=fetched_at,
        )
    )


def test_health_flags_the_sources_that_stopped_updating(session_factory):
    """Global `max(fetched_at)` bitta tirik konektor bilan qolganlarining
    o'limini yashirardi — monitoring "hammasi ok" deb uyquga ketardi."""
    session = session_factory()
    _rate(session, CONNECTORS[0], datetime.now(timezone.utc))
    session.commit()
    session.close()

    body = TestClient(app).get("/api/health").json()
    total = len(meta_router._source_addresses())

    assert body["status"] == "ok", "tizim darajasi o'zgarmasligi kerak"
    assert body["sources"]["total"] == total
    assert body["sources"]["stale"] == total - 1
    live = f"{CONNECTORS[0].bank_code}/{CONNECTORS[0].product_type}/{CONNECTORS[0].segment}"
    assert live not in body["sources"]["sample"]


def test_health_sample_stays_small_when_everything_is_dead(session_factory):
    session_factory()

    body = TestClient(app).get("/api/health").json()

    assert body["status"] == "stale"
    assert body["sources"]["stale"] == len(meta_router._source_addresses())
    assert len(body["sources"]["sample"]) <= 10


def test_source_addresses_are_the_distinct_row_targets():
    """Ikkita xato, birinchi versiyada ikkalasi ham bor edi:
    (1) bir manzilga yozuvchi bir necha sahifa (ORIENT krediti 6 URL) necha marta
    sanalsa, necha manba o'lganini o'qib bo'lmaydi;
    (2) agregatorlar (depozit.uz, uzse.uz) qatorni o'z banki kodi ostida yozadi —
    registrdagi manzilida qator HECH QACHON bo'lmaydi, doim "stale" turardi va
    monitoring birinchi kundan yolg'onga o'rganardi."""
    addresses = meta_router._source_addresses()

    assert len(addresses) == len(set(addresses)), "manzillar takrorlanmasligi kerak"
    assert all(code != "AGGREGATED" for code, _, _ in addresses)

    duplicated = [
        key for key in addresses
        if sum((c.bank_code, c.product_type, c.segment) == key for c in CONNECTORS) > 1
    ]
    assert duplicated, "bir manzilga yozuvchi bir necha sahifa registrda bor"


def _two_source_pair():
    """Health uchun ikki mustaqil manba: bazada o'z manzilida qator qoldiradigan,
    bir-biriga ustma-bir tushmaydigan ikkitasi. `CONNECTORS[1]` agregator
    (u qatorni o'z banki kodi ostida yozadi, monitoring hisoblamaydi)."""
    seen = set()
    pair = []
    for source in CONNECTORS:
        key = (source.bank_code, source.product_type, source.segment)
        if key[0] == "AGGREGATED" or key in seen:
            continue
        seen.add(key)
        pair.append(source)
        if len(pair) == 2:
            return pair
    raise AssertionError("registrda ikki xil manzil topilmadi")


def test_health_marks_an_idle_source_stale_but_not_a_fresh_one(session_factory, monkeypatch):
    """Biri yangi, biri o'lgan ikki manba: `stale`da faqat o'lgani qoladi,
    `status` esa `ok` — eng so'nggi yozuv tiriku. Global `max` bu juftlikda
    ikkalasini ham "tirik" ko'rsatardi."""
    stale_after = timedelta(minutes=TestClient(app).get("/api/health").json()["stale_after_minutes"])
    idle_source, fresh_source = _two_source_pair()
    session = session_factory()
    _rate(session, idle_source, datetime.now(timezone.utc) - stale_after - timedelta(minutes=1))
    _rate(session, fresh_source, datetime.now(timezone.utc))
    session.commit()
    session.close()

    # Faqat shu ikki manba ko'rinadi: qolganlarining "bazada yozuvi yo'q"
    # shovqini natijani o'qib bo'ladigan qilmas edi.
    monkeypatch.setattr(meta_router, "CONNECTORS", [idle_source, fresh_source])
    body = TestClient(app).get("/api/health").json()

    idle = f"{idle_source.bank_code}/{idle_source.product_type}/{idle_source.segment}"
    fresh = f"{fresh_source.bank_code}/{fresh_source.product_type}/{fresh_source.segment}"
    assert body["status"] == "ok"
    assert body["sources"]["total"] == 2
    assert body["sources"]["stale"] == 1
    assert body["sources"]["sample"] == [idle]
    assert fresh not in body["sources"]["sample"]
