"""Connectorlar uchun yagona HTTP transport qatlami.

Avval har bir connector o'zining `_HEADERS` konstantasini va bir xil
to'rt qatorli `requests.get(...) / raise_for_status() / return .text`
tanasini takrorlar edi (37 ta faylda) — natijada timeout, User-Agent yoki
xatolarga munosabat qoidasini o'zgartirish 37 joyni tahrirlashni talab
qilardi. Bu modul shu qarorlarni bitta joyga yig'adi; connectorlar esa
faqat "qaysi manzil" va "qanday parse qilinadi" degan o'z mas'uliyatida
qoladi.

Diqqat: `requests.get` modul atributi sifatida chaqiriladi (import
vaqtida nomga bog'lanmaydi), shu bois testlar uni odatdagidek
`monkeypatch.setattr(requests, "get", ...)` bilan almashtira oladi."""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlsplit

import requests

from app import outbound
from app.resilience import CircuitBreakerOpen, breaker_for

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "Mozilla/5.0"
# Ulanish (connect) bilan javob kutish (read) ikki xil kasallik: ulanish
# uzilgan/yopiq hostda bir necha soniyada, "tirik" lekin sekin API'da esa
# undan ancha ko'p vaqt ketadi. Bittasini ikkinchisiga teng qilib bo'lmaydi —
# ulanishga uzoq kutish butun scraping pool'ni bitta o'lik IP band qilib
# turadi, shu bois ular alohida beriladi.
DEFAULT_CONNECT_TIMEOUT_SECONDS = 5
DEFAULT_READ_TIMEOUT_SECONDS = 20
DEFAULT_TIMEOUT: tuple[float, float] = (
    DEFAULT_CONNECT_TIMEOUT_SECONDS,
    DEFAULT_READ_TIMEOUT_SECONDS,
)
DEFAULT_RETRIES = 1
DEFAULT_RETRY_BACKOFF_SECONDS = 0.5


def _host_of(url: str) -> str:
    return urlsplit(url).hostname or url


def _is_source_outage(error: BaseException) -> bool:
    """Xato manbaning o'zi nosozligidanmi, yo'qmi?

    Tarmoq xatolari (ulanish uzildi, timeout) va server tomonidagi 5xx/429 —
    ha. 4xx (manzil ko'chgan, sayt dizayni o'zgargan) va parse xatolari —
    yo'q: bunday holda hostning qolgan qismi ishlayapti, butun saytni chetga
    surish ma'lumotni yo'qotish bo'lardi."""
    if isinstance(error, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
        return True
    if isinstance(error, requests.exceptions.HTTPError):
        # `raise_for_status()` har doim javobni biriktiradi; javobsiz
        # HTTPError — sun'iy holat, statusini bilmaymiz. Noma'lum statusni
        # "nosoz" demaymiz: nohaq qayta-urinish nohaq kutish degani.
        response = error.response
        if response is None:
            return False
        return response.status_code >= 500 or response.status_code == 429
    return False


class HttpFetcher:
    """Bitta manba (sayt yoki API) uchun sozlangan HTTP o'quvchi.

    Har bir connector o'ziga mos sarlavha/timeout bilan nusxa yaratadi;
    qo'shimcha sozlama kerak bo'lmasa, modulning umumiy `HTTP` nusxasi
    ishlatiladi."""

    def __init__(
        self,
        headers: dict[str, str] | None = None,
        timeout: float | tuple[float, float] = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    ):
        self.headers = {"User-Agent": DEFAULT_USER_AGENT, **(headers or {})}
        self.timeout = timeout
        self.retries = retries
        self.retry_backoff = retry_backoff

    def with_headers(self, **extra: str) -> "HttpFetcher":
        """Shu sozlamalarning qo'shimcha sarlavhali nusxasini qaytaradi —
        masalan AJAX endpointlari uchun "Referer"/"X-Requested-With"."""
        return HttpFetcher(
            {**self.headers, **extra},
            self.timeout,
            retries=self.retries,
            retry_backoff=self.retry_backoff,
        )

    def _attempt(self, url: str, params: dict[str, Any] | None) -> requests.Response:
        # Host tanaffusi (app/outbound.py) — breaker ichida, lekin urinishdan
        # oldin: kutish muvaffaqiyatsiz urinish EMAS, shu bois hisoblagichga
        # tekisilmaydi. Har qayta-urinish ham shu tanaffusdan o'tadi, ya'ni
        # "500 qaytardi, darhol yana" degan hujum shakli ham yo'qoladi.
        outbound.wait_for_host(_host_of(url))
        # timeout ochiq ko'rinishda uzatiladi: `**kwargs` orqali yuborilganda
        # bandit B113 uni ko'rmay, noto'g'ri ogohlantiradi.
        response = requests.get(url, headers=self.headers, timeout=self.timeout, params=params)
        response.raise_for_status()
        return response

    def _get(self, url: str, params: dict[str, Any] | None) -> requests.Response:
        """Bitta so'rov — cheklangan qayta-urinish + host breaker bilan.

        Qayta-urinish faqat vaqtinchalik xatolarga qo'llanadi va soni
        cheklangan: manba chindan ham o'lik bo'lsa "ko'proq urish" uni
        tiklamaydi, faqat ishchi thread'larni band qilib, navbatdagi
        banklarni och qoldiradi. Breaker esa shu urinishlarning yakuniy
        natijasini ko'radi — har birini emas."""
        return breaker_for(_host_of(url)).call(
            self._get_with_retries, url, params, trips_on=_is_source_outage
        )

    def _get_with_retries(self, url: str, params: dict[str, Any] | None) -> requests.Response:
        attempt = 0
        while True:
            try:
                return self._attempt(url, params)
            except Exception as error:
                if attempt >= self.retries or not _is_source_outage(error):
                    raise
                delay = self.retry_backoff * (2**attempt)
                logger.debug(
                    "%s: vaqtinchalik xato (%s), %.1fs'dan keyin qayta uriladi (%d/%d)",
                    url, error, delay, attempt + 2, self.retries + 1,
                )
                time.sleep(delay)
                attempt += 1

    def text(self, url: str, params: dict[str, Any] | None = None) -> str:
        return self._get(url, params).text

    def utf8_text(self, url: str, params: dict[str, Any] | None = None) -> str:
        """Javobni majburan UTF-8 deb o'qiydi — ba'zi serverlar
        "Content-Type"da charset ko'rsatmaydi va `requests` shu sabab
        ISO-8859-1'ga tushib, "—" kabi belgilarni buzib qo'yadi."""
        return self._get(url, params).content.decode("utf-8")

    def json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        return self._get(url, params).json()

    def pages(self, urls: list[str], source: str) -> list[tuple[str, str]]:
        """Bir nechta sahifani ketma-ket yuklab, `(url, html)` juftliklarini
        qaytaradi.

        Ro'yxat sahifasi bo'lmagan banklarda har bir mahsulot o'z alohida
        (oldindan ma'lum) manzilidan olinadi — shunday hollarda bitta
        sahifaning 404/500 bo'lishi butun bankni ma'lumotsiz qoldirmasligi
        kerak, shu bois nosoz sahifa o'tkazib yuboriladi."""
        pages = []
        for url in urls:
            try:
                pages.append((url, self.text(url)))
            except (requests.RequestException, CircuitBreakerOpen):
                logger.warning("%s: %s yuklab bo'lmadi, o'tkazib yuborildi", source, url, exc_info=True)
        return pages


# Sozlama talab qilmaydigan connectorlar uchun umumiy nusxa.
HTTP = HttpFetcher()
