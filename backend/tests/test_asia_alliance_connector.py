from app.connectors.asia_alliance import (
    AsiaAllianceConnector,
    AsiaAllianceExchangeConnector,
    parse_element_cards,
    parse_exchange_rates,
)

HTML = """
<div class="element" data-aos="fade-up">
  <div class="element__content">
    <h3 class="element__title"><a href="/uz/private/deposit/barqaror/">Barqaror</a></h3>
    <div class="element__params">
      <div class="element__param"><div class="element__param--value">15%</div><div class="element__param--label">Foiz stavkasi</div></div>
      <div class="element__param"><div class="element__param--value">24 oy</div><div class="element__param--label">Joylashtirish muddati</div></div>
    </div>
  </div>
</div>
"""


def test_parse_element_cards():
    records = parse_element_cards(HTML)

    assert len(records) == 1
    assert records[0] == {
        "name": "Barqaror",
        "source": "aab.uz",
        "Foiz stavkasi": "15%",
        "Joylashtirish muddati": "24 oy",
        "url": "https://aab.uz/uz/private/deposit/barqaror/",
    }


def test_connector_uses_individual_segment_and_asiaalliance_bank_code():
    connector = AsiaAllianceConnector("deposit", "https://aab.uz/uz/private/deposit/")
    assert connector.segment == "individual"
    assert connector.bank_code == "ASIAALLIANCE"


# Har bir kanal/valyuta juftligi ``data-tabs-target="tab-BANK-USD"``
# kabi bitta atributda keladi — faqat "BANK" (filial) prefiksli
# bloklar olinishi kerak, "ATM" kabi boshqa kanallar e'tiborsiz
# qoldiriladi.
EXCHANGE_HTML = """
<div data-tabs-target="tab-BANK-USD">
  <ul class="exchange-info__data">
    <li><div class="exchange-info__label">Sotib olish</div><div class="exchange-info__value">11760 uzs</div></li>
    <li><div class="exchange-info__label">Sotish</div><div class="exchange-info__value">11830 uzs</div></li>
    <li><div class="exchange-info__label">MB kursi</div><div class="exchange-info__value">11797.92 uzs</div></li>
  </ul>
</div>
<div data-tabs-target="tab-ATM-USD">
  <ul class="exchange-info__data">
    <li><div class="exchange-info__label">Sotib olish</div><div class="exchange-info__value">11700 uzs</div></li>
    <li><div class="exchange-info__label">Sotish</div><div class="exchange-info__value">11900 uzs</div></li>
  </ul>
</div>
"""


def test_parse_exchange_rates_reads_only_the_bank_channel():
    records = parse_exchange_rates(EXCHANGE_HTML, url="https://aab.uz/uz/private/currency-operations/")
    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11760.0, "source": "aab.uz", "url": "https://aab.uz/uz/private/currency-operations/"},
        {"code": "USD", "side": "Sotish", "rate": 11830.0, "source": "aab.uz", "url": "https://aab.uz/uz/private/currency-operations/"},
    ]


def test_parse_exchange_rates_returns_empty_without_bank_blocks():
    assert parse_exchange_rates("<html><body>no rates here</body></html>") == []


def test_exchange_connector_uses_currency_product_type():
    connector = AsiaAllianceExchangeConnector()
    assert connector.bank_code == "ASIAALLIANCE"
    assert connector.product_type == "currency"
    assert connector.url == "https://aab.uz/uz/private/currency-operations/"
