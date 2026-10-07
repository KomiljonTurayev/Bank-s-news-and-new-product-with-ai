"""ofb.uz (Orient Finans bank) — jismoniy shaxslar uchun omonat/kredit,
karta va valyuta kursi. Mahsulot katalogi Alpine.js/Tailwind bilan
client-tomonda render qilinadi (boshlang'ich HTML'da bo'sh), shu bois
Playwright orqali ochiladi.

Kredit/omonat — bitta ro'yxat sahifasida bir nechta karta (``OrientFinansConnector``).
Jismoniy shaxs kartalari esa (biznes kartalaridan farqli — ular ``/kartalar``
umumiy sahifasida ``.card--product-catalog`` bilan chiqadi) ro'yxat
sahifasida faqat oddiy havolalar sifatida ko'rinadi, shartlari yo'q — har
birining shartlari faqat o'z alohida sahifasida (masalan
``/kartalar/uzcard-sherdor``) joylashgan, shu bois ular uchun
``MultiPageConnector`` ishlatiladi (``OrientFinansCardConnector``): har
sahifada ``<h1>`` mahsulot nomi, shartlari esa ``div.gap-regular.flex.flex-col``
o'ramida ``p.text-h5`` (yorliq) + ``div.text-h2`` (qiymat) juftligida.

Valyuta kursi sahifasi (``/kursy-valyut``) esa server-rendered —
oddiy `requests` yetarli, JS shart emas."""

import logging

from bs4 import BeautifulSoup

from app.connectors.base import HtmlPageConnector, MultiPageConnector, RenderedPageConnector
from app.connectors.exchange import parse_amount, rate_pair
from app.connectors.html_cards import CardLayout, SelectedFields, SiblingFields, parse_card_list, parse_single_product

_BASE_URL = "https://ofb.uz"
_EXCHANGE_URL = f"{_BASE_URL}/kursy-valyut"
_SOURCE = "ofb.uz"

PRODUCT_CARDS = CardLayout(
    source=_SOURCE,
    card=".card--product-catalog",
    title="h3.text-h2.font-medium",
    fields=SiblingFields(label=".text-md", value_tag="div"),
    link="a[href]",
)


def parse_product_cards(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, PRODUCT_CARDS, base_url)


class OrientFinansConnector(RenderedPageConnector):
    bank_code = "ORIENT"
    segment = "individual"

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_product_cards(html, base_url)


_CARD_DETAIL_FIELDS = SelectedFields(container="div.gap-regular.flex.flex-col", label="p.text-h5", value="div.text-h2")


def parse_card_detail_page(html: str, url: str) -> dict | None:
    return parse_single_product(html, _SOURCE, url, _CARD_DETAIL_FIELDS)


class OrientFinansCardConnector(MultiPageConnector):
    """Jismoniy shaxs kartalari — har biri o'z alohida (JS bilan render
    qilinadigan) sahifasida, shu bois odatdagi `requests`-asosli
    `MultiPageConnector.fetch_raw()` o'rniga Playwright ishlatiladi."""

    bank_code = "ORIENT"
    product_type = "card"
    segment = "individual"
    log_label = "Orient Finans (kartalar)"

    def __init__(self, urls: list[str]):
        self.urls = urls

    def fetch_raw(self) -> list[tuple[str, str]]:
        from playwright.sync_api import Error as PlaywrightError

        from app.connectors.playwright_fetch import fetch_rendered_html
        from app.resilience import CircuitBreakerOpen

        pages = []
        for url in self.urls:
            try:
                pages.append((url, fetch_rendered_html(url)))
            except (PlaywrightError, CircuitBreakerOpen):
                logging.getLogger(__name__).warning(
                    "%s: %s yuklab bo'lmadi, o'tkazib yuborildi", self.log_label, url, exc_info=True
                )
        return pages

    def parse_page(self, html: str, url: str) -> list[dict]:
        record = parse_card_detail_page(html, url)
        return [record] if record else []


def parse_exchange_rates(html: str, url: str = _EXCHANGE_URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.currency-table")
    if not table:
        return []

    records = []
    for row in table.select("tbody tr"):
        img = row.select_one("img[alt]")
        code = img["alt"].replace(" flag", "").strip() if img else None
        buy_el = row.select_one('td[data-label="Buy"] p')
        sell_el = row.select_one('td[data-label="Sell"] p')
        records.extend(rate_pair(
            code,
            parse_amount(buy_el.get_text(strip=True)) if buy_el else None,
            parse_amount(sell_el.get_text(strip=True)) if sell_el else None,
            source=_SOURCE,
            url=url,
        ))

    return records


class OrientFinansExchangeConnector(HtmlPageConnector):
    bank_code = "ORIENT"
    product_type = "currency"
    segment = "individual"
    url = _EXCHANGE_URL

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_exchange_rates(html, self.url)
