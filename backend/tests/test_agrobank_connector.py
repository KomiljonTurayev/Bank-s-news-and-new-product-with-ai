import html

from app.connectors.agrobank import (
    AgrobankConnector,
    AgrobankExchangeConnector,
    extract_items,
    parse_exchange_rates,
    parse_items,
)

PAYLOAD = {
    "data": {
        "sections": [
            {
                "blocks": [
                    {
                        "type": "product-list",
                        "content": {
                            "type": "deposits",
                            "items": [
                                {
                                    "title": "Baraka",
                                    "currency": "UZS",
                                    "url": "/uz/person/deposits/baraka",
                                    "calculationParams": {
                                        "interestRate": {"value": 16},
                                        "amount": {"min": 100000, "max": 500000000},
                                        "monthCount": {"min": 1, "max": 24},
                                    },
                                }
                            ],
                        },
                    },
                    {"type": "banner", "content": {"type": "banner"}},  # mahsulot emas
                ]
            }
        ]
    }
}

CARD_ITEM = {
    "title": "Uzcard Sherdor",
    "url": "/uz/person/cards/uzcard/uzcard-sherdor",
    "tags": [{"title": "Rasmiylashtirish", "type": "text", "value": "100&thinsp;000&nbsp;so‘m"}],
}

LOAN_ITEM = {
    "title": "Online mikroqarz",
    "currency": "UZS",
    "url": "/uz/person/loans/online-micro",
    "calculationParams": {
        "amount": {"min": 1000000, "max": 100000000},
        "monthCount": {"rates": [{"month": 12, "rate": 31}, {"month": 24, "rate": 32}]},
    },
}


def test_extract_items_only_pulls_deposit_and_loan_blocks():
    items = extract_items(PAYLOAD)
    assert len(items) == 1
    assert items[0]["title"] == "Baraka"


def test_extract_items_also_pulls_card_blocks():
    payload = {"data": {"sections": [{"blocks": [
        {"content": {"type": "cards", "items": [CARD_ITEM]}},
    ]}]}}
    items = extract_items(payload)
    assert len(items) == 1
    assert items[0]["title"] == "Uzcard Sherdor"


def test_parse_items_card_reads_tags_and_unescapes_html_entities():
    records = parse_items([CARD_ITEM])

    assert records[0]["name"] == "Uzcard Sherdor"
    assert records[0]["source"] == "agrobank.uz"
    assert records[0]["url"] == "https://agrobank.uz/uz/person/cards/uzcard/uzcard-sherdor"
    # HTML entity'lar (&thinsp;/&nbsp;) unescape qilingan bo'lishi kerak —
    # xom "&...;" matni sifatida qolib ketmasligi kerak.
    assert records[0]["Rasmiylashtirish"] == html.unescape(CARD_ITEM["tags"][0]["value"])
    assert "&" not in records[0]["Rasmiylashtirish"]


def test_parse_items_fixed_rate_deposit():
    records = parse_items(extract_items(PAYLOAD))
    assert records[0] == {
        "name": "Baraka",
        "source": "agrobank.uz",
        "Valyuta": "UZS",
        "Foiz stavkasi": "16%",
        "Miqdori": "100 000 so'm - 500 000 000 so'm",
        "Muddati": "1 - 24 oy",
        "url": "https://agrobank.uz/uz/person/deposits/baraka",
    }


def test_parse_items_summarizes_term_based_loan_rate_as_range():
    records = parse_items([LOAN_ITEM])
    assert records[0]["Foiz stavkasi"] == "31% - 32%"
    assert "Muddati" not in records[0]  # muddat bo'yicha o'zgaruvchan stavka uchun yagona muddat yo'q


def test_connector_uses_individual_segment_and_agro_bank_code():
    connector = AgrobankConnector("deposit", "uz/person/deposits")
    assert connector.segment == "individual"
    assert connector.bank_code == "AGRO"


# Sahifada uchta tab bor (filial/bankomat/xalqaro o'tkazma), har biri o'z
# "currency-rates" blokiga ega — faqat birinchisi (tab.code == "office")
# olinishi kerak. RUB'da "buy": 0 — hozircha xarid qilinmayapti, o'tkazib
# yuborilishi kerak.
EXCHANGE_PAYLOAD = {
    "data": {
        "sections": [
            {
                "blocks": [
                    {"type": "tabs", "content": {"code": "exchange-rate"}},
                    {"type": "tab", "content": {"code": "office", "title": "Ayirboshlash shoxobchasida"}},
                    {"type": "currency-rates", "content": {"items": [
                        {"alpha3": "USD", "buy": 11750, "sale": 11855},
                        {"alpha3": "RUB", "buy": 0, "sale": 180},
                    ]}},
                    {"type": "currency-calculator", "content": {"items": [
                        {"alpha3": "USD", "buy": 11750, "sale": 11855},
                    ]}},
                    {"type": "tab", "content": {"code": "atm", "title": "Bankomatlarda"}},
                    {"type": "currency-rates", "content": {"items": [
                        {"alpha3": "USD", "buy": 11500, "sale": 11855},
                    ]}},
                ]
            }
        ]
    }
}


def test_parse_exchange_rates_reads_only_the_office_tab():
    records = parse_exchange_rates(EXCHANGE_PAYLOAD, url="https://agrobank.uz/uz/person/exchange_rates")
    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11750.0, "source": "agrobank.uz", "url": "https://agrobank.uz/uz/person/exchange_rates"},
        {"code": "USD", "side": "Sotish", "rate": 11855.0, "source": "agrobank.uz", "url": "https://agrobank.uz/uz/person/exchange_rates"},
    ]


def test_parse_exchange_rates_returns_empty_without_office_tab():
    assert parse_exchange_rates({"data": {"sections": []}}) == []


def test_exchange_connector_uses_currency_product_type_and_agro_bank_code():
    connector = AgrobankExchangeConnector()
    assert connector.bank_code == "AGRO"
    assert connector.product_type == "currency"
    assert connector.url == "https://agrobank.uz/uz/person/exchange_rates"
