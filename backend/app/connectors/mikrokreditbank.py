"""mkbank.uz (Mikrokreditbank) — jismoniy shaxslar uchun omonat/kredit.
Statik HTML, Bitrix CMS. Omonat va kredit sahifalari bir xil "article.itemb"
kartasidan foydalanadi."""

from app.connectors.base import CardListConnector
from app.connectors.html_cards import CardLayout, SelectedFields, parse_card_list

_BASE_URL = "https://mkbank.uz"

ITEMB_CARDS = CardLayout(
    source="mkbank.uz",
    card="article.itemb",
    title=".itemb__title a",
    fields=SelectedFields(container=".itemb__info", label=".itemb__label", value=".itemb__value"),
)


def parse_itemb_cards(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, ITEMB_CARDS, base_url)


class MikrokreditbankConnector(CardListConnector):
    bank_code = "MICROCREDITBANK"
    segment = "individual"
    layout = ITEMB_CARDS

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url
