from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.models import BankRate

client = TestClient(app)


def insert(session_factory, bank_code, product_type, segment, data, fetched_at):
    with session_factory() as session:
        session.add(BankRate(bank_code=bank_code, product_type=product_type, segment=segment, data=data, fetched_at=fetched_at))
        session.commit()

def test_health_is_stale_when_no_data_yet(session_factory):
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "stale"
    assert body["last_fetch_at"] is None
    assert body["stale_after_minutes"] == 2 * body["fetch_interval_minutes"]


def test_health_is_ok_right_after_a_fetch(session_factory):
    insert(session_factory, "SQB", "deposit", "individual", {"name": "A"}, datetime.now(timezone.utc))

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["last_fetch_at"] is not None


def test_health_is_stale_after_the_threshold(session_factory):
    too_old = datetime.now(timezone.utc) - timedelta(hours=100)
    insert(session_factory, "SQB", "deposit", "individual", {"name": "A"}, too_old)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "stale"


def test_meta_lists_banks_product_types_and_segments(session_factory):
    response = client.get("/api/meta")

    assert response.status_code == 200
    body = response.json()
    assert any(b["code"] == "SQB" for b in body["banks"])
    assert {p["code"] for p in body["product_types"]} >= {"deposit", "credit", "card", "currency"}
    assert {s["code"] for s in body["segments"]} == {"individual", "business"}


