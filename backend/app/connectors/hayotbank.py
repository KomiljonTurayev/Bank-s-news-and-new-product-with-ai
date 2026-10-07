"""hayotbank.uz — jismoniy shaxslar uchun kredit. Angular SPA (JS render
talab qiladi, playwright_fetch orqali olinadi). Faqat kredit qo'llab-
quvvatlanadi: omonat yo'nalishi (``/main/individual/deposit``) hozircha
saytning o'zida ishlamaydi — to'g'ridan-to'g'ri ochilganda ham, nav
havolasi bosilganda ham bosh sahifaga qaytarib yuboradi (2026-08-26
sanasidagi bank e'loniga ko'ra, omonatni to'ldirish xizmati texnik
sabablarga ko'ra vaqtincha to'xtatilgan — ehtimol shu bilan bog'liq).

Kredit kartalari Angular ``routerlink`` atributi orqali navigatsiya
qiladi (haqiqiy ``<a href>`` emas), shu bois havola qo'lda
qurilgan/nisbiy manzil sifatida qo'shiladi."""

from app.connectors.base import CardListConnector, RenderedPageConnector
from app.connectors.html_cards import CardLayout, ChildPairFields, parse_card_list

_URL = "https://hayotbank.uz/main/individual/credit"
_SOURCE = "hayotbank.uz"

CREDIT_CARDS = CardLayout(
    source=_SOURCE,
    card=".hb-card.deposit-item",
    title=".deposit-item-title",
    fields=ChildPairFields(container=".info .d-grid", child_tags=("p", "p"), value_first=True),
    link="button[routerlink]",
    link_attr="routerlink",
)


def parse_credits(html: str, base_url: str = _URL) -> list[dict]:
    return parse_card_list(html, CREDIT_CARDS, base_url + "/")


class HayotBankConnector(RenderedPageConnector, CardListConnector):
    bank_code = "HAYOT"
    product_type = "credit"
    segment = "individual"
    url = _URL
    layout = CREDIT_CARDS

    @property
    def base_url(self) -> str:
        return self.url + "/"
