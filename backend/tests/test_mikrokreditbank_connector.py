from app.connectors.mikrokreditbank import MikrokreditbankConnector, parse_itemb_cards

HTML = """
<article class="itemb">
  <h3 class="itemb__title"><a href="/uz/private/deposit/bayramona/">Bayramona</a></h3>
  <div class="itemb__features">
    <div class="itemb__info"><div class="itemb__value">18%</div><div class="itemb__label">Yillik stavka</div></div>
    <div class="itemb__info"><div class="itemb__value">12 oy</div><div class="itemb__label">Omonat muddati</div></div>
  </div>
</article>
"""


def test_parse_itemb_cards():
    records = parse_itemb_cards(HTML)

    assert len(records) == 1
    assert records[0] == {
        "name": "Bayramona",
        "source": "mkbank.uz",
        "Yillik stavka": "18%",
        "Omonat muddati": "12 oy",
        "url": "https://mkbank.uz/uz/private/deposit/bayramona/",
    }


def test_connector_uses_individual_segment_and_microcreditbank_code():
    connector = MikrokreditbankConnector("deposit", "https://mkbank.uz/uz/private/deposit/")
    assert connector.segment == "individual"
    assert connector.bank_code == "MICROCREDITBANK"
