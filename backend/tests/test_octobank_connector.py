from app.connectors.octobank import OctobankCardConnector, OctobankConnector, parse_card_page, parse_product_page

PRODUCT_PAGE_HTML = """
<h1>Avtokredit 1.0</h1>
<div class="hero_16_items">
  <div class="hero_16_item"><h3 class="hero_16_item_heading">Cheklanmagan</h3><p class="hero_16_item_paragraph">Kredit summasi</p></div>
  <div class="hero_16_item"><h3 class="hero_16_item_heading">Har qanday model</h3><p class="hero_16_item_paragraph"></p></div>
  <div class="hero_16_item"><h3 class="hero_16_item_heading">Yillik 21%/24%</h3><p class="hero_16_item_paragraph">Foiz stavkasi</p></div>
  <div class="hero_16_item"><h3 class="hero_16_item_heading">60 oygacha</h3><p class="hero_16_item_paragraph">Kredit muddati</p></div>
</div>
"""

NO_STATS_HTML = "<h1>404</h1>"


def test_parse_product_page_extracts_stats_and_skips_empty_labels():
    record = parse_product_page(PRODUCT_PAGE_HTML, "https://octobank.uz/jismoniy-shaxslarga/avtokredit")
    assert record == {
        "name": "Avtokredit 1.0",
        "source": "octobank.uz",
        "url": "https://octobank.uz/jismoniy-shaxslarga/avtokredit",
        "Kredit summasi": "Cheklanmagan",
        "Foiz stavkasi": "Yillik 21%/24%",
        "Kredit muddati": "60 oygacha",
    }


def test_parse_product_page_returns_none_without_stats():
    assert parse_product_page(NO_STATS_HTML, "https://octobank.uz/x") is None


def test_connector_uses_ravnaq_bank_code_for_the_renamed_bank():
    connector = OctobankConnector(["/jismoniy-shaxslarga/avtokredit"])
    assert connector.bank_code == "RAVNAQ"
    assert connector.product_type == "credit"
    assert connector.urls == ["https://octobank.uz/jismoniy-shaxslarga/avtokredit"]


# Karta sahifalari kredit sahifalaridan boshqa razmetkadan foydalanadi
# (hero_17_bottom_item: <h5> yorliq + <p> qiymat, hero_16 emas).
CARD_PAGE_HTML = """
<h1>Visa Infinite</h1>
<div class="hero_17_bottom">
  <div class="hero_17_bottom_item"><h5 class="hero_17_bottom_item_heading">Karta ochilishi</h5><p class="hero_17_bottom_item_paragraph">200 000 UZS</p></div>
  <div class="hero_17_bottom_item"><h5 class="hero_17_bottom_item_heading">Minimal balans</h5><p class="hero_17_bottom_item_paragraph">100 USD</p></div>
  <div class="hero_17_bottom_item"><h5 class="hero_17_bottom_item_heading">Valyuta</h5><p class="hero_17_bottom_item_paragraph">USD</p></div>
</div>
"""


def test_parse_card_page_extracts_name_and_terms():
    record = parse_card_page(CARD_PAGE_HTML, "https://octobank.uz/jismoniy-shaxslarga/xalqaro-kartalar/visa-infinite")
    assert record == {
        "name": "Visa Infinite",
        "source": "octobank.uz",
        "url": "https://octobank.uz/jismoniy-shaxslarga/xalqaro-kartalar/visa-infinite",
        "Karta ochilishi": "200 000 UZS",
        "Minimal balans": "100 USD",
        "Valyuta": "USD",
    }


def test_parse_card_page_returns_none_without_stats():
    assert parse_card_page(NO_STATS_HTML, "https://octobank.uz/x") is None


def test_card_connector_uses_ravnaq_bank_code_and_card_product_type():
    connector = OctobankCardConnector(["/jismoniy-shaxslarga/som-kartalari/humo"])
    assert connector.bank_code == "RAVNAQ"
    assert connector.product_type == "card"
    assert connector.segment == "individual"
    assert connector.urls == ["https://octobank.uz/jismoniy-shaxslarga/som-kartalari/humo"]
