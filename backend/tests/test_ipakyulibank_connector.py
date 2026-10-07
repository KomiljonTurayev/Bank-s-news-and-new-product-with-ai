import json

from app.connectors.ipakyulibank import (
    IpakYuliBankConnector,
    IpakYuliExchangeConnector,
    parse_exchange_rates,
    parse_products,
)

# Haqiqiy sahifadan olingan soddalashtirilgan misol — "product-card-title-and-content"
# tashqi o'ramini ataylab saqlab qoldik, chunki u ham sarlavha (<h2>), ham
# statistika qiymatlarini ichiga oladi va aynan shu sabab dastlabki versiyada
# mahsulot nomi xato ravishda "label: value" juftligi sifatida ham qo'shilib
# qolayotgan edi.
DEPOSITS_HTML = """
<div data-test="product-card-container">
  <div data-test="product-card-title-and-content">
    <div>
      <h2 data-test="product-card-title">"Oddiy-18" omonati</h2>
      <div data-test="product-card-subtitle">Ishonchli daromad</div>
    </div>
    <div data-test="product-card-content-list">
      <div data-test="product-card-first-content">
        <div data-test="product-card-first-content-title">Yillik stavka</div>
        <div data-test="product-card-first-content-value">18%</div>
      </div>
      <div data-test="product-card-second-content">
        <div data-test="product-card-second-content-title">Muddat</div>
        <div data-test="product-card-second-content-value">24 oy</div>
      </div>
    </div>
  </div>
  <div data-test="product-card-buttons">
    <div data-test="product-card-additional-link"><a href="/physical/omonatlar/somli-omonatlar/oddiy-18-omonati">Batafsil</a></div>
  </div>
</div>
"""


def test_parse_products_does_not_leak_the_title_as_a_stat_pair():
    records = parse_products(DEPOSITS_HTML)
    assert records[0] == {
        "name": '"Oddiy-18" omonati',
        "source": "ipakyulibank.uz",
        "Yillik stavka": "18%",
        "Muddat": "24 oy",
        "url": "https://ipakyulibank.uz/physical/omonatlar/somli-omonatlar/oddiy-18-omonati",
    }


def test_connector_uses_ipakyuli_bank_code_and_individual_segment():
    connector = IpakYuliBankConnector("deposit", "https://ipakyulibank.uz/physical/omonatlar")
    assert connector.bank_code == "IPAKYULI"
    assert connector.segment == "individual"
    assert connector.product_type == "deposit"


class _NuxtPayloadBuilder:
    """Nuxt 3'ning "devalue" formatidagi tekis massivni qo'lda qurish
    uchun yordamchi — har bir ``add()`` chaqiruvi qiymatni massivga
    qo'shadi va uning indeksini qaytaradi, shu indeks boshqa
    dict/list'lar ichida "havola" sifatida ishlatiladi (haqiqiy
    sahifadagi kabi)."""

    def __init__(self):
        self.items = []

    def add(self, value):
        self.items.append(value)
        return len(self.items) - 1

    def add_currency_tab(self, name, is_active, currencies):
        currency_refs = []
        for code_name, buy, sell in currencies:
            rate_ref = self.add({"buy": self.add(buy), "sell": self.add(sell), "cb": self.add(buy)})
            currency_refs.append(
                self.add(
                    {
                        "id": self.add(1),
                        "name": self.add(code_name),
                        "code": self.add("000"),
                        "code_name": self.add(code_name),
                        "symbol": self.add("$"),
                        "rate": rate_ref,
                    }
                )
            )
        return self.add(
            {
                "name": self.add(name),
                "isActiveTab": self.add(is_active),
                "frontComponentName": self.add("CurrencyTable"),
                "contentType": self.add("list"),
                "varName": self.add("rates"),
                "rates": self.add(currency_refs),
                "lastUpdated": self.add(1788981001),
                "id": self.add(0),
            }
        )


def _nuxt_html(items: list) -> str:
    return f'<html><body><script id="__NUXT_DATA__" type="application/json">{json.dumps(items)}</script></body></html>'


def test_parse_exchange_rates_resolves_devalue_refs_and_scales_by_100():
    builder = _NuxtPayloadBuilder()
    # Faol bo'lmagan tab ataylab OLDIN qo'shiladi — parser birinchi
    # topilgan emas, faqat ``isActiveTab`` true bo'lganini olishi kerak.
    builder.add_currency_tab("Bankomatda", False, [("USD", 1170000, 1190000)])
    builder.add_currency_tab("Kassada", True, [("USD", 1176000, 1187000), ("EUR", 1320000, 1376000)])

    records = parse_exchange_rates(
        _nuxt_html(builder.items), url="https://ipakyulibank.uz/physical/valyuta-ayirboshlash"
    )

    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11760.0, "source": "ipakyulibank.uz", "url": "https://ipakyulibank.uz/physical/valyuta-ayirboshlash"},
        {"code": "USD", "side": "Sotish", "rate": 11870.0, "source": "ipakyulibank.uz", "url": "https://ipakyulibank.uz/physical/valyuta-ayirboshlash"},
        {"code": "EUR", "side": "Olish", "rate": 13200.0, "source": "ipakyulibank.uz", "url": "https://ipakyulibank.uz/physical/valyuta-ayirboshlash"},
        {"code": "EUR", "side": "Sotish", "rate": 13760.0, "source": "ipakyulibank.uz", "url": "https://ipakyulibank.uz/physical/valyuta-ayirboshlash"},
    ]


def test_parse_exchange_rates_returns_empty_without_nuxt_data_script():
    assert parse_exchange_rates("<html><body>no data here</body></html>") == []


def test_parse_exchange_rates_returns_empty_when_no_tab_is_active():
    builder = _NuxtPayloadBuilder()
    builder.add_currency_tab("Kassada", False, [("USD", 1176000, 1187000)])
    assert parse_exchange_rates(_nuxt_html(builder.items)) == []


def test_exchange_connector_uses_currency_product_type():
    connector = IpakYuliExchangeConnector()
    assert connector.bank_code == "IPAKYULI"
    assert connector.product_type == "currency"
    assert connector.url == "https://ipakyulibank.uz/physical/valyuta-ayirboshlash"
