import pytest

from app.resilience import CircuitBreaker, CircuitBreakerOpen, breaker_for, reset_breakers


def _ok():
    return "ok"


def _boom():
    raise RuntimeError("manba o'lik")


@pytest.fixture(autouse=True)
def _fresh_registry():
    reset_breakers()
    yield
    reset_breakers()


def test_closed_breaker_passes_calls_through():
    breaker = CircuitBreaker("test.uz", failure_threshold=3, recovery_seconds=10)
    assert breaker.call(_ok) == "ok"


def test_opens_after_threshold_and_refuses_without_calling():
    calls = []
    breaker = CircuitBreaker("test.uz", failure_threshold=2, recovery_seconds=10, clock=lambda: 0.0)

    for _ in range(2):
        with pytest.raises(RuntimeError):
            breaker.call(_boom)
        calls.append(1)

    with pytest.raises(CircuitBreakerOpen):
        breaker.call(_ok)  # chaqiruvmanbaga yuborilmaydi
    assert len(calls) == 2


def test_trial_after_recovery_reopens_on_failure_and_refuses_others():
    now = [0.0]
    breaker = CircuitBreaker("test.uz", failure_threshold=1, recovery_seconds=10, clock=lambda: now[0])

    with pytest.raises(RuntimeError):
        breaker.call(_boom)
    with pytest.raises(CircuitBreakerOpen):
        breaker.call(_ok)

    now[0] = 10.0  # tiklanish oynasi tugadi — bitta sinov o'tadi
    with pytest.raises(RuntimeError):
        breaker.call(_boom)
    # sinov ham xato bergach breaker qayta ochiladi
    now[0] = 10.5
    with pytest.raises(CircuitBreakerOpen):
        breaker.call(_ok)


def test_successful_trial_closes_the_breaker():
    now = [0.0]
    breaker = CircuitBreaker("test.uz", failure_threshold=1, recovery_seconds=10, clock=lambda: now[0])

    with pytest.raises(RuntimeError):
        breaker.call(_boom)
    now[0] = 10.0
    assert breaker.call(_ok) == "ok"
    # yopildi — oddiy oqim tiklandi
    assert breaker.call(_ok) == "ok"


def test_success_resets_the_consecutive_counter():
    breaker = CircuitBreaker("test.uz", failure_threshold=3, recovery_seconds=10, clock=lambda: 0.0)
    with pytest.raises(RuntimeError):
        breaker.call(_boom)
    breaker.call(_ok)  # ketma-ketlik uzildi
    with pytest.raises(RuntimeError):
        breaker.call(_boom)
    with pytest.raises(RuntimeError):
        breaker.call(_boom)
    # endigina 2 ta ketma-ket xato — breaker hali yopiq
    assert breaker.call(_ok) == "ok"


def test_registry_shares_one_breaker_per_name():
    first = breaker_for("cbu.uz")
    assert breaker_for("cbu.uz") is first
    assert breaker_for("depozit.uz") is not first
    with pytest.raises(RuntimeError):
        first.call(_boom)
    # ikkincha chaqiruv bitta host hisob-kitobiga qo'shiladi
    same_breaker = breaker_for("cbu.uz")
    with pytest.raises(RuntimeError):
        same_breaker.call(_boom)


def test_reset_breakers_clears_state():
    breaker = breaker_for("cbu.uz")
    for _ in range(5):
        with pytest.raises(RuntimeError):
            breaker.call(_boom)
    with pytest.raises(CircuitBreakerOpen):
        breaker.call(_ok)

    reset_breakers()
    assert breaker_for("cbu.uz").call(_ok) == "ok"
