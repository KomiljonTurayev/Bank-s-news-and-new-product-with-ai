from app.connectors.trastbank import (
    TrastbankConnector,
    TrastbankExchangeConnector,
    parse_credit_cards,
    parse_deposit_cards,
    parse_exchange_rates,
)

DEPOSIT_HTML = """
<div class="deposit__item element-item item">
  <div class="deposit__item_main">
    <div class="deposit__item_title">Maqsadli ipoteka</div>
    <ul class="deposit__item_info">
      <li><span>Yillik foiz:</span><strong>14%</strong></li>
      <li><span>Muddati:</span><strong>12 oy</strong></li>
    </ul>
    <div class="deposit__item_button"><a href="/uz/private/deposit/maqsadli-ipoteka/">Tavsifi</a></div>
  </div>
</div>
"""

CREDIT_HTML = """
<div class="item has-preview-picture has-preview-text has-properties">
  <div class="desc">
    <h3 class="title"><a href="/uz/private/crediting/mikroqarzlar/">Qulay mikroqarz</a></h3>
    <div class="row item-props _credit__info">
      <div class="col-xs-6 item-prop">
        <div class="item-prop-title">Yillik foiz:</div>
        <div class="item-prop-value"><strong>19.5</strong> <small>foizdan boshlab</small></div>
      </div>
    </div>
  </div>
</div>
"""


def test_parse_deposit_cards():
    records = parse_deposit_cards(DEPOSIT_HTML)
    assert records[0] == {
        "name": "Maqsadli ipoteka",
        "source": "trastbank.uz",
        "Yillik foiz": "14%",
        "Muddati": "12 oy",
        "url": "https://trastbank.uz/uz/private/deposit/maqsadli-ipoteka/",
    }


def test_parse_credit_cards():
    records = parse_credit_cards(CREDIT_HTML)
    assert records[0]["name"] == "Qulay mikroqarz"
    assert records[0]["Yillik foiz"] == "19.5 foizdan boshlab"
    assert records[0]["url"] == "https://trastbank.uz/uz/private/crediting/mikroqarzlar/"


def test_connector_uses_individual_segment_and_trast_bank_code():
    connector = TrastbankConnector("deposit", "https://trastbank.uz/uz/private/deposit/")
    assert connector.segment == "individual"
    assert connector.bank_code == "TRAST"


# Sahifadagi "Sotish"/"Sotib olish" UI yorliqlari mijoz nuqtai nazaridan
# yozilgan va JSON kalitlariga (BUY/SALE) mos kelmaydi — parser JS
# o'zgaruvchisidagi kalitlarga tayanishi kerak, UI matniga emas.
EXCHANGE_HTML = """
<html><body>
<script>
var arCurrencyRates = {"CB":{"EUR":"13719.86","USD":"11813.21","UZS":1},"BUY":{"USD":11780,"EUR":13200,"UZS":1},"SALE":{"USD":11870,"EUR":13800,"UZS":1}};
</script>
</body></html>
"""


def test_parse_exchange_rates_maps_buy_and_sale_json_keys_to_olish_sotish():
    records = parse_exchange_rates(EXCHANGE_HTML, url="https://trastbank.uz/uz/services/exchange-rates/")
    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11780.0, "source": "trastbank.uz", "url": "https://trastbank.uz/uz/services/exchange-rates/"},
        {"code": "EUR", "side": "Olish", "rate": 13200.0, "source": "trastbank.uz", "url": "https://trastbank.uz/uz/services/exchange-rates/"},
        {"code": "USD", "side": "Sotish", "rate": 11870.0, "source": "trastbank.uz", "url": "https://trastbank.uz/uz/services/exchange-rates/"},
        {"code": "EUR", "side": "Sotish", "rate": 13800.0, "source": "trastbank.uz", "url": "https://trastbank.uz/uz/services/exchange-rates/"},
    ]


def test_parse_exchange_rates_returns_empty_without_the_js_variable():
    assert parse_exchange_rates("<html><body>no rates here</body></html>") == []


def test_exchange_connector_uses_currency_product_type():
    connector = TrastbankExchangeConnector()
    assert connector.bank_code == "TRAST"
    assert connector.product_type == "currency"
    assert connector.url == "https://trastbank.uz/uz/services/exchange-rates/"
