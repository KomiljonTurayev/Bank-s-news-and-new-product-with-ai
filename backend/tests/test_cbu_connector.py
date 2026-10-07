from app.connectors.cbu import CBUConnector


def test_parse_converts_cbu_json_to_normalized_records():
    connector = CBUConnector()
    raw = [
        {"Ccy": "USD", "Rate": "11789.33", "Date": "08.09.2026"},
        {"Ccy": "EUR", "Rate": "13702.74", "Date": "08.09.2026"},
    ]

    records = connector.parse(raw)

    assert records == [
        {"code": "USD", "rate": 11789.33, "date": "08.09.2026", "url": "https://cbu.uz/uz/arkhiv-kursov-valyut/"},
        {"code": "EUR", "rate": 13702.74, "date": "08.09.2026", "url": "https://cbu.uz/uz/arkhiv-kursov-valyut/"},
    ]


def test_parse_returns_empty_list_for_empty_input():
    assert CBUConnector().parse([]) == []
