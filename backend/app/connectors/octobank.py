"""octobank.uz — sobiq "Ravnaq-bank" (domen ravnaqbank.uz endi
octobank.uz'ga yo'naltiriladi). Jismoniy shaxslar uchun faqat kredit va
karta mahsulotlari saytda ochiq — omonatlar veb-saytda umuman
ko'rsatilmaydi (faqat ilova orqali bo'lishi mumkin).

Kredit ro'yxat sahifasida (``/jismoniy-shaxslarga/kredity-i-mikrozaymy``)
faqat nom va tavsif bor, stavka/muddat yashiringan (``class="... hide"``)
— haqiqiy raqamlar har bir mahsulotning o'z sahifasida (``hero_16_item``
bloki) joylashgan, shu bois bu yerda ham (Garantbank kabi) alohida
sahifalar ro'yxati oldindan beriladi.

Kartalar xuddi shunday alohida sahifalarda, lekin BOSHQA razmetka
bilan (``hero_17_bottom_item``: ``h5`` yorliq + ``p`` qiymat) — ikkita
ro'yxat sahifasi bor: "Soʻm kartalari" (Humo) va "Xalqaro kartalar"
(Visa/Mastercard)."""

from app.connectors.base import MultiPageConnector
from app.connectors.html_cards import SelectedFields, parse_single_product

_BASE_URL = "https://octobank.uz"
_SOURCE = "octobank.uz"

_STATS = SelectedFields(container=".hero_16_item", label=".hero_16_item_paragraph", value=".hero_16_item_heading")


def parse_product_page(html: str, url: str) -> dict | None:
    return parse_single_product(html, _SOURCE, url, _STATS)


class OctobankConnector(MultiPageConnector):
    bank_code = "RAVNAQ"
    product_type = "credit"
    segment = "individual"
    log_label = "Octobank"

    def __init__(self, product_paths: list[str]):
        self.urls = [f"{_BASE_URL}{path}" for path in product_paths]

    def parse_page(self, html: str, url: str) -> list[dict]:
        record = parse_product_page(html, url)
        return [record] if record else []


_CARD_FIELDS = SelectedFields(
    container=".hero_17_bottom_item", label=".hero_17_bottom_item_heading", value=".hero_17_bottom_item_paragraph"
)


def parse_card_page(html: str, url: str) -> dict | None:
    return parse_single_product(html, _SOURCE, url, _CARD_FIELDS)


class OctobankCardConnector(MultiPageConnector):
    bank_code = "RAVNAQ"
    product_type = "card"
    segment = "individual"
    log_label = "Octobank (kartalar)"

    def __init__(self, product_paths: list[str]):
        self.urls = [f"{_BASE_URL}{path}" for path in product_paths]

    def parse_page(self, html: str, url: str) -> list[dict]:
        record = parse_card_page(html, url)
        return [record] if record else []
