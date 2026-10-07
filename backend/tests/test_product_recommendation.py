"""AI mahsulot tavsiyasi (`POST /api/products/recommend`) — Claude API
soxtalashtiriladi, tarmoqqa chiqilmaydi."""

from datetime import datetime, timezone
from types import SimpleNamespace

import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient

from app import product_recommendation
from app.api import app
from app.models import BankRate
from app.product_recommendation import MarketPick, RecommendationResult, RecommendedProduct

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
        goal_on_topic=True,
        market_overview="Omonat stavkalari 18-21% oralig'ida.",
        # #99 — ro'yxatda yo'q, ikkinchi #1 — takror: ikkalasi ham tashlanadi.
        market_leaders=[
            MarketPick(offer_no=1, why="Eng yuqori stavka"),
            MarketPick(offer_no=99, why="to'qima"),
            MarketPick(offer_no=1, why="takror"),
            MarketPick(offer_no=2, why="Davlat banki"),
        ],
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
    # Bozor yetakchilari: bank/nom/stavka/havola AI'dan emas, bazadan olinadi.
    leaders = body["market_leaders"]
    assert [(lead["bank_code"], lead["name"], lead["rate"]) for lead in leaders] == [
        ("SQB", "Jamg'arma", 21.0),
        ("NBU", "Hamma uchun", 18.0),
    ]
    assert leaders[0]["url"] == "https://x" and leaders[0]["why"] == "Eng yuqori stavka"
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


def test_recommend_hides_raw_ai_error_on_bad_request(session_factory, monkeypatch):
    _seed(session_factory)
    raw = "This API key is not scoped to a workspace"
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    error = anthropic.BadRequestError(raw, response=httpx.Response(400, request=request), body=None)
    _fake_client(monkeypatch, _FakeMessages(error=error))

    response = client.post("/api/products/recommend", json={"product_type": "deposit"})

    assert response.status_code == 503
    assert raw not in response.json()["detail"]


@pytest.mark.parametrize("goal", ["yoshlar uchun fuck omonat", "СУКА кредит", "jalablar uchun", "f*ck", "порно карта"])
def test_recommend_rejects_inappropriate_goal_without_calling_ai(session_factory, monkeypatch, goal):
    _seed(session_factory)
    messages = _FakeMessages(SimpleNamespace(stop_reason="end_turn", parsed_output=_result(), model="m"))
    _fake_client(monkeypatch, messages)

    response = client.post("/api/products/recommend", json={"product_type": "deposit", "goal": goal})

    assert response.status_code == 422
    assert messages.calls == []


@pytest.mark.parametrize(
    "goal",
    ["yoshlar uchun omonat", "Ipoteka uchun sekin o'suvchi stavka", "Сексуальная? нет — бизнес-карта", "Sikl bo'yicha kredit", "jismoniy shaxslar uchun karta"],
)
def test_input_guard_allows_normal_banking_text(goal):
    from app.input_guard import is_inappropriate

    # "Сексуальная" — ataylab: 18+ ildizi so'z boshida bo'lsa ushlanadi.
    assert is_inappropriate(goal) is ("Сексуальная" in goal)


def test_recommend_rejects_off_topic_goal(session_factory, monkeypatch):
    _seed(session_factory)
    off_topic = _result().model_copy(update={"goal_on_topic": False})
    _fake_client(monkeypatch, _FakeMessages(SimpleNamespace(stop_reason="end_turn", parsed_output=off_topic, model="m")))

    response = client.post("/api/products/recommend", json={"product_type": "deposit", "goal": "ertaga ob-havo qanday?"})

    assert response.status_code == 422
    assert "bank mahsulotlari" in response.json()["detail"]


def test_market_leaders_ranks_uzs_individual_offers_one_per_bank(session_factory):
    with session_factory() as session:
        now = datetime.now(timezone.utc)
        for bank, name, rate, segment, extra in [
            ("SQB", "Jamg'arma", "21%", "individual", {}),
            ("SQB", "Ikkinchi", "20%", "individual", {}),  # bir bankdan faqat eng yaxshisi
            ("NBU", "Hamma uchun", "18%", "individual", {"Muddati": "12 oy", "Summa": "100 000 so'mdan"}),
            ("KDB", "Dollar", "30%", "individual", {"Valyuta": "USD"}),  # valyuta — chiqariladi
            ("XB", "Biznes", "25%", "legal", {}),  # yuridik — chiqariladi
        ]:
            session.add(
                BankRate(
                    bank_code=bank,
                    product_type="deposit",
                    segment=segment,
                    data={"name": name, "Foiz stavkasi": rate, "url": "https://x", **extra},
                    fetched_at=now,
                )
            )
        session.commit()

    response = client.get("/api/products/market-leaders", params={"product_type": "deposit"})

    assert response.status_code == 200
    leaders = response.json()
    assert [(lead["bank_code"], lead["rate"]) for lead in leaders] == [("SQB", 21.0), ("NBU", 18.0)]
    assert leaders[1]["term"] == "12 oy" and leaders[1]["amount"] == "100 000 so'mdan"
    assert leaders[0]["why"] is None


def test_market_leaders_credit_prefers_lowest_realistic_rate(session_factory):
    with session_factory() as session:
        now = datetime.now(timezone.utc)
        for bank, rate in [("SQB", "24%"), ("NBU", "19%"), ("XB", "0% dan")]:
            session.add(
                BankRate(bank_code=bank, product_type="credit", segment="individual", data={"name": "K", "Foiz": rate}, fetched_at=now)
            )
        session.commit()

    leaders = client.get("/api/products/market-leaders", params={"product_type": "credit"}).json()

    assert [lead["bank_code"] for lead in leaders] == ["NBU", "SQB"]
