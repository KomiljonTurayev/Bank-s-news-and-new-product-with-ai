from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.market_compare import parse_amounts, parse_term_months
from app.models import BankRate

client = TestClient(app)


@pytest.mark.parametrize(
    "text, months",
    [
        ("24 oy", 24),
        ("1-12 oy", 12),
        ("1 - 24 oy", 24),
        ("3-18 yil", 216),
        ("20 yilgacha", 240),
        ("555 kun", 18),
        ("84 oygacha", 84),
        ("18 оy", 18),  # kirill "о"
        ("18 yoshgacha", None),
        ("Cheklanmagan", None),
        (None, None),
    ],
)
def test_parse_term_months(text, months):
    assert parse_term_months(text) == months


@pytest.mark.parametrize(
    "text, expected",
    [
        ("1,000,000 So’m", (1_000_000, None)),
        ("100 000 so'm", (100_000, None)),
        ("100 000 so'mdan", (100_000, None)),
        ("100 mln so'mgacha", (None, 100_000_000)),
        ("1.0 mlrd. so'mgacha", (None, 1_000_000_000)),
        ("100 000 so'm - 500 000 000 so'm", (100_000, 500_000_000)),
        ("Cheklanmagan", (None, None)),
    ],
)
def test_parse_amounts(text, expected):
    assert parse_amounts(text) == expected


def test_market_compare_buckets_and_stats(session_factory):
    with session_factory() as session:
        now = datetime.now(timezone.utc)
        for bank, name, rate, term, amount in [
            ("SQB", "Qisqa", "24%", "3 oy", "1,000,000 So’m"),
            ("NBU", "Yillik", "20%", "12 oy", "100 000 so'm"),
            ("XB", "Yillik-2", "22%", "12 oy", None),
            ("KDB", "Uzoq", "21%", "36 oy", None),
            ("IPOTEKA", "Dollar", "9%", "12 oy", "$100"),  # valyuta — chiqariladi
        ]:
            data = {"name": name, "Foiz stavkasi": rate, "Muddati": term, "url": "https://x"}
            if amount:
                data["Summa"] = amount
            session.add(BankRate(bank_code=bank, product_type="deposit", segment="individual", data=data, fetched_at=now))
        session.commit()

    body = client.get("/api/products/market-compare", params={"product_type": "deposit"}).json()

    assert [o["bank_code"] for o in body["offers"]] == ["SQB", "XB", "KDB", "NBU"]
    assert body["overall"]["count"] == 4 and body["overall"]["best"]["bank_code"] == "SQB"
    buckets = {b["key"]: b for b in body["term_buckets"]}
    assert set(buckets) == {"0-6", "7-12", "25+"}
    assert buckets["7-12"]["count"] == 2
    assert buckets["7-12"]["avg_rate"] == 21.0
    assert buckets["7-12"]["best"]["bank_code"] == "XB"
    assert body["offers"][0]["min_amount"] == 1_000_000
