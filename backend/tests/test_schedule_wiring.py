"""Jadval qatlamining *ulanish* sinovlari.

`tests/test_schedule.py` sof matematikani (parse, keyingi/o'tgan tikish,
gap'lar) sinaydi. Bu fayl boshqa savolga javob beradi: o'sha matematika kod
ning to'g'ri nuqtasiga ulangansmi — APScheduler triggerlari Toshkent soati
bilan quriladimi, startap reja tashqarisida tashqi manbalarga chiqadimi,
`/api/health` kuniga 2 marta rejimida tuni "eskirish" deb o'ylamaydimi.

Konftest `SCRAPE_TIMES=""` qilib jadvalni o'chiradi (aks holda butun suite
devor soatiga bog'lanardi); shu sabab jadval rejimining har bir testi
ro'yxatni o'zi yoqadi va soatni `app.schedule.utc_now` nuqtasidan almashtiradi.
"""
from datetime import datetime, timedelta, timezone

import pytest
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi.testclient import TestClient

from app import schedule
from app.api import app
from app.config import FETCH_INTERVAL_MINUTES
from app.models import BankRate
from app.schedule import TASHKENT, max_gap_minutes, parse_times
from app.scheduler import _cycle_deadline_seconds, startup_scrape, start_scheduler

# Umumiy kun: 2026-10-01, talab qilingan jadval [09:00, 14:00].
TIMES = parse_times("09:00,14:00")


def tk(hour: int, minute: int = 0) -> datetime:
    """2026-10-01, Toshkent vaqti — jadval huquqi shu."""
    return datetime(2026, 10, 1, hour, minute, tzinfo=TASHKENT)


def yday(hour: int, minute: int = 0) -> datetime:
    """2026-09-30 — tk() kunining kechasi (1-okabr uchun oldingi kun sentabrda)."""
    return datetime(2026, 9, 30, hour, minute, tzinfo=TASHKENT)


def naive_utc(moment: datetime) -> datetime:
    """Toshkent aware vaqtini DB konvensiyasiga o'giradi: `BankRate.fetched_at`
    SQLite'da naive UTC sifatida saqlanadi (q. app/routers/meta.py:_as_utc)."""
    return moment.astimezone(timezone.utc).replace(tzinfo=None)


@pytest.fixture
def clock(monkeypatch):
    """Yagona soat manbasi — scheduler, startap va health bir damda tursin."""
    def set_moment(tashkent_moment: datetime):
        monkeypatch.setattr(schedule, "utc_now",
                            lambda: tashkent_moment.astimezone(timezone.utc))
    return set_moment


@pytest.fixture
def scrapes(monkeypatch):
    """Sikl o'rniga yozuvchi — tarmoqqa chiqmasdan 'urildi_mi'ni bilamiz."""
    calls: list[str] = []
    monkeypatch.setattr("app.scheduler.run_all_connectors", lambda: calls.append("cycle"))
    return calls


@pytest.fixture
def schedule_mode(monkeypatch):
    monkeypatch.setattr("app.scheduler.SCRAPE_TIMES", TIMES)
    return TIMES


def seed(session_factory, fetched_at: datetime) -> None:
    with session_factory() as session:
        session.add(BankRate(bank_code="A", product_type="deposit",
                             segment="individual", data={}, fetched_at=fetched_at))
        session.commit()


# --- APScheduler triggerlari --------------------------------------------------

def test_schedule_mode_builds_one_cron_job_per_hour(schedule_mode):
    """Talab — kuniga aynan 2 tortish. Interval trigger buni ifodalay olmaydi:
    `minutes=60` soatiga bir marta degani."""
    scheduler = start_scheduler()
    try:
        jobs = {job.id: job for job in scheduler.get_jobs()}
        assert {"scrape_0900", "scrape_1400"} <= set(jobs)
        assert isinstance(jobs["scrape_0900"].trigger, CronTrigger)
        fields = {f.name: str(f) for f in jobs["scrape_0900"].trigger.fields}
        assert (fields["hour"], fields["minute"]) == ("9", "0")
    finally:
        scheduler.shutdown(wait=False)


def test_cron_next_run_is_tashkent_regardless_of_container_clock(schedule_mode):
    """Konteyner UTC'da yursа ham 09:00 — Toshkentdagi 09:00. Soat huquqi
    trigger'ning o'zida, jarayon muhitida emas."""
    scheduler = start_scheduler()
    try:
        job = scheduler.get_job("scrape_0900")
        assert job.next_run_time.utcoffset() == timedelta(hours=5)
        assert (job.next_run_time.hour, job.next_run_time.minute) == (9, 0)
    finally:
        scheduler.shutdown(wait=False)


def test_empty_schedule_keeps_the_old_interval_behaviour(monkeypatch):
    """`SCRAPE_TIMES=` bo'sh = jadval o'chiq: eski soatlik qadamga qaytish.
    Xato konfiguratsiya skreypingni butunlay o'ldirmasin."""
    monkeypatch.setattr("app.scheduler.SCRAPE_TIMES", [])
    scheduler = start_scheduler()
    try:
        scrape_jobs = [j for j in scheduler.get_jobs()
                       if j.func.__name__ == "run_all_connectors"]
        assert len(scrape_jobs) == 1
        trigger = scrape_jobs[0].trigger
        assert isinstance(trigger, IntervalTrigger)
        assert trigger.interval == timedelta(minutes=FETCH_INTERVAL_MINUTES)
    finally:
        scheduler.shutdown(wait=False)


# --- sikl watchdog'i ----------------------------------------------------------

