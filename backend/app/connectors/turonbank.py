"""turonbank.uz — jismoniy shaxslar uchun omonat/kredit/karta. Statik
HTML, Bitrix CMS. Omonat va kredit sahifalari bir xil ".item" kartasidan
foydalanadi.

Kartalar uchun esa Garantbank'dagi kabi bitta ro'yxat sahifasi yo'q —
har bir karta turi (Humo, Uzcard, Visa Classic va h.k.) o'z alohida
sahifasida joylashgan, tariflar esa toza label:value juftlik emas,
balki bitta ozod matnli blokda ("Tariflar" sarlavhali
".requirements__list--check"), qatorlar <br> bilan va har qatordagi
yorliq/qiymat esa "-" yoki "–" bilan ajratilgan
("Karta ochish - 50 000 so'm;")."""

import re
from dataclasses import replace
from typing import cast

from bs4 import BeautifulSoup, Tag

from app.connectors.base import CardListConnector, MultiPageConnector
from app.connectors.html_cards import CardLayout, SelectedFields, parse_card_list

_BASE_URL = "https://turonbank.uz"
_SOURCE = "turonbank.uz"
_FIELD_SPLIT_RE = re.compile(r"\s[-–]\s")

# Qiymat katakchasi saytda ikki xil klass bilan keladi (".item__value" va
# ".item__data") — ikkalasi ham bir xil ma'noda.
ITEM_CARDS = CardLayout(
    source=_SOURCE,
    card=".item",
    title=".item__title a",
    fields=SelectedFields(
        container=".item__info",
        label=".item__label",
        value=".item__value, .item__data",
    ),
)


def _layout_with_source(source: str) -> CardLayout:
    return cast(CardLayout, replace(ITEM_CARDS, source=source))


def parse_item_cards(
    html: str,
    base_url: str = _BASE_URL,
    source: str = _SOURCE,
) -> list[dict]:
    return parse_card_list(html, _layout_with_source(source), base_url)


class TuronbankConnector(CardListConnector):
    """turonbank.uz uchun. Poytaxt bank ham xuddi shu Bitrix shabloni
    (".item"/".item__info") ishlatadi — bank_code/segment/source'ni
    bekor qilib shu klassning o'zi qayta ishlatiladi (app/connectors/poytaxtbank.py)."""

    bank_code = "TURON"
    segment = "individual"
    source = _SOURCE

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url

    @property
    def layout(self) -> CardLayout:
        return _layout_with_source(self.source)


def parse_card_tariff_page(html: str, url: str) -> dict | None:
    """Bitta karta sahifasidagi "Tariflar" blokini o'qiydi — u strukturaviy
    yorliq/qiymat juftliklari emas, "Karta ochish - 50 000 so'm;" kabi
    qatorlardan iborat ozod matn."""
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.select_one("h1")
    if title_el is None:
        return None
    name = title_el.get_text(strip=True)
    if not name:
        return None

    tariff_block = _find_tariff_block(soup)
    if tariff_block is None:
        return None

    tariff_text = tariff_block.get_text(separator="\n")
    if not tariff_text.strip():
        return None

    record = {"name": name, "source": _SOURCE, "url": url}
    for line in tariff_text.split("\n"):
        line = line.strip().rstrip(";").strip()
        if not line:
            continue
        parts = _FIELD_SPLIT_RE.split(line, maxsplit=1)
        if len(parts) != 2:
            continue
        label, value = parts[0].strip(), parts[1].strip()
        if label and value:
            record[label] = value

    return record


def _find_tariff_block(soup: BeautifulSoup) -> Tag | None:
    for item in soup.select(".requirements__item"):
        title = item.select_one(".requirements__title")
        if title is None:
            continue
        if title.get_text(strip=True) != "Tariflar":
            continue
        tariff_list = item.select_one(".requirements__list")
        if tariff_list is None:
            continue
        return tariff_list
    return None


class TuronbankCardConnector(MultiPageConnector):
    """Kartalar sahifalarida bitta ro'yxat yo'q — har biri o'z alohida
    sahifasida (qarang: modul docstring'i)."""

    bank_code = "TURON"
    product_type = "card"
    segment = "individual"
    log_label = "Turonbank"

    def __init__(self, product_paths: list[str]):
        self.urls = [f"{_BASE_URL}{path}" for path in product_paths]

    def parse_page(self, html: str, url: str) -> list[dict]:
        record = parse_card_tariff_page(html, url)
        return [record] if record else []
