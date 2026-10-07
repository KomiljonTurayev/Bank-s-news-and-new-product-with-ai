import logging
import threading
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.connectors.base import BaseConnector
from app.models import BankRate
from app.scheduler import _run_one, run_all_connectors


class FakeConnector(BaseConnector):
    bank_code = "TESTBANK"
    product_type = "deposit"
    segment = "individual"

    def __init__(self, records, bank_code="TESTBANK"):
        self._records = records
        self.bank_code = bank_code

    def fetch_raw(self):
        return None

    def parse(self, raw):
        return self._records

    def set_records(self, records):
        self._records = records


class FailingConnector(BaseConnector):
    bank_code = "BROKEN"
    product_type = "deposit"
    segment = "individual"

    def fetch_raw(self):
        raise RuntimeError("tarmoq xatosi")

    def parse(self, raw):
        return []


def test_run_one_reports_inserted_then_unchanged(session_factory, caplog):
    connector = FakeConnector([{"name": "A", "rate": "10%"}])

    with caplog.at_level(logging.INFO):
        _run_one(connector)
    assert "1 yangi, 0 o'zgarishsiz" in caplog.text

    caplog.clear()
    with caplog.at_level(logging.INFO):
        _run_one(connector)
    assert "0 yangi, 1 o'zgarishsiz" in caplog.text

    with session_factory() as session:
        assert len(session.query(BankRate).all()) == 1


def test_run_one_logs_and_swallows_connector_exceptions(session_factory, caplog):
    with caplog.at_level(logging.ERROR):
        _run_one(FailingConnector())

    assert "BROKEN connectorida xatolik" in caplog.text


def test_run_all_connectors_dedups_across_full_cycle(session_factory, monkeypatch):
    connectors = [
        FakeConnector([{"name": "A", "rate": "10%"}], bank_code="BANK1"),
        FakeConnector([{"name": "B", "rate": "20%"}], bank_code="BANK2"),
    ]
    monkeypatch.setattr("app.scheduler.CONNECTORS", connectors)
    # Testdagi StaticPool bitta ulanishni thread'lar orasida baham ko'radi
    # (production'dagi WAL rejimli fayl bazasidan farqli) — chinakam
    # parallel flush'lar shu bitta ulanishni buzib qo'yishi mumkin. Bu yerda
    # ThreadPoolExecutor'ning o'zini emas, dedup mantig'ini tekshiramiz,
    # shu sabab worker'ni 1 taga tushirib ketma-ket ishlatamiz.
    monkeypatch.setattr("app.scheduler._MAX_WORKERS", 1)

    run_all_connectors()
    with session_factory() as session:
        assert len(session.query(BankRate).all()) == 2

    # Ikkinchi siklda ma'lumot o'zgarmagan — qatorlar soni oshmasligi kerak.
    run_all_connectors()
    with session_factory() as session:
        assert len(session.query(BankRate).all()) == 2

    # Endi bitta bank yangi kurs qaytaradi — faqat o'sha bank uchun yangi
    # qator qo'shiladi.
    connectors[0].set_records([{"name": "A", "rate": "12%"}])
    run_all_connectors()
    with session_factory() as session:
        rows = session.query(BankRate).filter_by(bank_code="BANK1").all()
        assert len(rows) == 2
        rows = session.query(BankRate).filter_by(bank_code="BANK2").all()
        assert len(rows) == 1


class HangingConnector:
    """`run()` tugashini kutishni to'xtatmaydigan manba — transport timeouti
    ham yordam bermagan holatni taqlid qiladi (masalan javobsiz proksi)."""

    bank_code = "HANG"
    product_type = "deposit"

    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()
        self.finished = threading.Event()

    def run(self):
        self.started.set()
        self.release.wait(timeout=10)
        self.finished.set()
        return SimpleNamespace(total=0, inserted=0, unchanged=0)


def test_cycle_deadline_does_not_wait_for_a_hanging_source(session_factory, monkeypatch, caplog):
    """Bitta manba osilib qolsa, sikl cheksiz kutmaydi — aks holda
    `max_instances=1` tufayli barcha keyingi yangilanishlar to'xtab qolardi."""
    hanging = HangingConnector()
    monkeypatch.setattr("app.scheduler.CONNECTORS", [hanging])
    monkeypatch.setattr("app.scheduler._cycle_deadline_seconds", lambda: 0.1)

    with caplog.at_level(logging.INFO):
        run_all_connectors()

    assert "1 ta manba natija bermadi" in caplog.text
    assert "HANG" in caplog.text
    assert "0 muvaffaqiyatli, 0 xato, 1 tugamagan (1 manba)" in caplog.text
    # Sikl darhol qaytdi — osilib qolgan oqim orqaga tortib qolmadi.
    assert not hanging.finished.is_set()

    hanging.release.set()
    assert hanging.finished.wait(timeout=10)


def test_overlapping_cycle_is_skipped_instead_of_stacking(session_factory, monkeypatch, caplog):
    """Startapdagi birinchi skreyping hali ketayotganda jadval tikishi
    ikkinchi to'lqinni boshlamaydi."""
    first_wave = HangingConnector()
    monkeypatch.setattr("app.scheduler.CONNECTORS", [first_wave])

    first = threading.Thread(target=run_all_connectors)
    first.start()
    try:
        assert first_wave.started.wait(timeout=10)
        with caplog.at_level(logging.WARNING):
            run_all_connectors()
        assert "o'tkazib yuborildi" in caplog.text
    finally:
        first_wave.release.set()
        first.join(timeout=10)
    assert not first.is_alive()


def test_sources_stuck_behind_the_deadline_are_not_started_afterwards(monkeypatch, caplog):
    """Muddatga yetmagan navbat keyin bajarilmasligi kerak: aks holda sekin
    manbalar har siklda qoldiq qator orttirib, bir-birining ustiga chiqqan
    cheksiz yuk berardi. Bunday banklar keyingi tikilda o'qiladi."""
    hanging = HangingConnector()
    queued = HangingConnector()
    queued.bank_code = "QUEUED"
    monkeypatch.setattr("app.scheduler.CONNECTORS", [hanging, queued])
    monkeypatch.setattr("app.scheduler._MAX_WORKERS", 1)
    monkeypatch.setattr("app.scheduler._cycle_deadline_seconds", lambda: 0.1)

    with caplog.at_level(logging.ERROR):
        run_all_connectors()

    assert not queued.started.is_set()
    assert "1 tasiga navbat yetmadi" in caplog.text
    hanging.release.set()
