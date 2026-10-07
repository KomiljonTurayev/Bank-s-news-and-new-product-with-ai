"""cbu.uz/uz/arkhiv-kursov-valyut/dinamika-kursov-valyut/ sahifasi ortidagi
JSON manba — har bir valyuta uchun 1994-yildan buyongi rasmiy kundalik
kurs tarixi. MPL (Min/O'rtacha/Max) tahlili shu yerdan hisoblanadi.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from app.connectors.http import HTTP

log = logging.getLogger(__name__)

_URL = "https://cbu.uz/common/json/amcharts.php"

# depozit.uz'dagi bank kurslari bilan solishtiriladigan asosiy valyutalar —
# har biri uchun alohida so'rov kerak, shu ro'yxat bilan cheklaymiz.
TRACKED_CODES = ["USD", "EUR", "RUB", "GBP", "CHF", "JPY", "KZT"]

# Har bir valyutaning oxirgi muvaffaqiyatli tarixi. Bitta valyutaning
# bugungi so'rovi uzilib qolsa, oldingi saqlangan tarixi ishlatiladi —
# aks holda diagrammadan butun valyuta yo'qolib qolardi.
_last_good: dict[str, list[dict]] = {}


def fetch_history(code: str) -> list[dict]:
    """Bitta valyuta uchun {date, value} tarixini qaytaradi (eskidan yangiga)."""
    points = []
    for item in HTTP.json(_URL, {"rate": code}):
        try:
            points.append({"date": item["date"], "value": float(item["value"])})
        except (KeyError, TypeError, ValueError):
            continue
    points.sort(key=lambda p: p["date"])
    return points


def fetch_all_histories(codes: list[str] = TRACKED_CODES) -> dict[str, list[dict]]:
    """Barcha kuzatiladigan valyutalar tarixini parallel oladi.

    Bitta valyutaning so'rovi uzilishi qolganlarini ham olib ketmasligi
    kerak: nosoz valyuta o'tkazib yuboriladi, agar avval bunday bo'lmagan
    bo'lsa esa oxirgi muvaffaqiyatli tarixi ishlatiladi. Ro'yxat bo'sh
    qaytishi (hech qaysi valyuta olmaganlik) — haqiqiy nosozlik, shu
    sabab unda xato ko'tariladi."""
    with ThreadPoolExecutor(max_workers=len(codes) or 1) as pool:
        futures = {code: pool.submit(fetch_history, code) for code in codes}

    histories: dict[str, list[dict]] = {}
    for code, future in futures.items():
        try:
            histories[code] = future.result()
        except Exception as error:
            log.warning("cbu.uz: %s tarixini olib bo'lmadi (%s)", code, error)
            if code in _last_good:
                histories[code] = _last_good[code]

    for code, points in histories.items():
        if points:
            _last_good[code] = points

    if not histories:
        raise RuntimeError("cbu.uz'dan birorta valyuta tarixini olib bo'lmadi")
    return histories


def window_for_days(points: list[dict], days: int | None) -> list[dict]:
    """Berilgan {date, value} ro'yxatidan so'nggi `days` kunlik oynani
    ajratib beradi. days=None — butun tarix. Oyna bo'sh chiqsa (masalan
    valyuta tarixi `days`dan qisqaroq bo'lsa), so'nggi nuqtaga tushadi."""
    if days is None:
        return points
    cutoff = date.today().toordinal() - days
    window = [p for p in points if date.fromisoformat(p["date"]).toordinal() >= cutoff]
    return window or points[-1:]


def stats_for_window(points: list[dict], days: int | None) -> dict | None:
    """Berilgan {date, value} ro'yxatidan so'nggi `days` kunlik oyna bo'yicha
    Min/O'rtacha/Max/Joriy/o'zgarish foizini hisoblaydi. days=None — butun
    tarix."""
    if not points:
        return None

    window = window_for_days(points, days)
    values = [p["value"] for p in window]
    current = points[-1]["value"]
    first = window[0]["value"]
    change_pct = ((current - first) / first * 100) if first else 0.0

    return {
        "min": min(values),
        "max": max(values),
        "avg": sum(values) / len(values),
        "current": current,
        "change_pct": change_pct,
        "samples": len(values),
        "sparkline": [p["value"] for p in window[-60:]],
    }
