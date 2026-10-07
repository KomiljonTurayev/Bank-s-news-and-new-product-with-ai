"""Bozorni batafsil solishtirish — `/api/products/market-compare`.

Bank saytlaridan kelgan takliflarda muddat va summa erkin matn ("24 oy",
"1-12 oy", "3-18 yil", "555 kun", "100 mln so'mgacha", "1,000,000 So'm") —
bu modul ularni raqamga (oy, so'm) keltiradi, so'ng muddat oraliqlari va
kategoriyalar kesimida stavka statistikasini (min / o'rtacha / max, eng
yaxshi taklif) hisoblaydi. Tashqi API'ga murojaat yo'q.
"""

import re
from datetime import date
from statistics import mean

from sqlalchemy.orm import Session

from app.product_analysis import (
    _AMOUNT_KEY_RE,
    _BANK_NAMES,
    _TERM_KEY_RE,
    _first_field,
    comparable_offers,
    lower_rate_is_better,
)

# Kirill "о" ba'zi saytlarda lotin "o" o'rnida yoziladi ("18 оy").
_CYRILLIC_LOOKALIKES = str.maketrans({"о": "o", "у": "y", "а": "a", "е": "e"})
_TERM_PART_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:-|–|—)?\s*(\d+(?:[.,]\d+)?)?\s*(?:gacha\s*|до\s*)?(oy|мес|yil|йил|год|лет|kun|день|дн)",
    re.IGNORECASE,
)
# "60 (oltmish) oy" — qavs ichidagi so'z bilan yozilgan son olib tashlanadi.
_PARENS_RE = re.compile(r"\([^)]*\)")
_DATE_RE = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b")
_UNIT_MONTHS = {"oy": 1, "мес": 1, "yil": 12, "йил": 12, "год": 12, "лет": 12, "kun": 1 / 30.4, "день": 1 / 30.4, "дн": 1 / 30.4}

_NUMBER_RE = re.compile(r"(\d[\d\s,. ]*)\s*(mlrd|млрд|mln|млн|ming|тыс)?", re.IGNORECASE)
_MULTIPLIERS = {"mlrd": 1e9, "млрд": 1e9, "mln": 1e6, "млн": 1e6, "ming": 1e3, "тыс": 1e3}
_MIN_PLAIN_AMOUNT = 1000
_MIN_MARKERS =re.compile(r"dan\b|от\b|minimal|min\.?\b", re.IGNORECASE)
_MAX_MARKERS = re.compile(r"gacha|до\b|maksimal|max\.?\b", re.IGNORECASE)

# Muddat oraliqlari (oy): omonat qisqa, kredit uzoq muddatli bo'ladi.
_TERM_BUCKETS = {
    "short": [(0, 6), (7, 12), (13, 24), (25, None)],
    "long": [(0, 12), (13, 36), (37, 84), (85, None)],
}


def parse_term_months(text: str | None) -> int | None:
    """Muddat matnini oyga keltiradi; oraliq bo'lsa ("1-12 oy", "3-18 yil")
    yuqori chegara olinadi. Birlik yo'q bo'lsa (masalan "18 yoshgacha",
    "Cheklanmagan") — None."""
    if not text:
        return None
    best = None
    normalized = _PARENS_RE.sub(" ", text.lower().translate(_CYRILLIC_LOOKALIKES))
    for low, high, unit in _TERM_PART_RE.findall(normalized):
        value = float((high or low).replace(",", "."))
        months = value * _UNIT_MONTHS[unit.lower()]
        best = months if best is None else max(best, months)
    return round(best) if best else None


def months_until(text: str | None, today: date) -> int | None:
    """Obligatsiya kabi sanali muddat ("21.05.2027") — bugundan necha oy qolgani."""
    match = _DATE_RE.search(text or "")
    if not match:
        return None
    day, month, year = map(int, match.groups())
    try:
        maturity = date(year, month, day)
    except ValueError:
        return None
    months = (maturity.year - today.year) * 12 + maturity.month - today.month - (maturity.day < today.day)
    return months if months > 0 else None


