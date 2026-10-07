"""Tashqariga chiqish siyosati: faollik darvozasi + host tanaffusi.

Bu yerda sinovdan o'tayotgan narsa — bloklanib qolmaslik uchun qo'yilgan ikki
cheklovning o'zi. Ikkalasida ham xavf bir xil: sozlama buzilsa yoki chegara
noto'g'ri hisoblansa, tizim jimlik bilan ya hech qachon skreyping qilmaydi, ya
keragidan ortiq so'rov yuboradi — ikkala holat ham log'siz sezilmaydi.
"""

import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app import outbound
from app.outbound import ActiveWindow, HostPacer

TASHKENT = timezone(timedelta(hours=5), "Asia/Tashkent")


def at(local: str) -> datetime:
    """Toshkentdagi mahalliy vaqt — `'2026-09-25 06:59'` ko'rinishida."""
    day, clock = local.split(" ")
    year, month, day_of_month = (int(part) for part in day.split("-"))
    hour, minute = (int(part) for part in clock.split(":"))
    return datetime(year, month, day_of_month, hour, minute, tzinfo=TASHKENT)


def window_for(monkeypatch, spec: str) -> ActiveWindow:
    monkeypatch.setattr(outbound.settings, "scrape_active_window", spec)
    return outbound.active_window()


class FixedClock:
    """`app.scheduler`dagi `datetime`ning o'rnini bosadi — sinov soatga bog'liq
    bo'lmasligi uchun. Scheduler bu nomdan faqat `now()` oladi."""

    def __init__(self, moment: datetime):
        self._moment = moment

    def now(self, tz=None):
        return self._moment.astimezone(tz) if tz else self._moment.replace(tzinfo=None)


class RecordingConnector:
    bank_code = "RECORDED"
    product_type = "deposit"

    def __init__(self, calls: list, bank_code: str | None = None):
        self._calls = calls
        if bank_code:
            self.bank_code = bank_code

    def run(self):
        self._calls.append(self.bank_code)
        return SimpleNamespace(total=0, inserted=0, unchanged=0)


# ---------------------------------------------------------------- oyna


def test_empty_window_means_no_restriction(monkeypatch):
    """Bo'sh satr — skreyping 24/7. Oyna noto'g'ri talqin qilinib butun kun
    yopiq deb o'qilmasligi kerak: u ma'lumotni jimlik to'xtatar edi."""
    window = window_for(monkeypatch, "")
    assert window.unrestricted
    assert str(window) == "24/7"
    assert window.contains(at("2026-09-25 03:17"))


def test_nonsense_window_falls_open_with_a_warning(monkeypatch, caplog):
    """Yozuvdagi xato skreypingni butunlay o'chirib qo'ymasligi kerak — ammo
    xato ko'rinish-shovqin bilan ko'rsatilishi ham shart."""
    with caplog.at_level(logging.WARNING):
        window = window_for(monkeypatch, "ertalab-kech")
    assert window.unrestricted
    assert "ajratib bo'lmadi" in caplog.text


def test_identical_boundaries_warn_because_that_freezes_everything(monkeypatch, caplog):
    """`07:00-07:00` — uzunligi 0 oralik. Monitoring `contains` bilan bir
    xil xulosa chiqarishi kerak: aks holda darvoza yopiq, idle hisoblagich
    esa "oyna ochiq edi, nima uchun data yo'q" deb yolg'on gapirardi."""
    with caplog.at_level(logging.WARNING):
        window = window_for(monkeypatch, "07:00-07:00")
    assert not window.contains(at("2026-09-25 07:01"))
    assert not window.contains(at("2026-09-25 15:00"))
    assert window.open_seconds_between(at("2026-09-24 00:00"), at("2026-09-26 00:00")) == 0
    assert "butun kun" in caplog.text


def test_window_bounds_are_local_and_end_is_exclusive(monkeypatch):
    window = window_for(monkeypatch, "07:00-21:00")
    assert not window.contains(at("2026-09-25 06:59"))
    assert window.contains(at("2026-09-25 07:00"))
    assert window.contains(at("2026-09-25 20:59"))
    assert not window.contains(at("2026-09-25 21:00"))


def test_window_crossing_midnight(monkeypatch):
    """`22:00-06:00` — kechani bosib o'tadigan oyna: ikki bo'lak yig'indisi."""
    window = window_for(monkeypatch, "22:00-06:00")
    assert window.contains(at("2026-09-25 23:30"))
    assert window.contains(at("2026-09-26 03:00"))
    assert not window.contains(at("2026-09-25 12:00"))


def test_boundary_is_measured_in_tashkent_not_utc(monkeypatch):
    """Konteyner UTC'da ishlaydi; `07:00` — Toshkent vaqti, ya'ni 02:00 UTC.
    UTC bo'yicha o'lchansa skreyping 5 soatga surilardi."""
    window = window_for(monkeypatch, "07:00-21:00")
    assert window.contains(datetime(2026, 9, 25, 2, 30, tzinfo=timezone.utc))
    assert not window.contains(datetime(2026, 9, 25, 1, 30, tzinfo=timezone.utc))


# ------------------------------------------------- oynaning ichidagi vaqt


def test_only_time_inside_the_window_counts_as_idle(monkeypatch):
    """Tundagi 6 soat 'data eskirgan' hisoblanmaydi — u vaqtda skreyping ruxsat
    etilmagan. Monitoring shu sabab tunda soxta signal bermaydi."""
    window = window_for(monkeypatch, "07:00-21:00")
    idle = window.open_seconds_between(at("2026-09-24 21:00"), at("2026-09-25 09:00"))
    assert idle == 2 * 3600  # 07:00 -> 09:00, qolgani oyna tashqarisida


