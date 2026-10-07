"""saderatbank.uz (Bank Saderat Tashkent, koddagi "SODEROT") — jismoniy
shaxslar uchun kredit. Har bir mahsulot o'z alohida (page-builder bilan
qo'lda tuzilgan) sahifasida, umumiy ko'rsatkichlar ``.lpc-autocredit__item``
kartalarida (qiymat + yorliq juftligi) beriladi.

Omonat yo'nalishi ataylab ulanmagan — saytdagi yagona omonat sahifasi
milliy va xorijiy valyuta uchun ham "Yillik foizi: 0%" deb ko'rsatadi,
ya'ni bank aholidan real depozit qabul qilmaydi (Eron bankining Toshkent
filiali sifatida asosan tijorat/savdo moliyalashuvi bilan shug'ullanadi).

Overdraft mahsuloti boshqa (oddiy matn ro'yxati) shablonda joylashgan
bo'lib, bu yerda hali qamrab olinmagan."""

from app.connectors.base import MultiPageConnector
from app.connectors.html_cards import SelectedFields, parse_single_product

_BASE_URL = "https://saderatbank.uz"
_SOURCE = "saderatbank.uz"

_STATS = SelectedFields(
    container=".lpc-autocredit__item",
    label=".lpc-autocredit__item-text",
    value=".lpc-autocredit__item-subtitle",
)


def _strip_slogan(name: str) -> str:
    # Ba'zi sahifalarda h1 "—"dan keyin reklama shiori bilan davom etadi
    # ("Avtokredit — oson va oddiy!") — faqat nomi kerak.
    return name.split("—")[0].strip()


def parse_credit_page(html: str, url: str) -> dict | None:
    return parse_single_product(html, _SOURCE, url, _STATS, clean_name=_strip_slogan)


class SaderatBankConnector(MultiPageConnector):
    bank_code = "SODEROT"
    product_type = "credit"
    segment = "individual"
    log_label = "Saderatbank"

    def __init__(self, product_paths: list[str]):
        self.urls = [f"{_BASE_URL}/{path}" for path in product_paths]

    def parse_page(self, html: str, url: str) -> list[dict]:
        record = parse_credit_page(html, url)
        return [record] if record else []
