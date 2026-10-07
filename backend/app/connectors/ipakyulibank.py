"""ipakyulibank.uz (Ipak Yo'li bank) — jismoniy shaxslar uchun
omonat/kredit va valyuta kursi. Statik HTML, Vue komponenti barqaror
``data-test`` atributlari bilan belgilangan — omonat va kredit
sahifalari bir xil "product-card" komponentidan foydalanadi.

Valyuta kursi sahifasi (``/physical/valyuta-ayirboshlash``) esa Nuxt 3
SPA bo'lib, raqamlar ``<script id="__NUXT_DATA__">`` ichidagi "devalue"
formatida keladi — bu oddiy JSON emas, balki takror strukturalarni
qisqartirish uchun butun sahifa bitta tekis massivga yoyiladi va har
bir qiymat (satr/bool/null bo'lmasa) shu massivdagi indeksga ishora
qiladi. Shu bois to'g'ridan-to'g'ri ``json.loads`` qilib bo'lmaydi —
avval indekslarni rekursiv "yechish" (resolve) kerak. Stavkalar 100
karra kattalashtirilgan holda saqlanadi (masalan 1176000 → 11760.00
so'm)."""

import json
import re
from collections.abc import Iterator

from bs4 import Tag

from app.connectors.base import CardListConnector, HtmlPageConnector
from app.connectors.exchange import rate_pair
from app.connectors.html_cards import CardLayout, FieldRule, parse_card_list

_BASE_URL = "https://ipakyulibank.uz"
_EXCHANGE_URL = f"{_BASE_URL}/physical/valyuta-ayirboshlash"
_SOURCE = "ipakyulibank.uz"
# S8786: eski `<script[^>]*id=...` qismi super-linear backtracking berardi
# (`[^>]*` literani "yutib", har bir pozitsiyada qayta urinadi). Yangi ko'rinish
# har belgini bir marta oladi; match boshlanishi, tugashi va group(1) eski bilan
# bir xil (fuzz-test bilan tekshirilgan).
_NUXT_DATA_RE = re.compile(
    r'<script(?:(?!id="__NUXT_DATA__")[^>])*id="__NUXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)

# Faqat "product-card-first-content" kabi bitta so'zli statistika bloklariga
# mos keladi — "product-card-title-and-content" kabi tashqi o'ram esa
# (o'zining ichida sarlavha <h2> ham, statistika qiymatlari ham bo'lgani
# uchun) chiqarib tashlanadi, aks holda mahsulot nomi ham noto'g'ri
# "label: value" juftligi sifatida qo'shilib qolar edi. Bu chegara oddiy
# CSS tanlagich bilan ifodalanmaydi (soupsieve ixtiyoriy regex qo'llab-
# quvvatlamaydi), shu bois alohida `FieldRule` sifatida yozilgan.
_STAT_WRAPPER_RE = re.compile(r"^product-card-\w+-content$")


class _RegexAttrFields(FieldRule):
    def _pairs(self, card: Tag) -> Iterator[tuple[str, str]]:
        for stat in card.find_all(attrs={"data-test": _STAT_WRAPPER_RE}):
            label_el = stat.select_one('[data-test$="-title"]')
            value_el = stat.select_one('[data-test$="-value"]')
            if label_el and value_el:
                yield _text(label_el), _text(value_el)


def _text(el: Tag) -> str:
    return " ".join(el.get_text(" ").split())


PRODUCT_CARDS = CardLayout(
    source=_SOURCE,
    card='[data-test="product-card-container"]',
    title='[data-test="product-card-title"]',
    fields=_RegexAttrFields(),
    link='[data-test="product-card-additional-link"] a[href]',
)


def parse_products(html: str, base_url: str = _BASE_URL) -> list[dict]:
    return parse_card_list(html, PRODUCT_CARDS, base_url)


class IpakYuliBankConnector(CardListConnector):
    bank_code = "IPAKYULI"
    segment = "individual"
    layout = PRODUCT_CARDS

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url


def _resolve_nuxt_ref(payload: list, index: int, memo: dict) -> object:
    """``payload[index]``dagi qiymatni to'liq "yechadi" — agar u dict/list
    bo'lsa, uning har bir int qiymati o'z navbatida shu massivdagi
    indeks hisoblanadi va rekursiv ravishda yechiladi."""
    if index in memo:
        return memo[index]
    value = payload[index]

    if isinstance(value, dict):
        resolved: dict = {}
        memo[index] = resolved
        for key, item in value.items():
            resolved[key] = _resolve_nuxt_ref(payload, item, memo) if isinstance(item, int) else item
        return resolved

    if isinstance(value, list):
        resolved_list: list = []
        memo[index] = resolved_list
        for item in value:
            resolved_list.append(_resolve_nuxt_ref(payload, item, memo) if isinstance(item, int) else item)
        return resolved_list

    return value


def _find_active_currency_tab(payload: list) -> dict | None:
    # "CurrencyTable" komponentining ma'lumot ob'ektini qidiramiz. Diqqat:
    # bu bosqichda dict qiymatlari hali "yechilmagan" — har biri o'zi
    # massivdagi indeks (masalan {"frontComponentName": 13, ...}), shu
    # bois moslikni kalitlar to'plami bo'yicha topamiz, keyin har bir
    # nomzodni "yechib" chiqib, haqiqiy nomi va faol-tab holatini
    # tekshiramiz (bir nechta tab bo'lishi mumkin — faqat faoli olinadi).
    _REQUIRED_KEYS = {"rates", "frontComponentName", "isActiveTab"}
    for i, item in enumerate(payload):
        if not isinstance(item, dict) or not _REQUIRED_KEYS.issubset(item.keys()):
            continue
        resolved = _resolve_nuxt_ref(payload, i, {})
        if resolved.get("frontComponentName") == "CurrencyTable" and resolved.get("isActiveTab"):
            return resolved
    return None


def _tab_rate_records(tab: dict, url: str) -> list[dict]:
    records = []
    for currency in tab.get("rates") or []:
        rate = currency.get("rate") or {}
        buy, sell = rate.get("buy"), rate.get("sell")
        buy_rate = buy / 100 if buy is not None else None
        sell_rate = sell / 100 if sell is not None else None
        records.extend(rate_pair(currency.get("code_name"), buy_rate, sell_rate, source=_SOURCE, url=url))
    return records


def parse_exchange_rates(html: str, url: str = _EXCHANGE_URL) -> list[dict]:
    match = _NUXT_DATA_RE.search(html)
    if not match:
        return []

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    tab = _find_active_currency_tab(payload)
    if tab is None:
        return []
    return _tab_rate_records(tab, url)


class IpakYuliExchangeConnector(HtmlPageConnector):
    bank_code = "IPAKYULI"
    product_type = "currency"
    segment = "individual"
    url = _EXCHANGE_URL

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_exchange_rates(html, self.url)
