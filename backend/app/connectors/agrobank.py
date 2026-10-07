"""agrobank.uz — jismoniy shaxslar uchun omonat/kredit/karta. Sayt React
SPA bo'lsa-da, orqasida ochiq (autentifikatsiyasiz) JSON API bor:
`GET /api/v1/?action=pages&code=<sahifa-yo'li>` — shu bois HTML parsing
yoki headless brauzer shart emas, to'g'ridan-to'g'ri JSON o'qiladi.

Kartalar bloki (`content.type == "cards"`) omonat/kredit'dagi
"calculationParams" o'rniga oddiy {title, value} juftliklaridan iborat
"tags" ro'yxatidan foydalanadi (masalan "Rasmiylashtirish: 40 000 so'm");
qiymatlar HTML entity ko'rinishida (&nbsp; kabi) kelgani uchun
unescape qilinadi.

Valyuta kursi sahifasida (`uz/person/exchange_rates`) uchta tab bor
("Ayirboshlash shoxobchasida" / "Bankomatlarda" / "Xalqaro pul
o'tkazmalari") — har biri o'z "currency-rates" blokiga ega, shu bois
faqat birinchisi (filial, ``tab.code == "office"``) olinadi."""

import html

from app.connectors.base import JsonApiConnector
from app.connectors.exchange import rate_pair

_API_URL = "https://agrobank.uz/api/v1/"
_BASE_URL = "https://agrobank.uz"
_EXCHANGE_PAGE_CODE = "uz/person/exchange_rates"
_EXCHANGE_URL = f"{_BASE_URL}/uz/person/exchange_rates"
_SOURCE = "agrobank.uz"


def _fmt_amount(value) -> str | None:
    if value is None:
        return None
    return f"{value:,}".replace(",", " ") + " so'm"


def extract_items(payload: dict) -> list[dict]:
    """API javobidagi barcha bo'lim/blok orasidan mahsulot ro'yxati
    (`content.type` "deposits" yoki "loans") bo'lgan bloklarni topadi."""
    items = []
    for section in (payload.get("data") or {}).get("sections", []):
        for block in section.get("blocks", []):
            content = block.get("content") or {}
            if content.get("type") in ("deposits", "loans", "cards"):
                items.extend(content.get("items", []))
    return items


def _untag_item(record: dict, item: dict) -> None:
    # Kartalar sahifasida omonat/kredit'dagi "calculationParams" o'rniga
    # oddiy {title, value} juftliklaridan iborat "tags" ro'yxati keladi
    # (masalan "Rasmiylashtirish: 40 000 so'm") — qiymatlar HTML
    # entity'lar (&nbsp; kabi) bilan kelgani uchun unescape qilinadi.
    for tag in item.get("tags") or []:
        label = (tag.get("title") or "").strip()
        value = html.unescape(tag.get("value") or "").strip()
        if label and value:
            record[label] = value


def _interest_rate_text(month_count: dict) -> str | None:
    rates = [r["rate"] for r in month_count.get("rates") or [] if r.get("rate") is not None]
    if not rates:
        return None
    return f"{min(rates)}%" if min(rates) == max(rates) else f"{min(rates)}% - {max(rates)}%"


def _apply_item_params(record: dict, item: dict) -> None:
    params = item.get("calculationParams") or {}
    interest = params.get("interestRate") or {}
    month_count = params.get("monthCount") or {}
    amount = params.get("amount") or {}

    if interest.get("value") is not None:
        record["Foiz stavkasi"] = f"{interest['value']}%"
    else:
        rate_text = _interest_rate_text(month_count)
        if rate_text:
            record["Foiz stavkasi"] = rate_text

    if amount.get("max") is not None:
        record["Miqdori"] = f"{_fmt_amount(amount.get('min'))} - {_fmt_amount(amount['max'])}"

    if month_count.get("max") is not None and not month_count.get("rates"):
        record["Muddati"] = f"{month_count.get('min', 0)} - {month_count['max']} oy"


def parse_items(items: list[dict], base_url: str = _BASE_URL) -> list[dict]:
    records = []
    for item in items:
        name = (item.get("title") or "").strip()
        if not name:
            continue

        record = {"name": name, "source": _SOURCE}
        if item.get("currency"):
            record["Valyuta"] = item["currency"]

        _untag_item(record, item)
        _apply_item_params(record, item)

        url = item.get("url")
        if url:
            record["url"] = base_url + url

        records.append(record)

    return records


class AgrobankConnector(JsonApiConnector):
    bank_code = "AGRO"
    segment = "individual"
    url = _BASE_URL
    api_url = _API_URL

    def __init__(self, product_type: str, page_code: str):
        self.product_type = product_type
        self.params = {"action": "pages", "code": page_code}

    def parse_payload(self, payload: dict, url: str) -> list[dict]:
        return parse_items(extract_items(payload))


def parse_exchange_rates(payload: dict, url: str = _EXCHANGE_URL) -> list[dict]:
    blocks = []
    for section in (payload.get("data") or {}).get("sections", []):
        blocks.extend(section.get("blocks", []))

    current_tab_code = None
    office_items = None
    for block in blocks:
        content = block.get("content") or {}
        if block.get("type") == "tab":
            current_tab_code = content.get("code")
        elif block.get("type") == "currency-rates" and current_tab_code == "office":
            office_items = content.get("items") or []
            break

    records = []
    for item in office_items or []:
        records.extend(rate_pair(item.get("alpha3"), item.get("buy"), item.get("sale"), source=_SOURCE, url=url))

    return records


class AgrobankExchangeConnector(JsonApiConnector):
    bank_code = "AGRO"
    product_type = "currency"
    segment = "individual"
    url = _EXCHANGE_URL
    api_url = _API_URL
    params = {"action": "pages", "code": _EXCHANGE_PAGE_CODE}

    def parse_payload(self, payload: dict, url: str) -> list[dict]:
        return parse_exchange_rates(payload, url)
