"""madadinvestbank.uz (Madad Invest Bank, "Mybank") — jismoniy shaxslar
uchun omonat/kredit. Statik HTML, lekin ikki mahsulot turi ikki xil
sxemada joylashgan:

- Omonatlar (`/vklads`) — bitta ro'yxat sahifasida to'liq ma'lumot bilan
  (`.vklad-bl__item` kartalari).
- Kreditlar (`/credits/physical`) — ro'yxat sahifasida faqat nom va
  havola bor, stavka/muddat HTML'da izohga olib qo'yilgan (kommentariya
  ichida); haqiqiy raqamlar faqat har bir kreditning o'z sahifasida
  (`/credit/<id>`) mavjud. Shu sabab kredit uchun avval ro'yxat
  sahifasidan havolalar terib olinadi, keyin har biri alohida yuklanadi.

Valyuta kursi (`/currency`) esa toza statik jadval — "Belgilar kodi"
ustuni to'g'ridan-to'g'ri ISO kodini beradi."""

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.connectors.base import BaseConnector, HtmlPageConnector
from app.connectors.exchange import parse_amount, rate_pair
from app.connectors.html_cards import CardLayout, ChildPairFields, parse_card_list
from app.connectors.http import HTTP

_BASE_URL = "https://madadinvestbank.uz"
_EXCHANGE_URL = f"{_BASE_URL}/currency"
_SOURCE = "madadinvestbank.uz"
_PARSER = "html.parser"

# Saytning o'zida xato — Angliya funtining kodi "GBR" (davlat kodi)
# deb yozilgan, to'g'risi "GBP". Boshqa banklar bilan solishtirish
# buzilmasligi uchun tuzatiladi.
_CODE_FIXES = {"GBR": "GBP"}

DEPOSIT_CARDS = CardLayout(
    source=_SOURCE,
    card=".vklad-bl__item",
    title=".vklad-main__tit",
    # ".vklad-main__pro" ichida qiymat span'i ("13") yorliq span'i
    # ("muddati") ichiga emas, uning yoniga (div ichiga) o'ralgan — shu
    # bois "birinchi span" emas, aynan direct-child div/span juftligi
    # olinadi (aks holda ichki span xato ravishda yorliq deb o'qilardi).
    fields=ChildPairFields(
        container=".vklad-main__pro", child_tags=("div", "span"), value_first=True, value_separator="",
    ),
    link=".vklad-main__link a[href]",
)


def parse_deposits(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, DEPOSIT_CARDS, base_url)


def find_credit_links(html: str, base_url: str = _BASE_URL) -> list[str]:
    soup = BeautifulSoup(html, _PARSER)
    links = []
    for card in soup.select(".kred-bl__item"):
        link = card.select_one("a[href]")
        if link is None:
            continue
        href = link.get("href")
        if href:
            links.append(urljoin(base_url, href))
    return links


def parse_credit_detail(html: str, url: str) -> dict | None:
    soup = BeautifulSoup(html, _PARSER)
    title_el = soup.select_one("h1")
    if title_el is None:
        return None
    name = title_el.get_text(strip=True)
    if not name:
        return None

    record = {"name": name, "source": _SOURCE, "url": url}
    for item in soup.select(".ipotek-form__item"):
        value_el = item.select_one("div span")
        if value_el is None:
            continue
        label_input = item.select_one("input[placeholder]")
        if label_input is None:
            # "Hisoblash" tugmasi kabi juftlikda kelmaydigan elementlar —
            # bitta nomukammal qator butun sahifani buzmasin.
            continue
        label = label_input.get("placeholder", "").strip()
        value = value_el.get_text(strip=True)
        if label and value:
            record[label] = value

    return record if len(record) > 3 else None  # name/source/url'dan tashqari kamida bitta ko'rsatkich


class MadadInvestBankConnector(BaseConnector):
    bank_code = "MADAD"
    segment = "individual"

    def __init__(self, product_type: str):
        self.product_type = product_type
        self.url = f"{_BASE_URL}/vklads" if product_type == "deposit" else f"{_BASE_URL}/credits/physical"

    def fetch_raw(self):
        listing_html = HTTP.text(self.url)
        if self.product_type == "deposit":
            return listing_html
        return HTTP.pages(find_credit_links(listing_html, _BASE_URL), "MadadInvestBank")

    def parse(self, raw):
        if self.product_type == "deposit":
            return parse_deposits(raw, _BASE_URL)

        records = []
        for url, html in raw:
            record = parse_credit_detail(html, url)
            if record:
                records.append(record)
        return records


def parse_exchange_rates(html: str, url: str = _EXCHANGE_URL) -> list[dict]:
    """Sahifada bir nechta jadval bor (filial, so'ng "Bankomat") — faqat
    birinchisi (filial) olinadi."""
    soup = BeautifulSoup(html, _PARSER)
    table = soup.select_one("table")
    if table is None:
        return []

    records = []
    for row in table.select("tbody tr"):
        cells = row.select("td")
        if len(cells) < 4:
            continue

        code = _CODE_FIXES.get(cells[1].get_text(strip=True), cells[1].get_text(strip=True))
        records.extend(rate_pair(
            code,
            parse_amount(cells[2].get_text(strip=True)),
            parse_amount(cells[3].get_text(strip=True)),
            source=_SOURCE,
            url=url,
        ))

    return records


class MadadInvestBankExchangeConnector(HtmlPageConnector):
    bank_code = "MADAD"
    product_type = "currency"
    segment = "individual"
    url = _EXCHANGE_URL

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_exchange_rates(html, self.url)
