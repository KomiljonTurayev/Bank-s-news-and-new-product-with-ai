"""Mahsulot g'oyasini tahrirlash (`PATCH /api/products/{id}`) — qismiy
yangilash xatti-harakati va maydon cheklovlari."""

from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)

_PAYLOAD = {
    "name": "Boshlang'ich pasport",
    "product_type": "credit",
    "category": "Ipoteka",
    "currency": "UZS",
    "rate": 20.0,
    "term_months": 120,
    "min_amount": 1_000_000,
    "max_amount": 50_000_000,
    "initial_payment_pct": 30.0,
}


def _create() -> int:
    return client.post("/api/products", json=_PAYLOAD).json()["id"]


def test_patch_updates_only_the_fields_sent(session_factory):
    product_id = _create()

    body = client.patch(f"/api/products/{product_id}", json={"rate": 17.5, "name": "Yangi nom"}).json()

    assert body["name"] == "Yangi nom"
    assert body["rate"] == 17.5
    # Yuborilmagan maydonlar o'zgarishsiz qolishi shart.
    assert body["category"] == "Ipoteka"
    assert body["term_months"] == 120
    assert body["min_amount"] == 1_000_000
    assert body["initial_payment_pct"] == 30.0

    # O'zgarish qaytib o'qilganda ham saqlanadi.
    assert client.get(f"/api/products/{product_id}").json()["rate"] == 17.5


def test_patch_can_clear_an_optional_field(session_factory):
    product_id = _create()

    body = client.patch(f"/api/products/{product_id}", json={"category": None, "term_months": None}).json()

    assert body["category"] is None
    assert body["term_months"] is None


def test_patch_validates_the_resulting_amounts(session_factory):
    product_id = _create()

    # So'rovda faqat max bor — min qatordagi eski qiymat bilan birga tekshiriladi.
    response = client.patch(f"/api/products/{product_id}", json={"max_amount": 500})
    assert response.status_code == 400
    assert client.get(f"/api/products/{product_id}").json()["max_amount"] == 50_000_000


def test_patch_rejects_mandatory_fields_being_cleared(session_factory):
    product_id = _create()

    # Sxemaga kirib kelmagan qiymatlar (majburiy maydonni null qilish, bo'sh
    # nom, diapazondan tashqari) — FastAPI standartida 422 bilan qaytadi;
    # 400 esa sxemadan o'tib, biznes qoidasida uriladigan holatlar uchun.
    for body in ({"rate": None}, {"name": None}, {"name": "   "}, {"rate": 5000}):
        assert client.patch(f"/api/products/{product_id}", json=body).status_code == 422

    # Hech narsa o'zgarmagan bo'lishi shart.
    product = client.get(f"/api/products/{product_id}").json()
    assert product["name"] == "Boshlang'ich pasport"
    assert product["rate"] == 20.0


def test_patch_rejects_unknown_product_type(session_factory):
    product_id = _create()

    assert client.patch(f"/api/products/{product_id}", json={"product_type": "currency"}).status_code == 400
