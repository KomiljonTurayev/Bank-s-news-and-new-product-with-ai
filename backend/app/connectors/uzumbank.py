"""uzumbank.uz (Uzum Bank) — jismoniy shaxslar uchun omonat. robots.txt
``/loans`` va ``/cards``'ni taqiqlaydi, shu bois faqat omonat sahifasi
qamrab olinadi. Bu sahifa boshqa banklardagi kabi bir nechta mahsulot
kartasi emas — bitta omonatning reklama-landing sahifasi (Astro bilan
qurilgan), stavka/summa/muddat esa alohida ``data-*`` atributlarda emas,
erkin matn jumlalarida keladi, shu bois ular regex orqali olinadi."""

import re

from bs4 import BeautifulSoup

from app.connectors.base import HtmlPageConnector
from app.connectors.http import HTTP

_URL = "https://uzumbank.uz/uz/deposits/"

_RATE_RE = re.compile(r"foiz stavkasi\s*[—-]\s*([\d.,]+)\s*%", re.IGNORECASE)
_MIN_AMOUNT_RE = re.compile(r"minimal summa\w*\s*[—-]\s*(?:kamida\s*)?(\d+(?:\s\d+)*)\s*so", re.IGNORECASE)
_TERM_RE = re.compile(r"muddat\s*-\s*(\d+)\s*oy", re.IGNORECASE)
_BILAN = " bilan "


def parse_deposits(html: str, url: str = _URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    rate_match = _RATE_RE.search(text)
    if not rate_match:
        return []

    h1 = soup.find("h1")
    name = "Omonat"
    if h1 is not None:
        # Sarlavha bo'sh kelsa ham bu yagona omonat sahifasi — fallback
        # nomida qolamiz, sahifani butunlay tashlab yubormaymiz.
        title_text = h1.get_text(" ", strip=True)
        if title_text:
            name = title_text
    # Sarlavha "NN% yillik daromad bilan <nom>" ko'rinishida — stavka
    # allaqachon "Foiz stavkasi" maydonida bo'lgani uchun, kartada
    # takrorlanmasligi uchun "bilan"dan keyingi haqiqiy nomni ajratamiz.
    lowered = name.lower()
    if _BILAN in lowered:
        tail = name[lowered.index(_BILAN) + len(_BILAN):].strip()
        if tail:
            name = tail[0].upper() + tail[1:]

    record = {"name": name, "source": "uzumbank.uz", "url": url, "Foiz stavkasi": f"{rate_match.group(1)}%"}

    min_match = _MIN_AMOUNT_RE.search(text)
    if min_match:
        record["Minimal summa"] = f"{' '.join(min_match.group(1).split())} so'm"

    term_match = _TERM_RE.search(text)
    if term_match:
        record["Muddati"] = f"{term_match.group(1)} oy"

    return [record]


class UzumBankConnector(HtmlPageConnector):
    bank_code = "UZUM"
    product_type = "deposit"
    segment = "individual"

    def __init__(self, url: str = _URL):
        self.url = url

    def fetch_raw(self):
        # Server "Content-Type" sarlavhasida charset ko'rsatmaydi — requests
        # shu sabab ISO-8859-1'ga tushib, "—" kabi UTF-8 belgilarni buzib
        # qo'yadi (sahifa matnida em-dash stavka jumlasining ajralmas qismi).
        return HTTP.utf8_text(self.url)

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_deposits(html, self.url)
