from app.connectors.hamkorbank import (
    HamkorbankConnector,
    HamkorbankExchangeConnector,
    parse_credit_cards,
    parse_deposit_cards,
    parse_exchange_rates,
)

DEPOSIT_HTML = """
<div id="catalog-deposit-list">
  <div class="rounded-2xl bg-white p-5 md:rounded-20 md:p-8 relative flex min-h-93 flex-col overflow-hidden">
    <h3 class="text-h3 font-montserrat mb-2">Erkin Dollar</h3>
    <div class="border-gray-light flex w-full flex-row-reverse items-center justify-between border-b pb-[11px]">
      <div class="text-body-l relative font-medium md:mb-2">5,5%</div>
      <div class="text-body-s text-secondary"><p>Yillik foiz stavkasi</p></div>
    </div>
    <div class="border-gray-light flex w-full flex-row-reverse items-center justify-between border-b pb-[11px]">
      <div class="text-body-l relative font-medium md:mb-2">15 oy</div>
      <div class="text-body-s text-secondary"><p>Omonat muddati</p></div>
    </div>
    <a href="/uz/physical/deposits/erkin-dollar/">Batafsil</a>
  </div>
  <div class="rounded-2xl bg-white p-5 md:rounded-20 md:p-8 relative flex min-h-93 flex-col overflow-hidden">
    <div class="text-h3">Mobil ilova orqali oching</div>
  </div>
</div>
"""

CREDIT_HTML = """
<div id="mse2_results">
  <div class="flex flex-col bg-white rounded-20 p-32 min-h-332 relative overflow-hidden">
    <h3 class="mb-20">Onlayn kredit</h3>
    <div class="px-20 w-1-3 sm--px-0 sm--w-full sm--py-8">
      <div class="font-medium mb-8 text-size-l sm--mb-4">100 mln so'mgacha</div>
      <div class="text-size-s text-gray sm--pl-14"><p>Onlayn krediti miqdori</p></div>
    </div>
    <div class="px-20 w-1-3 sm--px-0 sm--w-full sm--py-8">
      <div class="font-medium mb-8 text-size-l sm--mb-4">23% dan boshlab</div>
      <div class="text-size-s text-gray sm--pl-14"><p>Foiz stavkasi</p></div>
    </div>
    <a href="/uz/physical/credits/online-credit/#product_form"><span>Ariza qoldirish</span></a>
    <a href="/uz/physical/credits/online-credit/"><span>Batafsil</span></a>
  </div>
</div>
"""


def test_parse_deposit_cards_skips_titleless_card_and_extracts_fields():
    records = parse_deposit_cards(DEPOSIT_HTML)

    assert len(records) == 1  # "Mobil ilova" kartasida h3 yo'q
    assert records[0] == {
        "name": "Erkin Dollar",
        "source": "hamkorbank.uz",
        "Yillik foiz stavkasi": "5,5%",
        "Omonat muddati": "15 oy",
        "url": "https://hamkorbank.uz/uz/physical/deposits/erkin-dollar/",
    }


def test_parse_credit_cards_prefers_batafsil_link_over_ariza_link():
    records = parse_credit_cards(CREDIT_HTML)

    assert len(records) == 1
    assert records[0]["name"] == "Onlayn kredit"
    assert records[0]["Foiz stavkasi"] == "23% dan boshlab"
    assert records[0]["url"] == "https://hamkorbank.uz/uz/physical/credits/online-credit/"


def test_connector_uses_individual_segment_and_hamkor_bank_code():
    connector = HamkorbankConnector("deposit", "https://hamkorbank.uz/uz/physical/deposits/")

    assert connector.segment == "individual"
    assert connector.bank_code == "HAMKOR"
    assert connector.product_type == "deposit"


# API'da har valyuta uchun bir nechta yozuv bo'ladi: turli kanal
# (destination_code) va miqdor chegarasi (begin_sum_i) bo'yicha. Faqat
# asosiy filial kanali ("2") va chegarasiz ("begin_sum_i": 0) yozuv
# olinishi kerak; boshqalari (kanal "7", yoki 1 mlndan yuqori chegara)
# o'tkazib yuborilishi kerak. Stavkalar tiyinda keladi (100'ga bo'linadi).
EXCHANGE_JSON = {
    "data": [
        {"destination_code": "2", "currency_char": "USD", "begin_sum_i": 0, "buying_rate": 1174000, "selling_rate": 1185000},
        {"destination_code": "2", "currency_char": "USD", "begin_sum_i": 1000000, "buying_rate": 1175000, "selling_rate": 1184000},
        {"destination_code": "7", "currency_char": "USD", "begin_sum_i": 0, "buying_rate": 1175000, "selling_rate": 1184000},
        {"destination_code": "2", "currency_char": "RUB", "begin_sum_i": 0, "buying_rate": 8900, "selling_rate": 13500},
    ]
}


def test_parse_exchange_rates_keeps_only_primary_channel_and_no_minimum_tier():
    records = parse_exchange_rates(EXCHANGE_JSON, url="https://hamkorbank.uz/uz/physical/currency-exchange-offices/")
    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11740.0, "source": "hamkorbank.uz", "url": "https://hamkorbank.uz/uz/physical/currency-exchange-offices/"},
        {"code": "USD", "side": "Sotish", "rate": 11850.0, "source": "hamkorbank.uz", "url": "https://hamkorbank.uz/uz/physical/currency-exchange-offices/"},
        {"code": "RUB", "side": "Olish", "rate": 89.0, "source": "hamkorbank.uz", "url": "https://hamkorbank.uz/uz/physical/currency-exchange-offices/"},
        {"code": "RUB", "side": "Sotish", "rate": 135.0, "source": "hamkorbank.uz", "url": "https://hamkorbank.uz/uz/physical/currency-exchange-offices/"},
    ]


def test_parse_exchange_rates_returns_empty_without_data():
    assert parse_exchange_rates({}) == []


def test_exchange_connector_uses_currency_product_type_and_offices_url():
    connector = HamkorbankExchangeConnector()
    assert connector.bank_code == "HAMKOR"
    assert connector.product_type == "currency"
    assert connector.url == "https://hamkorbank.uz/uz/physical/currency-exchange-offices/"
