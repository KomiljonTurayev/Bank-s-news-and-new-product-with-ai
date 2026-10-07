"""brb.uz (Biznesni rivojlantirish banki) — jismoniy shaxslar uchun
omonat/kredit. Statik HTML, toza semantik <dt>/<dd> juftlari bilan."""

from app.connectors.base import CardListConnector
from app.connectors.html_cards import CardLayout, SelectedFields, parse_card_list

_BASE_URL = "https://brb.uz"

PRODUCT_OFFERS = CardLayout(
    source="brb.uz",
    card="section.product-offer",
    title=".product-offer__title",
    fields=SelectedFields(container=".product-offer__fact", label="dt", value="dd"),
    link=".product-offer__actions a[href]",
)


def parse_product_offers(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, PRODUCT_OFFERS, base_url)


class BRBConnector(CardListConnector):
    bank_code = "BRB"
    segment = "individual"
    layout = PRODUCT_OFFERS

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url