def test_idle_across_several_days_accumulates(monkeypatch):
    """Bir necha kun davomida oyna ichida ham yangilanmasa uzilish baribir
    ko'rinadi — oynani ayirish haqiqiy nosozlikni yashirmasligi kerak."""
    window = window_for(monkeypatch, "07:00-21:00")
    idle = window.open_seconds_between(at("2026-09-22 07:00"), at("2026-09-25 07:00"))
    assert idle == pytest.approx(3 * 14 * 3600)


def test_unrestricted_window_counts_the_whole_gap(monkeypatch):
    window = window_for(monkeypatch, "")
    idle = window.open_seconds_between(at("2026-09-22 07:00"), at("2026-09-25 07:00"))
    assert idle == pytest.approx(3 * 24 * 3600)


def test_midnight_crossing_window_accumulates_both_halves(monkeypatch):
    window = window_for(monkeypatch, "22:00-06:00")
    idle = window.open_seconds_between(at("2026-09-25 00:00"), at("2026-09-25 12:00"))
    assert idle == 6 * 3600  # 00:00 -> 06:00


# -------------------------------------------------------------- tanaffus


def test_first_request_to_a_host_is_not_delayed():
    slept: list[float] = []
    pacer = HostPacer(2.0, jitter_ratio=0.0, sleep=slept.append)
    assert pacer.acquire("cbu.uz") == 0.0
    assert slept == []


def test_next_request_waits_and_the_place_is_reserved_up_front():
    """8 worker bir lahzada navbat so'rasa, ular bir vaqtda uyg'onib bir xil
    soniyada urilib qolmasligi kerak — navbat oldindan band qilinadi."""
    slept: list[float] = []
    pacer = HostPacer(
        2.0, jitter_ratio=0.0, clock=lambda: 1000.0, sleep=slept.append
    )
    assert [pacer.acquire("cbu.uz") for _ in range(3)] == [0.0, 2.0, 4.0]
    assert slept == [2.0, 4.0]


def test_hosts_do_not_share_their_queue():
    pacer = HostPacer(2.0, jitter_ratio=0.0, clock=lambda: 1000.0, sleep=lambda seconds: None)
    assert pacer.acquire("cbu.uz") == 0.0
    assert pacer.acquire("depozit.uz") == 0.0


def test_jitter_stretches_the_gap():
    """Soatning bir xil soniyasida qaytalanadigan naqsh anti-bot uchun eng aniq
    belgi — tanaffus shu sabab tasodifiy cho'ziladi."""
    pacer = HostPacer(
        2.0, jitter_ratio=0.5, clock=lambda: 1000.0, sleep=lambda seconds: None,
        rng=lambda: 1.0,
    )
    pacer.acquire("cbu.uz")
    assert pacer.acquire("cbu.uz") == 3.0  # 2.0 * (1 + 0.5*1.0)


def test_gap_can_be_switched_off():
    slept: list[float] = []
    pacer = HostPacer(0.0, clock=lambda: 1000.0, sleep=slept.append)
    assert pacer.acquire("cbu.uz") == 0.0
    assert pacer.acquire("cbu.uz") == 0.0
    assert slept == []


def test_module_pacer_follows_the_setting(monkeypatch):
    monkeypatch.setattr(outbound.settings, "min_host_interval_seconds", 1.5)
    outbound.reset_pacer()
    monkeypatch.setattr(outbound._pacer, "_clock", lambda: 1000.0)
    monkeypatch.setattr(outbound._pacer, "_sleep", lambda seconds: None)
    assert outbound.wait_for_host("bank.uz") == 0.0
    first_gap = outbound.wait_for_host("bank.uz")
    assert 1.5 <= first_gap < 2.25  # asosiy 1.5s + tasodifiy qo'shimcha


# ------------------------------------------------------- sikl darvozasi


def test_cycle_stays_home_outside_the_window(session_factory, monkeypatch, caplog):
    """Eng qimmat xato — tunda ham so'rash: bloklanganda javob bermaydigan
    manbalar soni OSHADI. Shu sabab darvoza so'rov chiqishidan OLDIN turadi."""
    from app import scheduler

    calls: list[str] = []
    monkeypatch.setattr(outbound.settings, "scrape_active_window", "07:00-21:00")
    monkeypatch.setattr(scheduler, "CONNECTORS", [RecordingConnector(calls, "GATED")])
    monkeypatch.setattr(scheduler, "datetime", FixedClock(at("2026-09-25 03:00")))

    with caplog.at_level(logging.INFO):
        scheduler.run_all_connectors()

    assert calls == []
    assert "tashqi manbalarga murojaat qilinmadi" in caplog.text


def test_cycle_runs_inside_the_window(session_factory, monkeypatch, caplog):
    from app import scheduler

    calls: list[str] = []
    monkeypatch.setattr(outbound.settings, "scrape_active_window", "07:00-21:00")
    monkeypatch.setattr(scheduler, "CONNECTORS", [RecordingConnector(calls, "OPEN")])
    monkeypatch.setattr(scheduler, "datetime", FixedClock(at("2026-09-25 10:00")))

    with caplog.at_level(logging.INFO):
        scheduler.run_all_connectors()

    assert calls == ["OPEN"]
    assert "o'tkazib yuborildi" not in caplog.text
