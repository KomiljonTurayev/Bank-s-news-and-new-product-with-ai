"""CORS preflight — har bir ishlatiladigan HTTP metodi ruxsat etilganini tekshiradi.

Mahsulotni tahrirlash PATCH bilan boradi; `allow_methods` ro'yxatida metodi
bo'lmasa brauzer preflight'ni rad etadi va funksiya brauzerda ishlamaydi.
Oddiy (origin'siz) so'rovlar CORS tekshiruvidan o'tmaganligi uchunTestClient
testlarida bu xato ko'rinmaydi — preflight'ni mana shu yerda, Origin bilanoq
sinaymiz.
"""

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.config import FRONTEND_ORIGINS

client = TestClient(app)
ORIGIN = FRONTEND_ORIGINS[0]


def _preflight(method: str, path: str = "/api/products/1"):
    return client.options(
        path,
        headers={"Origin": ORIGIN, "Access-Control-Request-Method": method},
    )


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "DELETE"])
def test_preflight_allows_product_methods(method):
    response = _preflight(method)
    assert response.status_code == 200
    assert method in response.headers["access-control-allow-methods"]
    assert response.headers["access-control-allow-origin"] == ORIGIN


def test_preflight_patch_allows_json_header():
    response = client.options(
        "/api/products/1",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    allowed = response.headers.get("access-control-allow-headers", "").lower()
    assert "content-type" in allowed


def test_preflight_rejects_unlisted_origin():
    response = client.options(
        "/api/products/1",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "PATCH"},
    )
    assert "access-control-allow-origin" not in response.headers
