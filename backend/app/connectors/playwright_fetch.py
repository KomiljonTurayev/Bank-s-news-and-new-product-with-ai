"""JavaScript orqali client-tomonda render qilinadigan sahifalar uchun —
oddiy `requests.get()` bunday saytlarda bo'sh skelet HTML qaytaradi, chunki
mahsulotlar ro'yxati React/Next.js kabi freymvorklar tomonidan sahifa
yuklangandan keyin qo'shiladi. Bu yordamchi haqiqiy (headless) brauzerda
sahifani ochib, JS ishga tushgandan keyingi to'liq HTML'ni qaytaradi.

Diqqat: bu oddiy `requests`ga qaraganda ancha sekin (~2-5 soniya/sahifa) va
xotira sarflaydi (har chaqiriqda yangi headless Chromium ishga tushadi) —
shu sabab faqat statik HTML yetarli bo'lmagan saytlar uchun ishlatiladi.

Bitta tuzoq shu yo'lda boshqasiga qaraganda qimmatroq tushadi: o'lik yoki
bizni bloklay qo'ygan sayt `requests`da 5 soniyada chetlanadi, brauzerda esa
har bir ochilish boshidan ishga tushirilgan Chromium bilan daqiqalab vaqt
oladi. Bloklovchi WAF bunday saytni "hech qachon javob bermaydigan" qilib
qo'yadi, biz esa har siklda, har bir mahsulot sahifasi uchun shu kutishni
takrorlaymiz — ~10 ta bloklangan sayt bitta siklni soatlab cho'zadi va
navbatdagi tirik banklar ma'lumotsiz qoladi. Shu bois bu yerda ham
`app/connectors/http.py`dagidagilar ishlaydi: host breaker'i (nosoz saytni
bir necha daqiqaga chetga suradi) va har bosqich uchun ochiq taym-out."""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app import outbound
from app.resilience import breaker_for

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# Chromium ishga tushishi manbaga bog'liq emas, lekin u ham cheksiz qolmasligi
# kerak: driver yoki antivirus sababli launch osilib qolsa, bitta connector
# butun ishchi pool'ni ushlab qolardi.
BROWSER_LAUNCH_TIMEOUT_MS = 15_000
# Sahifa ochilishi uchun chegara. Bu yerda 60s emas, ~20s tanlandi: chaqiruv
# allaqachon breaker orqasida, ya'ni bir marta sekinlagan manba keyingi
# urinishlarga umuman chiqilmaydi — har bir sahifani bir daqiqa ushlab turish
# uchun hech qanday sabab qolmaydi.
DEFAULT_NAVIGATION_TIMEOUT_MS = 20_000
DEFAULT_RENDER_WAIT_MS = 4_000


def _host_of(url: str) -> str:
    return urlsplit(url).hostname or url


def _is_source_outage(error: BaseException) -> bool:
    """Brauzer xatosi manbaning nosozligimidir, yoki bizning muhitnimidir?

    Playwright bitta `Error` turini ham tarmoq uzilishiga (`net::ERR_...`),
    ham brauzerning o'chiq bo'lishiga (`Executable doesn't exist`) ishlatadi.
    Farq muhim: o'chiq brauzer barcha manbalar uchun bir xil yomon, lekin
    aybdor ular emas — hostni bloklab, sozlash xatosini "sayt o'ldi" deb
    yashirish noto'g'ri bo'lardi."""
    if isinstance(error, PlaywrightTimeoutError):
        return True
    if isinstance(error, PlaywrightError):
        text = str(error).lower()
        return "net::err_" in text or "timeout" in text
    return False


def _open(url: str, wait_ms: int, timeout_ms: int) -> str:
    # Brauzer orqali bo'lsa ham xuddi shu host tanaffusi qo'llanadi:
    # anti-bot uchun so'rov `requests`danmi yoki Chromium'danmi kelgani
    # farq qilmaydi, muhimi bitta hostga tushadigan chastota.
    outbound.wait_for_host(_host_of(url))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(timeout=BROWSER_LAUNCH_TIMEOUT_MS)
        try:
            page = browser.new_page(user_agent=_USER_AGENT)
            page.goto(url, wait_until="load", timeout=timeout_ms)
            # `wait_ms` — "load" hodisasidan keyin qo'shimcha kutish (ko'p
            # SPA'larda ma'lumot fetch/render qilinishi biroz kech boshlanadi,
            # "networkidle" esa doimiy fon so'rovlari borligi sabab ba'zi
            # saytlarda hech qachon yetib bo'lmaydi).
            page.wait_for_timeout(wait_ms)
            return page.content()
        finally:
            browser.close()


def fetch_rendered_html(
    url: str,
    wait_ms: int = DEFAULT_RENDER_WAIT_MS,
    timeout_ms: int = DEFAULT_NAVIGATION_TIMEOUT_MS,
) -> str:
    """Sahifani headless Chromium'da ochib, JS render tugagach to'liq
    HTML'ni qaytaradi.

    Xato `CircuitBreakerOpen` bo'lsa — manba hozir nosoz deb topilgan va
    brauzer umuman ishga tushirilmagan; chaqiruvchi buni "bu sahifa yo'q" deb
    o'tkazib yuboradi, qolgan manbalar bunga qaramay ishlashda davom etadi."""
    return breaker_for(_host_of(url)).call(
        _open, url, wait_ms, timeout_ms, trips_on=_is_source_outage
    )
