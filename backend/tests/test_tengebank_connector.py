from app.connectors.tengebank import TengeBankConnector, parse_table_page

COMPARISON_TABLE_HTML = """
<h1>Muddatli omonatlar</h1>
<div class="content-inner-editer">
  <table>
    <tr><td></td><td><strong>Qulay onlayn</strong></td><td><strong>Muddatli</strong></td></tr>
    <tr><td><strong>Foiz ustamasi (yillik)</strong></td><td>18%</td><td>19%</td></tr>
    <tr><td><strong>Minimal miqdor</strong></td><td>100 000 so'm</td><td>10 000 000 so'm</td></tr>
  </table>
</div>
"""

SINGLE_PRODUCT_TABLE_HTML = """
<h1>Xorijiy valyutada omonat</h1>
<div class="content-inner-editer">
  <table>
    <tr><td><strong>Ustamasi</strong></td><td>Yillik 4%</td></tr>
    <tr><td><strong>Muddati</strong></td><td>6 oy</td></tr>
    <tr><td><strong>Minimal miqdori</strong></td><td>100 AQSh dollari</td></tr>
  </table>
</div>
"""

NO_TABLE_HTML = "<h1>Omonatlar</h1><p>Kategoriya sahifasi, jadval yo'q.</p>"


def test_parse_table_page_splits_comparison_table_into_per_product_records():
    records = parse_table_page(COMPARISON_TABLE_HTML, "https://tengebank.uz/deposit/srochnye-vklady")
    assert records == [
        {
            "name": "Qulay onlayn",
            "source": "tengebank.uz",
            "url": "https://tengebank.uz/deposit/srochnye-vklady",
            "Foiz ustamasi (yillik)": "18%",
            "Minimal miqdor": "100 000 so'm",
        },
        {
            "name": "Muddatli",
            "source": "tengebank.uz",
            "url": "https://tengebank.uz/deposit/srochnye-vklady",
            "Foiz ustamasi (yillik)": "19%",
            "Minimal miqdor": "10 000 000 so'm",
        },
    ]


def test_parse_table_page_reads_single_product_key_value_table():
    records = parse_table_page(SINGLE_PRODUCT_TABLE_HTML, "https://tengebank.uz/deposit/vklad-v-inostrannoj-valyute")
    assert records == [
        {
            "name": "Xorijiy valyutada omonat",
            "source": "tengebank.uz",
            "url": "https://tengebank.uz/deposit/vklad-v-inostrannoj-valyute",
            "Ustamasi": "Yillik 4%",
            "Muddati": "6 oy",
            "Minimal miqdori": "100 AQSh dollari",
        }
    ]


def test_parse_table_page_returns_empty_list_when_no_table():
    assert parse_table_page(NO_TABLE_HTML, "https://tengebank.uz/deposits") == []


def test_connector_builds_full_urls_and_bank_code():
    connector = TengeBankConnector("deposit", ["/deposit/srochnye-vklady"])
    assert connector.urls == ["https://tengebank.uz/deposit/srochnye-vklady"]
    assert connector.bank_code == "TENGEBANK"
    assert connector.segment == "individual"
