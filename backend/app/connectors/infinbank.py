"""infinbank.com — jismoniy shaxslar uchun omonat/kredit va valyuta
kursi. Statik HTML, lekin omonat va kredit sahifalari ikki xil shablon
(turli CSS klasslar) ishlatadi, shu bois har biri o'z joylashuv
e'loniga ega.

Valyuta kursi sahifasi (``/uz/private/exchange-rates/``) valyutalarni
ustun sifatida (USD/EUR/GBP/...), kanallarni esa qator-guruh sifatida
("MB kurs", "Ayrboshlash shoxobchasi", "Ilova", "Bankomat" — har biri
Olish/Sotish qatorlari bilan, ``rowspan`` orqali guruh nomini
ulashadi) joylashtiradi. Faqat "Ayrboshlash shoxobchasi" (filial)
qatorlari olinadi; mavjud bo'lmagan qiymatlar "-" bilan belgilanadi."""

from bs4 import BeautifulSoup

from app.connectors.base import CardListConnector, HtmlPageConnector
from app.connectors.exchange import BUY, SELL, parse_amount
from app.connectors.html_cards import CardLayout, SelectedFields, parse_card_list

_BASE_URL = "https://www.infinbank.com"
_EXCHANGE_URL = f"{_BASE_URL}/uz/private/exchange-rates/"
_SOURCE = "infinbank.com"
_BRANCH_GROUP = "Ayrboshlash shoxobchasi"

DEPOSIT_CARDS = CardLayout(
    source=_SOURCE,
    card=".js-deposit-card",
    title="h4.deposit-card__title",
    fields=SelectedFields(
        container=".deposit-card__detail-list__item",
        label=".main-text",
        value=".sub-text",
        strip_colon=True,
    ),
    link=".deposit-card__link",
)

CREDIT_CARDS = CardLayout(
    source=_SOURCE,
    card=".plastic-in-list__item",
    title=".plastic-in-content__link",
    fields=SelectedFields(
        container=".owner-list__item",
        label=".owner-list__title",
        value=".owner-list__text",
    ),
)


def parse_deposit_cards(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, DEPOSIT_CARDS, base_url)


def parse_credit_cards(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, CREDIT_CARDS, base_url)


class InFinbankConnector(CardListConnector):
    bank_code = "INFIN"
    segment = "individual"

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url
        self.layout = DEPOSIT_CARDS if product_type == "deposit" else CREDIT_CARDS


def _side_rate_records(codes: list, side_cell, rate_cells: list, url: str) -> list[dict]:
    side = side_cell.get_text(strip=True)
    if side not in (BUY, SELL):
        return []
    records = []
    for code, rate_cell in zip(codes, rate_cells):
        rate = parse_amount(rate_cell.get_text(strip=True))
        if rate is None:
            continue
        records.append({"code": code, "side": side, "rate": rate, "source": _SOURCE, "url": url})
    return records


def parse_exchange_rates(html: str, url: str = _EXCHANGE_URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table")
    if not table:
        return []

    codes = _currency_columns(table)
    if not codes:
        return []

    records = []
    current_group = None
    for row in table.select("tbody tr"):
        cells = row.find_all("td")
        if not cells:
            continue

        # Guruh nomi birinchi katakda faqat guruhning birinchi qatorida
        # keladi (rowspan bilan pastga cho'ziladi) — keyingi qatorlarda
        # oxirgi ko'rilgan nom amal qiladi.
        if "rates-subtitle" in (cells[0].get("class") or []):
            current_group = cells[0].get_text(strip=True)
            side_cell, rate_cells = cells[1], cells[2:]
        else:
            side_cell, rate_cells = cells[0], cells[1:]

        if current_group != _BRANCH_GROUP:
            continue

        records.extend(_side_rate_records(codes, side_cell, rate_cells, url))

    return records


def _currency_columns(table) -> list[str]:
    """Sarlavha qatoridagi valyuta kodlari — dastlabki ikki ustun
    (kanal nomi va Olish/Sotish yorlig'i) valyuta emas."""
    header_cells = table.select("thead th")[2:]
    codes = []
    for th in header_cells:
        text = th.select_one(".text")
        if text is not None:
            codes.append(text.get_text(strip=True))
    return codes


class InFinbankExchangeConnector(HtmlPageConnector):
    bank_code = "INFIN"
    product_type = "currency"
    segment = "individual"
    url = _EXCHANGE_URL

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_exchange_rates(html, self.url)
