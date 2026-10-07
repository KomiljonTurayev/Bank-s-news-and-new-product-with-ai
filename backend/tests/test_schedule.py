"""`app/schedule.py` — kunlik jadval matematikasining yagona soat ostida
sinovi. Bu modul loyiha modullarini import qilmagani uchun testlari ham
sof: DB, TestClient, scheduler yo'q — faqat vaqt."""
from datetime import datetime, time as dtime, timedelta, timezone

import pytest

from app import schedule
from app.schedule import (
    TASHKENT,
    last_passed_fire,
    max_gap_minutes,
    min_gap_minutes,
    missed_fire,
    next_fire,
    normalize_tashkent,
    parse_times,
)

# Butun fayl bitta kunda yashaydi: 2026-10-01, jadval [09:00, 14:00].
TIMES = parse_times("09:00,14:00")


def tk(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=TASHKENT)


def yday(hour: int, minute: int = 0) -> datetime:
    """2026-09-30 — kundalik test kunining KECHASI (1-okabr uchun bugundan
    oldingi kun oktabrda emas, sentabrda)."""
    return datetime(2026, 9, 30, hour, minute, tzinfo=TASHKENT)


# --- parse_times ------------------------------------------------------------

def test_parse_orders_dedups_and_accepts_loose_separators():
    assert parse_times("14:00, 09:00;09:00\n9:05") == [
        dtime(9), dtime(9, 5), dtime(14),
    ]


def test_parse_empty_means_schedule_off():
    assert parse_times("") == []
    assert parse_times(None) == []
    assert parse_times("  ,, ; ") == []


@pytest.mark.parametrize("bad", ["09.00", "9-05", "24:00", "9:60", "0900", "9", "09:00,14"])
def test_parse_rejects_anything_not_hh_mm(bad):
    """`SCRAPE_TIMES=09.00` jimgina interval rejimiga siljimasin — xato
    format startapni o'ldiradi (config/base.py validatori shunga tayangan)."""
    with pytest.raises(ValueError):
        parse_times(bad)


# --- next_fire / last_passed_fire -------------------------------------------

def test_next_fire_walks_the_day_then_wraps():
    assert next_fire(TIMES, tk(1, 8)) == tk(1, 9)
    assert next_fire(TIMES, tk(1, 9, 1)) == tk(1, 14)
    assert next_fire(TIMES, tk(1, 14, 30)) == tk(2, 9)  # kun aylanishi
    assert next_fire(TIMES, tk(1, 9)) == tk(1, 14)      # aynan tikish — keyingisi
    assert next_fire([], tk(1, 8)) is None


def test_last_passed_fire_is_inclusive_and_wraps_back_one_day():
    assert last_passed_fire(TIMES, tk(1, 9)) == tk(1, 9)     # aynan tikish — o'tgan
    assert last_passed_fire(TIMES, tk(1, 8, 59)) == yday(14)
    assert last_passed_fire(TIMES, tk(1, 15)) == tk(1, 14)
    assert last_passed_fire([], tk(1, 15)) is None


def test_naive_db_values_are_treated_as_utc():
    """SQLite tz-aware qaytarmaydi; konvensiya — naive = UTC (meta._as_utc)."""
    aware = normalize_tashkent(datetime(2026, 10, 1, 4, 0))  # naive UTC
    assert aware.utcoffset() == timedelta(hours=5)
    assert aware == tk(1, 9)


# --- gap hisoblari -----------------------------------------------------------

def test_gaps_wrap_over_midnight():
    # 09→14 = 300; 14→ertaga 09 = 1140.
    assert min_gap_minutes(TIMES) == 300
    assert max_gap_minutes(TIMES) == 1140
    assert min_gap_minutes(parse_times("09:00")) == 24 * 60
    assert max_gap_minutes(parse_times("09:00")) == 24 * 60


@pytest.mark.parametrize("fn", [min_gap_minutes, max_gap_minutes])
def test_gaps_refuse_empty_schedule(fn):
    with pytest.raises(ValueError):
        fn([])


# --- missed_fire --------------------------------------------------------------

def test_not_missed_when_success_landed_after_the_last_fire():
    assert missed_fire(TIMES, tk(1, 9, 5), now=tk(1, 9, 5)) is False
    assert missed_fire(TIMES, tk(1, 9, 5), now=tk(1, 13, 0)) is False
    # 14→09 tuni NORMAL jimlik: ertaga 08:59'da ham oxirgi muvaffaqiyat
    # (kechagi 14:05) oxirgi o'tgan tikishdan (kechagi 14:00) keyin.
    assert missed_fire(TIMES, yday(14, 5), now=tk(1, 8, 59)) is False


def test_missed_when_the_current_hour_produced_nothing_once_grace_passed():
    old = yday(14, 5)  # kechagi oxirgi muvaffaqiyat
    # grace=None default 0 (catch-up rejimi); monitoring grace'ni O'ZI beradi
    # (meta._STALE_GRACE_MINUTES) — bu yerda shu monitoring chaqiruvini taqlid
    # qilamiz.
    assert missed_fire(TIMES, old, now=tk(1, 8, 0), grace_minutes=45) is False  # 09:00 hali kelmadi
    assert missed_fire(TIMES, old, now=tk(1, 9, 44), grace_minutes=45) is False  # grace ichi
    assert missed_fire(TIMES, old, now=tk(1, 9, 46), grace_minutes=45) is True


def test_grace_zero_for_catch_up_means_five_minutes_of_lag_is_fresh():
    """Startap catch-up'i grace=0 bilan chaqiriladi: yangi jarayonda davom
    etayotgan sikl yo'q — 09:05'dagi muvaffaqiyat 09:10'da 'taze'."""
    assert missed_fire(TIMES, tk(1, 9, 5), now=tk(1, 9, 10), grace_minutes=0) is False
    assert missed_fire(TIMES, yday(14, 5), now=tk(1, 9, 1), grace_minutes=0) is True


def test_no_data_at_all_is_missed_only_after_a_fire_happened():
    now = tk(1, 8, 0)  # bugungi 09:00 hali o'tmadi; kechagi 14:00 o'tgan
    assert missed_fire(TIMES, None, now=tk(1, 8, 44), grace_minutes=45) is True
    # ...lekin grace ichida emas:
    assert missed_fire(TIMES, None, now=tk(1, 9, 10), grace_minutes=45) is False


def test_missed_fire_accepts_naive_utc_success_timestamp():
    # 09:30 Toshkent = 04:30 UTC; naive (SQLite) holda berilsa ham tushadi.
    naive_utc = datetime(2026, 10, 1, 4, 30)
    assert missed_fire(TIMES, naive_utc, now=tk(1, 10, 0)) is False
    # 08:30 Toshkent (=03:30 UTC) 09:00 tikishidan OLDIN — o'tkazib yuborilgan.
    assert missed_fire(TIMES, datetime(2026, 10, 1, 3, 30), now=tk(1, 10, 0)) is True


# --- yagona soat manbasi -------------------------------------------------------

def test_utc_now_is_the_single_clock_hook(monkeypatch):
    monkeypatch.setattr(schedule, "utc_now", lambda: tk(1, 8).astimezone(timezone.utc))
    assert next_fire(TIMES) == tk(1, 9)          # now=None -> utc_now()
    assert last_passed_fire(TIMES) == yday(14)
