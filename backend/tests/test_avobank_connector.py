import json

from app.connectors.avobank import (
    AvobankConnector,
    AvobankCreditCardConnector,
    parse_credit_card_page,
    parse_deposit_page,
)

DEPOSIT_PAGE_HTML = """
<h1>AVO omonati</h1>
<dl class="SliceContent_rows__TsmDC">
  <div class="SliceContent_row__L_Oka">
    <dt class="SliceContent_row_label__rmsbk"><span>Muddati</span></dt>
    <dd><p>12 oy</p></dd>
  </div>
  <div class="SliceContent_row__L_Oka">
    <dt class="SliceContent_row_label__rmsbk"><span>Daromadlilik</span></dt>
    <dd><p>yillik 22% gacha</p></dd>
  </div>
  <div class="SliceContent_row__L_Oka">
    <dt class="SliceContent_row_label__rmsbk"><span>Bazaviy stavka</span></dt>
    <dd><p>yillik 20,05%</p></dd>
  </div>
</dl>
"""

NO_DL_HTML = "<h1>Shaxsiy ehtiyojlaringiz uchun onlayn kredit</h1><p>Akkordion ichida, statik HTML'da bo'sh</p>"

# Ba'zi sahifalarda h1 bir necha qatorli reklama sarlavhasi bo'ladi
# ("AVO omonati — yillik 22% gacha daromadlilik", <br/> bilan bo'lingan) —
# faqat "—"dan oldingi qismi haqiqiy mahsulot nomi.
MULTILINE_TITLE_HTML = """
<h1>AVO omonati &mdash;<br/>yillik 22% gacha<br/>daromadlilik</h1>
<dl class="SliceContent_rows__TsmDC">
  <div class="SliceContent_row__L_Oka">
    <dt class="SliceContent_row_label__rmsbk"><span>Muddati</span></dt>
    <dd><p>12 oy</p></dd>
  </div>
  <div class="SliceContent_row__L_Oka">
    <dt class="SliceContent_row_label__rmsbk"><span>Minimal to'ldirish\nsummasi</span></dt>
    <dd><p>1 000 so'm</p></dd>
  </div>
</dl>
"""


def test_parse_deposit_page_extracts_definition_list_rows():
    record = parse_deposit_page(DEPOSIT_PAGE_HTML, "https://avobank.uz/uz/products/deposits")
    assert record == {
        "name": "AVO omonati",
        "source": "avobank.uz",
        "url": "https://avobank.uz/uz/products/deposits",
        "Muddati": "12 oy",
        "Daromadlilik": "yillik 22% gacha",
        "Bazaviy stavka": "yillik 20,05%",
    }


def test_parse_deposit_page_takes_name_before_the_dash_in_a_multiline_title():
    record = parse_deposit_page(MULTILINE_TITLE_HTML, "https://avobank.uz/uz/products/deposits")
    assert record["name"] == "AVO omonati"
    assert record["Minimal to'ldirish summasi"] == "1 000 so'm"


def test_parse_deposit_page_returns_none_without_rows():
    assert parse_deposit_page(NO_DL_HTML, "https://avobank.uz/uz/products/personal-loan") is None


def test_connector_uses_avobank_code_and_deposit_type():
    connector = AvobankConnector(["/uz/products/deposits"])
    assert connector.bank_code == "AVOBANK"
    assert connector.product_type == "deposit"
    assert connector.urls == ["https://avobank.uz/uz/products/deposits"]


# Kredit karta sahifasi omonat sahifalaridan farqli — akkordion ichida JS
# bilan to'ldiriladigan bo'sh HTML o'rniga, ``<script type="application/
# ld+json">`` ichida schema.org "CreditCard" strukturasi bor.
CREDIT_CARD_LD_JSON = {
    "@context": "https://schema.org",
    "@type": ["Product", "CreditCard"],
    "name": "AVO platinum kredit kartasi",
    "annualPercentageRate": 27.9,
    "amount": {"@type": "MonetaryAmount", "minValue": 100000, "maxValue": 100000000, "currency": "UZS"},
}
CREDIT_CARD_HTML = (
    '<html><head><script type="application/ld+json">'
    + json.dumps(CREDIT_CARD_LD_JSON)
    + "</script></head><body></body></html>"
)


def test_parse_credit_card_page_extracts_rate_and_limit_from_json_ld():
    record = parse_credit_card_page(CREDIT_CARD_HTML, "https://avobank.uz/uz/products/credit-card")
    assert record == {
        "name": "AVO platinum kredit kartasi",
        "source": "avobank.uz",
        "url": "https://avobank.uz/uz/products/credit-card",
        "Yillik foiz stavkasi": "27.9%",
        "Kredit limiti": "100 000 - 100 000 000 so'm",
    }


def test_parse_credit_card_page_returns_none_without_json_ld_script():
    assert parse_credit_card_page("<html><body><h1>No structured data</h1></body></html>") is None


def test_credit_card_connector_uses_avobank_code_and_card_type():
    connector = AvobankCreditCardConnector()
    assert connector.bank_code == "AVOBANK"
    assert connector.product_type == "card"
    assert connector.url == "https://avobank.uz/uz/products/credit-card"
