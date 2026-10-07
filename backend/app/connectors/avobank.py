"""avobank.uz (AVO bank, sobiq O'zagroeksportbank) — jismoniy shaxslar
uchun omonat va "AVO platinum" kredit kartasi. Har bir omonat mahsuloti
o'z sahifasida, shartlar ``<dl class="SliceContent_rows...">`` ta'rif
ro'yxatida beriladi (``dt`` — label, ``dd`` — qiymat).

/products/personal-loan — alohida "muddatli kredit" mahsuloti emas,
balki xuddi shu "AVO platinum" kartasining boshqa marketing sahifasi
(kartaga naqd pul o'tkazish stsenariysi): statik HTML'da bo'sh
akkordionlar bo'lsa-da, kalkulyator bloki o'sha kartaning nomi va
stavkasini (27,9-74,9%) o'z ichiga oladi — bu sayt Prismic CMS'ga
tayanadi, buni ``https://avo-uz.cdn.prismic.io/api/v2`` ochiq API'si
orqali tasdiqlash mumkin (masalan "interest-rate-on-a-loan" akkordion
hujjati xuddi shu stavka oralig'ini qaytaradi). Shu sabab alohida
kredit connectori shart emas.

Kredit kartasi sahifasi (/products/credit-card) esa ancha sodda:
``<script type="application/ld+json">`` ichida schema.org
``CreditCard`` strukturasi bor (``annualPercentageRate``, ``amount``) —
oddiy `requests` bilan to'g'ridan-to'g'ri o'qiladi, JS render shart
emas."""

import json

from bs4 import BeautifulSoup

from app.connectors.base import HtmlPageConnector, MultiPageConnector
from app.connectors.html_cards import SelectedFields, parse_single_product

_BASE_URL = "https://avobank.uz"
_CREDIT_CARD_URL = f"{_BASE_URL}/uz/products/credit-card"
_SOURCE = "avobank.uz"

_DEPOSIT_ROWS = SelectedFields(container=".SliceContent_row__L_Oka", label=".SliceContent_row_label__rmsbk", value="dd")


def _strip_slogan(name: str) -> str:
    # Ba'zi sahifalarda h1 <br/> bilan bir necha qatorli reklama
    # sarlavhasi ("AVO omonati — yillik 22% gacha daromadlilik") —
    # faqat "—"dan oldingi qismini haqiqiy mahsulot nomi deb olamiz.
    return name.split("—")[0].strip()


def parse_deposit_page(html: str, url: str) -> dict | None:
    return parse_single_product(html, _SOURCE, url, _DEPOSIT_ROWS, clean_name=_strip_slogan)


class AvobankConnector(MultiPageConnector):
    bank_code = "AVOBANK"
    product_type = "deposit"
    segment = "individual"
    log_label = "Avobank"

    def __init__(self, product_paths: list[str]):
        self.urls = [f"{_BASE_URL}{path}" for path in product_paths]

    def parse_page(self, html: str, url: str) -> list[dict]:
        record = parse_deposit_page(html, url)
        return [record] if record else []


def parse_credit_card_page(html: str, url: str = _CREDIT_CARD_URL) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", type="application/ld+json")
    if not script or not script.string:
        return None

    try:
        data = json.loads(script.string)
    except json.JSONDecodeError:
        return None

    name = data.get("name")
    apr = data.get("annualPercentageRate")
    if not name or apr is None:
        return None

    record = {
        "name": name,
        "source": _SOURCE,
        "url": url,
        "Yillik foiz stavkasi": f"{apr}%",
    }

    amount = data.get("amount") or {}
    min_value, max_value = amount.get("minValue"), amount.get("maxValue")
    if min_value and max_value:
        record["Kredit limiti"] = f"{min_value:,} - {max_value:,} so'm".replace(",", " ")

    return record


class AvobankCreditCardConnector(HtmlPageConnector):
    bank_code = "AVOBANK"
    product_type = "card"
    segment = "individual"
    url = _CREDIT_CARD_URL

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        record = parse_credit_card_page(html, self.url)
        return [record] if record else []
