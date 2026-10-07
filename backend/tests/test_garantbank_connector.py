import requests

from app.connectors.garantbank import GarantbankConnector, parse_product_page

PRODUCT_PAGE_HTML = """
<h1>"Orzu sari" Omonati</h1>
<ul class="product-terms">
  <li class="product-term">
    <div class="product-term-content"><b>10 000 000 so'm</b><div><span>minimal miqdori</span></div></div>
  </li>
  <li class="product-term">
    <div class="product-term-content"><b>18%</b><div><span>foiz stavkasi</span></div></div>
  </li>
  <li class="product-term">
    <div class="product-term-content"><b>24 oy</b><div><span>saqlash muddati</span></div></div>
  </li>
</ul>
"""

EMPTY_PAGE_HTML = "<h1>404</h1>"


def test_parse_product_page_extracts_name_and_stats():
    record = parse_product_page(PRODUCT_PAGE_HTML, "https://garantbank.uz/uz/vklad-orzu-sari")
    assert record == {
        "name": '"Orzu sari" Omonati',
        "source": "garantbank.uz",
        "url": "https://garantbank.uz/uz/vklad-orzu-sari",
        "minimal miqdori": "10 000 000 so'm",
        "foiz stavkasi": "18%",
        "saqlash muddati": "24 oy",
    }


def test_parse_product_page_returns_none_when_no_stats_present():
    assert parse_product_page(EMPTY_PAGE_HTML, "https://garantbank.uz/uz/missing") is None


def test_connector_builds_full_urls_from_paths():
    connector = GarantbankConnector("deposit", ["/uz/vklad-orzu-sari", "/uz/bingo"])
    assert connector.urls == [
        "https://garantbank.uz/uz/vklad-orzu-sari",
        "https://garantbank.uz/uz/bingo",
    ]
    assert connector.bank_code == "GARANT"
    assert connector.segment == "individual"


def test_connector_parse_skips_pages_with_no_product():
    connector = GarantbankConnector("deposit", [])
    records = connector.parse([
        ("https://garantbank.uz/uz/vklad-orzu-sari", PRODUCT_PAGE_HTML),
        ("https://garantbank.uz/uz/missing", EMPTY_PAGE_HTML),
    ])
    assert len(records) == 1
    assert records[0]["name"] == '"Orzu sari" Omonati'


class _FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def test_fetch_raw_skips_a_failing_url_instead_of_aborting_the_whole_bank(monkeypatch):
    # Ro'yxat sahifasi yo'qligi sababli har mahsulot o'z alohida (hardcoded)
    # URL'idan olinadi — bitta sahifa 404/500 bersa, faqat o'sha sahifa
    # o'tkazib yuborilishi kerak, butun bank ma'lumoti emas.
    connector = GarantbankConnector("deposit", ["/uz/vklad-orzu-sari", "/uz/missing", "/uz/bingo"])

    def fake_get(url, headers=None, timeout=None, params=None):
        if url.endswith("/uz/missing"):
            raise requests.exceptions.HTTPError("404 Client Error")
        return _FakeResponse(f"<html>{url}</html>")

    monkeypatch.setattr(requests, "get", fake_get)

    pages = connector.fetch_raw()

    assert [url for url, _html in pages] == [
        "https://garantbank.uz/uz/vklad-orzu-sari",
        "https://garantbank.uz/uz/bingo",
    ]
