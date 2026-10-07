"""davrbank.uz — jismoniy shaxslar uchun omonat/kredit va valyuta kursi.
Statik HTML (Next.js SSR). Omonat va kredit sahifalari bir xil karta
komponentidan foydalanadi: ``.bg-secondary.rounded-4xl`` karta, ichida
sarlavha va ``.flex.flex-col.gap-2`` juftliklari (qiymat, keyin
yorliq).

Valyuta kursi sahifasida (``/uz/exchange-rate``) jadval to'liq
server-rendered — JS render shart emas. Faqat valyuta nomi bor (ISO
kodi yo'q), shu bois kod nomdan qattiq belgilangan lug'at orqali
topiladi."""

from bs4 import BeautifulSoup

from app.connectors.base import CardListConnector, HtmlPageConnector
from app.connectors.exchange import parse_amount, rate_pair
from app.connectors.html_cards import CardLayout, ChildPairFields, parse_card_list

_BASE_URL = "https://davrbank.uz"
_EXCHANGE_URL = f"{_BASE_URL}/uz/exchange-rate"
_SOURCE = "davrbank.uz"

_CURRENCY_CODES = {
    "aqsh dollari": "USD",
    "yevro": "EUR",
    "funt sterling": "GBP",
    "rossiya rubli": "RUB",
    "shveytsariya franki": "CHF",
    "yapon yenasi": "JPY",
}

PRODUCT_CARDS = CardLayout(
    source=_SOURCE,
    card=".bg-secondary.rounded-4xl",
    title=".typography-header-bold",
    fields=ChildPairFields(container=".flex.flex-col.gap-2", value_first=True),
    link="a[href]",
)


def parse_products(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, PRODUCT_CARDS, base_url)


class DavrbankConnector(CardListConnector):
    bank_code = "DAVR"
    segment = "individual"
    layout = PRODUCT_CARDS

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url


def parse_exchange_rates(html: str, url: str = _EXCHANGE_URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table")
    if not table:
        return []

    records = []
    for row in table.select("tbody tr"):
        cells = row.select("td")
        if len(cells) < 4:
            continue

        name = cells[0].get_text(" ", strip=True).lower()
        code = _CURRENCY_CODES.get(name)
        if not code:
            continue

        # Ustunlar tartibi: Valyuta | MB | Sotuv (bank sotadi) | Xarid
        # (bank xarid qiladi) — "Olish"/"Sotish" konvensiyasiga mos
        # kelishi uchun Xarid->Olish, Sotuv->Sotish deb belgilanadi.
        records.extend(rate_pair(
            code,
            parse_amount(cells[3].get_text()),
            parse_amount(cells[2].get_text()),
            source=_SOURCE,
            url=url,
        ))

    return records


class DavrbankExchangeConnector(HtmlPageConnector):
    bank_code = "DAVR"
    product_type = "currency"
    segment = "individual"
    url = _EXCHANGE_URL

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_exchange_rates(html, self.url)
