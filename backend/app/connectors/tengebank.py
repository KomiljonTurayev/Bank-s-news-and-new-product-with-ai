"""tengebank.uz — jismoniy shaxslar uchun omonat/kredit. Har bir
mahsulot turi/omonat sahifasida shartlar oddiy HTML ``<table>`` ichida
beriladi (``.content-inner-editer table``), lekin ikki xil shaklda:

- Bitta mahsulot uchun: ikki ustunli jadval (``label | qiymat``) — sahifa
  sarlavhasi (``<h1>``) mahsulot nomi bo'ladi.
- Bir nechta mahsulotni solishtirish uchun (masalan so'mdagi ikkita
  omonat turi bir sahifada): birinchi qator har bir ustun uchun mahsulot
  nomini beradi, keyingi qatorlar esa ``label | qiymat1 | qiymat2 | ...``
  ko'rinishida — har bir ustun alohida yozuvga aylantiriladi.

Bank ro'yxat sahifalari (``/deposits``, ``/credits``) faqat kategoriya
kartalarini ko'rsatadi, haqiqiy shartlar yo'q — shu bois bu yerda ham
(Garantbank/Octobank kabi) mahsulot sahifalari ro'yxati oldindan
beriladi."""

from bs4 import BeautifulSoup

from app.connectors.base import MultiPageConnector

_BASE_URL = "https://tengebank.uz"
_SOURCE = "tengebank.uz"


def _comparison_records(header_cells: list, url: str) -> list[dict]:
    # Solishtirish jadvali — birinchi katak bo'sh, qolganlari mahsulot nomlari.
    names = [c.get_text(strip=True) for c in header_cells[1:]]
    return [{"name": name, "source": _SOURCE, "url": url} for name in names if name]


def _fill_comparison_row(records: list[dict], cells: list) -> None:
    label = cells[0].get_text(strip=True)
    if not label:
        return
    for i, record in enumerate(records):
        value_idx = i + 1
        if value_idx < len(cells):
            value = cells[value_idx].get_text(" ", strip=True)
            if value:
                record[label] = value


def _fill_single_record(record: dict, cells: list) -> None:
    label = cells[0].get_text(strip=True)
    value = cells[1].get_text(" ", strip=True)
    if label and value:
        record[label] = value


def _append_comparison_rows(records: list[dict], rows: list) -> None:
    for row in rows:
        cells = row.find_all("td", recursive=False)
        if len(cells) >= 2:
            _fill_comparison_row(records, cells)


def parse_table_page(html: str, url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one(".content-inner-editer table")
    h1 = soup.select_one("h1")
    if table is None or h1 is None:
        return []

    rows = table.select("tr")
    if not rows:
        return []

    header_cells = rows[0].find_all("td", recursive=False)

    if len(header_cells) > 2:
        records = _comparison_records(header_cells, url)
        _append_comparison_rows(records, rows[1:])
        return records

    name = h1.get_text(strip=True)
    if not name:
        return []
    record = {"name": name, "source": _SOURCE, "url": url}
    for row in rows:
        cells = row.find_all("td", recursive=False)
        if len(cells) == 2:
            _fill_single_record(record, cells)
    return [record] if len(record) > 3 else []


class TengeBankConnector(MultiPageConnector):
    bank_code = "TENGEBANK"
    segment = "individual"
    log_label = "Tengebank"

    def __init__(self, product_type: str, product_paths: list[str]):
        self.product_type = product_type
        self.urls = [f"{_BASE_URL}{path}" for path in product_paths]

    def parse_page(self, html: str, url: str) -> list[dict]:
        return parse_table_page(html, url)
