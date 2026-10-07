"""Playwright yo'lining chidamlligi.

Bu yo'l `requests`ga qaraganda boshqacha xavfli: ochilmaydigan yoki bizni
bloklay qo'ygan sayt har bir sahifa uchun yangi headless Chromium
ishga tushiradi. Chegara bo'lmasa, bir necha bloklangan sayt bitta skreyping
siklini soatlab cho'zadi va navbatdagi tirik banklar ma'lumotsiz qoladi —
ya'ni bitta manba butun proektni sekinlashtiradi. Shu bois bu yerda ham
breaker + ochiq taym-outlar ishlashi shart, va ular `requests` yo'lidagi
bilan bir xil ma'noda bo'lishi kerak."""

import pytest

from app import outbound
from app.connectors import playwright_fetch as pf
from app.resilience import CircuitBreakerOpen, breaker_for, breaker_statuses

DEAD = "https://olik-sayt.uz/uz/products"
ALIVE = "https://tirik-sayt.uz/uz/products"


class _Recorder:
    def __init__(self):
        self.launches = 0
        self.launch_timeouts = []
        self.goto_timeouts = []
        self.closes = 0


class _FakePlaywright:
    """`sync_playwright()` o'rniga — haqiqiy brauzerni ochmay turib,
    qaysi bosqichda va qanday chegara bilan to'xtayotganimizni o'lchash uchun."""

    def __init__(self, recorder, on_goto=None):
        self._recorder = recorder
        self._on_goto = on_goto
        self.chromium = self

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def launch(self, timeout=None):
        self._recorder.launches += 1
        self._recorder.launch_timeouts.append(timeout)
        return _Browser(self._recorder, self._on_goto)


class _Browser:
    def __init__(self, recorder, on_goto):
        self._recorder = recorder
        self._on_goto = on_goto

    def new_page(self, user_agent=None):
        return _Page(self._recorder, self._on_goto)

    def close(self):
        self._recorder.closes += 1


class _Page:
    def __init__(self, recorder, on_goto):
        self._recorder = recorder
        self._on_goto = on_goto

    def goto(self, url, wait_until=None, timeout=None):
        self._recorder.goto_timeouts.append(timeout)
        if self._on_goto is not None:
            self._on_goto(url)

    def wait_for_timeout(self, ms):
        return None

    def content(self):
        return "<html>rendered</html>"


def _install(monkeypatch, recorder, on_goto=None):
    monkeypatch.setattr(pf, "sync_playwright", lambda: _FakePlaywright(recorder, on_goto))
    return recorder


def _network_error(url):
    def on_goto(target):
        if target == url:
            raise pf.PlaywrightError("net::ERR_CONNECTION_TIMED_OUT at " + target)

    return on_goto


def _trip(host, error_type, url):
    """Host breaker'ni ochirguncha nosozlikka uchratadi — ochiq holatdan
        keyingi xatti-harakatni sinash uchun poydevor."""
    breaker = breaker_for(host)
    for _ in range(breaker.failure_threshold):
        with pytest.raises(error_type):
            pf.fetch_rendered_html(url)
    return breaker


def test_timeouts_are_bounded():
    """Bloklangan sahifa bir daqiqani emas, o'nlab soniyani egallaydi:
    chaqiruv allaqachon breaker orqasida, shu bois bitta sahifani uzoq
    ushlab turishga sabab yo'q. Brauzer ishga tushishi ham cheksiz
    qolmasligi kerak — driver yoki antivirus osilib qolsa, bitta connector
    butun ishchi pool'ni band qilib qo'ymasligi uchun."""
    assert 0 < pf.BROWSER_LAUNCH_TIMEOUT_MS <= 30_000
    assert 0 < pf.DEFAULT_NAVIGATION_TIMEOUT_MS <= 30_000


def test_every_stage_receives_an_explicit_timeout(monkeypatch):
    recorder = _install(monkeypatch, _Recorder())

    assert pf.fetch_rendered_html(ALIVE) == "<html>rendered</html>"

    assert recorder.launch_timeouts == [pf.BROWSER_LAUNCH_TIMEOUT_MS]
    assert recorder.goto_timeouts == [pf.DEFAULT_NAVIGATION_TIMEOUT_MS]


def test_dead_site_is_set_aside_without_launching_a_browser_again(monkeypatch):
    recorder = _install(monkeypatch, _Recorder(), on_goto=_network_error(DEAD))
    breaker = _trip("olik-sayt.uz", pf.PlaywrightError, DEAD)

    assert breaker_statuses() == [
        {"source": "olik-sayt.uz", "open": True, "consecutive_failures": breaker.failure_threshold}
    ]

    # Shu testning mohi: breaker ochiq bo'lsa Chromium umuman ishga
    # tushirilmaydi — aks holda "chetga surish" hech narsa tejamas,
    # chunki eng qimmat qism brauzerning o'zi.
    launches_before = recorder.launches
    with pytest.raises(CircuitBreakerOpen):
        pf.fetch_rendered_html(DEAD)
    assert recorder.launches == launches_before


