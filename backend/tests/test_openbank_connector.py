import json

from app.connectors.openbank import OpenBankConnector, parse_mortgage

# Haqiqiy sahifa Next.js "flight" oqimida (self.__next_f.push) JSON
# yuboradi — bu yordamchi funksiya haqiqiy saytdagi kabi "infoSheet"
# strukturasini shu formatga o'rab, ikkita bo'lakka bo'lib beradi (real
# sahifada ham ma'lumot bir nechta push chaqiruviga bo'linib keladi).
def _build_html(info_sheet: dict) -> str:
    decoded = f'0:{{"a":1}}\n1:noise before "infoSheet":{json.dumps(info_sheet, ensure_ascii=False)} noise after'
    midpoint = len(decoded) // 2
    chunks = [decoded[:midpoint], decoded[midpoint:]]
    scripts = "".join(
        f"<script>self.__next_f.push([1,{json.dumps(chunk, ensure_ascii=False)}])</script>"
        for chunk in chunks
    )
    return f"<html><body>{scripts}</body></html>"


_INFO_SHEET = {
    "groups": [
        {
            "title": "Mahsulot haqida asosiy ma’lumotlar",
            "rows": [
                {
                    "label": "Moliyalashtirish turi",
                    "value": [
                        {
                            "type": "paragraph",
                            "children": [
                                {"text": "Yangi uy — turar joy xarid qilish uchun muddatli to‘lov", "type": "text"}
                            ],
                        }
                    ],
                },
                {"label": "Bandlik turi", "value": None},
            ],
        },
        {
            "title": "Bank ustamasi",
            "rows": [
                {
                    "label": "Doimiy daromadli fuqarolar uchun",
                    "value": [{"type": "paragraph", "children": [{"text": "24.99%", "type": "text"}]}],
                },
                {
                    "label": "O‘zini o‘zi band qilgan fuqarolar uchun",
                    "value": [{"type": "paragraph", "children": [{"text": "25.99%", "type": "text"}]}],
                },
            ],
        },
    ]
}


def test_parse_mortgage_extracts_both_rate_variants_from_split_flight_chunks():
    html = _build_html(_INFO_SHEET)
    records = parse_mortgage(html, url="https://openbank.uz/mortgage")
    assert records == [
        {
            "name": "Yangi uy (Doimiy daromadli fuqarolar uchun)",
            "source": "openbank.uz",
            "url": "https://openbank.uz/mortgage",
            "Bank ustamasi": "24.99%",
        },
        {
            "name": "Yangi uy (O‘zini o‘zi band qilgan fuqarolar uchun)",
            "source": "openbank.uz",
            "url": "https://openbank.uz/mortgage",
            "Bank ustamasi": "25.99%",
        },
    ]


def test_parse_mortgage_returns_empty_when_info_sheet_is_missing():
    assert parse_mortgage("<html><body>no flight data here</body></html>") == []


def test_parse_mortgage_returns_empty_when_bank_ustamasi_group_is_missing():
    info_sheet = {"groups": [_INFO_SHEET["groups"][0]]}
    assert parse_mortgage(_build_html(info_sheet)) == []


def test_connector_defaults_to_the_mortgage_page():
    connector = OpenBankConnector()
    assert connector.url == "https://openbank.uz/mortgage"
    assert connector.bank_code == "OPEN"
    assert connector.product_type == "credit"
