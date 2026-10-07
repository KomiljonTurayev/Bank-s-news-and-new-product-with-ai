"""trastbank.uz — jismoniy shaxslar uchun omonat/kredit va valyuta
kursi. Statik HTML, Bitrix CMS. Omonat va kredit sahifalari ikki xil
shablon ishlatadi.

Valyuta kursi sahifasida (``/uz/services/exchange-rates/``) raqamlar
oddiy ``<script>`` ichidagi JS o'zgaruvchida keladi:
``var arCurrencyRates = {"CB":{...},"BUY":{...},"SALE":{...}};`` — JS
render shart emas. Diqqat: sahifaning o'zidagi "Sotish"/"Sotib olish"
UI yorliqlari mijoz nuqtai nazaridan yozilgan (chalkashtiruvchi — pastroq
narx "Sotish" deb ko'rsatiladi), shu bois biz JSON kalitlariga
tayanamiz: ``BUY`` — bank xarid qiladigan (pastroq) narx, ``SALE`` —
bank sotadigan (yuqoriroq) narx — bu depozit.uz'dagi "Olish"/"Sotish"
konvensiyasiga mos keladi."""

import json
import re

from app.connectors.base import CardListConnector, HtmlPageConnector
from app.connectors.exchange import BUY, SELL
from app.connectors.html_cards import CardLayout, SelectedFields, parse_card_list

_BASE_URL = "https://trastbank.uz"
_EXCHANGE_URL = f"{_BASE_URL}/uz/services/exchange-rates/"
_SOURCE = "trastbank.uz"
# S5857: `(\{.*?\});` dangasal (reluctant) `.` o'rniga `[^\n]` (no-DOTALL
# holatida `.` aynan shu) + `(?!};)` tempered klass — match to'liq bir xil:
# qiziqish `};` gacha bo'lgan eng qisqa iqtibos. Oddiy `[^}]*`/alohida klass
# mos kelmaydi, chunki JSON ichida uyasi (`{...}`) bor.
_RATES_VAR_RE = re.compile(r"var\s+arCurrencyRates\s*=\s*(\{(?:(?!};)[^\n])*\});")

DEPOSIT_CARDS = CardLayout(
    source=_SOURCE,
    card=".deposit__item",
    title=".deposit__item_title",
    fields=SelectedFields(
        container=".deposit__item_info li",
        label="span",
        value="strong",
        strip_colon=True,
    ),
    link=".deposit__item_button a",
)

CREDIT_CARDS = CardLayout(
    source=_SOURCE,
    card=".item.has-preview-picture",
    title="h3.title a",
    fields=SelectedFields(
        container=".item-prop",
        label=".item-prop-title",
        value=".item-prop-value",
        strip_colon=True,
    ),
)


def parse_deposit_cards(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, DEPOSIT_CARDS, base_url)


def parse_credit_cards(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, CREDIT_CARDS, base_url)


class TrastbankConnector(CardListConnector):
    bank_code = "TRAST"
    segment = "individual"

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url
        self.layout = DEPOSIT_CARDS if product_type == "deposit" else CREDIT_CARDS


def parse_exchange_rates(html: str, url: str = _EXCHANGE_URL) -> list[dict]:
    match = _RATES_VAR_RE.search(html)
    if not match:
        return []

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    records = []
    for side, key in ((BUY, "BUY"), (SELL, "SALE")):
        for code, rate in (data.get(key) or {}).items():
            if code == "UZS":
                continue
            records.append({"code": code, "side": side, "rate": float(rate), "source": _SOURCE, "url": url})

    return records


class TrastbankExchangeConnector(HtmlPageConnector):
    bank_code = "TRAST"
    product_type = "currency"
    segment = "individual"
    url = _EXCHANGE_URL

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_exchange_rates(html, self.url)
