"""aloqabank.uz — jismoniy shaxslar uchun omonat/kredit. Statik HTML,
Bitrix CMS. Omonat va kredit sahifalari bir xil ".element" kartasidan
foydalanadi."""

from app.connectors.base import CardListConnector
from app.connectors.html_cards import CardLayout, SelectedFields, parse_card_list

_BASE_URL = "https://aloqabank.uz"

ELEMENT_CARDS = CardLayout(
    source="aloqabank.uz",
    card=".element",
    title=".element__title a",
    fields=SelectedFields(
        container=".element-info__group",
        label=".element-info__label",
        value=".element-info__value",
    ),
)


def parse_element_cards(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, ELEMENT_CARDS, base_url)


class AloqabankConnector(CardListConnector):
    bank_code = "ALOQA"
    segment = "individual"
    layout = ELEMENT_CARDS

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url
