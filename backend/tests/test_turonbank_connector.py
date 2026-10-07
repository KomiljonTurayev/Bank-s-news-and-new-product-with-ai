import requests

from app.connectors.turonbank import (
    TuronbankCardConnector,
    TuronbankConnector,
    parse_card_tariff_page,
    parse_item_cards,
)

HTML = """
<div class="item">
  <div class="item__content">
    <h3 class="item__title"><a href="/uz/private/deposit/maksimum-onlayn-omonati/">Maksimum</a></h3>
    <div class="item__features">
      <div class="item__info"><div class="item__value">18%</div><div class="item__label">Yillik stavka</div></div>
      <div class="item__info"><div class="item__data">18 oy</div><div class="item__label">Omonat muddati</div></div>
    </div>
  </div>
</div>
"""


def test_parse_item_cards_handles_both_value_and_data_classes():
    records = parse_item_cards(HTML)

    assert len(records) == 1
    assert records[0] == {
        "name": "Maksimum",
        "source": "turonbank.uz",
        "Yillik stavka": "18%",
        "Omonat muddati": "18 oy",
        "url": "https://turonbank.uz/uz/private/deposit/maksimum-onlayn-omonati/",
    }


def test_connector_uses_individual_segment_and_turon_bank_code():
    connector = TuronbankConnector("deposit", "https://turonbank.uz/uz/private/deposit/")
    assert connector.segment == "individual"
    assert connector.bank_code == "TURON"


# Kartalar sahifasida ro'yxat yo'q — har biri o'z alohida sahifasida,
# tariflar esa toza label:value emas, balki "Tariflar" sarlavhali
# bloqdagi <br> bilan ajratilgan, "-"/"–" bilan bo'lingan qatorlar.
CARD_TARIFF_HTML = """
<h1 class="heading__title">Visa Classic</h1>
<div class="requirements__item">
  <div class="requirements__top"><div class="requirements__title">Shartlar</div></div>
  <div class="requirements__list">Pasport talab qilinadi.</div>
</div>
<div class="requirements__item">
  <div class="requirements__top"><div class="requirements__title">Tariflar</div></div>
  <div class="requirements__list requirements__list--check">
    <p>
      Visa Classic kartasini ochish - 50 000 so'm;<br>
      Karta qoldig'ining eng kam miqdori - 10 usd;<br>
      SMS banking xizmati – bepul
    </p>
  </div>
</div>
"""

CARD_TARIFF_HTML_NO_TARIFF_SECTION = '<h1 class="heading__title">Bo\'sh</h1>'


def test_parse_card_tariff_page_reads_only_the_tariflar_block():
    record = parse_card_tariff_page(CARD_TARIFF_HTML, "https://turonbank.uz/uz/private/plastic-cards/list/visa-classic/")

    assert record == {
        "name": "Visa Classic",
        "source": "turonbank.uz",
        "url": "https://turonbank.uz/uz/private/plastic-cards/list/visa-classic/",
        "Visa Classic kartasini ochish": "50 000 so'm",
        "Karta qoldig'ining eng kam miqdori": "10 usd",
        "SMS banking xizmati": "bepul",
    }


def test_parse_card_tariff_page_returns_none_without_tariflar_section():
    assert parse_card_tariff_page(CARD_TARIFF_HTML_NO_TARIFF_SECTION, "https://turonbank.uz/uz/missing") is None


def test_card_connector_builds_full_urls_and_uses_turon_bank_code():
    connector = TuronbankCardConnector(["/uz/private/plastic-cards/list/visa-classic/", "/uz/private/plastic-cards/list/humo-/"])
    assert connector.urls == [
        "https://turonbank.uz/uz/private/plastic-cards/list/visa-classic/",
        "https://turonbank.uz/uz/private/plastic-cards/list/humo-/",
    ]
    assert connector.bank_code == "TURON"
    assert connector.product_type == "card"
    assert connector.segment == "individual"


class _FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


def test_card_connector_fetch_raw_skips_a_failing_url(monkeypatch):
    connector = TuronbankCardConnector(["/uz/private/plastic-cards/list/visa-classic/", "/uz/private/plastic-cards/list/missing/"])

    def fake_get(url, headers=None, timeout=None, params=None):
        if url.endswith("/missing/"):
            raise requests.exceptions.HTTPError("404 Client Error")
        return _FakeResponse(CARD_TARIFF_HTML)

    monkeypatch.setattr(requests, "get", fake_get)

    pages = connector.fetch_raw()

    assert [url for url, _html in pages] == ["https://turonbank.uz/uz/private/plastic-cards/list/visa-classic/"]
