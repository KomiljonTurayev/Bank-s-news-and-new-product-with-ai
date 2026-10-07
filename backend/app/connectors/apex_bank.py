"""apexbank.uz — jismoniy shaxslar uchun omonat/kredit. Statik HTML,
omonat va kredit sahifalari bir xil ".debet-card-block" kartasidan
foydalanadi.

Valyuta kursi (`/about/exchange-rates/`) sahifasida ikkita jadval bor:
"SOTUV OFISLARIDA" (jismoniy shaxslar/naqd) va "YURIDIK SHAXSLAR UCHUN" —
ikkinchisi JS orqali (tugma bosilganda) ma'lumot bilan to'ldiriladi, shu
sabab statik HTML'da faqat birinchisi keladi, bu esa bizga kerak bo'lgan
segment bilan mos keladi."""

from bs4 import BeautifulSoup

from app.connectors.base import CardListConnector, HtmlPageConnector
from app.connectors.exchange import parse_amount, rate_pair
from app.connectors.html_cards import CardLayout, SiblingFields, parse_card_list

_BASE_URL = "https://www.apexbank.uz"
_EXCHANGE_URL = f"{_BASE_URL}/about/exchange-rates/"
_SOURCE = "apexbank.uz"

DEBET_CARDS = CardLayout(
    source=_SOURCE,
    card=".debet-card-block",
    title=".card-content .heading",
    fields=SiblingFields(label=".p5.mb-1", value_tag="div"),
    link="a[href]",
)


def parse_debet_cards(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, DEBET_CARDS, base_url)


class ApexBankConnector(CardListConnector):
    bank_code = "APEX"
    segment = "individual"
    layout = DEBET_CARDS

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url


def parse_exchange_rates(html: str, url: str = _EXCHANGE_URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one(".currency-card table")
    if not table:
        return []

    records = []
    for row in table.select("tr.tr-border"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        code_span = cells[0].find("span")
        buy_span = cells[1].find("span")
        sell_span = cells[2].find("span")
        if not code_span or not buy_span or not sell_span:
            continue

        code = code_span.get_text(strip=True)
        records.extend(rate_pair(
            code,
            parse_amount(buy_span.get_text(strip=True)),
            parse_amount(sell_span.get_text(strip=True)),
            source=_SOURCE,
            url=url,
        ))

    return records


class ApexBankExchangeConnector(HtmlPageConnector):
    bank_code = "APEX"
    product_type = "currency"
    segment = "individual"
    url = _EXCHANGE_URL

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_exchange_rates(html, self.url)
