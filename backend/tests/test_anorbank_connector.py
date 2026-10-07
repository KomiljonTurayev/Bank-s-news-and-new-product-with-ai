from app.connectors.anorbank import AnorbankConnector, AnorbankExchangeConnector, parse_cards, parse_exchange_rates

HTML = """
<div class="cards__item">
  <div class="cards__teaser">
    <h3>MILLIY HAR KUNLIK omonati</h3>
    <ul>
      <li><p>Muddati - 24 oy</p></li>
      <li><p>Yillik 20%</p></li>
      <li><p>Cheksiz to'ldirish imkoniyati</p></li>
    </ul>
    <div class="cards__btns"><a href="/uz/deposit/milliy-har-kunlik-uz/">Batafsil</a></div>
  </div>
</div>
<div class="cards__item">
  <div class="cards__teaser">
    <h3>Limitni bilib oling</h3>
    <ul></ul>
  </div>
</div>
"""


def test_parse_cards_skips_promo_card_without_bullets():
    records = parse_cards(HTML)

    assert len(records) == 1
    assert records[0] == {
        "name": "MILLIY HAR KUNLIK omonati",
        "source": "anorbank.uz",
        "Muddati": "Muddati - 24 oy",
        "Foiz stavkasi": "Yillik 20%",
        "Xususiyatlari": "Cheksiz to'ldirish imkoniyati",
        "url": "https://anorbank.uz/uz/deposit/milliy-har-kunlik-uz/",
    }


def test_connector_uses_individual_segment_and_anor_bank_code():
    connector = AnorbankConnector("deposit", "https://anorbank.uz/uz/deposit/")
    assert connector.segment == "individual"
    assert connector.bank_code == "ANOR"


# Haqiqiy sahifaning soddalashtirilgan nusxasi:
# - USD "curr__name"ga ega emas (shahar bo'yicha <select>), kod img
#   alt'idan olinadi;
# - CHF'da bayroqcha "alt" matni saytning o'zida xato ("USD" deb
#   yozilgan) — kod nomdan ("Shveytsariya franki, CHF") olinishi kerak;
# - GBP sotish narxi "0,00" — hozircha almashtirilmaydi, o'tkazib
#   yuborilishi kerak;
# - izohga o'ralgan EUR kartasi (bo'sh qiymatlar bilan) — umuman
#   ko'rinmasligi kerak;
# - ikkinchi (Bankomat) bo'limdagi karta ham e'tiborga olinmasligi kerak.
EXCHANGE_HTML = """
<h1>Valyuta kursi (ayriboshlash shoxobchalarida)</h1>
<div class="currency--card">
  <div class="curr__flag"><img alt="USD"></div>
  <select name="usdCur"><option data-buy="11 810,00" data-sell="11 870,00">umumiy</option></select>
</div>
<div class="currency--card">
  <div class="curr__flag"><img alt="USD"></div>
  <div class="curr__name">Shveytsariya franki, CHF</div>
  <div class="currency--card__purchase"><div class="currency__card__value">13 520,00</div></div>
  <div class="currency--card__sale"><div class="currency__card__value">13 900,00</div></div>
</div>
<div class="currency--card">
  <div class="curr__flag"><img alt="GBP"></div>
  <div class="curr__name">Angliya funt sterlingi, GBP</div>
  <div class="currency--card__purchase"><div class="currency__card__value">15 240,00</div></div>
  <div class="currency--card__sale"><div class="currency__card__value">0,00</div></div>
</div>
<!--
<div class="currency--card">
  <div class="curr__flag"><img alt="EUR"></div>
  <div class="curr__name">Evro, EUR</div>
  <div class="currency--card__purchase"><div class="currency__card__value"></div></div>
  <div class="currency--card__sale"><div class="currency__card__value"></div></div>
</div>
-->
<h1>Bankomatlar uchun valyuta kurslari</h1>
<div class="currency--card">
  <div class="curr__flag"><img alt="JPY"></div>
  <div class="curr__name">Yaponiya iyenasi, JPY</div>
  <div class="currency--card__purchase"><div class="currency__card__value">42,00</div></div>
  <div class="currency--card__sale"><div class="currency__card__value">78,00</div></div>
</div>
"""


def test_parse_exchange_rates_only_reads_the_branch_section():
    records = parse_exchange_rates(EXCHANGE_HTML, url="https://anorbank.uz/uz/about/exchange-rates/")
    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11810.0, "source": "anorbank.uz", "url": "https://anorbank.uz/uz/about/exchange-rates/"},
        {"code": "USD", "side": "Sotish", "rate": 11870.0, "source": "anorbank.uz", "url": "https://anorbank.uz/uz/about/exchange-rates/"},
        {"code": "CHF", "side": "Olish", "rate": 13520.0, "source": "anorbank.uz", "url": "https://anorbank.uz/uz/about/exchange-rates/"},
        {"code": "CHF", "side": "Sotish", "rate": 13900.0, "source": "anorbank.uz", "url": "https://anorbank.uz/uz/about/exchange-rates/"},
    ]


def test_parse_exchange_rates_returns_empty_without_branch_heading():
    assert parse_exchange_rates("<html><body>no rates here</body></html>") == []


def test_exchange_connector_uses_currency_product_type():
    connector = AnorbankExchangeConnector()
    assert connector.bank_code == "ANOR"
    assert connector.product_type == "currency"
    assert connector.url == "https://anorbank.uz/uz/about/exchange-rates/"
