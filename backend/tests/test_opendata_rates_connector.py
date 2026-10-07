from app.connectors.opendata_rates import OpenDataRatesConnector, parse_open_data_rates

# Turonbank/Poytaxtbank/Aloqabank/Mikrokreditbank hammasi bir xil Bitrix
# "ochiq ma'lumotlar" JSON sxemasidan foydalanadi: G2 kanal (BANK/APP/
# ATM/IMT — faqat BANK olinadi), G4 xarid narxi, G5 sotish narxi.
RAW_RATES = [
    {"G1": "09.09.2026 09:00:00", "G2": "BANK", "G3": "USD", "G4": "11790", "G5": "11870"},
    {"G1": "09.09.2026 09:00:00", "G2": "BANK", "G3": "RUB", "G4": "", "G5": "140"},
    {"G1": "09.09.2026 09:00:00", "G2": "BANK", "G3": "KZT", "G4": "-", "G5": "-"},
    {"G1": "09.09.2026 09:00:00", "G2": "APP", "G3": "USD", "G4": "11790", "G5": "11870"},
    {"G1": "09.09.2026 09:00:00", "G2": "ATM", "G3": "USD", "G4": "11500", "G5": "11870"},
]


def test_parse_open_data_rates_keeps_only_branch_channel():
    records = parse_open_data_rates(RAW_RATES, url="https://turonbank.uz/uz/services/open_data/rates/json/", source="turonbank.uz")
    assert records == [
        {"code": "USD", "side": "Olish", "rate": 11790.0, "source": "turonbank.uz", "url": "https://turonbank.uz/uz/services/open_data/rates/json/"},
        {"code": "USD", "side": "Sotish", "rate": 11870.0, "source": "turonbank.uz", "url": "https://turonbank.uz/uz/services/open_data/rates/json/"},
    ]


def test_parse_open_data_rates_skips_missing_or_dash_values():
    # RUB'da G4 bo'sh satr, KZT'da ikkalasi ham "-" — ikkalasi ham
    # o'tkazib yuborilishi kerak.
    records = parse_open_data_rates([RAW_RATES[1], RAW_RATES[2]], url="x", source="x")
    assert records == []


def test_connector_builds_the_open_data_url_from_base_url():
    connector = OpenDataRatesConnector("TURON", "https://turonbank.uz", "turonbank.uz")
    assert connector.url == "https://turonbank.uz/uz/services/open_data/rates/json/"
    assert connector.bank_code == "TURON"
    assert connector.product_type == "currency"
