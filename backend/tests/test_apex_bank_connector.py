from app.connectors.apex_bank import (
    ApexBankConnector,
    ApexBankExchangeConnector,
    parse_debet_cards,
    parse_exchange_rates,
)

HTML = """
<div class="debet-card-block filtered-card-block all sum">
  <a href="customer/impulse/">
    <div class="card-content">
      <div class="position-relative p-4">
        <div class="heading text-uppercase">IMPULSE</div>
        <div class="d-flex stats-block">
          <div class="col-auto">
            <div class="p5 mb-1"> Muddati</div>
            <div><span class="heading">24 oy</span></div>
          </div>
          <div class="col-auto">
            <div class="p5 mb-1"> Yillik Stavka</div>
            <div class="heading">19%</div>
          </div>
        </div>
      </div>
    </div>
  </a>
</div>
"""


def test_parse_debet_cards_picks_first_heading_as_title():
    records = parse_debet_cards(HTML)

    assert len(records) == 1
    assert records[0] == {
        "name": "IMPULSE",
        "source": "apexbank.uz",
        "Muddati": "24 oy",
        "Yillik Stavka": "19%",
        "url": "https://www.apexbank.uz/customer/impulse/",
    }


def test_connector_uses_individual_segment_and_apex_bank_code():
    connector = ApexBankConnector("deposit", "https://www.apexbank.uz/customer/deposit/")
    assert connector.segment == "individual"
    assert connector.bank_code == "APEX"


# Har qatorda kod/qiymatdan tashqari o'zgarish foizini ko'rsatuvchi
# klassli <span> ham bor ("rate-down"/"rate-up") — shular emas, birinchi
# (klasssiz) <span> haqiqiy stavka. "tr-fold" qatori (grafik) o'tkazib
# yuborilishi kerak.
EXCHANGE_HTML = """
<div class="currency-card p3">
  <table>
    <tr class="tr-border">
      <th><span class="d-none d-md-block">Kurs yangilandi 10.09.2026</span></th>
      <th>Xarid</th>
      <th>Sotuv</th>
      <th class="actions" width="30px"></th>
    </tr>
    <tr class="tr-border">
      <td><div class="d-flex flex-row align-items-baseline">
        <span>USD</span><span class="p4 d-none d-md-block ml-2">AQSH dollari</span>
      </div></td>
      <td><span>11 760,00</span><span class="p4 p5-md rate-down">- 0,00</span></td>
      <td><div class="d-flex justify-content-end">
        <span>11 830,00</span><span class="ml-3 p4 rate-down">- 0,00</span>
      </div></td>
    </tr>
    <tr class="tr-fold">
      <td colspan="4"><div class="charts-block-wrapper" data-currency="usd">chart</div></td>
    </tr>
  </table>
</div>
"""


def test_parse_exchange_rates_reads_first_bare_span_per_cell():
    records = parse_exchange_rates(EXCHANGE_HTML, url="https://www.apexbank.uz/about/exchange-rates/")
    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11760.0, "source": "apexbank.uz", "url": "https://www.apexbank.uz/about/exchange-rates/"},
        {"code": "USD", "side": "Sotish", "rate": 11830.0, "source": "apexbank.uz", "url": "https://www.apexbank.uz/about/exchange-rates/"},
    ]


def test_parse_exchange_rates_returns_empty_without_a_table():
    assert parse_exchange_rates("<html><body>no table</body></html>") == []


def test_exchange_connector_uses_currency_product_type():
    connector = ApexBankExchangeConnector()
    assert connector.bank_code == "APEX"
    assert connector.product_type == "currency"
    assert connector.url == "https://www.apexbank.uz/about/exchange-rates/"
