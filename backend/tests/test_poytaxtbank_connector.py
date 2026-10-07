from app.connectors.poytaxtbank import PoytaxtbankConnector

HTML = """
<div class="item">
  <div class="item__content">
    <h3 class="item__title"><a href="/uz/private/deposit/oyma-oy/">OYMA-OY</a></h3>
    <div class="item__features">
      <div class="item__info"><div class="item__value">20%</div><div class="item__label">Yillik stavka</div></div>
    </div>
  </div>
</div>
"""


def test_reuses_turonbank_parser_with_own_source_and_bank_code():
    connector = PoytaxtbankConnector("deposit", "https://poytaxtbank.uz/uz/private/deposit/")

    records = connector.parse(HTML)

    assert connector.bank_code == "POYTAXT"
    assert connector.segment == "individual"
    assert records[0]["source"] == "poytaxtbank.uz"
    assert records[0]["name"] == "OYMA-OY"
