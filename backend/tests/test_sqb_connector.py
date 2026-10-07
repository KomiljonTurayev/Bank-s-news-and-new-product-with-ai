from app.connectors.sqb import SQBConnector, SQBExchangeConnector, parse_checkout_cards, parse_exchange_rates

DEPOSITS_HTML = """
<div class="checkoutEasy">
  <div class="checkoutEasy__text"><h4>SQB Mobile orqali tezkor ochish</h4></div>
</div>
<div class="checkoutEasy">
  <div class="deposits_type">
    <div class="checkoutEasy__title">Imkoniyat-2</div>
    <div class="buttonLined"><a href="/uz/individuals/deposits/imkoniyat-2-uz/">Batafsil</a></div>
    <div class="blured__block"><div class="Deposits_percentage">24 %</div><div class="Deposits_rate">Foiz:</div></div>
    <div class="blured__block"><div class="Deposits_percentage">3 oy</div><div class="Deposits_rate">Muddati:</div></div>
  </div>
</div>
"""

CARDS_HTML = """
<div class="checkoutEasy">
  <div class="checkoutEasy__img"></div>
  <div class="checkoutEasy__text">
    <div class="checkoutEasy__title"><a href="/uz/individuals/bank-cards/visa-infinite-uz/"><b>Visa Infinite</b></a></div>
    <p>
      Abonent to'lovi: <b>6 AQSh dollari</b><br/>
      Karta chiqarish : <b>600 000 so'mdan</b><br/>
      O'zgarmaydigan qoldiq: <b>50 AQSh dollari</b>
    </p>
    <div class="buttonLined"><a href="/uz/individuals/bank-cards/visa-infinite-uz/">Batafsil</a></div>
  </div>
</div>
"""

CREDITS_HTML = """
<div class="checkoutEasy">
  <div class="credit__info">
    <div class="checkoutEasy__title"><a href="/uz/individuals/credits/oson-uz/">Oson kredit</a></div>
    <div class="credit__info__item"><div class="credit-values-name">Kredit miqdori</div><span class="credit-values">100 million so'm</span></div>
    <div class="credit__info__item"><div class="credit-values-name">Yillik foiz stavkasi</div><span class="credit-values">26,9 % dan</span></div>
  </div>
  <div class="checkoutEasy__btn"><a href="/uz/individuals/credits/oson-uz/">Batafsil</a></div>
</div>
"""


def test_parse_deposits_skips_howto_card_and_extracts_fields():
    records = parse_checkout_cards(DEPOSITS_HTML)

    assert len(records) == 1  # "SQB Mobile" qo'llanma kartasi mahsulot emas
    assert records[0] == {
        "name": "Imkoniyat-2",
        "source": "sqb.uz",
        "Foiz:": "24 %",
        "Muddati:": "3 oy",
        "url": "https://sqb.uz/uz/individuals/deposits/imkoniyat-2-uz/",
    }


def test_parse_cards_falls_back_to_label_bold_value_pairs():
    records = parse_checkout_cards(CARDS_HTML)

    assert len(records) == 1
    assert records[0] == {
        "name": "Visa Infinite",
        "source": "sqb.uz",
        "Abonent to'lovi": "6 AQSh dollari",
        "Karta chiqarish": "600 000 so'mdan",
        "O'zgarmaydigan qoldiq": "50 AQSh dollari",
        "url": "https://sqb.uz/uz/individuals/bank-cards/visa-infinite-uz/",
    }


def test_parse_credits_extracts_label_value_pairs():
    records = parse_checkout_cards(CREDITS_HTML)

    assert len(records) == 1
    assert records[0]["name"] == "Oson kredit"
    assert records[0]["Kredit miqdori"] == "100 million so'm"
    assert records[0]["Yillik foiz stavkasi"] == "26,9 % dan"
    assert records[0]["url"] == "https://sqb.uz/uz/individuals/credits/oson-uz/"


def test_connector_uses_individual_segment_and_sqb_bank_code():
    connector = SQBConnector("deposit", "https://example.test/deposits")

    assert connector.segment == "individual"
    assert connector.bank_code == "SQB"
    assert connector.product_type == "deposit"


# API'da bir nechta kanal bor ("offline"/"online"/"atm"/"juridic") — faqat
# "offline" (filial) olinishi kerak. Qiymatlar tiyinda keladi (100'ga
# bo'linadi). RUB "buy": 0 — hozircha xarid qilinmayapti, o'tkazib
# yuborilishi kerak.
EXCHANGE_PAYLOAD = {
    "data": {
        "offline": [
            {"code": "USD", "buy": 1174000, "sell": 1185000},
            {"code": "RUB", "buy": 0, "sell": 13900},
        ],
        "online": [
            {"code": "USD", "buy": 1176000, "sell": 1184000},
        ],
    },
    "success": True,
}


def test_parse_exchange_rates_reads_only_offline_channel_and_divides_by_100():
    records = parse_exchange_rates(EXCHANGE_PAYLOAD, url="https://sqb.uz/uz/individuals/exchange-money/")
    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11740.0, "source": "sqb.uz", "url": "https://sqb.uz/uz/individuals/exchange-money/"},
        {"code": "USD", "side": "Sotish", "rate": 11850.0, "source": "sqb.uz", "url": "https://sqb.uz/uz/individuals/exchange-money/"},
    ]


def test_parse_exchange_rates_returns_empty_without_offline_data():
    assert parse_exchange_rates({"data": {}}) == []


def test_exchange_connector_uses_currency_product_type_and_sqb_bank_code():
    connector = SQBExchangeConnector()
    assert connector.bank_code == "SQB"
    assert connector.product_type == "currency"
    assert connector.url == "https://sqb.uz/uz/individuals/exchange-money/"
