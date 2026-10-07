from app.connectors.orient_finans import (
    OrientFinansCardConnector,
    OrientFinansConnector,
    OrientFinansExchangeConnector,
    parse_card_detail_page,
    parse_exchange_rates,
    parse_product_cards,
)

HTML = """
<div class="card card--product-catalog default">
  <div class="content">
    <h3 class="text-h2 font-medium">OFB Ishonch</h3>
    <div class="sm:gap-micro flex flex-col">
      <div class="text-base-200 text-md">Stavka</div>
      <div class="text-h3 font-light">18 <sup>%</sup></div>
    </div>
    <div class="sm:gap-micro flex flex-col">
      <div class="text-base-200 text-md">Muddat</div>
      <div class="text-h3 font-light">13 <sup>oy</sup></div>
    </div>
    <a href="/omonatlar/ofb-ishonch#form">Batafsil</a>
  </div>
</div>
"""


def test_parse_product_cards_combines_number_and_sup_unit():
    records = parse_product_cards(HTML)

    assert len(records) == 1
    assert records[0]["name"] == "OFB Ishonch"
    assert records[0]["Stavka"] == "18 %"
    assert records[0]["Muddat"] == "13 oy"
    assert records[0]["url"] == "https://ofb.uz/omonatlar/ofb-ishonch#form"


def test_connector_uses_individual_segment_and_orient_bank_code():
    connector = OrientFinansConnector("deposit", "https://ofb.uz/omonatlar")
    assert connector.segment == "individual"
    assert connector.bank_code == "ORIENT"


# Haqiqiy karta sahifasining soddalashtirilgan nusxasi — ro'yxat
# sahifasidagi (.card--product-catalog) razmetkadan butunlay farqli:
# <h1> nomi, shartlari esa div.gap-regular.flex.flex-col ichida
# p.text-h5 (yorliq) + div.text-h2 (qiymat) juftligida.
CARD_DETAIL_HTML = """
<html><body>
<h1>Uzcard <br/>Sherdor</h1>
<div class="gap-regular flex flex-col">
  <p class="text-h5 text-base-300 font-light">Xizmatlar uchun to'lov komissiyasi</p>
  <div class="text-h2">0%</div>
</div>
<div class="gap-regular flex flex-col">
  <p class="text-h5 text-base-300 font-light">Amal qilish muddati</p>
  <div class="text-h2">3 yil</div>
</div>
</body></html>
"""


def test_parse_card_detail_page_extracts_name_and_terms():
    record = parse_card_detail_page(CARD_DETAIL_HTML, "https://ofb.uz/kartalar/uzcard-sherdor")
    assert record == {
        "name": "Uzcard Sherdor",
        "source": "ofb.uz",
        "url": "https://ofb.uz/kartalar/uzcard-sherdor",
        "Xizmatlar uchun to'lov komissiyasi": "0%",
        "Amal qilish muddati": "3 yil",
    }


def test_parse_card_detail_page_returns_none_without_h1():
    assert parse_card_detail_page("<html><body>404</body></html>", "https://ofb.uz/kartalar/missing") is None


def test_card_connector_parse_skips_pages_with_no_product():
    connector = OrientFinansCardConnector([])
    records = connector.parse([
        ("https://ofb.uz/kartalar/uzcard-sherdor", CARD_DETAIL_HTML),
        ("https://ofb.uz/kartalar/missing", "<html><body>404</body></html>"),
    ])
    assert len(records) == 1
    assert records[0]["name"] == "Uzcard Sherdor"


def test_card_connector_bank_code_and_product_type():
    connector = OrientFinansCardConnector(["https://ofb.uz/kartalar/uzcard-sherdor"])
    assert connector.bank_code == "ORIENT"
    assert connector.product_type == "card"
    assert connector.segment == "individual"
    assert connector.urls == ["https://ofb.uz/kartalar/uzcard-sherdor"]


def test_card_connector_fetch_raw_skips_a_failing_url_instead_of_aborting(monkeypatch):
    from playwright.sync_api import Error as PlaywrightError

    def fake_fetch_rendered_html(url):
        if url.endswith("/missing"):
            raise PlaywrightError("net::ERR_NAME_NOT_RESOLVED")
        return f"<html>{url}</html>"

    monkeypatch.setattr("app.connectors.playwright_fetch.fetch_rendered_html", fake_fetch_rendered_html)

    connector = OrientFinansCardConnector([
        "https://ofb.uz/kartalar/uzcard-sherdor",
        "https://ofb.uz/kartalar/missing",
        "https://ofb.uz/kartalar/moment",
    ])
    pages = connector.fetch_raw()

    assert [url for url, _html in pages] == [
        "https://ofb.uz/kartalar/uzcard-sherdor",
        "https://ofb.uz/kartalar/moment",
    ]


EXCHANGE_HTML = """
<table class="currency-table w-full border-collapse">
<tbody>
<tr>
  <td data-label="Currency"><img alt="USD flag"><p>$1 USD</p></td>
  <td data-label="Buy"><p>11760</p></td>
  <td data-label="Sell"><p>11860</p></td>
</tr>
</tbody>
</table>
"""


def test_parse_exchange_rates_extracts_code_from_flag_alt():
    records = parse_exchange_rates(EXCHANGE_HTML, url="https://ofb.uz/kursy-valyut")
    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11760.0, "source": "ofb.uz", "url": "https://ofb.uz/kursy-valyut"},
        {"code": "USD", "side": "Sotish", "rate": 11860.0, "source": "ofb.uz", "url": "https://ofb.uz/kursy-valyut"},
    ]


def test_parse_exchange_rates_returns_empty_without_a_table():
    assert parse_exchange_rates("<html><body>no table</body></html>") == []


def test_exchange_connector_uses_currency_product_type():
    connector = OrientFinansExchangeConnector()
    assert connector.bank_code == "ORIENT"
    assert connector.product_type == "currency"
    assert connector.url == "https://ofb.uz/kursy-valyut"
