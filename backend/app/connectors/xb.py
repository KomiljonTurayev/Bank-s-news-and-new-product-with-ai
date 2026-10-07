"""xb.uz (Xalq banki) — jismoniy shaxslar uchun omonat/kredit mahsulotlari.
Sayt Next.js'da qurilgan va ma'lumot client-tomonda render qilinadi, lekin
har bir sahifaning boshlang'ich server javobida ".__NEXT_DATA__" degan
<script> ichida to'liq JSON (barcha mahsulot bloklari bilan) keladi — shu
bois headless brauzer shart emas, oddiy `requests` yetarli."""

import json
import re

from app.connectors.base import HtmlPageConnector
from app.connectors.html_cards import dedupe_records

_NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
_PRODUCT_TEMPLATES = {"deposit-card-block", "list"}


def _parse_block(block: dict, base_url: str) -> dict | None:
    if block.get("template") not in _PRODUCT_TEMPLATES:
        return None
    name = (block.get("title") or "").strip()
    if not name:
        return None

    block_data = block.get("data") or {}
    labels = block_data.get("description", [])
    values = block_data.get("title", [])
    record = {"name": name, "source": "xb.uz"}
    for label, value in zip(labels, values):
        label = label.strip().rstrip(":").strip()
        value = value.strip()
        if label:
            record[label] = value

    urls = block_data.get("btn_url") or []
    if urls:
        record["url"] = base_url + urls[0]
    return record


def _extract_blocks(data: dict) -> list[dict]:
    queries = data.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries", [])
    if not queries:
        return []
    page = queries[0].get("state", {}).get("data") or {}
    return page.get("blocks") or []


def parse_blocks(html: str, base_url: str = "https://xb.uz") -> list[dict]:
    match = _NEXT_DATA_RE.search(html)
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    records = []
    for block in _extract_blocks(data):
        record = _parse_block(block, base_url)
        if record:
            records.append(record)

    # Bir xil blok sahifada qayta chiqishi mumkin (masalan valyuta
    # filtridan qat'i nazar to'liq ro'yxat qaytadi) — dublikatlarni
    # saqlamaymiz.
    return dedupe_records(records)


class XBConnector(HtmlPageConnector):
    """Xalq banki rasmiy sayti (xb.uz) — jismoniy shaxslar uchun omonat/kredit."""

    bank_code = "XB"
    segment = "individual"

    def __init__(self, product_type: str, url: str, category: str | None = None):
        self.product_type = product_type
        self.url = url
        self.category = category

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        records = parse_blocks(html, base_url)
        if self.category:
            for record in records:
                record["category"] = self.category
        return records
