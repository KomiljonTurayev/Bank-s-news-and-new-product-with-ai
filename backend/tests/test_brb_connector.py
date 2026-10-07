from app.connectors.brb import BRBConnector, parse_product_offers

HTML = """
<section class="product-offer" aria-labelledby="x">
  <div class="product-offer__content">
    <h3 class="product-offer__title">Start 18</h3>
    <div class="product-offer__facts">
      <div class="product-offer__fact"><dt>Yillik foiz stavkasi</dt><dd>15%</dd></div>
      <div class="product-offer__fact"><dt>Omonat muddati</dt><dd>18 yoshgacha</dd></div>
    </div>
    <div class="product-offer__actions">
      <a href="/jismoniy-shaxslarga/omonatlar/start-18" class="w-button">Batafsil</a>
    </div>
  </div>
</section>
"""


def test_parse_product_offers():
    records = parse_product_offers(HTML)

    assert len(records) == 1
    assert records[0] == {
        "name": "Start 18",
        "source": "brb.uz",
        "Yillik foiz stavkasi": "15%",
        "Omonat muddati": "18 yoshgacha",
        "url": "https://brb.uz/jismoniy-shaxslarga/omonatlar/start-18",
    }


def test_connector_uses_individual_segment_and_brb_bank_code():
    connector = BRBConnector("deposit", "https://brb.uz/jismoniy-shaxslarga/omonatlar")
    assert connector.segment == "individual"
    assert connector.bank_code == "BRB"
