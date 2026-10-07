import logging
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup

from app.banks import resolve_bank_code
from app.connectors.base import BaseConnector
from app.connectors.html_cards import dedupe_records
from app.connectors.http import HTTP

log = logging.getLogger(__name__)

_AJAX_URL = "https://depozit.uz/exchange/ajax/table"
_HTTP = HTTP.with_headers(**{"X-Requested-With": "XMLHttpRequest", "Referer": "https://depozit.uz/exchange-rate-bank"})

# depozit.uz'dagi valyuta id'lari (sahifadagi "currencies-holder" tugmalaridan)
CURRENCIES = [
    (2, "USD"),
    (3, "RUB"),
    (4, "EUR"),
    (5, "GBP"),
    (6, "CHF"),
    (7, "JPY"),
    (8, "KZT"),
]

_SIDE_LABELS = {"Olish": "Olish", "Sotish": "Sotish"}


def _column_side(header_el) -> str | None:
    header = header_el.get_text(" ", strip=True) if header_el else ""
    return next((label for key, label in _SIDE_LABELS.items() if key in header), None)


def _cell_record(cell, side: str, currency_code: str) -> dict | None:
    bank_img = cell.select_one("img")
    value_el = cell.select_one(".currency-rate-value")
    if not bank_img or not value_el:
        return None

    bank_name = bank_img.get("alt", "").strip()
    rate_text = value_el.get_text(" ", strip=True).replace("UZS", "").strip()
    if not bank_name or not rate_text:
        return None

    try:
        rate = float(rate_text.replace(",", ""))
    except ValueError:
        return None

    record = {
        "_bank_code": resolve_bank_code(bank_name),
        "bank_name": bank_name,
        "code": currency_code,
        "side": side,
        "rate": rate,
        "source": "depozit.uz",
    }
    link = cell.select_one("a")
    if link and link.get("href"):
        record["url"] = link["href"]
    return record


def parse_exchange_rates(html: str, currency_code: str) -> list[dict]:
    """Bitta valyuta uchun banklar bo'yicha naqd olish/sotish kursi jadvalini
    normalizatsiya qilingan dict'lar ro'yxatiga aylantiradi."""
    soup = BeautifulSoup(html, "html.parser")
    records = []

    for column in soup.select(".table-column"):
        side = _column_side(column.select_one(".table-header"))
        if not side:
            continue

        for cell in column.select(".table-cell"):
            record = _cell_record(cell, side, currency_code)
            if record:
                records.append(record)

    return dedupe_records(records)


class DepozitExchangeConnector(BaseConnector):
    """depozit.uz — banklar bo'yicha naqd valyuta olish/sotish kursi
    (shoxobchalardagi kurs). CBUConnector rasmiy markaziy bank kursini
    beradi, bu esa har bir bankning haqiqiy kursini qo'shadi."""

    bank_code = "AGGREGATED"
    product_type = "currency"
    segment = "individual"

    def fetch_raw(self):
        def fetch_one(currency):
            currency_id, currency_code = currency
            params = {"rate_type": "office", "currency_id": currency_id, "is_single_currency": "false"}
            return currency_code, _HTTP.json(_AJAX_URL, params)

        # 7 ta valyuta so'rovi bir-biriga bog'liq emas — ketma-ket emas,
        # parallel yuborish umumiy vaqtni ~7x qisqartiradi. Bittasi uzilsa,
        # qolgan 6 tasining kursi baribir yig'ilsin: nosoz valyuta o'tkazib
        # yuboriladi, hammasi uzilsagina connector nosoz hisoblanadi.
        with ThreadPoolExecutor(max_workers=len(CURRENCIES)) as pool:
            futures = [pool.submit(fetch_one, currency) for currency in CURRENCIES]
            raw = []
            for future in futures:
                try:
                    raw.append(future.result())
                except Exception as error:
                    log.warning("depozit.uz: valyuta kursini olib bo'lmadi (%s)", error)

        if not raw:
            raise RuntimeError("depozit.uz'dan birorta valyuta kursini olib bo'lmadi")
        return raw

    def parse(self, raw):
        records = []
        for currency_code, html in raw:
            records.extend(parse_exchange_rates(html, currency_code))
        return records
