"""ziraatbank.uz — jismoniy shaxslar uchun omonat/kredit. Shartlar
tahririyat (CMS) matni ichidagi oddiy HTML ``<table>``larda beriladi,
lekin ikki xil joylashuvda:

- Omonat sahifalarida (masalan ``/uz/milliy-valyutadagi-omonatlar``) bir
  nechta mahsulot bitta sahifada ``<h2>Mahsulot nomi</h2>`` sarlavhasi va
  undan keyingi jadval bilan ketma-ket keladi.
- Kredit sahifalarida har bir mahsulot o'z alohida sahifasida, bitta
  "kredit pasporti" jadvali bilan (qator hujayralari band raqami/label/
  qiymat — 3 ustunli); mahsulot nomi jadvaldagi "nomlanishi" so'zi bor
  qatorning qiymatidan olinadi (sahifa <h1>'i tarjima xatosi bilan
  chiqadi, ishonchli emas)."""

from bs4 import BeautifulSoup

from app.connectors.base import MultiPageConnector

_BASE_URL = "https://ziraatbank.uz"
_SOURCE = "ziraatbank.uz"


def _label_value_cells(row):
    """Qator ham 2 ustunli (label, qiymat), ham 3 ustunli (band raqami,
    label, qiymat — kredit pasporti jadvallari) bo'lishi mumkin."""
    cells = row.find_all("td")
    if len(cells) == 2:
        return cells[0], cells[1]
    if len(cells) == 3:
        return cells[1], cells[2]
    return None, None


def _table_pairs(table):
    # Yaroqsiz qatorlar (label yoki qiymat yo'q) shu yerda o'tkazib yuboriladi.
    for row in table.select("tr"):
        label_el, value_el = _label_value_cells(row)
        if not label_el or not value_el:
            continue
        label = label_el.get_text(strip=True)
        value = value_el.get_text(" ", strip=True)
        if label and value:
            yield label, value


def parse_deposit_page(html: str, url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one(".sub-page-content")
    if not container:
        return []

    records = []
    for h2 in container.select("h2"):
        name = h2.get_text(strip=True)
        table = h2.find_next("table")
        if not name or not table:
            continue

        record = {"name": name, "source": _SOURCE, "url": url}
        for label, value in _table_pairs(table):
            record[label] = value

        if len(record) > 3:
            records.append(record)

    return records


def parse_credit_page(html: str, url: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one(".sub-page-content")
    table = container.select_one("table") if container is not None else None
    if not table:
        return None

    record = {"source": _SOURCE, "url": url}
    name = None
    for label, value in _table_pairs(table):
        # Ba'zi sahifalarda "Kredit mahsulotining nomlanishi", boshqalarida
        # "Kredit mahsulotining nomi" deb yozilgan — ikkalasi ham shu
        # qismstringni o'z ichiga oladi.
        if "mahsulotining nom" in label.lower():
            name = value
        record[label] = value

    if not name or len(record) < 3:
        return None
    record["name"] = name
    return record


class ZiraatBankConnector(MultiPageConnector):
    bank_code = "ZIRAAT"
    segment = "individual"
    log_label = "Ziraatbank"

    def __init__(self, product_type: str, product_paths: list[str]):
        self.product_type = product_type
        self.urls = [f"{_BASE_URL}{path}" for path in product_paths]

    def parse_page(self, html: str, url: str) -> list[dict]:
        if self.product_type == "deposit":
            return parse_deposit_page(html, url)
        record = parse_credit_page(html, url)
        return [record] if record else []
