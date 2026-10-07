from app.connectors.html_cards import parse_card_list
from app.connectors.kdbbank import (
    KDBBankCardConnector,
    KDBBankConnector,
    KDBBankExchangeConnector,
    _CARD_LAYOUT,
    parse_credit,
    parse_exchange_rates,
)

# Haqiqiy sahifaning soddalashtirilgan nusxasi — shartlar jadvali
# h3'dan keyin darhol keladigan div.row ketma-ketligida, undan keyin
# "Istisno holatlar" bo'limi ham xuddi shu "row" klassidan foydalanadi
# (parser shu birodarda to'xtashi kerak).
CREDIT_HTML = """
<html><body>
<main class="main-hero">
<h2 class="heading-2 mb-4">Korporativ Mijozlar Xodimlariga Mikroqarz (Overdraft)</h2>
<h3 class="heading-3 mb-4">Kredit Berish Shartlari</h3>
<div class="row"><div class="col-lg-3"><p><strong>Qarz Oluvchi</strong></p></div><div class="col-lg-9"><p>Doimiy ishlaydigan xodim</p></div></div>
<div class="row"><div class="col-lg-3"><p><strong>Kredit Muddati</strong></p></div><div class="col-lg-9"><p>12 oygacha</p></div></div>
<div class="row"><div class="col-lg-3"><p><strong>Yillik Foiz Stavkasi</strong></p></div><div class="col-lg-9"><p>Bankning Kredit qo'mitasi tomonidan belgilanadi (34% va undan yuqori)</p></div></div>
<div class="mt-4"><b>Garov narsasini bosqichma-bosqich garovdan chiqarish</b></div>
<h3 class="heading-3 mb-3">Istisno holatlarda kredit shartlarini qayta ko'rib chiqish</h3>
<div class="row mt-5"><div class="col-lg-3"><p><strong>Bu qatorga kirmasligi kerak</strong></p></div><div class="col-lg-9"><p>100%</p></div></div>
</main>
</body></html>
"""


def test_parse_credit_extracts_single_product_and_stops_at_exceptions_section():
    records = parse_credit(CREDIT_HTML, url="https://kdb.uz/uz/individuals/credit")
    assert records == [
        {
            "name": "Korporativ Mijozlar Xodimlariga Mikroqarz (Overdraft)",
            "source": "kdb.uz",
            "url": "https://kdb.uz/uz/individuals/credit",
            "Qarz Oluvchi": "Doimiy ishlaydigan xodim",
            "Kredit Muddati": "12 oygacha",
            "Yillik Foiz Stavkasi": "Bankning Kredit qo'mitasi tomonidan belgilanadi (34% va undan yuqori)",
        }
    ]


def test_parse_credit_returns_empty_when_no_rate_found():
    html = """
    <main class="main-hero">
    <h2>Mahsulot</h2>
    <h3>Kredit Berish Shartlari</h3>
    <div class="row"><div class="col-lg-3"><p><strong>Muddat</strong></p></div><div class="col-lg-9"><p>12 oy</p></div></div>
    </main>
    """
    assert parse_credit(html) == []


def test_parse_credit_returns_empty_when_expected_structure_is_missing():
    assert parse_credit("<html><body><h1>Boshqa sahifa</h1></body></html>") == []


def test_connector_defaults_to_the_credit_page():
    connector = KDBBankConnector()
    assert connector.url == "https://kdb.uz/uz/individuals/credit"
    assert connector.bank_code == "KDBUZ"
    assert connector.product_type == "credit"


# Haqiqiy sahifaning soddalashtirilgan nusxasi — har xususiyat ikkita
# "small-paragraph" <p>dan iborat (birinchisi yorliq, ikkinchisi
# ichida <strong> bilan qiymat) — shu bois yorliq tanlagichi
# ":not(.fs-14)" bilan ikkinchisidan ajratiladi.
CARD_HTML = """
<div class="products-items">
  <a class="card-link" href="/uz/individuals/international-cards/visa-gold">
    <article class="card-cards">
      <h3 class="heading-3">Visa Gold</h3>
      <div class="row">
        <div class="col-md-4">
          <p class="small-paragraph">To'lov Tizim Turi :</p>
          <p class="small-paragraph fs-14"><strong>VISA</strong></p>
        </div>
        <div class="col-md-4">
          <p class="small-paragraph">Pul Birligi:</p>
          <p class="small-paragraph fs-14"><strong>USD</strong></p>
        </div>
      </div>
    </article>
  </a>
</div>
"""


def test_card_layout_extracts_name_and_labeled_fields():
    records = parse_card_list(CARD_HTML, _CARD_LAYOUT, "https://kdb.uz")
    assert records == [
        {
            "name": "Visa Gold",
            "source": "kdb.uz",
            "url": "https://kdb.uz/uz/individuals/international-cards/visa-gold",
            "To'lov Tizim Turi :": "VISA",
            "Pul Birligi:": "USD",
        }
    ]


def test_card_connector_uses_given_url():
    connector = KDBBankCardConnector("https://kdb.uz/uz/individuals/local-cards")
    assert connector.url == "https://kdb.uz/uz/individuals/local-cards"
    assert connector.bank_code == "KDBUZ"
    assert connector.product_type == "card"


# Haqiqiy sahifaning soddalashtirilgan nusxasi — bir nechta tab (filial,
# bankomat, mobil) bor, birinchi jadval har doim filial (shoxobcha)
# kurslariga tegishli.
EXCHANGE_HTML = """
<table class="d-none d-lg-block">
  <thead><tr><th></th><th>USD</th><th>EUR</th><th>RUB</th></tr></thead>
  <tbody><tr><th>UZS</th><td>11705 / 11820</td><td>13200 / 14000</td><td>n/a / n/a</td></tr></tbody>
</table>
"""


def test_parse_exchange_rates_extracts_buy_sell_pairs_and_skips_unavailable():
    records = parse_exchange_rates(EXCHANGE_HTML, url="https://kdb.uz/uz/interactive-services/exchange-rates")
    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11705.0, "source": "kdb.uz", "url": "https://kdb.uz/uz/interactive-services/exchange-rates"},
        {"code": "USD", "side": "Sotish", "rate": 11820.0, "source": "kdb.uz", "url": "https://kdb.uz/uz/interactive-services/exchange-rates"},
        {"code": "EUR", "side": "Olish", "rate": 13200.0, "source": "kdb.uz", "url": "https://kdb.uz/uz/interactive-services/exchange-rates"},
        {"code": "EUR", "side": "Sotish", "rate": 14000.0, "source": "kdb.uz", "url": "https://kdb.uz/uz/interactive-services/exchange-rates"},
    ]
    assert all(r["code"] != "RUB" for r in records)


def test_exchange_connector_defaults():
    connector = KDBBankExchangeConnector()
    assert connector.url == "https://kdb.uz/uz/interactive-services/exchange-rates"
    assert connector.bank_code == "KDBUZ"
    assert connector.product_type == "currency"
