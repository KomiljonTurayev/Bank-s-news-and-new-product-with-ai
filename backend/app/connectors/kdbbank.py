"""kdb.uz (KDB Bank O'zbekiston) — jismoniy shaxslar uchun kredit, karta
va valyuta ayirboshlash. Bank depozitlarni nol foizli hisobvaraq
sifatida yuritadi (foiz to'lamaydi), shu bois depozit sahifasi
qamrab olinmaydi.

Kredit sahifasida bitta mahsulot bor — "Korporativ mijozlar
xodimlariga mikroqarz (overdraft)" — shartlari ``<h3>Kredit Berish
Shartlari</h3>``'dan keyin darhol keladigan bir qator ``div.row``
bloklarida (``.col-lg-3 strong`` yorliq, ``.col-lg-9 p`` qiymat)
joylashgan.

Kartalar ikkita alohida sahifada — "Milliy kartalar" (HUMO/UzCard) va
"Xalqaro kartalar" (Visa) — bir xil ``a.card-link > article.card-cards``
razmetkasi bilan: sarlavha ``h3``, har bir xususiyat ``.col-md-4`` ichida
ikkita ``<p class="small-paragraph">`` juftligi (birinchisi yorliq,
ikkinchisi ichida ``<strong>`` bilan qiymat).

Valyuta kursi sahifasida (interaktiv xizmatlar) bir nechta tab (filial,
bankomat, mobil ilova) bor, har biri o'z jadvaliga ega — bularning
birinchisi ("Ayirboshlash/kassa shoxobchalarida", filial kurslari)
sahifa hujjatida ham birinchi ``<table>`` sifatida keladi va sahifaning
yuqori qismidagi marquee'dagi rasmiy kurs bilan mos keladi — shu bois
``soup.select("table")[0]`` orqali olinadi, tab ID'lariga tayanmasdan
(ID'lar sahifada boshqa, konversiya vidjeti kabi widjetlar bilan
ziddiyatga tushishi mumkin ekan)."""

from bs4 import BeautifulSoup

from app.connectors.base import CardListConnector, HtmlPageConnector
from app.connectors.exchange import parse_amount, rate_pair
from app.connectors.html_cards import CardLayout, SelectedFields

_SOURCE = "kdb.uz"
_URL = "https://kdb.uz/uz/individuals/credit"


def _condition_rows(h3) -> list:
    # Shartlar jadvali h3'dan keyin darhol keladigan uzluksiz div.row
    # ketma-ketligi — pastroqda "Istisno holatlar" bo'limi ham xuddi
    # shu "row" klassidan foydalanadi, shu bois birinchi mos kelmagan
    # birodarda to'xtaymiz.
    rows = []
    sibling = h3.find_next_sibling()
    while sibling is not None and sibling.name == "div" and "row" in (sibling.get("class") or []):
        rows.append(sibling)
        sibling = sibling.find_next_sibling()
    return rows


def _apply_condition_row(record: dict, row) -> None:
    label_el = row.select_one(".col-lg-3 strong")
    value_el = row.select_one(".col-lg-9 p")
    if label_el and value_el:
        label = label_el.get_text(strip=True).rstrip(":")
        value = value_el.get_text(" ", strip=True)
        if label and value:
            record[label] = value


def parse_credit(html: str, url: str = _URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("main.main-hero")
    if not main:
        return []

    h2 = main.find("h2")
    h3 = main.find("h3")
    if not h2 or not h3:
        return []

    name = h2.get_text(strip=True)
    if not name:
        return []

    record = {"name": name, "source": _SOURCE, "url": url}

    for row in _condition_rows(h3):
        _apply_condition_row(record, row)

    if not any(isinstance(v, str) and "%" in v for v in record.values()):
        return []

    return [record]


class KDBBankConnector(HtmlPageConnector):
    bank_code = "KDBUZ"
    product_type = "credit"
    segment = "individual"

    def __init__(self, url: str = _URL):
        self.url = url

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_credit(html, self.url)


_CARD_LAYOUT = CardLayout(
    source=_SOURCE,
    card="a.card-link",
    title="h3",
    link_from_card=True,
    fields=SelectedFields(container=".col-md-4", label="p.small-paragraph:not(.fs-14)", value="strong"),
)


class KDBBankCardConnector(CardListConnector):
    bank_code = "KDBUZ"
    product_type = "card"
    segment = "individual"
    layout = _CARD_LAYOUT

    def __init__(self, url: str):
        self.url = url


_EXCHANGE_URL = "https://kdb.uz/uz/interactive-services/exchange-rates"


def parse_exchange_rates(html: str, url: str = _EXCHANGE_URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table")
    if not table:
        return []

    headers = [th.get_text(strip=True) for th in table.select("thead th")]
    row = table.select_one("tbody tr")
    if not row:
        return []
    cells = row.select("td")

    records = []
    for code, cell in zip(headers[1:], cells):
        buy_text, sell_text = (cell.get_text(strip=True).split("/") + [None, None])[:2]
        records.extend(rate_pair(code, parse_amount(buy_text), parse_amount(sell_text), source=_SOURCE, url=url))
    return records


class KDBBankExchangeConnector(HtmlPageConnector):
    bank_code = "KDBUZ"
    product_type = "currency"
    segment = "individual"
    url = _EXCHANGE_URL

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_exchange_rates(html, self.url)
