"""anorbank.uz — jismoniy shaxslar uchun omonat/kredit/karta va valyuta
kursi. Statik HTML, lekin depozit_uz.py'dagi kabi toza label:value
juftlari o'rniga har mahsulot ozod matnli belgilar ro'yxatiga ega
(masalan "Muddati - 24 oy", "Yillik 20%") — shu bois oddiy heuristika
bilan tasniflanadi. Kartalar sahifasi (``/uz/cards/``) ham xuddi shu
".cards__item" razmetkasidan foydalanadi, shu bois parse_cards
omonat/kredit/karta uchalasiga ham baravar ishlaydi.

Valyuta kursi sahifasida (``/uz/about/exchange-rates/``) uchta bo'lim
bor — "shoxobchalarida" (filial), "Bankomatlar uchun" va "mobil
ilovada" — bir xil ``h1`` sarlavhalar bilan ajratilgan va bir xil
``.currency--card`` razmetkasi qayta ishlatiladi, shu bois faqat
birinchi (filial) bo'lim olinadi. Sahifada ba'zi kartalar shablon
qoldig'i sifatida HTML izohi (``<!-- -->``) ichida "o'chirib qo'yilgan"
holda qoladi (bo'sh qiymatlar bilan) — BeautifulSoup bunday izohlarni
elementga aylantirmagani uchun ular avtomatik chiqarib tashlanadi. USD
esa shahar bo'yicha tanlov (``<select>``) ko'rinishida keladi —
birinchi "umumiy" variant (``data-buy``/``data-sell``) olinadi."""

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.connectors.base import HtmlPageConnector
from app.connectors.exchange import parse_amount, rate_pair

_BASE_URL = "https://anorbank.uz"
_EXCHANGE_URL = f"{_BASE_URL}/uz/about/exchange-rates/"
_SOURCE = "anorbank.uz"


def _apply_bullet_conditions(record: dict, bullets: list) -> None:
    # Bullet matnlarini tasniflash: "%" saqlagan matn stavka, "muddati"
    # bilan boshlangani muddat, qolgani umumiy xususiyat sifatida yig'iladi.
    extras = []
    for p in bullets:
        text = p.get_text(strip=True)
        if not text:
            continue
        if "%" in text:
            record["Foiz stavkasi"] = text
        elif text.lower().startswith("muddati"):
            record["Muddati"] = text
        else:
            extras.append(text)
    if extras:
        record["Xususiyatlari"] = "; ".join(extras)


def _record_from_card(card, base_url: str) -> dict | None:
    title_el = card.select_one("h3")
    bullets = card.select("ul li p")
    if title_el is None or not bullets:
        # Bullet ro'yxati bo'sh kartalar "Limitni bilib oling" kabi
        # tashviqot bloklari — haqiqiy mahsulot emas.
        return None
    name = title_el.get_text(strip=True)
    if not name:
        return None

    record = {"name": name, "source": _SOURCE}
    _apply_bullet_conditions(record, bullets)

    link = card.select_one(".cards__btns a")
    if link is not None and link.get("href"):
        record["url"] = urljoin(base_url, link["href"])
    return record


def parse_cards(html: str, base_url: str = _BASE_URL) -> list[dict]:
    """".cards__item" kartalarini o'qiydi — shartlar toza label:value emas,
    balki ozod matnli belgilar ro'yxati (masalan "Muddati - 24 oy",
    "Yillik 20%"), shu bois oddiy heuristika bilan tasniflanadi: "%"
    saqlagan matn stavka, "muddati" bilan boshlangani muddat, qolgani
    umumiy xususiyat sifatida yig'iladi."""
    soup = BeautifulSoup(html, "html.parser")
    records = []
    seen = set()

    for card in soup.select(".cards__item"):
        record = _record_from_card(card, base_url)
        if record is None:
            continue

        # Sahifada "Barcha" va valyuta bo'yicha filtr tab'lari bir xil
        # kartani qayta chiqarishi mumkin — dublikatlarni saqlamaymiz.
        fingerprint = tuple(sorted(record.items()))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        records.append(record)

    return records


class AnorbankConnector(HtmlPageConnector):
    bank_code = "ANOR"
    segment = "individual"

    def __init__(self, product_type: str, url: str):
        self.product_type = product_type
        self.url = url

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_cards(html, base_url)


def _card_currency_code(el) -> str | None:
    # Nomdan kod olinadi ("Shveytsariya franki, CHF" -> "CHF") —
    # bayroqcha rasmining "alt" matni saytning o'zida ba'zi
    # valyutalar (masalan CHF, KZT) uchun xato ravishda "USD" deb
    # yozilgan, shu bois faqat "curr__name" yo'q holatda (USD'ning
    # shahar-tanlov kartasi) alt'ga tayaniladi.
    name_el = el.select_one(".curr__name")
    if name_el and "," in name_el.get_text():
        return name_el.get_text().rsplit(",", 1)[-1].strip()
    img = el.select_one(".curr__flag img[alt]")
    return img.get("alt") if img else None


def _card_rates(el) -> tuple:
    option = el.select_one("select option")
    if option:
        return parse_amount(option.get("data-buy")), parse_amount(option.get("data-sell"))
    buy_el = el.select_one(".currency--card__purchase .currency__card__value")
    sell_el = el.select_one(".currency--card__sale .currency__card__value")
    return (
        parse_amount(buy_el.get_text() if buy_el else None),
        parse_amount(sell_el.get_text() if sell_el else None),
    )


def parse_exchange_rates(html: str, url: str = _EXCHANGE_URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    branch_h1 = next(
        (h1 for h1 in soup.find_all("h1") if "ayriboshlash shoxobchalarida" in h1.get_text()), None
    )
    if not branch_h1:
        return []

    records = []
    for el in branch_h1.find_all_next():
        if el.name == "h1":
            break
        if el.name != "div" or el.get("class") != ["currency--card"]:
            continue

        code = _card_currency_code(el)
        if not code:
            continue
        buy_rate, sell_rate = _card_rates(el)
        records.extend(rate_pair(code, buy_rate, sell_rate, source=_SOURCE, url=url))

    return records


class AnorbankExchangeConnector(HtmlPageConnector):
    bank_code = "ANOR"
    product_type = "currency"
    segment = "individual"
    url = _EXCHANGE_URL

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_exchange_rates(html, self.url)
