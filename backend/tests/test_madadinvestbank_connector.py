from app.connectors.madadinvestbank import (
    MadadInvestBankConnector,
    MadadInvestBankExchangeConnector,
    find_credit_links,
    parse_credit_detail,
    parse_deposits,
    parse_exchange_rates,
)

DEPOSITS_HTML = """
<div class="vklad-bl__item">
  <div class="vklad-main">
    <div class="vklad-main__tit">Omonat my capital USD</div>
    <div class="vklad-main__pro"><div><span>13</span></div><span>muddati</span></div>
    <div class="vklad-main__pro"><div><span>6</span>%</div><span>Foizi</span></div>
    <div class="vklad-main__link"><a href="/vklad/24">Batafsil</a></div>
  </div>
</div>
"""

CREDITS_LIST_HTML = """
<div class="kred-bl__item">
  <div class="kred-bl__item-main">
    <div class="main__tit">Yangi avtomobil uchun avtokredit</div>
    <a class="site_link" href="https://madadinvestbank.uz/credit/15">Batafsil</a>
  </div>
</div>
"""

CREDIT_DETAIL_HTML = """
<h1>Yangi avtomobil uchun avtokredit</h1>
<form class="ipotek-form">
  <div class="ipotek-form__item"><div><span>60 oygacha</span></div><label><input placeholder="Kredit muddati"></label></div>
  <div class="ipotek-form__item"><div><span>27.9%</span></div><label><input placeholder="Foizi"></label></div>
  <div class="ipotek-form__item"><a href="#calc">Hisoblash</a></div>
</form>
"""


def test_parse_deposits_extracts_stat_pairs():
    records = parse_deposits(DEPOSITS_HTML)
    assert records == [
        {
            "name": "Omonat my capital USD",
            "source": "madadinvestbank.uz",
            "muddati": "13",
            "Foizi": "6%",
            "url": "https://madadinvestbank.uz/vklad/24",
        }
    ]


def test_find_credit_links_resolves_absolute_urls():
    links = find_credit_links(CREDITS_LIST_HTML)
    assert links == ["https://madadinvestbank.uz/credit/15"]


def test_parse_credit_detail_reads_form_item_pairs():
    record = parse_credit_detail(CREDIT_DETAIL_HTML, "https://madadinvestbank.uz/credit/15")
    assert record == {
        "name": "Yangi avtomobil uchun avtokredit",
        "source": "madadinvestbank.uz",
        "url": "https://madadinvestbank.uz/credit/15",
        "Kredit muddati": "60 oygacha",
        "Foizi": "27.9%",
    }


def test_parse_credit_detail_ignores_the_calculate_button_item():
    record = parse_credit_detail(CREDIT_DETAIL_HTML, "https://madadinvestbank.uz/credit/15")
    assert "Hisoblash" not in record.values()


def test_connector_picks_url_by_product_type():
    deposit_connector = MadadInvestBankConnector("deposit")
    assert deposit_connector.url == "https://madadinvestbank.uz/vklads"
    assert deposit_connector.bank_code == "MADAD"

    credit_connector = MadadInvestBankConnector("credit")
    assert credit_connector.url == "https://madadinvestbank.uz/credits/physical"


# GBP qatorida saytning o'zida xato — kod "GBR" (davlat kodi) deb
# yozilgan, "GBP"ga tuzatilishi kerak. JPY sotib olish/sotish 0.00 —
# hozircha almashtirilmaydi, o'tkazib yuborilishi kerak. Ikkinchi
# ("Bankomat") jadval e'tiborga olinmasligi kerak.
EXCHANGE_HTML = """
<table>
<thead><tr><th>Valyuta</th><th>Belgilar kodi</th><th>Sotib olish</th><th>Sotish</th></tr></thead>
<tbody>
<tr><td>AQSh dollari</td><td>USD</td><td>11 780.00</td><td>11 870.00</td></tr>
<tr><td>Funt sterling</td><td>GBR</td><td>15 000.00</td><td>16 000.00</td></tr>
<tr><td>Yaponiya yenasi</td><td>JPY</td><td>0.00</td><td>0.00</td></tr>
</tbody>
</table>
<h4>Bankomat</h4>
<table>
<tbody><tr><td>AQSh dollari</td><td>USD</td><td>11 700.00</td><td>11 900.00</td></tr></tbody>
</table>
"""


def test_parse_exchange_rates_fixes_the_gbp_code_and_skips_zero_rates():
    records = parse_exchange_rates(EXCHANGE_HTML, url="https://madadinvestbank.uz/currency")
    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11780.0, "source": "madadinvestbank.uz", "url": "https://madadinvestbank.uz/currency"},
        {"code": "USD", "side": "Sotish", "rate": 11870.0, "source": "madadinvestbank.uz", "url": "https://madadinvestbank.uz/currency"},
        {"code": "GBP", "side": "Olish", "rate": 15000.0, "source": "madadinvestbank.uz", "url": "https://madadinvestbank.uz/currency"},
        {"code": "GBP", "side": "Sotish", "rate": 16000.0, "source": "madadinvestbank.uz", "url": "https://madadinvestbank.uz/currency"},
    ]


def test_parse_exchange_rates_returns_empty_without_a_table():
    assert parse_exchange_rates("<html><body>no table</body></html>") == []


def test_exchange_connector_uses_currency_product_type():
    connector = MadadInvestBankExchangeConnector()
    assert connector.bank_code == "MADAD"
    assert connector.product_type == "currency"
    assert connector.url == "https://madadinvestbank.uz/currency"
