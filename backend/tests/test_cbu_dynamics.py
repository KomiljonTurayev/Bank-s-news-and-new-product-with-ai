from datetime import date, timedelta

import pytest

from app.connectors import cbu_dynamics
from app.connectors.cbu_dynamics import (
    TRACKED_CODES,
    fetch_all_histories,
    stats_for_window,
    window_for_days,
)


def _points(*values_ago_days):
    """(qiymat, necha kun oldin) juftliklaridan {date, value} ro'yxati yasaydi."""
    today = date.today()
    points = [
        {"date": (today - timedelta(days=days_ago)).isoformat(), "value": value}
        for value, days_ago in values_ago_days
    ]
    points.sort(key=lambda p: p["date"])
    return points


def test_stats_for_window_computes_min_avg_max_current():
    points = _points((100.0, 10), (120.0, 5), (110.0, 0))

    stats = stats_for_window(points, days=None)

    assert stats["min"] == 100.0
    assert stats["max"] == 120.0
    assert stats["avg"] == 110.0
    assert stats["current"] == 110.0
    assert stats["samples"] == 3


def test_stats_for_window_filters_to_recent_days():
    points = _points((50.0, 400), (100.0, 10), (200.0, 1))

    stats = stats_for_window(points, days=30)

    assert stats["min"] == 100.0
    assert stats["max"] == 200.0
    assert stats["samples"] == 2


def test_stats_for_window_computes_change_percent():
    points = _points((100.0, 10), (110.0, 0))

    stats = stats_for_window(points, days=30)

    assert stats["change_pct"] == 10.0


def test_stats_for_window_returns_none_for_empty_history():
    assert stats_for_window([], days=30) is None


def test_stats_for_window_falls_back_to_latest_point_when_window_is_empty():
    points = _points((100.0, 500),)

    stats = stats_for_window(points, days=7)

    assert stats["samples"] == 1
    assert stats["current"] == 100.0


def test_window_for_days_returns_full_history_when_days_is_none():
    points = _points((50.0, 400), (100.0, 10))

    assert window_for_days(points, None) == points


def test_window_for_days_filters_and_falls_back_to_latest():
    points = _points((50.0, 400), (100.0, 10), (200.0, 1))

    assert len(window_for_days(points, 30)) == 2
    assert window_for_days(points, 1) == points[-1:]


@pytest.fixture(autouse=True)
def _clean_snapshot():
    """Testlar orasida 'oxirgi yaxshi tarix' holati oqib qolmasin."""
    cbu_dynamics._last_good.clear()
    yield
    cbu_dynamics._last_good.clear()


def test_one_dead_currency_does_not_lose_the_others(monkeypatch):
    def fake_fetch(code):
        if code == "USD":
            raise TimeoutError("cbu.uz javob bermayapti")
        return _points((1.0, 1))

    monkeypatch.setattr(cbu_dynamics, "fetch_history", fake_fetch)

    histories = fetch_all_histories(["USD", "EUR", "RUB"])

    assert set(histories) == {"EUR", "RUB"}


def test_previously_fetched_history_survives_later_failure(monkeypatch):
    monkeypatch.setattr(cbu_dynamics, "fetch_history", lambda code: _points((1.0, 1)))
    assert set(fetch_all_histories(["USD", "EUR"])) == {"USD", "EUR"}

    monkeypatch.setattr(cbu_dynamics, "fetch_history", _dead)

    histories = fetch_all_histories(["USD", "EUR"])

    assert set(histories) == {"USD", "EUR"}  # diagrammalar bo'shashmaydi


def test_all_currencies_dead_and_nothing_cached_raises(monkeypatch):
    monkeypatch.setattr(cbu_dynamics, "fetch_history", _dead)

    with pytest.raises(RuntimeError):
        fetch_all_histories(TRACKED_CODES)


def _dead(code):
    raise TimeoutError("cbu.uz o'lik")
