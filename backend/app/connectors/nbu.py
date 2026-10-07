"""nbu.uz (Milliy bank) — jismoniy shaxslar uchun omonatlar. Statik HTML,
har bir mahsulot ``data-*`` atributlarida strukturaviy ma'lumot olib yuradi
(foiz, muddat, summa oralig'i, valyuta) — kalkulyator JS orqali ishlaydi,
lekin bu qiymatlar sahifa yuklanganda allaqachon HTML'da mavjud."""

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.connectors.base import HtmlPageConnector, MultiPageConnector
from app.connectors.html_cards import dedupe_records

_BASE_URL = "https://nbu.uz"

_CURRENCY_LABELS = {
    "sum": "So'm",
    "aqsh-dollari": "AQSH dollari",
    "evro": "Yevro",
}


_CURRENCY_UNITS = {
    "sum": "so'm",
    "aqsh-dollari": "USD",
    "evro": "EUR",
}


def _fmt_amount(raw: str, currency_key: str) -> str | None:
    raw = (raw or "").strip()
    if not raw or not raw.isdigit():
        return None
    unit = _CURRENCY_UNITS.get(currency_key, "so'm")
    return f"{int(raw):,}".replace(",", " ") + f" {unit}"


def _deposit_term_text(month_from: str, month: str) -> str:
    return f"{month_from}-{month} oy" if month_from and month_from != month else f"{month} oy"


def _deposit_record(card, base_url: str) -> dict | None:
    # Sarlavha + minimal yig'indi bilan belgilanadi: sahifada aynan shu
    # klassdagi bo'sh shablon element ham bor (uzulumidan chiqib turgan).
    title_el = card.select_one(".product_19_item-heading")
    if title_el is None:
        return None
    name = title_el.get_text(strip=True)
    if not name:
        return None

    record = {"name": name, "source": "nbu.uz"}

    currency_key = (card.get("data-contrubutecost") or "").strip()
    record["Valyuta"] = _CURRENCY_LABELS.get(currency_key, currency_key or "So'm")

    # Bo'sh va "0" qiymatlar tashlab yuboriladi — ular placeholder.
    rate = (card.get("data-proc") or "").strip()
    if rate and rate != "0":
        record["Foiz stavkasi"] = f"{rate}%"

    month_from = (card.get("data-month-from") or "").strip()
    month = (card.get("data-month") or "").strip()
    if month:
        record["Muddati"] = _deposit_term_text(month_from, month)

    min_amount = _fmt_amount(card.get("data-min"), currency_key)
    max_amount = _fmt_amount(card.get("data-max"), currency_key)
    if min_amount:
        record["Minimal summa"] = min_amount
    if max_amount:
        record["Maksimal summa"] = max_amount

    link = card.select_one(".actions a")
    if link is not None and link.get("href"):
        record["url"] = urljoin(base_url, link["href"].strip())

    return record


def parse_deposits(html: str, base_url: str = _BASE_URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    records = []
    seen = set()

    for card in soup.select(".product_19_item-wrapper"):
        record = _deposit_record(card, base_url)
        if record is None:
            continue
        fingerprint = tuple(sorted(record.items()))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        records.append(record)

    return records


class NBUConnector(HtmlPageConnector):
    bank_code = "NBU"
    product_type = "deposit"
    segment = "individual"

    def __init__(self, url: str = "https://nbu.uz/jismoniy-shaxslar-omonatlar"):
        self.url = url

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_deposits(html, base_url=_BASE_URL)


def _credit_stat_pairs(stats_list):
    for li in stats_list.select("li"):
        strong = li.select_one("strong")
        if not strong:
            continue
        label = strong.get_text(strip=True).rstrip(":").strip()
        # Li matnidan faqat strong qismigini emas, strong'dan keyingi qismini
        # olamiz (bu erda ":" strong ichida, matnning oxirida bo'lishi ham mumkin).
        value = li.get_text(" ", strip=True)[len(strong.get_text(strip=True)):].strip()
        # Ba'zi kartalarda ":" <strong> ichida ("Muddat: "), ba'zilarida
        # tashqarisida ("Muddat" : ) — ikkinchi holatda qoldiq ":" ni
        # qiymatdan tozalash kerak.
        value = value.lstrip(":").strip()
        if label and value:
            yield label, value


def _credit_href(card, base_url: str) -> str | None:
    link = card.select_one(".actions a[href]")
    if link is not None and link.get("href"):
        return urljoin(base_url, link["href"].strip())
    return None


def parse_credits(html: str, base_url: str = _BASE_URL) -> list[dict]:
    """Har bir kredit kategoriyasi sahifasida bir xil mahsulot to'plami
    bir necha marta (turli tab/filtrlarda) takrorlanadi — shu bois
    (nom, havola) juftligi bo'yicha dublikatlar olib tashlanadi. Faqat
    ro'yxatli shartlar (``<ul>``) bor kartalar haqiqiy kredit mahsuloti
    hisoblanadi — reklama banner-kartalarida bunday ro'yxat yo'q."""
    soup = BeautifulSoup(html, "html.parser")
    records = []
    seen = set()

    for card in soup.select(".feature_09_content"):
        title_el = card.select_one(".feature_09_heading")
        stats_list = card.select_one(".feature_09_paragraph ul")
        if title_el is None or stats_list is None:
            continue
        name = title_el.get_text(strip=True)
        if not name:
            continue

        href = _credit_href(card, base_url)

        # Kartalar ro'yxati sahifada takrorlanadi (filtrlandi/umumiy) — bir xil
        # sarlavha+havola bo'yicha dublikatlarni saqlamaymiz.
        fingerprint = (name, href)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)

        record = {"name": name, "source": "nbu.uz"}
        record.update(_credit_stat_pairs(stats_list))

        if href:
            record["url"] = href
        records.append(record)

    return records


class NBUCardConnector(HtmlPageConnector):
    """Jismoniy shaxslarga debet kartalar ro'yxati bitta sahifada, bir nechta
    tab ("free", "premium", "forthetraveler", "sum", "visa", "mastercard")
    ostida — xuddi kredit sahifalaridagi bilan bir xil ``.feature_09_content``
    shabloni, shu bois ``parse_credits`` qayta ishlatiladi. Har bir karta bir
    nechta tabda takrorlanishi mumkin — funksiya ichidagi (nom, havola)
    dedup shuni allaqachon hal qiladi."""

    bank_code = "NBU"
    product_type = "card"
    segment = "individual"

    def __init__(self, url: str = "https://nbu.uz/jismoniy-shaxslarga-debet-kartalar"):
        self.url = url

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_credits(html, base_url=_BASE_URL)


class NBUCreditConnector(MultiPageConnector):
    bank_code = "NBU"
    product_type = "credit"
    segment = "individual"
    log_label = "NBU kredit"

    def __init__(self, category_paths: list[str]):
        self.urls = [f"{_BASE_URL}/jismoniy-shaxslarga-kreditlar/{path}" for path in category_paths]

    def parse_page(self, html: str, url: str) -> list[dict]:
        return parse_credits(html, base_url=_BASE_URL)

    def parse(self, raw: list[tuple[str, str]]) -> list[dict]:
        # Har bir kategoriya sahifasi bir xil mahsulot to'plamini
        # ko'rsatishi mumkin (masalan umumiy "Mikroqarz" bir nechta
        # kategoriya ostida takrorlanadi) — sahifalar bo'ylab ham
        # (nom, havola) bo'yicha dublikat tashlanadi.
        return dedupe_records(super().parse(raw))
