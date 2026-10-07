"""ipotekabank.uz — Ipoteka-bank rasmiy sayti. Biznes va jismoniy shaxs
sahifalari bir xil ".product-card" razmetkasidan foydalanadi, shu bois
ikkala segment ham bitta joylashuv e'loni bilan o'qiladi.

Valyuta kursi sahifasidagi "Filialda" tabi (bosh, ``id="all"``) olinadi —
"Bankomatda"/"Ilovada" tablari o'z alohida stavkalariga ega, lekin
filial stavkasi asosiy/qiyoslanadigan qiymat hisoblanadi."""

from bs4 import BeautifulSoup

from app.connectors.base import CardListConnector, HtmlPageConnector
from app.connectors.exchange import parse_amount, rate_pair
from app.connectors.html_cards import CardLayout, SelectedFields, parse_card_list

_BASE_URL = "https://ipotekabank.uz"
_EXCHANGE_URL = "https://www.ipotekabank.uz/private/services/currency/"
_SOURCE = "ipotekabank.uz"

# ipotekabank.uz'ning turli shablonlarida .dt/.dd tartibi izchil emas —
# biznes va omonat sahifalarida .dt=nom/.dd=qiymat, jismoniy shaxs kredit
# sahifasida esa teskari, shu bois raqam saqlagan tomon qiymat deb
# hisoblanadi (`swap_on_digits`).
PRODUCT_CARDS = CardLayout(
    source=_SOURCE,
    card=".product-card",
    title=".product-card__title",
    fields=SelectedFields(
        container=".dl",
        label=".dt",
        value=".dd",
        swap_on_digits=True,
        value_separator="",
    ),
    link=("a.button--text", ".product-card__btns a"),
)


def parse_product_cards(html: str, base_url: str = _BASE_URL) -> list[dict]:
    """".product-card" bloklarini (nom + dt/dd juftlari) normalizatsiya
    qilingan dict'lar ro'yxatiga aylantiradi. Har bir mahsulot o'zining
    "Barcha shartlari" havolasini (bankning haqiqiy sahifasi) olib
    yuradi."""
    return parse_card_list(html, PRODUCT_CARDS, base_url)


class IpotekaBusinessConnector(CardListConnector):
    bank_code = "IPOTEKA"
    layout = PRODUCT_CARDS

    def __init__(self, product_type: str, url: str, segment: str = "business"):
        self.product_type = product_type
        self.url = url
        self.segment = segment


def parse_exchange_rates(html: str, url: str = _EXCHANGE_URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("#all table.currency-table") or soup.select_one("table.currency-table")
    if not table:
        return []

    records = []
    for row in table.select("tbody tr"):
        cells = row.select("td")
        if len(cells) < 3:
            continue
        # Valyuta kodi nishonchaning ikkinchi bo'lagida ("🇺🇸" + "USD").
        badge_spans = cells[0].select(".currency-badge span")
        if len(badge_spans) < 2:
            continue
        records.extend(rate_pair(
            badge_spans[1].get_text(strip=True),
            parse_amount(cells[1].get_text()),
            parse_amount(cells[2].get_text()),
            source=_SOURCE,
            url=url,
        ))

    return records


class IpotekaExchangeConnector(HtmlPageConnector):
    bank_code = "IPOTEKA"
    product_type = "currency"
    segment = "individual"
    url = _EXCHANGE_URL

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_exchange_rates(html, self.url)
