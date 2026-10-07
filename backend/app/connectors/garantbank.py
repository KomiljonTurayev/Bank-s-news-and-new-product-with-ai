"""garantbank.uz — jismoniy shaxslar uchun omonat/kredit. Boshqa
banklardan farqli — bitta ro'yxat sahifasi yo'q, har bir mahsulot o'z
alohida sahifasida joylashgan (masalan /uz/vklad-orzu-sari).

Har bir mahsulot sahifasida bir xil "at-a-glance" xulosa bloki bor:
``ul.product-terms > li.product-term`` — har biri ``<b>qiymat</b>`` va
``<span>yorliq</span>`` juftligi."""

from app.connectors.base import MultiPageConnector
from app.connectors.html_cards import SelectedFields, parse_single_product

_BASE_URL = "https://garantbank.uz"
_SOURCE = "garantbank.uz"

_TERMS = SelectedFields(container=".product-term-content", label="span", value="b")


def parse_product_page(html: str, url: str) -> dict | None:
    return parse_single_product(html, _SOURCE, url, _TERMS)


class GarantbankConnector(MultiPageConnector):
    bank_code = "GARANT"
    segment = "individual"
    log_label = "Garantbank"

    def __init__(self, product_type: str, product_paths: list[str]):
        self.product_type = product_type
        self.urls = [f"{_BASE_URL}{path}" for path in product_paths]

    def parse_page(self, html: str, url: str) -> list[dict]:
        record = parse_product_page(html, url)
        return [record] if record else []
