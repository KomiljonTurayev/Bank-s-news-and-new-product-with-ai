from app.connectors.davrbank import DavrbankConnector, DavrbankExchangeConnector, parse_exchange_rates, parse_products

PRODUCTS_HTML = """
<div class="bg-secondary relative flex w-full overflow-hidden rounded-4xl" id="individual-silver-2">
  <div class="flex w-full flex-col gap-6">
    <div class="flex flex-col gap-9">
      <div class="typography-header-bold w-full">Silver-2</div>
      <div class="flex w-full flex-row">
        <div class="flex w-full flex-col gap-2">
          <div class="typography-headline-semibold">25 oygacha</div>
          <div class="typography-callout text-secondary-foreground">Omonat muddati</div>
        </div>
        <div class="flex w-full flex-col gap-2">
          <div class="typography-headline-semibold">6.5 %</div>
          <div class="typography-callout text-secondary-foreground">Foiz stavkasi</div>
        </div>
      </div>
    </div>
    <a href="/uz/deposits/individual-silver-2">Batafsil</a>
  </div>
</div>
<div class="bg-secondary relative flex w-full overflow-hidden rounded-4xl" id="guarantee-card">
  <a href="/uz/deposits/guarantee?rt=individual">Batafsil</a>
</div>
"""


def test_parse_products_extracts_stat_pairs_and_link():
    records = parse_products(PRODUCTS_HTML)
    assert records == [
        {
            "name": "Silver-2",
            "source": "davrbank.uz",
            "Omonat muddati": "25 oygacha",
            "Foiz stavkasi": "6.5 %",
            "url": "https://davrbank.uz/uz/deposits/individual-silver-2",
        }
    ]


def test_parse_products_skips_cards_without_a_title():
    records = parse_products(PRODUCTS_HTML)
    assert len(records) == 1


def test_connector_uses_davr_bank_code_and_individual_segment():
    connector = DavrbankConnector("deposit", "https://davrbank.uz/uz/deposits")
    assert connector.bank_code == "DAVR"
    assert connector.segment == "individual"
    assert connector.product_type == "deposit"


# Ustunlar: Valyuta | MB | Sotuv (bank sotadi) | Xarid (bank xarid
# qiladi). Raqamlarda ajratuvchi \xa0 (NBSP) va vergul o'nlik nuqta
# o'rnida keladi. RUB qatorida "0,00" — hozircha almashtirilmaydigan
# valyuta, o'tkazib yuborilishi kerak.
EXCHANGE_HTML = """
<table>
<thead><tr><th>Valyuta</th><th>MB</th><th>Sotuv</th><th>Xarid</th></tr></thead>
<tbody>
<tr><td>AQSH dollari</td><td>11 813,21</td><td>11 870,00</td><td>11 760,00</td></tr>
<tr><td>Rossiya rubli</td><td>0,00</td><td>0,00</td><td>0,00</td></tr>
</tbody>
</table>
"""


def test_parse_exchange_rates_maps_columns_and_skips_zero_rates():
    records = parse_exchange_rates(EXCHANGE_HTML, url="https://davrbank.uz/uz/exchange-rate")
    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11760.0, "source": "davrbank.uz", "url": "https://davrbank.uz/uz/exchange-rate"},
        {"code": "USD", "side": "Sotish", "rate": 11870.0, "source": "davrbank.uz", "url": "https://davrbank.uz/uz/exchange-rate"},
    ]


def test_parse_exchange_rates_returns_empty_without_a_table():
    assert parse_exchange_rates("<html><body>no table</body></html>") == []


def test_exchange_connector_uses_currency_product_type():
    connector = DavrbankExchangeConnector()
    assert connector.bank_code == "DAVR"
    assert connector.product_type == "currency"
    assert connector.url == "https://davrbank.uz/uz/exchange-rate"
