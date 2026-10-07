"""/api/meta/sources — "manbalar javob bermayaptimi, yoki biz chetga
surib qo'ydikmi?" degan savolga javob. Bu endpoint monitor uchun yagona
kuzatuv nuqtasi, shu sabab uning javob shakli ham shartnoma."""

from fastapi.testclient import TestClient

from app.api import app
from app.resilience import breaker_for

client = TestClient(app)


def _fail(host: str, times: int) -> None:
    breaker = breaker_for(host)
    for _ in range(times):
        try:
            breaker.call(lambda: (_ for _ in ()).throw(ConnectionError("o'lik sayt")))
        except ConnectionError:
            pass


def test_no_tripped_source_means_ok():
    body = client.get("/api/meta/sources").json()
    assert body["status"] == "ok"
    assert body["open_sources"] == 0
    assert body["sources"] == []


def test_single_failure_is_not_yet_an_outage():
    """Bitta uzilish — hali nosozlik emas: breaker ochilmagan, holat `ok`.
    Aks holda har bir tarqoq tarmoq xatosi monitorra "degraded" deb
    signal berardi, haqiqiy uzilish shu shovqin ichida ko'rinmasdi."""
    _fail("olikk.uz", 1)
    body = client.get("/api/meta/sources").json()
    assert body["status"] == "ok"
    assert body["open_sources"] == 0
    assert body["sources"] == [
        {"source": "olikk.uz", "open": False, "consecutive_failures": 1}
    ]


def test_open_breaker_is_degraded_not_failed():
    """Manba chetga surilganda holat `degraded`, xato EMAS: qolgan manbalar
    ishlayapti. Monitor HTTP 200 kutishi kerak, aks holda har bir nosoz sayt
    butun servis "down" bo'lgandek signal berardi."""
    breaker = breaker_for("olikk.uz")
    _fail("olikk.uz", breaker.failure_threshold)
    body = client.get("/api/meta/sources").json()
    assert body["status"] == "degraded"
    assert body["open_sources"] == 1
    assert body["sources"][0]["open"] is True
    assert client.get("/api/meta/sources").status_code == 200


def test_response_carries_the_outbound_policy(monkeypatch):
    """Ma'lumot nega yangilanmagani ko'pincha manbadan emas, bizning siyosatan
    keladi — shuning uchun javobda oyna va host tanaffusi ham bor."""
    monkeypatch.setattr(
        "app.routers.meta.policy_snapshot",
        lambda now=None: {
            "scrape_window": "07:00-21:00",
            "scrape_active_now": False,
            "min_host_interval_seconds": 2.0,
        },
    )
    body = client.get("/api/meta/sources").json()
    assert body["scrape_window"] == "07:00-21:00"
    assert body["scrape_active_now"] is False
    assert body["min_host_interval_seconds"] == 2.0