def _to_number(raw: str, unit: str | None) -> float | None:
    digits = re.sub(r"[\s ]", "", raw).rstrip(".,")
    if unit:
        # "1.0 mlrd", "1,5 mln" — kasr ajratuvchi
        digits = digits.replace(",", ".")
        if digits.count(".") > 1:
            return None
    else:
        # "1,000,000" / "1.000.000" — minglik ajratuvchi
        digits = digits.replace(",", "").replace(".", "")
    try:
        value = float(digits)
    except ValueError:
        return None
    return value * _MULTIPLIERS.get((unit or "").lower(), 1)


def parse_amounts(text: str | None, single_is_max: bool = False) -> tuple[float | None, float | None]:
    """Summa matnidan (min, max) so'mda. "A - B" — ikkalasi; "…dan" — min;
    "…gacha" — max; belgisiz bitta son — omonatda min, kredit/kartada max
    (kredit summasi/limit) — `single_is_max`."""
    if not text:
        return None, None
    # Birliksiz kichik son summa emas: "ish haqining 3 baravarigacha",
    # "18 yoshgacha" — so'mdagi summa kamida 1 000 bo'ladi.
    numbers = [
        n
        for n in (_to_number(raw, unit) for raw, unit in _NUMBER_RE.findall(text))
        if n and n >= _MIN_PLAIN_AMOUNT
    ]
    if not numbers:
        return None, None
    if len(numbers) >= 2:
        return min(numbers), max(numbers)
    if _MIN_MARKERS.search(text) and not _MAX_MARKERS.search(text):
        return numbers[0], None
    if _MAX_MARKERS.search(text) or single_is_max:
        return None, numbers[0]
    return numbers[0], None


def _bucket_label(low: int, high: int | None) -> str:
    return f"{low}+" if high is None else f"{low}-{high}"


def _stats(items: list[dict], lower_is_better: bool) -> dict:
    rates = [item["rate"] for item in items]
    best = (min if lower_is_better else max)(items, key=lambda item: item["rate"])
    return {
        "count": len(items),
        "min_rate": min(rates),
        "avg_rate": round(mean(rates), 2),
        "max_rate": max(rates),
        "banks": len({item["bank_code"] for item in items}),
        "best": best,
    }


def compare_market(product_type: str, session: Session, category: str | None = None) -> dict:
    lower_is_better = lower_rate_is_better(product_type)
    today = date.today()
    single_is_max = product_type in ("credit", "card")
    offers = []
    for rate, row in comparable_offers(product_type, session, today):
        if category and row.data.get("category") != category:
            continue
        term_text = _first_field(row.data, _TERM_KEY_RE)
        amount_text = _first_field(row.data, _AMOUNT_KEY_RE)
        min_amount, max_amount = parse_amounts(amount_text, single_is_max)
        offers.append(
            {
                "bank_code": row.bank_code,
                "bank_name": _BANK_NAMES.get(row.bank_code, row.bank_code),
                "name": str(row.data.get("name") or ""),
                "category": row.data.get("category"),
                "rate": rate,
                "term_months": parse_term_months(term_text) or months_until(term_text, today),
                "term_text": term_text,
                "min_amount": min_amount,
                "max_amount": max_amount,
                "amount_text": amount_text,
                "url": row.data.get("url"),
            }
        )
    offers.sort(key=lambda item: item["rate"], reverse=not lower_is_better)

    buckets = []
    for low, high in _TERM_BUCKETS["long" if product_type == "credit" else "short"]:
        items = [
            o for o in offers
            if o["term_months"] is not None and o["term_months"] >= low and (high is None or o["term_months"] <= high)
        ]
        if items:
            buckets.append({"key": _bucket_label(low, high), "from_months": low, "to_months": high, **_stats(items, lower_is_better)})

    by_category: dict[str, list[dict]] = {}
    for offer in offers:
        if offer["category"]:
            by_category.setdefault(offer["category"], []).append(offer)
    categories = [
        {"name": name, **_stats(items, lower_is_better)}
        for name, items in sorted(by_category.items(), key=lambda kv: -len(kv[1]))
    ]

    return {
        "product_type": product_type,
        "category": category,
        "lower_is_better": lower_is_better,
        "overall": _stats(offers, lower_is_better) if offers else None,
        "term_buckets": buckets,
        "categories": categories,
        "offers": offers,
    }