def test_latest_rates_filters_by_product_type_and_segment(session_factory):
    now = datetime.now(timezone.utc)
    insert(session_factory, "SQB", "deposit", "individual", {"name": "A"}, now)
    insert(session_factory, "SQB", "credit", "individual", {"name": "B"}, now)
    insert(session_factory, "SQB", "deposit", "business", {"name": "C"}, now)

    response = client.get("/api/rates/latest", params={"product_type": "deposit", "segment": "individual"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["data"]["name"] == "A"


def test_latest_rates_returns_only_the_newest_batch_per_bank(session_factory):
    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    new_time = datetime.now(timezone.utc)
    insert(session_factory, "SQB", "deposit", "individual", {"name": "Standart", "rate": "eski"}, old_time)
    insert(session_factory, "SQB", "deposit", "individual", {"name": "Standart", "rate": "yangi"}, new_time)

    response = client.get("/api/rates/latest", params={"product_type": "deposit", "segment": "individual"})

    body = response.json()
    assert len(body) == 1
    assert body[0]["data"]["rate"] == "yangi"


def test_latest_rates_filters_by_bank(session_factory):
    now = datetime.now(timezone.utc)
    insert(session_factory, "SQB", "deposit", "individual", {"name": "SQB taklifi"}, now)
    insert(session_factory, "XB", "deposit", "individual", {"name": "XB taklifi"}, now)

    response = client.get("/api/rates/latest", params={"product_type": "deposit", "segment": "individual", "bank": "XB"})

    body = response.json()
    assert len(body) == 1
    assert body[0]["bank_code"] == "XB"


def test_latest_rates_keeps_each_source_even_if_one_finished_earlier(session_factory):
    # Bitta bank/tur/segment ikkita mustaqil connector (masalan depozit.uz VA
    # bankning o'z sayti) orqali to'ldirilishi mumkin — ularning fetched_at
    # vaqti sal-pal farq qiladi. Ikkalasi ham "eng so'nggi" hisoblanishi kerak,
    # faqat vaqt jihatdan oldinroq tugagani butunlay yo'qolib qolmasligi kerak.
    earlier = datetime.now(timezone.utc) - timedelta(minutes=1)
    later = datetime.now(timezone.utc)
    insert(session_factory, "SQB", "deposit", "individual", {"name": "A", "source": "depozit.uz"}, later)
    insert(session_factory, "SQB", "deposit", "individual", {"name": "B", "source": "sqb.uz"}, earlier)

    response = client.get("/api/rates/latest", params={"product_type": "deposit", "segment": "individual", "bank": "SQB"})

    body = response.json()
    assert {row["data"]["source"] for row in body} == {"depozit.uz", "sqb.uz"}


def test_latest_rates_keeps_each_category_connector_from_the_same_source(session_factory):
    # xb.uz'da har kredit turi (Ipoteka, Avtokredit, ...) o'z alohida
    # connectoriga ega, lekin barchasi bir xil source="xb.uz" yozadi va
    # har birining fetched_at vaqti sal-pal farq qiladi — faqat "source"
    # bo'yicha guruhlash yetarli emas, kategoriya/nom ham hisobga olinishi
    # kerak, aks holda faqat bittasi (eng oxiri tugagani) ko'rinib qoladi.
    t1 = datetime.now(timezone.utc) - timedelta(seconds=3)
    t2 = datetime.now(timezone.utc) - timedelta(seconds=2)
    t3 = datetime.now(timezone.utc) - timedelta(seconds=1)
    insert(session_factory, "XB", "credit", "individual", {"name": "Farovon", "source": "xb.uz", "category": "Ipoteka"}, t1)
    insert(session_factory, "XB", "credit", "individual", {"name": "Nasiya", "source": "xb.uz", "category": "Iste'mol krediti"}, t2)
    insert(session_factory, "XB", "credit", "individual", {"name": "Avtokredit", "source": "xb.uz", "category": "Avtokredit"}, t3)

    response = client.get("/api/rates/latest", params={"product_type": "credit", "segment": "individual", "bank": "XB"})

    body = response.json()
    assert {row["data"]["category"] for row in body} == {"Ipoteka", "Iste'mol krediti", "Avtokredit"}


def test_latest_rates_keeps_every_currency_code_without_a_name_field(session_factory):
    # Valyuta yozuvlarida "name" maydoni yo'q (o'rniga "code"/"side") —
    # avval dedup kaliti faqat "name"ga tayanardi, shu sabab bir xil
    # bankning (source/category ham bo'sh bo'lgan) barcha valyutalari
    # bitta kalitga to'planib, faqat bittasi qolib ketardi.
    now = datetime.now(timezone.utc)
    insert(session_factory, "CBU", "currency", "individual", {"code": "USD", "rate": 12700}, now)
    insert(session_factory, "CBU", "currency", "individual", {"code": "EUR", "rate": 13700}, now)
    insert(session_factory, "CBU", "currency", "individual", {"code": "RUB", "rate": 140}, now)

    response = client.get("/api/rates/latest", params={"product_type": "currency", "segment": "individual", "bank": "CBU"})

    body = response.json()
    assert {row["data"]["code"] for row in body} == {"USD", "EUR", "RUB"}


def test_latest_rates_keeps_both_sides_of_the_same_currency_code(session_factory):
    now = datetime.now(timezone.utc)
    insert(session_factory, "SQB", "currency", "individual", {"code": "USD", "side": "Sotib olish", "rate": 12650}, now)
    insert(session_factory, "SQB", "currency", "individual", {"code": "USD", "side": "Sotish", "rate": 12750}, now)

    response = client.get("/api/rates/latest", params={"product_type": "currency", "segment": "individual", "bank": "SQB"})

    body = response.json()
    assert {row["data"]["side"] for row in body} == {"Sotib olish", "Sotish"}


def test_latest_rates_empty_when_no_data(session_factory):
    response = client.get("/api/rates/latest", params={"product_type": "investment", "segment": "individual"})

    assert response.status_code == 200
    assert response.json() == []


def test_currency_stats_computes_min_avg_max_from_cbu_dynamics(monkeypatch):
    fake_history = {
        "USD": [
            {"date": "2026-08-01", "value": 12000.0},
            {"date": "2026-08-15", "value": 12200.0},
            {"date": "2026-09-08", "value": 12100.0},
        ],
    }
    monkeypatch.setattr("app.routers.rates._get_dynamics_histories", lambda: fake_history)

    response = client.get("/api/rates/currency-stats", params={"days": 365})

    assert response.status_code == 200
    body = response.json()
    usd = next(s for s in body if s["code"] == "USD")
    assert usd["min"] == 12000.0
    assert usd["max"] == 12200.0
    assert usd["avg"] == pytest.approx(12100.0)
    assert usd["current"] == 12100.0
    assert usd["samples"] == 3


def test_currency_stats_empty_when_cbu_unreachable(monkeypatch):
    def boom():
        raise RuntimeError("network down")

    monkeypatch.setattr("app.routers.rates._get_dynamics_histories", boom)

    response = client.get("/api/rates/currency-stats")

    assert response.status_code == 502


def test_currency_history_returns_full_points_for_window(monkeypatch):
    fake_history = {
        "USD": [
            {"date": "2026-08-01", "value": 12000.0},
            {"date": "2026-08-15", "value": 12200.0},
            {"date": "2026-09-08", "value": 12100.0},
        ],
    }
    monkeypatch.setattr("app.routers.rates._get_dynamics_histories", lambda: fake_history)

    response = client.get("/api/rates/currency-history", params={"code": "usd", "days": 365})

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "USD"
    assert body["points"] == fake_history["USD"]


def test_currency_history_404_for_unknown_code(monkeypatch):
    monkeypatch.setattr("app.routers.rates._get_dynamics_histories", lambda: {"USD": [{"date": "2026-09-08", "value": 1.0}]})

    response = client.get("/api/rates/currency-history", params={"code": "XXX"})

    assert response.status_code == 404


def test_create_product_rejects_currency_type(session_factory):
    response = client.post("/api/products", json={"name": "Test", "product_type": "currency", "rate": 10})

    assert response.status_code == 400


def test_create_product_rejects_negative_rate(session_factory):
    response = client.post("/api/products", json={"name": "Test", "product_type": "credit", "rate": -15})

    assert response.status_code == 422


def test_create_product_rejects_blank_name(session_factory):
    response = client.post("/api/products", json={"name": "   ", "product_type": "credit", "rate": 15})

    assert response.status_code == 422


def test_create_product_rejects_unreasonably_high_rate(session_factory):
    response = client.post("/api/products", json={"name": "Test", "product_type": "credit", "rate": 2000})

    assert response.status_code == 422


def test_create_product_rejects_min_amount_above_max_amount(session_factory):
    response = client.post(
        "/api/products",
        json={"name": "Test", "product_type": "credit", "rate": 20, "min_amount": 50_000_000, "max_amount": 1_000_000},
    )

    assert response.status_code == 422


def test_create_product_rejects_out_of_range_initial_payment_pct(session_factory):
    response = client.post(
        "/api/products",
        json={"name": "Test", "product_type": "credit", "rate": 20, "initial_payment_pct": 150},
    )

    assert response.status_code == 422


def test_create_product_rejects_non_positive_term_months(session_factory):
    response = client.post(
        "/api/products",
        json={"name": "Test", "product_type": "credit", "rate": 20, "term_months": 0},
    )

    assert response.status_code == 422


def test_create_product_rejects_term_months_above_240(session_factory):
    response = client.post(
        "/api/products",
        json={"name": "Test", "product_type": "credit", "rate": 20, "term_months": 241},
    )

    assert response.status_code == 422


def test_create_product_accepts_term_months_at_240(session_factory):
    response = client.post(
        "/api/products",
        json={"name": "Test", "product_type": "credit", "rate": 20, "term_months": 240},
    )

    assert response.status_code == 201


def test_create_product_rejects_negative_initial_payment_pct(session_factory):
    response = client.post(
        "/api/products",
        json={"name": "Test", "product_type": "credit", "rate": 20, "initial_payment_pct": -5},
    )

    assert response.status_code == 422


def test_create_product_rejects_amount_above_one_billion(session_factory):
    response = client.post(
        "/api/products",
        json={"name": "Test", "product_type": "credit", "rate": 20, "max_amount": 2_000_000_000},
    )

    assert response.status_code == 422


def test_create_product_rejects_unknown_currency(session_factory):
    response = client.post(
        "/api/products",
        json={"name": "Test", "product_type": "credit", "rate": 20, "currency": "RUB"},
    )

    assert response.status_code == 422


def test_create_list_and_get_product_with_analysis(session_factory):
    insert(session_factory, "SQB", "deposit", "individual", {"name": "Bozor taklifi", "Foiz stavkasi": "20%"}, datetime.now(timezone.utc))

    create_response = client.post(
        "/api/products",
        json={"name": "Milliy omonat", "product_type": "deposit", "bank_name": "Test bank", "rate": 25},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Milliy omonat"
    product_id = created["id"]

    list_response = client.get("/api/products")
    assert list_response.status_code == 200
    assert any(p["id"] == product_id for p in list_response.json())

    detail_response = client.get(f"/api/products/{product_id}")
    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["analysis"]["market_count"] == 1
    assert body["analysis"]["score"] == 100

    detail_ru = client.get(f"/api/products/{product_id}", params={"lang": "ru"})
    assert detail_ru.status_code == 200
    assert "На рынке найдено" in detail_ru.json()["analysis"]["summary"]

    detail_bad_lang = client.get(f"/api/products/{product_id}", params={"lang": "fr"})
    assert detail_bad_lang.status_code == 422


def test_create_product_rate_limited_per_ip(session_factory, monkeypatch):
    # Autentifikatsiya yo'qligi sababli hech bo'lmasa bitta IP manzil
    # /api/products'ni spam yozuvlar bilan cheksiz to'ldirib
    # yubormasligi kerak.
    import app.routers.products as api_module

    api_module._create_product_limiter.reset()
    monkeypatch.setattr(api_module._create_product_limiter, "limit", 2)

    payload = {"name": "Test", "product_type": "credit", "rate": 15}
    assert client.post("/api/products", json=payload).status_code == 201
    assert client.post("/api/products", json=payload).status_code == 201

    third = client.post("/api/products", json=payload)
    assert third.status_code == 429
    assert int(third.headers["retry-after"]) >= 0


def test_get_product_404_for_unknown_id(session_factory):
    response = client.get("/api/products/999")

    assert response.status_code == 404


def test_delete_product(session_factory):
    create_response = client.post("/api/products", json={"name": "O'chiriladigan", "product_type": "credit", "rate": 18})
    product_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/products/{product_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/products/{product_id}")
    assert get_response.status_code == 404

