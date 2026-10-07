from app.connectors.saderatbank import SaderatBankConnector, parse_credit_page

CREDIT_PAGE_HTML = """
<h1>Avtokredit &mdash;oson va oddiy!</h1>
<div class="lpc-autocredit__item">
  <div class="lpc-autocredit__item-subtitle">25% dan</div>
  <div class="lpc-autocredit__item-text">boshlang'ich to'lov</div>
</div>
<div class="lpc-autocredit__item">
  <div class="lpc-autocredit__item-subtitle">25% dan</div>
  <div class="lpc-autocredit__item-text">yillik stavka</div>
</div>
<div class="lpc-autocredit__item">
  <div class="lpc-autocredit__item-subtitle">60 gacha oylar</div>
  <div class="lpc-autocredit__item-text">to'lash muddati</div>
</div>
"""

NO_ITEMS_HTML = "<h1>Overdraft</h1><ul><li><span>Kredit foizi:</span> 28%.</li></ul>"


def test_parse_credit_page_takes_name_before_dash_and_extracts_stats():
    record = parse_credit_page(CREDIT_PAGE_HTML, "https://saderatbank.uz/avtokredit")
    assert record == {
        "name": "Avtokredit",
        "source": "saderatbank.uz",
        "url": "https://saderatbank.uz/avtokredit",
        "boshlang'ich to'lov": "25% dan",
        "yillik stavka": "25% dan",
        "to'lash muddati": "60 gacha oylar",
    }


def test_parse_credit_page_returns_none_without_lpc_items():
    assert parse_credit_page(NO_ITEMS_HTML, "https://saderatbank.uz/overdraft") is None


def test_connector_uses_soderot_bank_code_and_credit_type():
    connector = SaderatBankConnector(["avtokredit", "istemol-krediti"])
    assert connector.bank_code == "SODEROT"
    assert connector.product_type == "credit"
    assert connector.urls == [
        "https://saderatbank.uz/avtokredit",
        "https://saderatbank.uz/istemol-krediti",
    ]
