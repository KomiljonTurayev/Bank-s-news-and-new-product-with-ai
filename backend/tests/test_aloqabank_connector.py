from app.connectors.aloqabank import AloqabankConnector, parse_element_cards

HTML = """
<div class="element element--deposits">
  <div class="element__header">
    <h3 class="element__title"><a href="/uz/private/deposit/intellekt/">Intellekt</a></h3>
  </div>
  <div class="element__info element-info">
    <div class="element-info__group"><div class="element-info__value">16%</div><div class="element-info__label">Yillik stavka</div></div>
    <div class="element-info__group"><div class="element-info__value">24 oy</div><div class="element-info__label">Omonat muddati</div></div>
  </div>
</div>
"""


def test_parse_element_cards_reverses_value_then_label_order():
    records = parse_element_cards(HTML)

    assert len(records) == 1
    assert records[0] == {
        "name": "Intellekt",
        "source": "aloqabank.uz",
        "Yillik stavka": "16%",
        "Omonat muddati": "24 oy",
        "url": "https://aloqabank.uz/uz/private/deposit/intellekt/",
    }


def test_connector_uses_individual_segment_and_aloqa_bank_code():
    connector = AloqabankConnector("deposit", "https://aloqabank.uz/uz/private/deposit/")
    assert connector.segment == "individual"
    assert connector.bank_code == "ALOQA"
