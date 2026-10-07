from app.connectors.ipoteka_business import (
    IpotekaBusinessConnector,
    IpotekaExchangeConnector,
    parse_exchange_rates,
    parse_product_cards,
)

PRODUCT_CARDS_HTML = """
<div class="product-card">
  <div class="product-card__title">Tadbirkorlik subyektlari uchun milliy valyutada depozit</div>
  <div class="dl"><div class="dt">Valyuta</div><div class="dd">UZS</div></div>
  <div class="dl"><div class="dt">Foiz</div><div class="dd">14,85% gacha</div></div>
  <div class="dl"><div class="dt">Depozit muddati</div><div class="dd">24 oygacha</div></div>
  <div class="product-card__btns">
    <a class="button button--primary" href="/business/deposites/x/#calculator-block">Jamg'arishni boshlash</a>
    <a class="button button--text" href="/business/deposites/yuridik-shaxslar-uchun-depozit-nat/">Barcha shartlari</a>
  </div>
</div>
<div class="product-card">
  <div class="product-card__title">BUSINESS CHEVY avtokredit</div>
  <div class="dl"><div class="dt">Kredit foizi</div><div class="dd">0,0%</div></div>
</div>
<div class="product-card">
  <div class="dl"><div class="dt">Valyuta</div><div class="dd">USD</div></div>
</div>
"""


def test_parse_product_cards_extracts_name_and_fields():
    records = parse_product_cards(PRODUCT_CARDS_HTML)

    assert len(records) == 2  # nomsiz karta o'tkazib yuboriladi
    assert records[0] == {
        "name": "Tadbirkorlik subyektlari uchun milliy valyutada depozit",
        "source": "ipotekabank.uz",
        "Valyuta": "UZS",
        "Foiz": "14,85% gacha",
        "Depozit muddati": "24 oygacha",
        "url": "https://ipotekabank.uz/business/deposites/yuridik-shaxslar-uchun-depozit-nat/",
    }
    assert records[1]["name"] == "BUSINESS CHEVY avtokredit"
    assert records[1]["Kredit foizi"] == "0,0%"
    assert "url" not in records[1]  # bu kartada "Barcha shartlari" havolasi yo'q


def test_connector_uses_business_segment_and_ipoteka_bank_code():
    connector = IpotekaBusinessConnector("deposit", "https://example.test/deposits")

    assert connector.segment == "business"
    assert connector.bank_code == "IPOTEKA"
    assert connector.product_type == "deposit"


# Uch tab bor ("Filialda"/"Bankomatda"/"Ilovada") — har birining o'z
# jadvali bor, faqat bosh "Filialda" tabidagi (#all) qatorlar olinishi
# kerak.
EXCHANGE_HTML = """
<div class="tab-pane active show" id="all">
  <table class="currency-table">
    <tbody>
      <tr>
        <td><div class="currency-badge"><span>AQSH Dollari</span><span>USD</span></div></td>
        <td class="currency-sale">11 740</td>
        <td class="currency-sale">11 855</td>
        <td class="currency-sale">11797.92</td>
      </tr>
    </tbody>
  </table>
</div>
<div class="tab-pane" id="atms">
  <table class="currency-table">
    <tbody>
      <tr>
        <td><div class="currency-badge"><span>AQSH Dollari</span><span>USD</span></div></td>
        <td class="currency-sale">11 700</td>
        <td class="currency-sale">11 900</td>
        <td class="currency-sale">11797.92</td>
      </tr>
    </tbody>
  </table>
</div>
"""


def test_parse_exchange_rates_reads_only_the_branch_tab():
    records = parse_exchange_rates(EXCHANGE_HTML, url="https://www.ipotekabank.uz/private/services/currency/")
    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11740.0, "source": "ipotekabank.uz", "url": "https://www.ipotekabank.uz/private/services/currency/"},
        {"code": "USD", "side": "Sotish", "rate": 11855.0, "source": "ipotekabank.uz", "url": "https://www.ipotekabank.uz/private/services/currency/"},
    ]


def test_parse_exchange_rates_returns_empty_without_a_table():
    assert parse_exchange_rates("<html><body>no table</body></html>") == []


def test_exchange_connector_uses_currency_product_type():
    connector = IpotekaExchangeConnector()
    assert connector.bank_code == "IPOTEKA"
    assert connector.product_type == "currency"
    assert connector.url == "https://www.ipotekabank.uz/private/services/currency/"