def test_broken_browser_install_does_not_blacklist_the_bank(monkeypatch):
    """`playwright install` bajarilmagan bo'lsa yoki brauzer o'chirilsa, bu
    xato barcha banklarga bir xil tegradi — lekin aybdor ular emas. Hostni
    bloklab sozlash xatosini "sayt o'ldi" deb yashirish noto'g'ri, ochiq
    breaker esa tirik saytlarni ham o'chirilgan ko'rsatib qo'yardi."""

    def no_browser(url):
        raise pf.PlaywrightError("Executable doesn't exist at C:\\ms-playwright\\chrome")

    recorder = _install(monkeypatch, _Recorder(), on_goto=no_browser)
    for _ in range(10):
        with pytest.raises(pf.PlaywrightError):
            pf.fetch_rendered_html(ALIVE)

    assert recorder.launches == 10  # har urinishda brauzer ochilgan, ammo...
    assert breaker_statuses() == [
        {"source": "tirik-sayt.uz", "open": False, "consecutive_failures": 0}
    ]  # ...host "nosoz" deb belgilanmagan.


def test_one_dead_site_does_not_stop_the_others(monkeypatch):
    def on_goto(url):
        if url == DEAD:
            raise pf.PlaywrightError("net::ERR_EMPTY_RESPONSE at " + url)

    _install(monkeypatch, _Recorder(), on_goto=on_goto)
    _trip("olik-sayt.uz", pf.PlaywrightError, DEAD)

    # Bitta o'lik sayt qolgan manbalarni to'xtatmaydi.
    assert pf.fetch_rendered_html(ALIVE) == "<html>rendered</html>"


def test_timeout_counts_as_source_outage(monkeypatch):
    def hang(url):
        raise pf.PlaywrightTimeoutError("Timeout 20000ms exceeded")

    recorder = _install(monkeypatch, _Recorder(), on_goto=hang)
    breaker = _trip("tirik-sayt.uz", pf.PlaywrightTimeoutError, ALIVE)

    # Hech qachon javob bermaydigan sayt — bloklovchi WAF belgisi, chetga suriladi.
    assert breaker_statuses()[0]["open"] is True
    assert recorder.launches == breaker.failure_threshold


def test_playwright_path_honours_the_host_pacer(monkeypatch):
    """Tashqiga chiqish siyosati: host tanaffusi `requests`da ham, brauzerda
    ham bir xil ishlaydi — anti-bot uchun so'rov qaysi transportdan
    kelgani farq qilmaydi, muhimi bitta hostga tushadigan chastota."""
    seen = []
    _install(monkeypatch, _Recorder())
    monkeypatch.setattr(outbound, "wait_for_host", seen.append)

    pf.fetch_rendered_html(DEAD)
    pf.fetch_rendered_html(ALIVE)

    assert seen == ["olik-sayt.uz", "tirik-sayt.uz"]


def test_browser_is_closed_even_when_the_page_fails(monkeypatch):
    """Har chaqiriqda yangi Chromium ochiladi — yopilmasa protsesslar
    yig'ilib, xotira osilib boradi."""
    recorder = _install(monkeypatch, _Recorder(), on_goto=_network_error(DEAD))

    with pytest.raises(pf.PlaywrightError):
        pf.fetch_rendered_html(DEAD)

    assert recorder.closes == recorder.launches


def test_single_page_failure_does_not_lose_the_whole_bank(monkeypatch):
    """Ko'p sahifali conectorda bitta sahifa ochilmasa qolganlari
    saqlanishi kerak — breaker bu qoidani buzmasligi lozim."""
    from app.connectors.orient_finans import OrientFinansCardConnector

    _install(monkeypatch, _Recorder(), on_goto=_network_error("https://bank.uz/p/2"))
    connector = OrientFinansCardConnector(
        ["https://bank.uz/p/1", "https://bank.uz/p/2", "https://bank.uz/p/3"]
    )

    pages = connector.fetch_raw()

    assert [url for url, _html in pages] == ["https://bank.uz/p/1", "https://bank.uz/p/3"]


def test_open_breaker_does_not_lose_the_whole_bank(monkeypatch):
    """Manba hozir nosoz deb topilgan bo'lsa ham connector yiqilmasligi
    kerak: sahifa o'tkazib yuboriladi, qolgan manbalar ishlayveradi."""
    from app.connectors.orient_finans import OrientFinansCardConnector

    recorder = _install(monkeypatch, _Recorder(), on_goto=_network_error("https://bank.uz/p/1"))
    _trip("bank.uz", pf.PlaywrightError, "https://bank.uz/p/1")
    launches_after_trip = recorder.launches

    pages = OrientFinansCardConnector(["https://bank.uz/p/1"]).fetch_raw()

    assert pages == []  # xato ko'tarilmadi
    assert recorder.launches == launches_after_trip  # brauzer umuman ochilmadi
