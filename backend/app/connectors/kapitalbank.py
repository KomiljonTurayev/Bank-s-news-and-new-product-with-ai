"""kapital24.uz — Kapitalbank'ning jismoniy shaxslar uchun rasmiy sayti
(kapitalbank.uz o'zi asosan yuridik shaxslarga qaratilgan; jismoniy shaxs
mahsulotlari alohida kapital24.uz domenida joylashgan). Sayt oddiy
`requests` bilan Cloudflare/WAF orqali 403 qaytaradi — faqat haqiqiy
brauzer sifatida (Playwright) so'ralganda ochiladi."""

from app.connectors.base import CardListConnector, RenderedPageConnector
from app.connectors.html_cards import CardLayout, SelectedFields, parse_card_list

_BASE_URL = "https://www.kapital24.uz"

# Omonat sahifasida h3.item-title, kredit sahifasida h3.title ishlatiladi;
# kredit kartalarida ba'zan ikkinchi h3.title (masalan YouTube havolasi)
# ham uchraydi — tanlagich birinchi mos kelganini oladi.
ITEM_CARDS = CardLayout(
    source="kapital24.uz",
    card=".item.has-preview-picture",
    title="h3.item-title a, h3.title a",
    fields=SelectedFields(container=".item-prop", label="b", value="span", strip_colon=True),
)


def parse_item_cards(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, ITEM_CARDS, base_url)


class KapitalbankConnector(RenderedPageConnector, CardListConnector):
    """Kapitalbank rasmiy sayti (kapital24.uz) — jismoniy shaxslar uchun
    omonat/kredit/karta."""

    bank_code = "KDB"
    segment = "individual"
    layout = ITEM_CARDS

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url
