"""HTTP transportining chidamllik xulq-atvori: tez ulanish uzilishi,
vaqtinchalik xatoga bitta qayta-urinish, nosoz hostni vaqtincha chetga
surish — va bularning hech biri qolgan manbalarga tegamasligi."""

import pytest
import requests

from app.connectors.http import DEFAULT_TIMEOUT, HttpFetcher
from app.resilience import CircuitBreakerOpen, breaker_for, breaker_statuses


class _Response:
    def __init__(self, status_code=200, text="<html>ok</html>"):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.exceptions.HTTPError(f"{self.status_code}")
            error.response = self
            raise error


def _fetcher(**kwargs):
    kwargs.setdefault("retry_backoff", 0)
    return HttpFetcher(**kwargs)


def test_connect_timeout_is_shorter_than_read_timeout():
    connect, read = DEFAULT_TIMEOUT
    assert connect < read
    # Ulanish uzilgan host javob kutish davomida Emas, bir necha soniyada chetlanadi.
    assert connect <= 10


def test_transient_error_is_retried_once(monkeypatch):
    calls = []

    def flaky(url, headers=None, timeout=None, params=None):
        calls.append(url)
        if len(calls) == 1:
            raise requests.exceptions.ConnectionError("ulanish uzildi")
        return _Response()

    monkeypatch.setattr(requests, "get", flaky)
    assert _fetcher().text("https://cbu.uz/uz/keys/") == "<html>ok</html>"
    assert len(calls) == 2


def test_client_error_is_not_retried_and_does_not_trip_breaker(monkeypatch):
    calls = []

    def gone(url, headers=None, timeout=None, params=None):
        calls.append(url)
        return _Response(404)

    monkeypatch.setattr(requests, "get", gone)
    fetcher = _fetcher()
    for _ in range(10):
        with pytest.raises(requests.exceptions.HTTPError):
            fetcher.text("https://bank.uz/uz/missing")
    assert len(calls) == 10  # qayta-urinish yo'q
    assert not breaker_statuses()[0]["open"]  # sayt tirik, faqat manzil yo'q


def test_dead_host_is_set_aside_without_calling_it_again(monkeypatch):
    calls = []

    def dead(url, headers=None, timeout=None, params=None):
        calls.append(url)
        raise requests.exceptions.ConnectionError("host javob bermayapti")

    monkeypatch.setattr(requests, "get", dead)
    breaker = breaker_for("olik-sayt.uz")
    for _ in range(breaker.failure_threshold):
        fetcher = _fetcher(retries=0)
        with pytest.raises(requests.exceptions.ConnectionError):
            fetcher.text("https://olik-sayt.uz/uz/")

    assert breaker_statuses() == [
        {"source": "olik-sayt.uz", "open": True, "consecutive_failures": breaker.failure_threshold}
    ]
    # Breaker ochiq — endi tarmoqqa so'rov chiqmaydi, pool band bo'lmaydi.
    before = len(calls)
    open_breaker_fetcher = _fetcher(retries=0)
    with pytest.raises(CircuitBreakerOpen):
        open_breaker_fetcher.text("https://olik-sayt.uz/uz/boshqa-sahifa")
    assert len(calls) == before


def test_one_dead_host_does_not_block_others(monkeypatch):
    calls = []

    def selective(url, headers=None, timeout=None, params=None):
        calls.append(url)
        if "olik-sayt.uz" in url:
            raise requests.exceptions.ConnectionError("host javob bermayapti")
        return _Response()

    monkeypatch.setattr(requests, "get", selective)
    fetcher = _fetcher(retries=0)
    breaker = breaker_for("olik-sayt.uz")
    for _ in range(breaker.failure_threshold):
        with pytest.raises(requests.exceptions.ConnectionError):
            fetcher.text("https://olik-sayt.uz/uz/")

    # Bitta o'lik sayt qolgan manbalarni sekinlashtirmaydi yoki to'xtatmaydi.
    assert fetcher.text("https://ishlaydigan.uz/uz/") == "<html>ok</html>"


def test_pages_skips_broken_pages_but_keeps_the_rest(monkeypatch):
    def intermittent(url, headers=None, timeout=None, params=None):
        if url.endswith("/2"):
            raise requests.exceptions.ConnectionError("ulanish uzildi")
        return _Response()

    monkeypatch.setattr(requests, "get", intermittent)
    fetcher = _fetcher(retries=0)
    pages = fetcher.pages(
        ["https://bank.uz/p/1", "https://bank.uz/p/2", "https://bank.uz/p/3"],
        "BANK",
    )
    assert [url for url, _html in pages] == ["https://bank.uz/p/1", "https://bank.uz/p/3"]
