"""SQB (Sanoat-qurilish banki) rasmiy sayti — jismoniy shaxslar uchun
omonat/kredit/karta mahsulotlari. Uchalasi ham bir xil ".checkoutEasy"
razmetkasidan foydalanadi, lekin har biri ichki maydonlarni butunlay
boshqa tuzilishda beradi, shu bois uchta joylashuv qoidasi ustuvorlik
tartibida sinaladi (`FirstMatchFields`):

- Kreditlar: ``.credit__info__item`` ichida label/qiymat alohida elementda.
- Omonatlar: ``.blured__block`` ichida xuddi shunday, lekin teskari
  klass nomlari bilan (``Deposits_rate``=yorliq, ``Deposits_percentage``=qiymat).
- Kartalar: tafsilotlar strukturaviy label/value juftlik emas, balki
  ``.checkoutEasy__text p`` ichida "Label matni: <b>Qiymat</b><br/>"
  ketma-ketligi sifatida beriladi (label — oddiy matn tugun, undan
  keyingi ``<b>`` — qiymat, ``<br/>`` esa keyingi juftlikka o'tish
  belgisi) — shu bois alohida `_FreeTextBoldFields` qoidasi yozilgan."""

from collections.abc import Iterator

from bs4 import NavigableString, Tag

from app.connectors.base import CardListConnector, JsonApiConnector
from app.connectors.exchange import rate_pair
from app.connectors.html_cards import CardLayout, FieldRule, FirstMatchFields, SelectedFields, parse_card_list

_BASE_URL = "https://sqb.uz"
_EXCHANGE_API_URL = "https://sqb.uz/api/site-kurs-api/"
_EXCHANGE_URL = "https://sqb.uz/uz/individuals/exchange-money/"
_SOURCE = "sqb.uz"


class _FreeTextBoldFields(FieldRule):
    """Kartalar sahifasida tafsilotlar ".checkoutEasy__text p" ichida
    ozod matn sifatida keladi: "Label matni: <b>Qiymat</b><br/>" —
    label oddiy matn tugun, undan keyingi <b> uning qiymati."""

    def _pairs(self, card: Tag) -> Iterator[tuple[str, str]]:
        detail_p = card.select_one(".checkoutEasy__text p")
        if not detail_p:
            return
        pending_label = None
        for node in detail_p.children:
            if isinstance(node, NavigableString):
                text = node.strip().rstrip(":").strip()
                if text:
                    pending_label = text
            elif isinstance(node, Tag) and node.name == "b" and pending_label:
                value = node.get_text(strip=True)
                if value:
                    yield pending_label, value
                pending_label = None


CHECKOUT_CARDS = CardLayout(
    source=_SOURCE,
    card=".checkoutEasy",
    title=".checkoutEasy__title",
    fields=FirstMatchFields(rules=(
        SelectedFields(container=".credit__info__item", label=".credit-values-name", value=".credit-values"),
        SelectedFields(container=".blured__block", label=".Deposits_rate", value=".Deposits_percentage"),
        _FreeTextBoldFields(),
    )),
    link=(".buttonLined a", ".checkoutEasy__btn a", ".checkoutEasy__title a"),
)


def parse_checkout_cards(html: str, base_url: str = _BASE_URL) -> list[dict]:
    """sqb.uz'ning ".checkoutEasy" blokini (omonat va kredit sahifalarida
    bir xil klass ishlatiladi, faqat ichki maydon nomlari farq qiladi)
    normalizatsiya qilingan dict'lar ro'yxatiga aylantiradi. "SQB Mobile
    orqali ochish" kabi sarlavhasiz qo'llanma kartalari `CardLayout`
    darajasida (sarlavha topilmasa karta o'tkazib yuboriladi) chetlab
    o'tiladi."""
    return parse_card_list(html, CHECKOUT_CARDS, base_url)


class SQBConnector(CardListConnector):
    """SQB rasmiy sayti — jismoniy shaxslar uchun omonat/kredit/karta."""

    bank_code = "SQB"
    segment = "individual"
    layout = CHECKOUT_CARDS

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url


def parse_exchange_rates(payload: dict, url: str = _EXCHANGE_URL) -> list[dict]:
    """sqb.uz'ning valyuta sahifasi client-tomonda "site-kurs-api"dan
    to'ldiriladi (statik HTML'da faqat eski, ishlamaydigan bo'sh jadval
    qoladi). API'da bir nechta kanal bor ("offline"/"online"/"atm"/
    "juridic") — faqat "offline" (filial/shaxobcha) olinadi, boshqa bank
    connectorlaridagi "asosiy filial kanali" konvensiyasiga mos. Qiymatlar
    tiyinda keladi (so'mga aylantirish uchun 100'ga bo'linadi)."""
    records = []
    for item in (payload.get("data") or {}).get("offline", []):
        buy, sell = item.get("buy"), item.get("sell")
        buy_rate = buy / 100 if buy else None
        sell_rate = sell / 100 if sell else None
        records.extend(rate_pair(item.get("code"), buy_rate, sell_rate, source=_SOURCE, url=url))

    return records


class SQBExchangeConnector(JsonApiConnector):
    bank_code = "SQB"
    product_type = "currency"
    segment = "individual"
    url = _EXCHANGE_URL
    api_url = _EXCHANGE_API_URL

    def parse_payload(self, payload: dict, url: str) -> list[dict]:
        return parse_exchange_rates(payload, url)
