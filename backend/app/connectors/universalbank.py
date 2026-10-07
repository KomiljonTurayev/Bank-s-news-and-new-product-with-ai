"""universalbank.uz — jismoniy shaxslar uchun omonat/kredit/karta. Nuxt SSR —
oddiy `requests` bilan to'liq render qilingan HTML keladi, JS ishga
tushirish shart emas (faqat "/uz/..." lokal prefiksli yo'l bilan;
prefikssiz yo'l ba'zan bo'sh javob beradi).

Kartalar sahifasi (`/uz/cards`) deposit/credit'dagi bilan bir xil
umumiy andozadan foydalanadi, faqat CSS prefiksi "deposit"/"credit"
emas, "cards" va maydonlar ".{prefix}__card-list ul li" o'rniga
".{prefix}__card-fees-item" ichida keladi (ikkalasida ham <p>/<span>
juftligi) — shu bois ikkala variant ham sinab ko'riladi. Bu ikki xil
konteyner variantidan biri ishlatilishi umumiy `CardLayout` algoritmiga
sig'maydi (u bitta qattiq konteyner tanlagichini kutadi), shu bois
konteyner tanlash shu yerda qo'lda qilinadi, qolgan barcha qismlar
(yorliq/qiymat ajratish, havola, dublikatni tashlash) esa umumiy
`FieldRule`/`base_url_of` yordamchilaridan foydalanadi.

Valyuta kursi (`/uz/currency`) esa client-tomonda JS orqali to'ldiriladi —
sahifaning o'zi bo'sh keladi. Lekin sayt shu ma'lumotni ochiq JSON API'dan
oladi (`/api/currencies/daily`), shu sabab Playwright shart emas — API'ga
to'g'ridan-to'g'ri so'rov yuboriladi. Valyuta ISO 4217 raqamli kod bilan
qaytadi (masalan "840" = USD), shu sabab alifbo kodiga o'giriladi."""

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.connectors.base import HtmlPageConnector, JsonApiConnector
from app.connectors.exchange import rate_pair
from app.connectors.html_cards import ChildPairFields

_BASE_URL = "https://universalbank.uz"
_EXCHANGE_URL = f"{_BASE_URL}/uz/currency"
_EXCHANGE_API_URL = f"{_BASE_URL}/api/currencies/daily?locale=uz"
_SOURCE = "universalbank.uz"

_NUMERIC_CODES = {
    "392": "JPY",
    "643": "RUB",
    "826": "GBP",
    "840": "USD",
    "978": "EUR",
}

# Har bir maydon <p>(qiymat)/<span>(yorliq) juftligi, lekin ba'zi qatorlarda
# (masalan "Kredit summasi") tartib teskari — raqam saqlagan tomon qiymat
# deb hisoblanadi (`swap_on_digits`, `FieldRule._normalize`da amalga oshadi).
_FIELDS = ChildPairFields(
    container="li, .cards__card-fees-item",
    child_tags=("p", "span"),
    value_first=True,
    swap_on_digits=True,
)


def parse_cards(html: str, prefix: str, base_url: str = _BASE_URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    records = []
    seen = set()

    for card in soup.select(f"a.{prefix}__card"):
        title_el = card.select_one(f".{prefix}__card-title")
        if not title_el:
            continue
        name = title_el.get_text(strip=True)
        if not name:
            continue

        record = {"name": name, "source": _SOURCE}
        container = card.select_one(f".{prefix}__card-list ul") or card.select_one(f".{prefix}__card-fees")
        if container:
            record.update(_FIELDS.extract(container))

        href = card.get("href")
        if href:
            record["url"] = urljoin(base_url, href)

        fingerprint = tuple(sorted(record.items()))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        records.append(record)

    return records


class UniversalbankConnector(HtmlPageConnector):
    bank_code = "UNIVERSAL"
    segment = "individual"

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url
        self._prefix = {"deposit": "deposit", "card": "cards"}.get(product_type, "credit")

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_cards(html, self._prefix, base_url)


def parse_exchange_rates(data: dict, url: str = _EXCHANGE_URL) -> list[dict]:
    records = []
    for item in data.get("items", []):
        code = _NUMERIC_CODES.get(item.get("code"))
        if not code:
            continue
        # "hasBuyingRate"/"hasSellingRate" false — bank hozircha shu
        # valyutani almashtirmayapti degani (masalan RUB), haqiqiy stavka emas.
        if not item.get("hasBuyingRate") or not item.get("hasSellingRate"):
            continue
        try:
            buy_rate = float(item["buyingRate"])
            sell_rate = float(item["sellingRate"])
        except (KeyError, TypeError, ValueError):
            continue

        records.extend(rate_pair(code, buy_rate, sell_rate, source=_SOURCE, url=url))

    return records


class UniversalbankExchangeConnector(JsonApiConnector):
    bank_code = "UNIVERSAL"
    product_type = "currency"
    segment = "individual"
    url = _EXCHANGE_URL
    api_url = _EXCHANGE_API_URL

    def parse_payload(self, payload: dict, url: str) -> list[dict]:
        return parse_exchange_rates(payload, url)