def test_scheduled_cycle_deadline_stays_capped(schedule_mode):
    """Jadvalda tikishlar orasi soatlab (09→14 = 300 daqiqa), lekin osiq sikl
    keyingi tikishga yo'l qo'ymasligi uchun chegava baribir 54 daqiqa."""
    assert _cycle_deadline_seconds() == 54 * 60


def test_deadline_follows_the_tightest_gap(monkeypatch):
    """Jadval siqilsa (09:00/09:30) watchdog ham siqiladi — osiq sikl
    30 daqiqadan keyin yo'l berishi kerak."""
    monkeypatch.setattr("app.scheduler.SCRAPE_TIMES", parse_times("09:00,09:30"))
    assert _cycle_deadline_seconds() == int(30 * 60 * 0.9)


def test_deadline_unchanged_in_interval_mode(monkeypatch):
    monkeypatch.setattr("app.scheduler.SCRAPE_TIMES", [])
    assert _cycle_deadline_seconds() == int(FETCH_INTERVAL_MINUTES * 60 * 0.9)


# --- startap xatti-harakati ---------------------------------------------------

def test_boot_scrapes_immediately_when_schedule_is_off(monkeypatch, scrapes):
    monkeypatch.setattr("app.scheduler.SCRAPE_TIMES", [])
    assert startup_scrape() is True
    assert scrapes == ["cycle"]


def test_boot_does_not_scrape_when_the_schedule_is_up_to_date(
        schedule_mode, scrapes, clock, session_factory):
    """Jadval yoqiqda istalgan damdagi boot — reja tashqarisidagi tashqi
    chiqish. 09:05'da ishlagan jarayon 09:10'da qayta o'rmaydi."""
    seed(session_factory, naive_utc(tk(9, 5)))
    clock(tk(9, 10))
    assert startup_scrape() is False
    assert scrapes == []


def test_boot_catches_a_missed_hour_once(schedule_mode, scrapes, clock, session_factory):
    """Crash-restart shu yo'l bilan qoplanadi: oxirgi muvaffaqiyat kechagi
    14:05'da, hozir 09:10 — bugungi 09:00 o'tkazib yuborilgan."""
    seed(session_factory, naive_utc(yday(14, 5)))
    clock(tk(9, 10))
    assert startup_scrape() is True
    assert scrapes == ["cycle"]


def test_boot_catches_up_on_an_empty_database(schedule_mode, scrapes, clock,
        session_factory):
    """Baza bo'sh — 'hammasi joyida' emas: birinchi tikish natijasiz qoldi.
    `session_factory` bo'sh holi bilan ham kerak: u sxemani (bank_rates) yaratadi,
    aks holda so'rov jadval yo'qligida yiqiladi."""
    clock(tk(9, 10))
    assert startup_scrape() is True
    assert scrapes == ["cycle"]


def test_boot_before_the_first_hour_waits_for_the_schedule(
        schedule_mode, scrapes, clock, session_factory):
    """08:00, bazada kechagi 14:05 bor — bugungi 09:00 hali kelmadi, boot
    tarmoqqa chiqmaydi, keyingi tikishni kutadi."""
    seed(session_factory, naive_utc(yday(14, 5)))
    clock(tk(8, 0))
    assert startup_scrape() is False
    assert scrapes == []


# --- /api/health jadval rejimida ----------------------------------------------

@pytest.fixture
def health(monkeypatch, clock):
    """Soatni sozlab `/api/health`ni ochadi (auth konftestda override)."""
    monkeypatch.setattr("app.routers.meta.SCRAPE_TIMES", TIMES)

    def get(tashkent_moment: datetime):
        clock(tashkent_moment)
        return TestClient(app).get("/api/health").json()

    return get


def test_health_advertises_the_schedule(health, session_factory):
    body = health(tk(9, 30))
    assert body["scrape_times"] == ["09:00", "14:00"]
    assert body["next_fire_at"].startswith("2026-10-01T14:00:00+05:00")
    # Monitoring "2 soat jimlik = jazo" deb o'lmasligi kerak: 14:00→09:00 tuni
    # normal. Skalyar shu uzon oraliq + grace ni bildiradi.
    assert body["stale_after_minutes"] == max_gap_minutes(TIMES) + 45


def test_health_stays_ok_while_the_current_hour_is_inside_grace(health, session_factory):
    """09:30 — sikl endigina tugayotgan bo'lishi mumkin; bo'sh baza ham bu
    paytda "stale" emas (interval geometriyasi 09:00'dayoq yoqardi)."""
    assert health(tk(9, 30))["status"] == "ok"


def test_health_flags_a_fired_hour_with_nothing_behind_it(health, session_factory):
    """10:00 — 09:00 o'tdi, grace (45 daqiqa) ham tugadi, bazada yozuv yo'q."""
    body = health(tk(10, 0))
    assert body["status"] == "stale"
    assert body["sources"]["stale"] == body["sources"]["total"] > 0


def test_the_night_gap_is_not_an_outage(health, session_factory):
    """Kechagi 14:05 + hozir 08:59 — interval geometriyasi buni ~19 soatlik
    'eskirish' deb jazolardi; jadval rejimida bu normal jimlik."""
    seed(session_factory, naive_utc(yday(14, 5)))
    assert health(tk(8, 59))["status"] == "ok"


def test_a_morning_success_goes_stale_after_the_afternoon_fire(health, session_factory):
    """15:00 — 14:00 tikishi o'tdi, oxirgi ma'lumot ertalabki 09:05'da.
    Global `max(fetched_at)` tirik ko'rinadi, jadval esa yolg'on aytmaydi."""
    seed(session_factory, naive_utc(tk(9, 5)))
    assert health(tk(15, 0))["status"] == "stale"
