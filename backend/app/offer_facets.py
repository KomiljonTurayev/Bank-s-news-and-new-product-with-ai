"""Bosh sahifadagi batafsil filtrlar uchun har bir taklifning "qirralari".

Bank saytlaridan kelgan `data` erkin shaklda — filtrlash uchun kerakli
belgilar (kredit turi, muddat, valyuta, karta turi va to'lov tizimi)
shu yerda bir xil, sodda shaklga keltiriladi. Xom `data` o'zgarmaydi.
"""

import re

from app.market_compare import parse_amounts, parse_term_months
from app.product_analysis import _AMOUNT_KEY_RE, _TERM_KEY_RE, _first_field, _infer_credit_category

_CURRENCY_PATTERNS = (
    ("USD", re.compile(r"\busd\b|aqsh dollar|\bdollar|\$", re.IGNORECASE)),
    ("EUR", re.compile(r"\beur\b|yevro|evro|euro|€", re.IGNORECASE)),
)
_CREDIT_CARD_RE = re.compile(r"kredit|credit|кредит", re.IGNORECASE)
_NETWORKS = (
    ("Visa", re.compile(r"\bvisa\b", re.IGNORECASE)),
    ("Mastercard", re.compile(r"master\s*card", re.IGNORECASE)),
    ("Humo", re.compile(r"\bhumo\b", re.IGNORECASE)),
    ("Uzcard", re.compile(r"\buzcard\b", re.IGNORECASE)),
    ("UnionPay", re.compile(r"union\s*pay", re.IGNORECASE)),
    ("Mir", re.compile(r"\bmir\b|\bмир\b", re.IGNORECASE)),
)
_ONLINE_RE = re.compile(r"onlayn|online|онлайн|masofaviy|mobil", re.IGNORECASE)
_KIDS_RE = re.compile(r"bola|farzand|yosh|kelajak|детск|child|kids", re.IGNORECASE)


def _currency(text: str) -> str:
    for code, pattern in _CURRENCY_PATTERNS:
        if pattern.search(text):
            return code
    return "UZS"


def offer_facets(product_type: str, data: dict) -> dict:
    """Filtr qirralari: faqat shu mahsulot turiga mos kalitlar qaytariladi."""
    if product_type not in ("credit", "deposit", "card", "investment"):
        return {}
    name = str(data.get("name") or "")
    whole = " ".join(str(v) for v in data.values())
    facets: dict = {"currency": _currency(whole)}

    if product_type in ("credit", "deposit"):
        facets["term_months"] = parse_term_months(_first_field(data, _TERM_KEY_RE))
        min_amount, max_amount = parse_amounts(_first_field(data, _AMOUNT_KEY_RE), product_type == "credit")
        facets["min_amount"], facets["max_amount"] = min_amount, max_amount

    if product_type == "credit":
        facets["category"] = data.get("category") or _infer_credit_category(name) or "Boshqa"
    elif product_type == "deposit":
        facets["online"] = bool(_ONLINE_RE.search(name))
        facets["kids"] = bool(_KIDS_RE.search(name))
    elif product_type == "card":
        facets["card_type"] = "credit" if _CREDIT_CARD_RE.search(name) else "debit"
        facets["network"] = next((label for label, pattern in _NETWORKS if pattern.search(f"{name} {whole}")), None)
    return facets
