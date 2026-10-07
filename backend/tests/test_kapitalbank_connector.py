from app.connectors.kapitalbank import KapitalbankConnector, parse_item_cards

DEPOSIT_HTML = """
<div class="item has-preview-picture">
  <div class="item-desc">
    <h3 class="item-title"><a href="/uz/deposit/kapital-ziynat-02/">Kapital Ziynat</a></h3>
    <div class="item-prop"><b>Foiz stavkasi:</b><span>18%</span></div>
    <div class="item-prop"><b>Valyuta:</b><span>So'm</span></div>
  </div>
</div>
"""

CREDIT_HTML = """
<div class="item has-preview-picture">
  <div class="desc">
    <h3 class="title"><a href="/uz/crediting/ekonom-plyus-cobalt/">Ekonom plyus (Cobalt)</a></h3>
    <h3 class="title"><a href="https://youtube.com/x" target="_blank"><span>Kreditni to'lash</span></a></h3>
    <div class="item-prop"><b>Foiz stavkasi:</b><span>0% - 17%</span></div>
    <div class="item-prop"><b>Kredit muddati:</b><span>11 oydan 60 oygacha</span></div>
  </div>
</div>
"""


def test_parse_deposit_cards_uses_item_title_class():
    records = parse_item_cards(DEPOSIT_HTML)

    assert len(records) == 1
    assert records[0] == {
        "name": "Kapital Ziynat",
        "source": "kapital24.uz",
        "Foiz stavkasi": "18%",
        "Valyuta": "So'm",
        "url": "https://www.kapital24.uz/uz/deposit/kapital-ziynat-02/",
    }


def test_parse_credit_cards_picks_first_title_not_youtube_link():
    records = parse_item_cards(CREDIT_HTML)

    assert len(records) == 1
    assert records[0]["name"] == "Ekonom plyus (Cobalt)"
    assert records[0]["url"] == "https://www.kapital24.uz/uz/crediting/ekonom-plyus-cobalt/"
    assert records[0]["Kredit muddati"] == "11 oydan 60 oygacha"


def test_connector_uses_individual_segment_and_kdb_bank_code():
    connector = KapitalbankConnector("deposit", "https://kapital24.uz/uz/deposit/")

    assert connector.segment == "individual"
    assert connector.bank_code == "KDB"
    assert connector.product_type == "deposit"
