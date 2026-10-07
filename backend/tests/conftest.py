import os

# PROFILE'ning standart qiymati yo'q (config/__init__.py:get_settings) —
# testlar dev profilida ishlaydi; `app.*` import qilinishidan OLDIN
# o'rnatiladi, chunki sozlamalar import paytida yuklanadi.
os.environ.setdefault("PROFILE", "dev")

# Kunlik jadval STANDART HOLATDA yoqiq ("09:00,14:00") — testlarni devor
# soatiga bog'lardi: 09:45 oldidan/yolidan keyin o'qxigan health kutilmalari
# tongida yiqilardi. Bu yerdа majburiy o'chiriladi (setdefault EMAS — lokal
# .env/CI env ham test ma'nosini o'zgartira olmasin); jadval rejimining o'zi
# tests/test_schedule.py + test_schedule_wiring.py'da soat monkeypatch
# bilan qat'iy sinovdan o'tadi.
os.environ["SCRAPE_TIMES"] = ""

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import Base  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_breakers():
    """Circuit breaker holati butun jarayon davomida saqlanadi — bu foydali,
    lekin testlar bir xil host nomidan foydalangani uchun bitta testdagi
    "bu sayt o'lik" qarori keyingisiga o'tib qolmasligi kerak."""
    from app.resilience import reset_breakers

    reset_breakers()
    yield
    reset_breakers()


@pytest.fixture(autouse=True)
def _always_active_outbound(monkeypatch):
    """Tashqariga chiqish siyosati (app/outbound.py) soatlarga bog'liq,
    testlar esa soatga bog'liq bo'lmasligi kerak. Standart `07:00-21:00`
    oynasida ishlaydigan scheduler testi Toshkentda 22:00 bo'lganda yiqilardi
    (sikl darvoza tufayli umuman boshlanmaydi), host tanaffusi esa har bir
    testga 2 soniyalik uyqu qo'shar edi. Bu yerda ikkala qoida ham o'chiriladi;
    darvozaning o'zi tests/test_outbound.py'da sinovdan o'tadi."""
    from app import outbound

    monkeypatch.setattr(outbound.settings, "scrape_active_window", "")
    monkeypatch.setattr(outbound.settings, "min_host_interval_seconds", 0.0)
    outbound.reset_pacer()
    yield
    outbound.reset_pacer()


@pytest.fixture
def session_factory(monkeypatch):
    """Har bir testga alohida, xotiradagi (in-memory) SQLite baza beradi.

    StaticPool shart: FastAPI TestClient endpoint'larni alohida thread'da
    ishga tushiradi, StaticPool esa bitta ulanishni barcha thread'lar bilan
    baham ko'rish orqali xotiradagi bazani yo'qolib qolishdan saqlaydi.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    monkeypatch.setattr("app.db.SessionLocal", TestSessionLocal)
    monkeypatch.setattr("app.connectors.base.SessionLocal", TestSessionLocal)
    monkeypatch.setattr("app.routers.meta.SessionLocal", TestSessionLocal)
    monkeypatch.setattr("app.routers.rates.SessionLocal", TestSessionLocal)
    monkeypatch.setattr("app.routers.products.SessionLocal", TestSessionLocal)

    return TestSessionLocal
