"""tayanchbank.uz (Tayanch mikromoliya banki) — jismoniy shaxslar uchun
omonat/kredit. Next.js sahifasi barqaror CSS klasslardan foydalanmaydi
(faqat Tailwind utility klasslar), shu bois kartalar strukturaviy
tarzda — har bir "Batafsil" havolasidan (``/uz/private/<turi>/...``)
yuqoriga ko'tarilib, eng yaqin ``<h3>``li ota elementi karta sifatida
olinadi — topilgan statistikalar esa ``<span>label</span><div>qiymat
qismlari</div>`` juftliklari (``span + div`` CSS qo'shni tanlagichi).

Diqqat: kredit ro'yxat sahifasida jismoniy shaxslarga mo'ljallangan
bo'lsa-da, ba'zan yuridik shaxslar mahsuloti ham reklama qilinadi — bu
havolasi ``/uz/private/...`` bilan boshlanmagani uchun avtomatik
chiqarib tashlanadi."""

from bs4 import BeautifulSoup

from app.connectors.base import HtmlPageConnector
from app.connectors.html_cards import dedupe_records

_BASE_URL = "https://tayanchbank.uz"
_SOURCE = "tayanchbank.uz"


def parse_products(html: str, url_prefix: str, base_url: str = _BASE_URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    records = []

    for link in soup.select(f'a[href^="{url_prefix}"]'):
        href = link["href"].split("#")[0]

        card = _find_single_product_card(link)
        if not card:
            continue

        h3 = card.find("h3")
        name = h3.get_text(strip=True)
        if not name:
            continue

        record = {"name": name, "source": _SOURCE, "url": base_url + href}
        for value_div in card.select("span + div"):
            label_el = value_div.find_previous_sibling("span")
            if not label_el:
                continue
            label = label_el.get_text(strip=True)
            value = " ".join(s.get_text(strip=True) for s in value_div.find_all("span"))
            if label and value:
                record[label] = value

        records.append(record)

    return dedupe_records(records)


def _find_single_product_card(link):
    """`link`dan yuqoriga ko'tarilib, eng yaqin bitta ``<h3>``li ota
    elementini topadi — aks holda bir nechta mahsulot yoki pastdagi
    kalkulyator bo'limi bilan birga qo'shilib, statistikalar aralashib
    ketishi mumkin edi."""
    node = link
    for _ in range(8):
        node = node.parent
        if node is None:
            return None
        h3s = node.find_all("h3")
        if len(h3s) == 1:
            return node
        if len(h3s) > 1:
            return None
    return None


class TayanchBankConnector(HtmlPageConnector):
    bank_code = "TAYANCH"
    segment = "individual"

    def __init__(self, product_type: str):
        self.product_type = product_type
        section = "deposits" if product_type == "deposit" else "credits"
        self.url = f"{_BASE_URL}/uz/private/{section}"
        self._prefix = f"/uz/private/{section}/"

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_products(html, self._prefix, base_url)
