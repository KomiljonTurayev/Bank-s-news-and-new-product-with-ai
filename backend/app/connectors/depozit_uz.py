from bs4 import BeautifulSoup

from app.banks import resolve_bank_code
from app.connectors.base import HtmlPageConnector
from app.connectors.html_cards import dedupe_records


def _extract_fields(block) -> dict:
    fields = {}
    for content in block.find_all("div", class_="content", recursive=False):
        title = content.select_one(".title")
        value = content.select_one(".value")
        if title and value:
            fields[title.get_text(strip=True)] = " ".join(value.get_text(" ", strip=True).split())
    return fields


def _record_from_block(block, name_class: str, source: str) -> dict | None:
    bank_img = block.select_one(".image-box img")
    name_el = block.select_one(f".{name_class} a")
    if bank_img is None or name_el is None:
        return None

    bank_name = bank_img.get("alt", "").strip()
    product_name = name_el.get_text(strip=True).strip('"')
    if not bank_name or not product_name:
        return None

    fields = _extract_fields(block)
    if not fields:
        return None

    record = {
        "_bank_code": resolve_bank_code(bank_name),
        "bank_name": bank_name,
        "name": product_name,
        "source": source,
        **fields,
    }
    href = name_el.get("href", "").strip()
    if href and href != "#":
        record["url"] = href
    return record


def parse_content_rows(html: str, name_class: str, source: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    records = []

    for block in soup.select(".content-row.mainContent"):
        record = _record_from_block(block, name_class, source)
        if record:
            records.append(record)

    # depozit.uz sahifasida bir xil mahsulot bloki qayta chiqishi mumkin
    # (masalan mobil/desktop ikkilamchi razmetka) — dublikatlarni saqlamaymiz.
    return dedupe_records(records)


class DepozitUzConnector(HtmlPageConnector):
    """depozit.uz — robots.txt cheklamagan ochiq bank mahsulotlari agregatori.
    Bitta so'rovda bir nechta bankning real takliflarini beradi."""

    segment = "individual"
    bank_code = "AGGREGATED"  # har yozuv o'z bank kodini olib yuradi (run() da almashtiriladi)

    def __init__(self, product_type: str, url: str, name_class: str, category: str | None = None):
        self.product_type = product_type
        self.url = url
        self.name_class = name_class
        self.category = category

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        records = parse_content_rows(html, self.name_class, source="depozit.uz")
        if self.category:
            for record in records:
                record["category"] = self.category
        return records
