"""AI mahsulot tavsiyasi (`POST /api/products/recommend`) — Claude API
soxtalashtiriladi, tarmoqqa chiqilmaydi."""

from datetime import datetime, timezone
from types import SimpleNamespace

import anthropic
import pytest
from fastapi.testclient import TestClient

from app import product_recommendation
from app.api import app
from app.models import BankRate
from app.product_recommendation import RecommendationResult, RecommendedProduct

client = TestClient(app)


def _seed(session_factory):
    with session_factory() as session:
        for bank, name, rate in [("NBU", "Hamma uchun", "18%"), ("SQB", "Jamg'arma", "21%")]:
            session.add(
                BankRate(
                    bank_code=bank,
                    product_type="deposit",
                    segment="individual",
                    data={"name": name, "Foiz stavkasi": rate, "Muddati": "12 oy", "url": "https://x"},
                    fetched_at=datetime.now(timezone.utc),
                )
            )
        session.commit()


def _result() -> RecommendationResult:
    return RecommendationResult(
        market_overview="Omonat stavkalari 18-21% oralig'ida.",
        recommendations=[
            RecommendedProduct(
                name="Yoshlar omonati",
                product_type="deposit",
                category=None,
                currency="UZS",
                rate=21.5,
                min_amount=100_000,
                max_amount=None,
                term_months=12,
                initial_payment_pct=None,
                target_segment="18-30 yoshlilar",
                purpose="Yoshlarni jamg'arishga jalb qilish",
                rationale="Bozordagi eng yuqori 21% dan biroz yuqori",
                risks=["Foiz xarajati oshadi"],
            )
        ],
    )


class _FakeMessages:
    def __init__(self, response=None, error=None):
        self.calls = []
        self._response = response
        self._error = error

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return self._response


def _fake_client(monkeypatch, messages):
    fake = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    monkeypatch.setattr(product_recommendation, "_client", lambda: fake)


@pytest.fixture(autouse=True)
def _fresh_limiter(monkeypatch):
    from app.rate_limiter import RateLimiter
    from app.routers import products

    monkeypatch.setattr(products, "_recommend_limiter", RateLimiter(limit=10, window_seconds=3600))


def test_recommend_returns_parsed_products_and_sends_market_data(session_factory, monkeypatch):
    _seed(session_factory)
    messages = _FakeMessages(
        SimpleNamespace(stop_reason="end_turn", parsed_output=_result(), model="claude-opus-5-5")
    )
    _fake_client(monkeypatch, messages)

    response = client.post("/api/products/recommend", json={"product_type": "deposit", "goal": "yoshlar uchun"})

    assert response.status_code == 200
    body = response.json()
    assert body["market_count"] == 2
    assert body["recommendations"][0]["name"] == "Yoshlar omonati"
    prompt = messages.calls[0]["messages"][0]["content"]
    assert "Hamma uchun" in prompt and "yoshlar uchun" in prompt
    # Yuqoriroq stavka omonatda foydali — eng yaxshisi birinchi.
    assert prompt.index("Jamg'arma") < prompt.index("Hamma uchun")


def test_recommend_404_when_market_is_empty(session_factory, monkeypatch):
    _fake_client(monkeypatch, _FakeMessages())

    response = client.post("/api/products/recommend", json={"product_type": "credit"})

    assert response.status_code == 404


def test_recommend_503_without_api_key(session_factory, monkeypatch):
    _seed(session_factory)
    monkeypatch.setattr(product_recommendation, "ANTHROPIC_API_KEY", "")

    response = client.post("/api/products/recommend", json={"product_type": "deposit"})

    assert response.status_code == 503


def test_recommend_502_on_refusal(session_factory, monkeypatch):
    _seed(session_factory)
    _fake_client(monkeypatch, _FakeMessages(SimpleNamespace(stop_reason="refusal", parsed_output=None, model="m")))

    response = client.post("/api/products/recommend", json={"product_type": "deposit"})

    assert response.status_code == 502


def test_recommend_502_when_ai_unreachable(session_factory, monkeypatch):
    _seed(session_factory)
    error = anthropic.APIConnectionError(request=None)
    _fake_client(monkeypatch, _FakeMessages(error=error))

    response = client.post("/api/products/recommend", json={"product_type": "deposit"})

    assert response.status_code == 502


def test_recommend_rejects_currency_type(session_factory):
    response = client.post("/api/products/recommend", json={"product_type": "currency"})

    assert response.status_code == 422
