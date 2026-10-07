"""tbcbank.uz — jismoniy shaxslar uchun omonatlar. Statik HTML, umumiy
CMS "block" tizimidan foydalanadi (har bir bo'lim ``data-block-type``
bilan belgilangan). TBC boshqa banklardan farqli — atigi 2 ta nomlangan
omonat turi bor ("Odat" va "Muddatli omonat"), shu bois mahsulot ro'yxati
o'rniga: (1) shu ikki turning umumiy karta ko'rsatkichlari, (2) so'mdagi
muddatli omonat kalkulyatoridagi har bir muddat uchun aniq stavka
alohida yozuv sifatida olinadi.

TBC kreditni faqat mobil ilova orqali beradi, saytda alohida kredit
ro'yxati sahifasi yo'q — shu bois faqat omonat connectori mavjud.

Diqqat: dollardagi muddatli omonat stavkalari (5,5%-6,5%) saytda faqat
"So'mda/Dollarda" tab almashtirilganda JS orqali render qilinadi,
statik HTML'da yo'q — shu bois bu yerda qamrab olinmagan."""

import re

from bs4 import BeautifulSoup

from app.connectors.base import HtmlPageConnector
from app.connectors.html_cards import CardLayout, ChildPairFields, parse_card_list

_URL = "https://tbcbank.uz/product/depozity/"
_SOURCE = "tbcbank.uz"

_TERM_RATE_RE = re.compile(r"^(\d+)\s*oy\s*\(([\d.,]+)%\)$")

SUMMARY_CARDS = CardLayout(
    source=_SOURCE,
    card=(
        '[data-block-type="blocks.image-with-text-block"], '
        '[data-block-type="blocks.image-with-text-tabs-block"]'
    ),
    title='h4[data-testid="text"]',
    fields=ChildPairFields(container='ul[data-testid="list"] > li', child_tags=("h4", "h4"), value_first=False),
)


def _parse_summary_cards(html: str) -> list[dict]:
    # "name" + "source"dan tashqari kamida bitta ko'rsatkichi bor kartalar
    # olinadi — reklama banneri (masalan "Ishonchli va kafolatlangan
    # onlayn omonatlar") stat ro'yxatiga ega emas.
    return [record for record in parse_card_list(html, SUMMARY_CARDS, _URL) if len(record) > 2]


def _parse_term_calculator(soup: BeautifulSoup) -> list[dict]:
    calc = soup.select_one('[data-block-type="blocks.deposit-calculator-form-block"]')
    if not calc:
        return []

    records = []
    for button in calc.find_all("button"):
        match = _TERM_RATE_RE.match(button.get_text(strip=True))
        if not match:
            continue
        term, rate = match.groups()
        records.append({
            "name": f"So'mdagi muddatli omonat ({term} oy)",
            "source": _SOURCE,
            "Muddati": f"{term} oy",
            "Foiz stavkasi": f"{rate}%",
            "url": _URL,
        })
    return records


def parse_deposits(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    return _parse_summary_cards(html) + _parse_term_calculator(soup)


class TBCBankConnector(HtmlPageConnector):
    bank_code = "TBC"
    product_type = "deposit"
    segment = "individual"
    url = _URL

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_deposits(html)
