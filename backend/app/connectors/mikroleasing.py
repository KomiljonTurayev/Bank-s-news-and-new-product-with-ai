"""mikro-leasing.uz — "MK Leasing" (Mikro Leasing) — bank emas,
litsenziyalangan lizing kompaniyasi. Avval faqat depozit.uz'ning kredit
ro'yxatida tasodifan uchragani uchun "MIKROLEASING" kodi bilan bazaga
kirib qolgan edi (qarang app/banks.py izohi); endi o'z rasmiy saytidan
olinadi.

Ro'yxat sahifasi (/uz/loans/) bor, lekin unda faqat qisqa xulosa
ko'rsatiladi — to'liq shartlar har bir mahsulotning o'z sahifasida
(masalan /uz/loans/yengil-avtomobillar-lizingi.html). Sahifada mahsulot
nomini ko'rsatuvchi <h1> yo'q — nom ``<meta property="og:title">``dan
olinadi. Shartlar jadvali (“Foydalanish shartlari”) juft ``<div>``
qatorlardan iborat: ``.conditions-items .item.row`` ichida birinchi
``<div>`` — yorliq, ikkinchisi — qiymat.

DIQQAT: bu saytda banklardagidek "Foiz stavkasi" (APR) umuman e'lon
qilinmaydi — narxlash "Tranzaksiyani qayta ishlash uchun to'lov"
(taxminan 3-3,5%, moliyalashtirish miqdoriga emas, tranzaksiyaga
olinadi) orqali ifodalanadi — bu bank krediti foiz stavkasi bilan
solishtirib bo'lmaydigan butunlay boshqa ko'rsatkich. Shu bois "%"
belgisi bor maydonlar (Avans miqdori, Tranzaksiya to'lovi) ATAYLAB
record'ga qo'shilmaydi — aks holda extract_rate_percent()
(app/product_analysis.py) buni chin foiz stavkasi deb xato o'qib,
bozor solishtirmasi reytingini buzib qo'yar edi. Natijada bu yozuvlar
rate=None bilan chiqadi: haqiqiy shartlari (lizing predmeti,
moliyalashtirish miqdori, muddat) ko'rsatiladi, lekin foiz asosidagi
saralash/ballashda ishtirok etmaydi — bu aynan haqiqiy holatni
aks ettiradi, xato emas."""

from bs4 import BeautifulSoup

from app.connectors.base import MultiPageConnector
from app.connectors.html_cards import ChildPairFields

_BASE_URL = "https://mikro-leasing.uz"
_SOURCE = "mikro-leasing.uz"

_TERMS = ChildPairFields(container=".conditions-items .item.row", value_first=False, child_tags=("div", "div"))


def parse_product_page(html: str, url: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.select_one('meta[property="og:title"]')
    name = title_el.get("content", "").strip() if title_el is not None else None
    if not name:
        return None

    record = {"name": name, "source": _SOURCE, "url": url}
    for label, value in _TERMS.extract(soup):
        if "%" in value:
            continue
        record[label] = value

    return record if len(record) > 3 else None


class MikroLeasingConnector(MultiPageConnector):
    bank_code = "MIKROLEASING"
    product_type = "credit"
    segment = "individual"
    log_label = "Mikro Leasing"

    def __init__(self, product_paths: list[str]):
        self.urls = [f"{_BASE_URL}{path}" for path in product_paths]

    def parse_page(self, html: str, url: str) -> list[dict]:
        record = parse_product_page(html, url)
        return [record] if record else []
