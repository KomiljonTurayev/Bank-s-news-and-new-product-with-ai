from app.connectors.universalbank import (
    UniversalbankConnector,
    UniversalbankExchangeConnector,
    parse_cards,
    parse_exchange_rates,
)

DEPOSIT_HTML = """
<a href="/deposit/poydevor" class="deposit__card">
  <div class="deposit__card-content">
    <div class="deposit__card-title">Poydevor</div>
    <div class="deposit__card-list"><ul>
      <li><p>14%</p><span>Foiz stavkasi</span></li>
      <li><p>12 oy</p><span>Muddat</span></li>
    </ul></div>
  </div>
</a>
"""

CREDIT_HTML = """
<a href="/credit/ipoteka" class="credit__card">
  <div class="credit__card-content">
    <div class="credit__card-title">Ipoteka</div>
    <div class="credit__card-list"><ul>
      <li><p>24%</p><span>Foiz</span></li>
      <li><span>Kredit summasi</span><p>3000000000</p></li>
    </ul></div>
  </div>
</a>
"""

# Kartalar sahifasi boshqa CSS prefiks ("cards", "deposit"/"credit" emas)
# va maydon konteyneri ishlatadi (".cards__card-fees-item", "ul li" emas)
# — ikkalasi ham <p>/<span> juftligi bo'lsa-da.
CARDS_HTML = """
<a href="/cards/humo" class="cards__card">
  <div class="cards__card-content">
    <div class="cards__card-title">HUMO</div>
    <div class="cards__card-fees">
      <div class="cards__card-fees-item"><p>BHM 5%</p><span>Karta chiqarish</span></div>
      <div class="cards__card-fees-item"><p>BEPUL</p><span>Kartaga xizmat ko'rsatish</span></div>
    </div>
  </div>
</a>
"""


def test_parse_cards_normal_order():
    records = parse_cards(DEPOSIT_HTML, "deposit")
    assert records[0] == {
        "name": "Poydevor",
        "source": "universalbank.uz",
        "Foiz stavkasi": "14%",
        "Muddat": "12 oy",
        "url": "https://universalbank.uz/deposit/poydevor",
    }


def test_parse_cards_fixes_reversed_p_span_order():
    records = parse_cards(CREDIT_HTML, "credit")
    assert records[0]["Foiz"] == "24%"
    assert records[0]["Kredit summasi"] == "3000000000"


def test_parse_cards_handles_cards_prefix_fees_item_layout():
    records = parse_cards(CARDS_HTML, "cards")
    assert records[0] == {
        "name": "HUMO",
        "source": "universalbank.uz",
        "Karta chiqarish": "BHM 5%",
        "Kartaga xizmat ko'rsatish": "BEPUL",
        "url": "https://universalbank.uz/cards/humo",
    }


def test_connector_uses_individual_segment_and_universal_bank_code():
    connector = UniversalbankConnector("deposit", "https://universalbank.uz/uz/deposit")
    assert connector.segment == "individual"
    assert connector.bank_code == "UNIVERSAL"


def test_connector_uses_cards_prefix_for_card_product_type():
    connector = UniversalbankConnector("card", "https://universalbank.uz/uz/cards")
    assert connector._prefix == "cards"


# Sayt ISO 4217 raqamli kod bilan qaytaradi ("840" = USD, "643" = RUB).
# RUB'da "hasBuyingRate": False — bank hozircha xarid qilmayapti, o'tkazib
# yuborilishi kerak.
EXCHANGE_JSON = {
    "result": {"successful": True, "error": None},
    "items": [
        {
            "code": "840", "buyingRate": "11810.00", "hasBuyingRate": True,
            "sellingRate": "11870.00", "hasSellingRate": True,
        },
        {
            "code": "643", "buyingRate": "0.00", "hasBuyingRate": False,
            "sellingRate": "137.00", "hasSellingRate": True,
        },
        {
            "code": "999", "buyingRate": "1.00", "hasBuyingRate": True,
            "sellingRate": "2.00", "hasSellingRate": True,
        },
    ],
}


def test_parse_exchange_rates_maps_numeric_code_and_skips_incomplete_rates():
    records = parse_exchange_rates(EXCHANGE_JSON, url="https://universalbank.uz/uz/currency")
    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11810.0, "source": "universalbank.uz", "url": "https://universalbank.uz/uz/currency"},
        {"code": "USD", "side": "Sotish", "rate": 11870.0, "source": "universalbank.uz", "url": "https://universalbank.uz/uz/currency"},
    ]


def test_parse_exchange_rates_returns_empty_without_items():
    assert parse_exchange_rates({}) == []


def test_exchange_connector_uses_currency_product_type_and_api_url():
    connector = UniversalbankExchangeConnector()
    assert connector.bank_code == "UNIVERSAL"
    assert connector.product_type == "currency"
    assert connector.url == "https://universalbank.uz/uz/currency"
