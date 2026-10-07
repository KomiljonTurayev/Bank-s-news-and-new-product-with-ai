from app.connectors.ziraatbank import ZiraatBankConnector, parse_credit_page, parse_deposit_page

DEPOSIT_PAGE_HTML = """
<div class="sub-page-content">
  <p><strong>Jismoniy shaxslar uchun milliy valyutadagi muddatli omonatlar</strong></p>
  <h2>FOYDA (VIII) &ndash; 6 (S78)</h2>
  <div class="table"><table>
    <tr><td>Foiz stavkasi</td><td>Yillik 6%</td></tr>
    <tr><td>Omonat muddati</td><td>3 oy;</td></tr>
    <tr><td>Omonatchi tashabbusi bilan omonat muddatidan avval qaytarib olinganda, foizlar to'lanmaydi;</td><td>&nbsp;</td></tr>
  </table></div>
  <h2>FOYDA (VIII) &ndash; 7 (S79)</h2>
  <div class="table"><table>
    <tr><td>Foiz stavkasi</td><td>Yillik 7%</td></tr>
    <tr><td>Omonat muddati</td><td>6 oy;</td></tr>
  </table></div>
</div>
"""

CREDIT_PAGE_HTML = """
<div class="sub-page-content">
  <table>
    <tr><td colspan="3">Kreditlashning asosiy parametrlari</td></tr>
    <tr><td>1.1.</td><td>Kreditining xususiyatlari</td><td>Muddatli kredit</td></tr>
    <tr><td>1.2.</td><td>Kredit mahsulotining nomlanishi</td><td>Avtokredit</td></tr>
    <tr><td>1.6.</td><td>Muddati</td><td>60 oy</td></tr>
    <tr><td>1.7.</td><td>Foiz stavkasi</td><td>22.5%</td></tr>
  </table>
</div>
"""

NO_NAME_ROW_HTML = """
<div class="sub-page-content">
  <table><tr><td>1.1.</td><td>Muddati</td><td>60 oy</td></tr></table>
</div>
"""

# Ba'zi kredit sahifalarida "nomlanishi" o'rniga "nomi" so'zi ishlatiladi
# ("Kredit mahsulotining nomi") — ikkalasi ham qabul qilinishi kerak.
CREDIT_PAGE_NOMI_VARIANT_HTML = """
<div class="sub-page-content">
  <table>
    <tr><td>2.2.</td><td>Kredit mahsulotining nomi</td><td>&#171;Shinam uy 2.0&#187;</td></tr>
    <tr><td>2.6.</td><td>Kredit muddati</td><td>36 oygacha</td></tr>
  </table>
</div>
"""


def test_parse_deposit_page_splits_by_h2_and_skips_empty_value_rows():
    records = parse_deposit_page(DEPOSIT_PAGE_HTML, "https://ziraatbank.uz/uz/milliy-valyutadagi-omonatlar")
    assert records == [
        {
            "name": "FOYDA (VIII) – 6 (S78)",
            "source": "ziraatbank.uz",
            "url": "https://ziraatbank.uz/uz/milliy-valyutadagi-omonatlar",
            "Foiz stavkasi": "Yillik 6%",
            "Omonat muddati": "3 oy;",
        },
        {
            "name": "FOYDA (VIII) – 7 (S79)",
            "source": "ziraatbank.uz",
            "url": "https://ziraatbank.uz/uz/milliy-valyutadagi-omonatlar",
            "Foiz stavkasi": "Yillik 7%",
            "Omonat muddati": "6 oy;",
        },
    ]


def test_parse_credit_page_takes_name_from_nomlanishi_row_not_h1():
    record = parse_credit_page(CREDIT_PAGE_HTML, "https://ziraatbank.uz/uz/birlamchi-bozor-uchun-avtokredit")
    assert record["name"] == "Avtokredit"
    assert record["Foiz stavkasi"] == "22.5%"
    assert record["Muddati"] == "60 oy"


def test_parse_credit_page_returns_none_without_a_nomlanishi_row():
    assert parse_credit_page(NO_NAME_ROW_HTML, "https://ziraatbank.uz/uz/x") is None


def test_parse_credit_page_accepts_the_nomi_wording_variant():
    record = parse_credit_page(CREDIT_PAGE_NOMI_VARIANT_HTML, "https://ziraatbank.uz/uz/shinam-uy")
    assert record["name"] == "«Shinam uy 2.0»"


def test_connector_uses_ziraat_bank_code_and_individual_segment():
    connector = ZiraatBankConnector("deposit", ["/uz/milliy-valyutadagi-omonatlar"])
    assert connector.bank_code == "ZIRAAT"
    assert connector.segment == "individual"
    assert connector.urls == ["https://ziraatbank.uz/uz/milliy-valyutadagi-omonatlar"]
