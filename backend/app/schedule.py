"""Kunlik skreyping jadvalining matematikasi: soatlarni parse qilish,
keyingi/o'tgan qo'ng'iroqni topish, "reja o'tkazib yuborildimi" predicate'i.

Vaqt huquqi — Asia/Tashkent (UTC+5, yoz/qish siljishi yo'q): foydalanuvchi
talabi "kuniga 09:00 va 14:00" mahalliy soat bilan aytilgan. DB'dagi
``fetched_at`` esa UTC da saqlanadi (app/connectors/base.py) — shu sabab
barcha solishtiruv aware holatga keltirilib bajariladi (naive qiymat DB
konvensiyasi bo'yicha UTC hisoblanadi, meta.py dagi `_as_utc` bilan bir xil).

Bu modul loyiha modullarini import QILMAYDI: `config/` validatsiyasi
import sikliga kirmasdan ishlatishi uchun. APScheduler triggerlari bu
yerda qurilmaydi — faqat sof hisob, shu sabab testi ham oson.
"""
from __future__ import annotations

import re
from datetime import datetime, time as dtime, timedelta, timezone

TASHKENT = timezone(timedelta(hours=5), name="Asia/Tashkent")

# "09:00" va "9:05" qabul; dag'al variantlar ("09.00", "9-05") — yo'q:
# jadinal env'dan qo'lda yoziladi, xato format startapda ovoz bilan
# ko'tarilishi kerak (quyidagi parse_times).
_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def utc_now() -> datetime:
    """Yagona 'hozir' manbasi — testlar shu funksiyani monkeypatch qilib,
    jadval mantig'ini devor soatiga bog'liq qilmasdan tekshiradi."""
    return datetime.now(timezone.utc)


def parse_times(raw: str | None) -> list[dtime]:
    """``"09:00,14:00"`` -> ``[time(9), time(14)]`` (tartibli, takrorsiz).

    Bo'sh satr -> ``[]`` — jadval o'chiq, scheduler interval rejimiga
    tushadi. Format xatosi ValueError ko'taradi: ``SCRAPE_TIMES=09.00``
    jimgina interval rejimiga siljib, "kuniga 2 marta" talabi buzilib,
    soatiga bir skreyping ketaverishi monitoringda payqalmas edi.
    """
    times: set[dtime] = set()
    for part in re.split(r"[,\s;]+", (raw or "").strip()):
        if not part:
            continue
        match = _TIME_RE.match(part)
        if not match:
            raise ValueError(
                f"SCRAPE_TIMES: {part!r} HH:MM formatida emas (to'g'ri misol: '09:00,14:00')"
            )
        times.add(dtime(int(match.group(1)), int(match.group(2))))
    return sorted(times)


def normalize_tashkent(moment: datetime) -> datetime:
    """Istalgan vaqtni Toshkent aware vaqtiga o'giradi. Naive qiymat —
    DB konvensiyasi bo'yicha UTC (`_as_utc` izohidagi kabi)."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(TASHKENT)


def next_fire(times: list[dtime], after: datetime | None = None) -> datetime | None:
    """`after`dan keyingi birinchi rejalashtirilgan lahzа (Toshkent aware).
    Bo'sh jadval -> None (interval rejimini oldindan bilib bo'lmaydi)."""
    if not times:
        return None
    start = normalize_tashkent(after if after is not None else utc_now())
    for day in (start.date(), start.date() + timedelta(days=1)):
        upcoming = [datetime.combine(day, t, tzinfo=TASHKENT) for t in times]
        upcoming = [c for c in upcoming if c > start]
        if upcoming:
            return min(upcoming)
    return None  # amaliyotda erishilmaydi: kunlik jadvalda ertaga albatar bo'ladi


def last_passed_fire(times: list[dtime], now: datetime | None = None) -> datetime | None:
    """`now`da o'tib bo'lingan eng oxirgi rejalashtirilgan lahzа.

    Ikki kunlik oynа yetarli: jadval kunlik (cron ma'nosi), shu sabab
    "oxirgi o'tgan soat" doim bugun yoki kecha ichida bo'ladi.
    """
    if not times:
        return None
    moment = normalize_tashkent(now if now is not None else utc_now())
    latest: datetime | None = None
    for day in (moment.date() - timedelta(days=1), moment.date()):
        for t in times:
            candidate = datetime.combine(day, t, tzinfo=TASHKENT)
            if candidate <= moment and (latest is None or candidate > latest):
                latest = candidate
    return latest


def min_gap_minutes(times: list[dtime]) -> int:
    """Ikki qo'ng'iroq orasidagi ENG QISQA tanaffus (daqiqada), kun aylanishi
    hisobiga: [09:00, 14:00] -> 300. Sikl watchdog'i shuni bilishi kerak —
    sikl keyingi tikishga yetib qaytishi shart, shu bois chegarani jadvalning
    eng tor burchigi belgilaydi. Bitta soatlik jadvalda tanaffus — 24 soat."""
    marks = sorted(t.hour * 60 + t.minute for t in times)
    if not marks:
        raise ValueError("min_gap_minutes: bo'sh jadval uchun oraliq hisoblanmaydi")
    if len(marks) == 1:
        return 24 * 60
    return min(b - a for a, b in zip(marks, marks[1:]))


def max_gap_minutes(times: list[dtime]) -> int:
    """Ikki qo'ng'iroq orasidagi ENG UZON tanaffus (daqiqada), kun
    aylanishi hisobiga: [09:00, 14:00] -> 09->14 = 300, 14->ertaga 09 =
    1140 -> javob 1140. Ma'lumot normal holatda shu qadar 'keksa' oladi —
    stale monitoringi shu ustunlik chegarasini bilishi kerak."""
    marks = sorted(t.hour * 60 + t.minute for t in times)
    if not marks:
        raise ValueError("max_gap_minutes: bo'sh jadval uchun oraliq hisoblanmaydi")
    day = 24 * 60
    gaps = [b - a for a, b in zip(marks, marks[1:])]
    gaps.append(marks[0] + day - marks[-1])
    return max(gaps)


def missed_fire(
    times: list[dtime],
    latest_success: datetime | None,
    now: datetime | None = None,
    grace_minutes: int = 0,
) -> bool:
    """Oxirgi rejalashtirilgan soat o'tib ketdi-yu, O'SHA soatda ish
    tugamaganmi?

    ``latest_success`` — bazadagi eng so'nggi muvaffaqiyatli yozuv vaqti
    (naive bo'lsa UTC). ``grace_minutes`` — ishga tushgandan keyin
    tugashiga beriladigan muddat: sikl watchdog chegarasi ~54 daqiqa
    (app/scheduler.py `_cycle_deadline_seconds`), monitoring shu zaxiradan
    keyingina "o'tkazib yuborildi" deydi — aks holda har kun 09:00-09:10
    oralig'ida soxta signal yoqilardi. Catch-up chaqiruvi grace=0 bilan
    chaqiriladi: yangi jarayonda davom etayotgan sikl bo'lmaydi.
    """
    last = last_passed_fire(times, now)
    if last is None:
        return False
    moment = normalize_tashkent(now if now is not None else utc_now())
    if moment < last + timedelta(minutes=grace_minutes):
        return False
    if latest_success is None:
        return True
    return normalize_tashkent(latest_success) < last
