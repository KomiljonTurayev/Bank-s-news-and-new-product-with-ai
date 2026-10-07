from app.connectors.depozit_tables import (
    DepozitBondConnector,
    DepozitCreditCardConnector,
    DepozitDebitCardConnector,
    parse_bonds,
    parse_credit_cards,
    parse_debit_cards,
)

CREDIT_CARD_HTML = """
<table>
<tr><td></td><td>Bank nomi</td><td>Maksimal summa</td><td>Foiz stavkasi</td><td>Muddat</td><td>Imtiyozli davr</td><td>Mijozlar</td></tr>
<tr>
    <td>1</td>
    <td><strong>Agrobank</strong></td>
    <td>50 mln. so'm</td>
    <td>27.99%</td>
    <td>4 yil</td>
    <td>2 yil</td>
    <td>Barcha jismoniy shaxslar</td>
</tr>
<tr>
    <td>2</td>
    <td><p><strong>Asia Alliance bank</strong></p><p><strong>Qulay Hamyon kredit kartasi</strong></p></td>
    <td>50 mln. so'm</td>
    <td>36%</td>
    <td>3 yil</td>
    <td>2 yil</td>
    <td>Barcha jismoniy shaxslar</td>
</tr>
</table>
"""

DEBIT_CARD_HTML = """
<table>
<tr><td></td><td>Bank</td><td>Karta turi</td><td>Ochish narxi</td><td>Minimal qoldiq</td></tr>
<tr>
    <td rowspan="2"><strong>1.</strong></td>
    <td rowspan="2"><strong>O'zmilliybank</strong></td>
    <td>Visa Infinite</td>
    <td>5 000 000</td>
    <td>200 USD</td>
</tr>
<tr>
    <td>Visa Platinum</td>
    <td>270 000</td>
    <td>100 USD</td>
</tr>
</table>
"""

BOND_HTML = """
<table>
<tr><td>Chiqaruvchi</td><td>Foiz</td><td>Narxi</td><td>Nominal</td><td>Muddati</td><td></td></tr>
<tr><td>Kapitalbank ATB</td><td>19%</td><td>1,000,000 so'm</td><td>1,000,000 so'm</td><td>21.05.2027</td><td>Sotib olish</td></tr>
</table>
"""


def test_parse_credit_cards_splits_bank_and_card_name():
    records = parse_credit_cards(CREDIT_CARD_HTML)

    assert len(records) == 2
    assert records[0] == {
        "_bank_code": "AGRO",
        "bank_name": "Agrobank",
        "name": "Kredit karta",
        "source": "depozit.uz",
        "category": "Kredit karta",
        "Maksimal summa": "50 mln. so'm",
        "Foiz stavkasi": "27.99%",
        "Muddat": "4 yil",
        "Imtiyozli davr": "2 yil",
    }
    assert records[1]["bank_name"] == "Asia Alliance bank"
    assert records[1]["name"] == "Qulay Hamyon kredit kartasi"


def test_parse_debit_cards_carries_bank_name_across_rowspan_rows():
    records = parse_debit_cards(DEBIT_CARD_HTML)

    assert len(records) == 2
    assert all(r["bank_name"] == "O'zmilliybank" for r in records)
    assert records[0]["name"] == "Visa Infinite"
    assert records[1]["name"] == "Visa Platinum"
    assert records[1]["Ochish narxi"] == "270 000"


def test_parse_bonds_extracts_issuer_and_terms():
    records = parse_bonds(BOND_HTML)

    assert records == [{
        "_bank_code": "KDB",
        "bank_name": "Kapitalbank ATB",
        "name": "Obligatsiya",
        "source": "depozit.uz",
        "Foiz stavkasi": "19%",
        "Joriy narxi": "1,000,000 so'm",
        "Nominal qiymati": "1,000,000 so'm",
        "Muddati": "21.05.2027",
    }]


def test_connectors_expose_expected_product_type():
    assert DepozitCreditCardConnector().product_type == "card"
    assert DepozitDebitCardConnector().product_type == "card"
    assert DepozitBondConnector().product_type == "investment"


def test_connector_parse_tags_records_with_listing_page_url():
    records = DepozitCreditCardConnector().parse(CREDIT_CARD_HTML)
    assert all(r["url"] == "https://depozit.uz/cards/credit" for r in records)
