from app.connectors.uzse import UzseBondConnector, parse_bonds

# Haqiqiy sahifaning soddalashtirilgan nusxasi — bitta emitentning bir
# nechta obligatsiyasi (turli tiker/muddat) alohida qatorlarda keladi.
BONDS_HTML = """
<table>
  <tr><th>#</th><th>Emitent</th><th>Tiker</th><th>ISIN</th><th>Nominal</th><th>Miqdor</th><th>Hajm</th><th>Kupon</th><th>Ro'yxatga olingan</th><th>Muddat</th><th>Holati</th></tr>
  <tr>
    <td>1</td><td>AGAT CREDIT AJ MMT</td><td>ACMT1B3</td><td>UZ6058977AC4</td>
    <td>100,000</td><td>400,000</td><td>40,0млрд</td><td>27,0%</td>
    <td>07.11.2025</td><td>11.11.2026</td><td>Muddati yaqin</td>
  </tr>
  <tr>
    <td>2</td><td>AGAT CREDIT AJ MMT</td><td>ACMT2B4</td><td>UZ6058977AD2</td>
    <td>100,000</td><td>400,000</td><td>40,0млрд</td><td>26,0%</td>
    <td>16.01.2026</td><td>17.01.2028</td><td>Muomalada</td>
  </tr>
  <tr>
    <td>3</td><td>Kapitalbank ATB</td><td>KAPB1B</td><td>UZ0000000000</td>
    <td>500,000</td><td>100,000</td><td>50,0млрд</td><td>20,0%</td>
    <td>01.01.2026</td><td>01.01.2029</td><td>Muomalada</td>
  </tr>
</table>
"""

EMPTY_HTML = "<html><body>no table here</body></html>"


def test_parse_bonds_extracts_all_fields_and_resolves_bank_code():
    # "AGAT CREDIT AJ MMT" -> AGATCREDITMMTMCHJ faqat app/banks.py'dagi
    # qo'lda qo'shilgan alias orqali (oddiy slugify o'zi "AGATCREDITAJMMT"
    # berardi) — depozit.uz'dan kelgan eski kod bilan bog'lash uchun.
    records = parse_bonds(BONDS_HTML, url="https://uzse.uz/bonds2?locale=uz")
    assert len(records) == 3
    assert records[0] == {
        "_bank_code": "AGATCREDITMMTMCHJ",
        "bank_name": "AGAT CREDIT AJ MMT",
        "name": "ACMT1B3",
        "source": "uzse.uz",
        "ISIN": "UZ6058977AC4",
        "Nominal qiymati": "100,000",
        "Miqdori": "400,000",
        "Emissiya hajmi": "40,0млрд",
        "Kupon stavkasi": "27,0%",
        "Ro'yxatga olingan sana": "07.11.2025",
        "To'lov muddati": "11.11.2026",
        "Holati": "Muddati yaqin",
        "url": "https://uzse.uz/bonds2?locale=uz",
    }


def test_parse_bonds_keeps_multiple_bonds_from_the_same_issuer_distinct():
    records = parse_bonds(BONDS_HTML)
    agat_bonds = [r for r in records if r["_bank_code"] == "AGATCREDITMMTMCHJ"]
    assert len(agat_bonds) == 2
    assert {r["name"] for r in agat_bonds} == {"ACMT1B3", "ACMT2B4"}


def test_parse_bonds_resolves_known_bank_via_alias():
    # "Kapitalbank ATB" resolve_bank_code() orqali mavjud "KDB" kodiga
    # to'g'ri keladi — bond ma'lumoti allaqachon tanish bankka biriktiriladi.
    records = parse_bonds(BONDS_HTML)
    kapital = next(r for r in records if r["name"] == "KAPB1B")
    assert kapital["_bank_code"] == "KDB"


def test_parse_bonds_returns_empty_without_a_table():
    assert parse_bonds(EMPTY_HTML) == []


def test_connector_config():
    connector = UzseBondConnector()
    assert connector.bank_code == "AGGREGATED"
    assert connector.product_type == "investment"
    assert connector.segment == "individual"
    assert connector.url == "https://uzse.uz/bonds2?locale=uz"
