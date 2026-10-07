"""asakabank.uz — jismoniy shaxslar uchun omonat/kredit. Nuxt.js SPA (JS
render talab qiladi, playwright_fetch orqali olinadi). Omonat va kredit
sahifalari bir xil komponent (`.ui-card` + `.product-description-list`)
ishlatadi — bitta joylashuv ikkalasiga ham mos keladi.

Sahifada uchta tab bor (Barcha mahsulotlar / Xorijiy valyutadagi /
Milliy valyutadagi) — ularning kontenti DOM'da bir vaqtda mavjud, faqat
birinchisi (barchasi) ``hidden`` atributisiz, shu bois faqat o'shani
o'qish dublikatlarning oldini oladi.

Kartalar sahifasidagi ba'zi mahsulotlar (masalan "UzukPay") xuddi shu
".product-description-list" klassini reklama matni uchun ham ishlatadi
(qisqa sarlavha h1'da, uzun tavsif esa p'da — stavka/muddat kabi
qisqa qiymatlarning teskarisi), shu bois haqiqiy maydon emasligini
aniqlash uchun uzun matnli juftliklar chetlab o'tiladi (`max_length`)."""

from bs4 import BeautifulSoup

from app.connectors.base import RenderedPageConnector
from app.connectors.html_cards import CardLayout, ChildPairFields, parse_card_list

_BASE_URL = "https://asakabank.uz"
_MAX_FIELD_LEN = 60

PRODUCT_CARDS = CardLayout(
    source="asakabank.uz",
    card=".ui-card",
    title="h1",
    fields=ChildPairFields(
        container=".product-description-list > div",
        child_tags=("h1", "p"),
        value_first=True,
        max_length=_MAX_FIELD_LEN,
    ),
    link="a",
)


def parse_products(html: str, base_url: str = _BASE_URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    panel = soup.select_one('[role="tabpanel"]:not([hidden])') or soup
    return parse_card_list(str(panel), PRODUCT_CARDS, base_url)


class AsakabankConnector(RenderedPageConnector):
    bank_code = "ASAKA"
    segment = "individual"

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_products(html, base_url)
