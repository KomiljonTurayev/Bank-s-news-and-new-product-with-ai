import pytest

from app.connectors import depozit_exchange
from app.connectors.depozit_exchange import DepozitExchangeConnector, parse_exchange_rates

EXCHANGE_HTML = """
<div class="table-holder">
  <div class="table-column">
    <div class="table-header"><span>Olish</span><span>Kurs</span></div>
    <div class="table-body">
      <div class="table-cell">
        <div><img alt="Agrobank" src="/logo.png"></div>
        <div class="currency-rate-value">12,900.00 <span>UZS</span></div>
      </div>
      <div class="table-cell">
        <div><img alt="Kapitalbank" src="/logo2.png"></div>
        <div class="currency-rate-value">12,880.00 <span>UZS</span></div>
      </div>
    </div>
  </div>
  <div class="table-column">
    <div class="table-header"><span>Sotish</span><span>Kurs</span></div>
    <div class="table-body">
      <div class="table-cell">
        <div><img alt="Agrobank" src="/logo.png"></div>
        <div class="currency-rate-value">12,970.00 <span>UZS</span></div>
      </div>
    </div>
  </div>
</div>
"""


def test_parse_exchange_rates_splits_buy_and_sell_sides():
    records = parse_exchange_rates(EXCHANGE_HTML, "USD")

    assert len(records) == 3
    assert records[0] == {
        "_bank_code": "AGRO",
        "bank_name": "Agrobank",
        "code": "USD",
        "side": "Olish",
        "rate": 12900.0,
        "source": "depozit.uz",
    }
    assert records[1]["_bank_code"] == "KDB"
    assert records[2]["side"] == "Sotish"
    assert records[2]["rate"] == 12970.0


def test_parse_exchange_rates_skips_cells_without_bank_or_value():
    html = '<div class="table-column"><div class="table-header"><span>Olish</span></div><div class="table-body"><div class="table-cell"></div></div></div>'
    assert parse_exchange_rates(html, "USD") == []


def test_connector_exposes_currency_product_type():
    connector = DepozitExchangeConnector()
    assert connector.product_type == "currency"
    assert connector.segment == "individual"


def test_one_dead_currency_does_not_lose_the_rest(monkeypatch):
    def fake_json(url, params=None):
        if params["currency_id"] == 3:  # RUB
            raise TimeoutError("depozit.uz javob bermayapti")
        return EXCHANGE_HTML

    monkeypatch.setattr(depozit_exchange._HTTP, "json", fake_json)

    raw = DepozitExchangeConnector().fetch_raw()

    assert len(raw) == len(depozit_exchange.CURRENCIES) - 1
    assert "RUB" not in [code for code, _ in raw]


def test_all_currencies_dead_marks_connector_as_failed(monkeypatch):
    def fake_json(url, params=None):
        raise TimeoutError("depozit.uz o'lik")

    monkeypatch.setattr(depozit_exchange._HTTP, "json", fake_json)

    connector = DepozitExchangeConnector()
    with pytest.raises(RuntimeError):
        connector.fetch_raw()
