import json

from app.connectors.xb import XBConnector, parse_blocks


def _next_data_html(blocks):
    payload = {"props": {"pageProps": {"dehydratedState": {"queries": [{"state": {"data": {"blocks": blocks}}}]}}}}
    return f'<html><head><script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script></head></html>'


DEPOSIT_BLOCKS = [
    {
        "title": "Stimul 2",
        "template": "deposit-card-block",
        "data": {
            "description": ["Foiz stavkasi", "Muddat"],
            "title": ["4.5 %", "18 oy"],
            "btn_url": ["/page/stimul-2-omonati"],
        },
    },
    {"title": "", "template": "deposit-card-block", "data": {}},  # nomsiz blok o'tkazilishi kerak
    {"title": "Banner", "template": "banner", "data": {"description": ["x"], "title": ["y"]}},  # mahsulot emas
]


def test_parse_blocks_extracts_named_product_blocks_only():
    html = _next_data_html(DEPOSIT_BLOCKS)
    records = parse_blocks(html)

    assert len(records) == 1
    assert records[0] == {
        "name": "Stimul 2",
        "source": "xb.uz",
        "Foiz stavkasi": "4.5 %",
        "Muddat": "18 oy",
        "url": "https://xb.uz/page/stimul-2-omonati",
    }


def test_parse_blocks_returns_empty_when_next_data_missing():
    assert parse_blocks("<html><body>no data here</body></html>") == []


def test_connector_tags_category_and_uses_xb_bank_code():
    connector = XBConnector("credit", "https://example.test/credits", category="Ipoteka")
    html = _next_data_html([
        {"title": "Farovon", "template": "list", "data": {"description": [], "title": []}},
    ])

    records = connector.parse(html)

    assert connector.bank_code == "XB"
    assert connector.segment == "individual"
    assert all(r["category"] == "Ipoteka" for r in records)
