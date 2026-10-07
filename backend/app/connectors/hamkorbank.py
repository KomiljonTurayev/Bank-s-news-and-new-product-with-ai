"""hamkorbank.uz — jismoniy shaxslar uchun omonat/kredit/karta mahsulotlari.
Sayt JavaScript orqali client-tomonda render qilinadi (Next.js), shu sabab
oddiy `requests` o'rniga app/connectors/playwright_fetch.py orqali headless
brauzerda ochiladi. Omonat va kredit sahifalari ikki xil shablon (turli CSS
klasslar) ishlatadi, shu bois har biri o'z joylashuv e'loniga ega. Kartalar
sahifasi kredit sahifasi bilan bir xil razmetkadan foydalanadi (shu bois
"card" turi ham kredit joylashuviga yo'naltiriladi).

Valyuta kursi sahifasi (`/uz/physical/currency-exchange-offices/`) o'zi
ham client-tomonda to'ldiriladi, lekin ochiq REST API'dan
(`api-dbo.hamkorbank.uz/webflow/v1/exchanges`) foydalanadi — shu sabab
Playwright shart emas. API'da har valyuta uchun bir nechta yozuv bor
(turli kanal/miqdor chegarasi bo'yicha); faqat asosiy filial kanali
(`destination_code == "2"`) va minimal miqdor chegarasi yo'q
(`begin_sum_i == 0`) yozuvlar olinadi. Stavkalar tiyinda beriladi
(UZS'ga aylantirish uchun 100'ga bo'linadi)."""

from app.connectors.base import JsonApiConnector, RenderedPageConnector
from app.connectors.exchange import rate_pair
from app.connectors.html_cards import CardLayout, SelectedFields, parse_card_list

_BASE_URL = "https://hamkorbank.uz"
_EXCHANGE_URL = f"{_BASE_URL}/uz/physical/currency-exchange-offices/"
_EXCHANGE_API_URL = "https://api-dbo.hamkorbank.uz/webflow/v1/exchanges"
_SOURCE = "hamkorbank.uz"

DEPOSIT_CARDS = CardLayout(
    source=_SOURCE,
    card="div.rounded-2xl.bg-white.p-5",
    title="h3",
    fields=SelectedFields(
        container=".border-gray-light.flex.w-full.flex-row-reverse",
        label=".text-body-s.text-secondary",
        value=".text-body-l",
    ),
    link_text="Batafsil",
)

CREDIT_CARDS = CardLayout(
    source=_SOURCE,
    card="div.flex.flex-col.bg-white.rounded-20.p-32.min-h-332",
    title="h3",
    fields=SelectedFields(
        container=".px-20.w-1-3",
        label=".text-size-s.text-gray",
        value=".font-medium.mb-8.text-size-l",
    ),
    link_text="Batafsil",
)


def parse_deposit_cards(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, DEPOSIT_CARDS, base_url)


def parse_credit_cards(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, CREDIT_CARDS, base_url)


class HamkorbankConnector(RenderedPageConnector):
    """hamkorbank.uz rasmiy sayti — jismoniy shaxslar uchun omonat/kredit/karta."""

    bank_code = "HAMKOR"
    segment = "individual"

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url
        self._layout = DEPOSIT_CARDS if product_type == "deposit" else CREDIT_CARDS

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_card_list(html, self._layout, base_url)


def parse_exchange_rates(data: dict, url: str = _EXCHANGE_URL) -> list[dict]:
    records = []
    for item in data.get("data", []):
        if item.get("destination_code") != "2" or item.get("begin_sum_i"):
            continue
        try:
            buy_rate = float(item["buying_rate"]) / 100
            sell_rate = float(item["selling_rate"]) / 100
        except (KeyError, TypeError, ValueError):
            continue
        records.extend(rate_pair(item.get("currency_char"), buy_rate, sell_rate, source=_SOURCE, url=url))

    return records


class HamkorbankExchangeConnector(JsonApiConnector):
    bank_code = "HAMKOR"
    product_type = "currency"
    segment = "individual"
    url = _EXCHANGE_URL
    api_url = _EXCHANGE_API_URL

    def parse_payload(self, payload: dict, url: str) -> list[dict]:
        return parse_exchange_rates(payload, url)
