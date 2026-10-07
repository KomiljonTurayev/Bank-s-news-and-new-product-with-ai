from app.connectors.infinbank import (
    InFinbankConnector,
    InFinbankExchangeConnector,
    parse_credit_cards,
    parse_deposit_cards,
    parse_exchange_rates,
)

DEPOSIT_HTML = """
<div class="js-deposit-card">
  <h4 class="deposit-card__title">Infin Daromad</h4>
  <ul class="deposit-card__detail-list">
    <li class="deposit-card__detail-list__item"><p><span class="main-text">Yillik foiz:</span><b class="sub-text">18%</b></p></li>
    <li class="deposit-card__detail-list__item"><p><span class="main-text">Omonat muddati:</span><b class="sub-text">18 oy</b></p></li>
  </ul>
  <a href="/uz/private/deposit/daromad/" class="deposit-card__link">Axborot varaqasi</a>
</div>
"""

CREDIT_HTML = """
<li class="plastic-in-list__item">
  <div class="plastic-in-content">
    <a href="/uz/private/credits/nrg_mortgage/" class="news-preview__link plastic-in-content__link dlink">NRG ipotekasi</a>
    <ul>
      <li class="map-reg-list__item owner-list__item"><div><b class="owner-list__title">Foiz stavkasi</b><p class="owner-list__text">yillik 16,99% dan</p></div></li>
      <li class="map-reg-list__item owner-list__item"><div><b class="owner-list__title">Kredit muddati</b><p class="owner-list__text">240 oygacha</p></div></li>
    </ul>
  </div>
</li>
"""


def test_parse_deposit_cards():
    records = parse_deposit_cards(DEPOSIT_HTML)
    assert records[0] == {
        "name": "Infin Daromad",
        "source": "infinbank.com",
        "Yillik foiz": "18%",
        "Omonat muddati": "18 oy",
        "url": "https://www.infinbank.com/uz/private/deposit/daromad/",
    }


def test_parse_credit_cards():
    records = parse_credit_cards(CREDIT_HTML)
    assert records[0]["name"] == "NRG ipotekasi"
    assert records[0]["Foiz stavkasi"] == "yillik 16,99% dan"
    assert records[0]["url"] == "https://www.infinbank.com/uz/private/credits/nrg_mortgage/"


def test_connector_uses_individual_segment_and_infin_bank_code():
    connector = InFinbankConnector("deposit", "https://www.infinbank.com/uz/private/deposit/")
    assert connector.segment == "individual"
    assert connector.bank_code == "INFIN"


# Valyutalar ustun, kanallar qator-guruh ("MB kurs"/"Ayrboshlash
# shoxobchasi"/"Ilova" — har biri ``rowspan``li birinchi katakda nom
# ulashadi). Faqat "Ayrboshlash shoxobchasi" (filial) olinishi kerak;
# "-" bilan belgilangan mavjud bo'lmagan qiymatlar o'tkazib yuboriladi.
EXCHANGE_HTML = """
<table>
<thead><tr><th>Valyuta</th><th></th>
<th><div class="rates-flag"><span class="text">USD</span></div></th>
<th><div class="rates-flag"><span class="text">EUR</span></div></th>
</tr></thead>
<tbody>
<tr><td class="rates-subtitle">MB kurs</td><td></td><td>11 797.92</td><td>13 739.86</td></tr>
<tr><td class="rates-subtitle" rowspan="2">Ayrboshlash shoxobchasi</td><td>Olish</td><td>11 780.00</td><td>13 000.00</td></tr>
<tr><td>Sotish</td><td>11 870.00</td><td>14 000.00</td></tr>
<tr><td class="rates-subtitle" rowspan="2">Ilova</td><td>Olish</td><td>11 780.00</td><td>-</td></tr>
<tr><td>Sotish</td><td>11 830.00</td><td>-</td></tr>
</tbody>
</table>
"""


def test_parse_exchange_rates_reads_only_the_branch_group():
    records = parse_exchange_rates(EXCHANGE_HTML, url="https://www.infinbank.com/uz/private/exchange-rates/")
    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11780.0, "source": "infinbank.com", "url": "https://www.infinbank.com/uz/private/exchange-rates/"},
        {"code": "EUR", "side": "Olish", "rate": 13000.0, "source": "infinbank.com", "url": "https://www.infinbank.com/uz/private/exchange-rates/"},
        {"code": "USD", "side": "Sotish", "rate": 11870.0, "source": "infinbank.com", "url": "https://www.infinbank.com/uz/private/exchange-rates/"},
        {"code": "EUR", "side": "Sotish", "rate": 14000.0, "source": "infinbank.com", "url": "https://www.infinbank.com/uz/private/exchange-rates/"},
    ]


def test_parse_exchange_rates_returns_empty_without_a_table():
    assert parse_exchange_rates("<html><body>no table</body></html>") == []


def test_exchange_connector_uses_currency_product_type():
    connector = InFinbankExchangeConnector()
    assert connector.bank_code == "INFIN"
    assert connector.product_type == "currency"
    assert connector.url == "https://www.infinbank.com/uz/private/exchange-rates/"
