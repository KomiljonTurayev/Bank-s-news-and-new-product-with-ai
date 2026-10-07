from app.connectors.depozit_uz import DepozitUzConnector, parse_content_rows

DEPOSIT_HTML = """
<html><body>
<div class="content-row mainContent">
    <div class="image-box"><img src="/logo.png" alt="Anor Bank"></div>
    <div class="deposit-name"><div class="title"><a href="#">"BARQAROR"</a></div></div>
    <div class="content"><div class="title">Foiz</div><div class="value">22%</div></div>
    <div class="content"><div class="title">Minimal summa</div><div class="value">1,000,000 So'm</div></div>
    <div class="content"><div class="title">Muddat</div><div class="value">24 oy</div></div>
</div>
<div class="content-row mainContent">
    <div class="image-box"><img src="/logo2.png" alt="Kapitalbank"></div>
    <div class="deposit-name"><div class="title"><a href="#">"Kapital Ziynat"</a></div></div>
    <div class="content"><div class="title">Foiz</div><div class="value">18%</div></div>
    <div class="content"><div class="title">Muddat</div><div class="value">25 oy</div></div>
</div>
<div class="content-row mainContent">
    <div class="image-box"><img src="/logo3.png" alt=""></div>
    <div class="deposit-name"><div class="title"><a href="#">"Nomsiz bank mahsuloti"</a></div></div>
    <div class="content"><div class="title">Foiz</div><div class="value">10%</div></div>
</div>
</body></html>
"""


def test_parse_extracts_bank_name_and_fields():
    records = parse_content_rows(DEPOSIT_HTML, "deposit-name", source="depozit.uz")

    assert len(records) == 2  # bank nomi bo'sh bo'lgan uchinchi blok o'tkazib yuboriladi
    assert records[0] == {
        "_bank_code": "ANOR",
        "bank_name": "Anor Bank",
        "name": "BARQAROR",
        "source": "depozit.uz",
        "Foiz": "22%",
        "Minimal summa": "1,000,000 So'm",
        "Muddat": "24 oy",
    }
    assert records[1]["_bank_code"] == "KDB"
    assert records[1]["name"] == "Kapital Ziynat"


def test_connector_parse_tags_category():
    connector = DepozitUzConnector("credit", "https://example.test/credits", "deposit-name", category="Ipoteka")

    records = connector.parse(DEPOSIT_HTML)

    assert all(r["category"] == "Ipoteka" for r in records)


def test_parse_skips_blocks_missing_bank_or_name():
    html = '<div class="content-row mainContent"><div class="content"><div class="title">Foiz</div><div class="value">10%</div></div></div>'
    assert parse_content_rows(html, "deposit-name", source="depozit.uz") == []


def test_parse_captures_real_product_url():
    html = """
    <div class="content-row mainContent">
        <div class="image-box"><img src="/logo.png" alt="Anor Bank"></div>
        <div class="deposit-name"><div class="title"><a href="https://depozit.uz/deposits/view/barqaror-17843">"BARQAROR"</a></div></div>
        <div class="content"><div class="title">Foiz</div><div class="value">22%</div></div>
    </div>
    """
    records = parse_content_rows(html, "deposit-name", source="depozit.uz")
    assert records[0]["url"] == "https://depozit.uz/deposits/view/barqaror-17843"
