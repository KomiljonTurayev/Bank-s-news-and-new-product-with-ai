"""aab.uz (Asia Alliance Bank) — jismoniy shaxslar uchun omonat/kredit
va valyuta kursi. Statik HTML, Bitrix CMS. Omonat va kredit sahifalari
bir xil ".element" kartasidan foydalanadi (Aloqabank'nikiga o'xshash,
lekin maydon klasslari farq qiladi).

Valyuta kursi sahifasi (``/uz/private/currency-operations/``) har bir
kanal/valyuta juftligi uchun alohida blok beradi:
``data-tabs-target="tab-BANK-USD"`` kabi — kanal (BANK/ATM/APP) va
valyuta kodi shu atributning o'zida keladi, shu bois faqat "BANK"
(filial) prefiksli bloklar olinadi."""

import re

from bs4 import BeautifulSoup

from app.connectors.base import CardListConnector, HtmlPageConnector
from app.connectors.exchange import rate_pair
from app.connectors.html_cards import CardLayout, SelectedFields, parse_card_list

_BASE_URL = "https://aab.uz"
_EXCHANGE_URL = f"{_BASE_URL}/uz/private/currency-operations/"
_SOURCE = "aab.uz"

ELEMENT_CARDS = CardLayout(
    source=_SOURCE,
    card=".element",
    title=".element__title a",
    fields=SelectedFields(
        container=".element__param",
        label=".element__param--label",
        value=".element__param--value",
        value_separator="",
    ),
)


def parse_element_cards(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, ELEMENT_CARDS, base_url)


class AsiaAllianceConnector(CardListConnector):
    bank_code = "ASIAALLIANCE"
    segment = "individual"
    layout = ELEMENT_CARDS

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url


_RATE_NUMBER_RE = re.compile(r"[\d.]+")


def _rate_from(text: str) -> float | None:
    match = _RATE_NUMBER_RE.search(text)
    return float(match.group()) if match else None


def parse_exchange_rates(html: str, url: str = _EXCHANGE_URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    records = []
    for content in soup.select('[data-tabs-target^="tab-BANK-"]'):
        code = content["data-tabs-target"].rsplit("-", 1)[-1]

        values = {}
        for li in content.select(".exchange-info__data li"):
            label = li.select_one(".exchange-info__label")
            value = li.select_one(".exchange-info__value")
            if label and value:
                values[label.get_text(strip=True)] = value.get_text(strip=True)

        records.extend(rate_pair(
            code,
            _rate_from(values.get("Sotib olish", "")),
            _rate_from(values.get("Sotish", "")),
            source=_SOURCE,
            url=url,
        ))

    return records


class AsiaAllianceExchangeConnector(HtmlPageConnector):
    bank_code = "ASIAALLIANCE"
    product_type = "currency"
    segment = "individual"
    url = _EXCHANGE_URL

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_exchange_rates(html, self.url)
