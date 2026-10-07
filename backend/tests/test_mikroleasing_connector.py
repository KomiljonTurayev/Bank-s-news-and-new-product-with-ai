from app.connectors.mikroleasing import MikroLeasingConnector, parse_product_page

PRODUCT_PAGE_HTML = """
<html>
<head><meta property="og:title" content="Yengil avtomobillar lizingi"></head>
<body>
<div class="conditions-items">
  <div class="item row">
    <div class="fw-5 col-6">Lizing predmeti</div>
    <div class="col-6">Yangi yengil avtomobil</div>
  </div>
  <div class="item row">
    <div class="fw-5 col-6">Avans miqdori</div>
    <div class="col-6">20% dan</div>
  </div>
  <div class="item row">
    <div class="fw-5 col-6">Lizing muddati</div>
    <div class="col-6">13 oydan 60 oygacha</div>
  </div>
  <div class="item row">
    <div class="fw-5 col-6">Tranzaksiyani qayta ishlash uchun to'lov</div>
    <div class="col-6">3% dan 3,5% gacha</div>
  </div>
</div>
</body>
</html>
"""

EMPTY_PAGE_HTML = "<html><head></head><body>404</body></html>"


def test_parse_product_page_extracts_name_and_non_percent_terms():
    record = parse_product_page(PRODUCT_PAGE_HTML, "https://mikro-leasing.uz/uz/loans/yengil-avtomobillar-lizingi.html")
    assert record == {
        "name": "Yengil avtomobillar lizingi",
        "source": "mikro-leasing.uz",
        "url": "https://mikro-leasing.uz/uz/loans/yengil-avtomobillar-lizingi.html",
        "Lizing predmeti": "Yangi yengil avtomobil",
        "Lizing muddati": "13 oydan 60 oygacha",
    }


def test_parse_product_page_excludes_percent_bearing_fields():
    # mikro-leasing.uz'da hech qanday "Foiz stavkasi" (APR) e'lon qilinmaydi —
    # "Avans miqdori" va tranzaksiya to'lovi kabi "%" belgili maydonlar
    # extract_rate_percent() tomonidan xato ravishda kredit stavkasi deb
    # o'qilib ketmasligi uchun ataylab chiqarib tashlanadi (app/connectors/
    # mikroleasing.py izohiga qarang).
    record = parse_product_page(PRODUCT_PAGE_HTML, "https://mikro-leasing.uz/uz/loans/yengil-avtomobillar-lizingi.html")
    assert "Avans miqdori" not in record
    assert "Tranzaksiyani qayta ishlash uchun to'lov" not in record
    assert not any("%" in value for value in record.values())


def test_parse_product_page_returns_none_without_og_title():
    assert parse_product_page(EMPTY_PAGE_HTML, "https://mikro-leasing.uz/uz/loans/missing.html") is None


def test_connector_builds_full_urls_from_paths():
    connector = MikroLeasingConnector(["/uz/loans/yengil-avtomobillar-lizingi.html", "/uz/loans/uskunalar-lizingi.html"])
    assert connector.urls == [
        "https://mikro-leasing.uz/uz/loans/yengil-avtomobillar-lizingi.html",
        "https://mikro-leasing.uz/uz/loans/uskunalar-lizingi.html",
    ]
    assert connector.bank_code == "MIKROLEASING"
    assert connector.product_type == "credit"
    assert connector.segment == "individual"


def test_connector_parse_skips_pages_with_no_product():
    connector = MikroLeasingConnector([])
    records = connector.parse([
        ("https://mikro-leasing.uz/uz/loans/yengil-avtomobillar-lizingi.html", PRODUCT_PAGE_HTML),
        ("https://mikro-leasing.uz/uz/loans/missing.html", EMPTY_PAGE_HTML),
    ])
    assert len(records) == 1
    assert records[0]["name"] == "Yengil avtomobillar lizingi"
