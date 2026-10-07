import threading

import pytest

from app.ttl_cache import TTLCache


def test_caches_the_loader_result_between_calls():
    calls = []

    def loader():
        calls.append(1)
        return "value"

    cache = TTLCache(loader, ttl_seconds=3600)

    assert cache.get() == "value"
    assert cache.get() == "value"
    assert len(calls) == 1


def test_reloads_after_ttl_expires(monkeypatch):
    calls = []

    def loader():
        calls.append(1)
        return f"value-{len(calls)}"

    current_time = [1000.0]
    monkeypatch.setattr("app.ttl_cache.time.time", lambda: current_time[0])
    cache = TTLCache(loader, ttl_seconds=10)

    assert cache.get() == "value-1"

    current_time[0] += 11  # TTL (10s) dan tashqariga chiqadi
    assert cache.get() == "value-2"
    assert len(calls) == 2


def test_loader_exception_propagates_and_is_retried_next_call():
    calls = []

    def loader():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("boom")
        return "recovered"

    cache = TTLCache(loader, ttl_seconds=3600)

    with pytest.raises(RuntimeError):
        cache.get()

    assert cache.get() == "recovered"


def test_last_good_value_is_served_when_refresh_fails(monkeypatch):
    calls = []
    current_time = [1000.0]
    monkeypatch.setattr("app.ttl_cache.time.time", lambda: current_time[0])

    def loader():
        calls.append(1)
        if len(calls) > 1:
            raise TimeoutError("manba javob bermayapti")
        return "jonli"

    cache = TTLCache(loader, ttl_seconds=10)
    assert cache.get() == "jonli"

    current_time[0] += 11
    assert cache.get() == "jonli"  # xato chaqiruvchiga yetib bormadi
    assert cache.get() == "jonli"
    assert len(calls) >= 2  # urinish bo'ldi, lekin natija eski qiymat bilan yopildi


def test_cold_cache_fails_fast_during_backoff(monkeypatch):
    calls = []
    current_time = [1000.0]
    monkeypatch.setattr("app.ttl_cache.time.time", lambda: current_time[0])

    def loader():
        calls.append(1)
        raise TimeoutError("manba o'lik")

    cache = TTLCache(loader, ttl_seconds=10, retry_backoff_seconds=60)

    with pytest.raises(TimeoutError):
        cache.get()
    for _ in range(5):
        with pytest.raises(TimeoutError):
            cache.get()
    assert len(calls) == 1  # qolganlari backoff ichida darrov rad etildi

    current_time[0] += 61
    with pytest.raises(TimeoutError):
        cache.get()
    assert len(calls) == 2  # backoff tugadi — yana bir marta uranildi


def test_only_one_loader_runs_for_many_concurrent_callers():
    calls = []
    release = threading.Event()
    started = threading.Event()

    def loader():
        calls.append(1)
        started.set()
        release.wait(timeout=5)
        return "value"

    cache = TTLCache(loader, ttl_seconds=3600)
    results = []

    def caller():
        results.append(cache.get())

    first = threading.Thread(target=caller)
    first.start()
    assert started.wait(timeout=5)

    waiters = [threading.Thread(target=caller) for _ in range(8)]
    for thread in waiters:
        thread.start()
    assert not calls[1:]  # hech kim ikkinchi marta yuklamadi
    release.set()

    first.join(timeout=5)
    for thread in waiters:
        thread.join(timeout=5)

    assert len(calls) == 1
    assert results == ["value"] * 9


def test_stale_value_is_returned_without_waiting_for_the_refresh(monkeypatch):
    current_time = [1000.0]
    monkeypatch.setattr("app.ttl_cache.time.time", lambda: current_time[0])
    loaded_once = threading.Event()
    refresh_started = threading.Event()
    release = threading.Event()

    def loader():
        if loaded_once.is_set():
            refresh_started.set()
            release.wait(timeout=5)
            return "yangi"
        loaded_once.set()
        return "jonli"

    cache = TTLCache(loader, ttl_seconds=10)
    assert cache.get() == "jonli"
    current_time[0] += 11  # TTL tugadi — foni yangilanadi

    leader_returned = []
    leader = threading.Thread(target=lambda: leader_returned.append(cache.get()))
    leader.start()
    assert refresh_started.wait(timeout=5)

    stale_returned = threading.Event()

    def follower():
        if cache.get() == "jonli":
            stale_returned.set()

    second = threading.Thread(target=follower)
    second.start()
    # Eski qiymat bor — yuklovchi tugashini kutmasdan darrov qaytadi.
    assert stale_returned.wait(timeout=1)

    release.set()
    leader.join(timeout=5)
    second.join(timeout=5)
    assert leader_returned == ["yangi"]


def test_waiter_gives_up_after_the_refresh_wait_deadline():
    """Transport timeouti ham yordam bermagan holat (javobsiz proksi) —
    navbatdagi oqim yetakchini cheksiz kutmaydi, aks holda FastAPI thread
    pool'i bitta o'lik manba bilan to'lib qolardi."""
    started = threading.Event()
    release = threading.Event()

    def loader():
        started.set()
        release.wait(timeout=10)
        return "value"

    cache = TTLCache(loader, ttl_seconds=3600, refresh_wait_seconds=0.05, name="cbu_tarixi")

    leader = threading.Thread(target=cache.get, daemon=True)
    leader.start()
    assert started.wait(timeout=5)

    errors = []

    def waiter():
        try:
            cache.get()
        except TimeoutError as error:
            errors.append(error)

    waiting = threading.Thread(target=waiter)
    waiting.start()
    waiting.join(timeout=5)

    assert not waiting.is_alive(), "kutuvchi cheksiz kutib qoldi"
    assert len(errors) == 1
    assert "cbu_tarixi" in str(errors[0])

    release.set()
    leader.join(timeout=10)


def test_loader_is_called_outside_the_lock():
    """Yuklovchi lock TASHQARISIDA chaqirilishi shart — bitta sekin kalit
    qolgan kalitlarning (valyuta, inflyatsiya, xabarlar) so'rovlarini
    bloklab qo'ymasligi uchun."""
    observed = []

    def loader():
        # Lock bizda bo'lmasagina olish mumkin; olsak darrov qaytamiz.
        acquired = cache._lock.acquire(blocking=False)
        observed.append(acquired)
        if acquired:
            cache._lock.release()
        return 5

    cache = TTLCache(loader, ttl_seconds=60, name="lock-scope")

    assert cache.get() == 5
    assert observed == [True]


def test_leader_marks_itself_inflight_for_the_duration_of_the_load():
    """Yuklash ketayotgan davrda `_inflight` to'ldirilgan bo'ladi — aks holda
    shu orada kelgan ikkinchi oqim ham qimmat yuklovchini ishga tushirardi
    (thundering herd). Yuklash tugagach iz qolmaydi."""
    seen = []

    def loader():
        seen.append(cache._inflight is not None)
        return 7

    cache = TTLCache(loader, ttl_seconds=60, name="leader-flag")

    assert cache.get() == 7
    assert seen == [True]
    assert cache._inflight is None

