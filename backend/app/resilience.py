"""Tashqi manba uzilishlariga chidamllik primitivlari.

Asosiy tamoyil: bitta buzilgan manba butun ilovani sekinlashtirmasligi va
to'xtatmasligi kerak. Buning uchun har bir tashqi host o'z hisob-kitobini
yuradi — `CircuitBreaker` bir necha marta ketma-ket xato bergan manbani
ma'lum vaqtga "ochiq" holatga o'tkazadi va u ichida chaqiruvni manbaga
yubormaydi (hamyon qaytaradi). Taym-out tugagach bitta "sinov" chaqiruvi
o'tkaziladi: agar manba tiklangan bo'lsa breaker yopiladi, aks holda
qayta ochiladi.

Nega host bo'yicha? Bitta sayt (masalan cbu.uz) bir nechta iste'molchi —
connectorlar va API endpointlari — orasidan so'raladi. Bitta chung'ak
manbaga urinishni ko'paytirish uni tiklamaydi, faqat bizning thread
pool'ni band qiladi; breaker buni kesadi, ammo faqat shu host uchun."""

from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)


class CircuitBreakerOpen(Exception):
    """Manba vaqtincha nosoz deb topilgan — chaqiruv manbaga yuborilmaydi."""

    def __init__(self, name: str, retry_in: float):
        super().__init__(f"{name}: breaker ochiq, qariyb {retry_in:.0f}s'dan keyin qayta uriniladi")
        self.name = name
        self.retry_in = retry_in


def _trips_on_any(error: BaseException) -> bool:
    return True


class CircuitBreaker:
    """Bitta manba uchun ketma-ket xatolar hisoblagichi.

    - yopilgan (oddiy holat): chaqiruvlar o'tadi; ketma-ket
      `failure_threshold` marta xato — ochiladi;
    - ochiq: `recovery_seconds` davomida chaqiruvlar `CircuitBreakerOpen`
      bilan darhol qaytadi (manbaga hech narsa boramaydi);
    - ochiq + muddat tugadi: bitta sinov chaqiruvi o'tadi (qolganlari
      yana darhol qaytadi); sinov muvaffaqiyatli bo'lsa — yopiladi,
      xato — qayta ochiladi."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_seconds: float = 60.0,
        clock=time.monotonic,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._failures = 0
        self._opened_at: float | None = None
        self._trial_in_flight = False

    def call(self, func, /, *args, trips_on=_trips_on_any, **kwargs):
        """`func`ni chaqiradi va natijani qaytaradi; breaker ochiq bo'lsa
        chaqirmay `CircuitBreakerOpen` ko'taradi.

        `trips_on` — qaysi xato manba nosozligi HISOBLANISHINI hal qiladi.
        Standart bo'yicha har qanday xato hisoblanadi; HTTP qatlami esa
        bundan `False` qaytarganini yuboradi: 404 yoki buzilgan HTML — sayt
        "o'lgani" emas, faqat bitta manzil o'zgargani, shu bois butun hostni
        bloklash noto'g'ri bo'lardi."""
        self._acquire_slot()
        try:
            result = func(*args, **kwargs)
        except BaseException as error:
            counted = trips_on(error)
            was_open = self._record_failure(counted)
            if was_open:
                logger.warning("CircuitBreaker(%s): manba yana nosoz — qayta ochildi", self.name)
            raise
        if self._record_success():
            logger.info("CircuitBreaker(%s): manba tiklandi, breaker yopildi", self.name)
        return result

    def _acquire_slot(self) -> None:
        with self._lock:
            if self._opened_at is None:
                return
            elapsed = self._clock() - self._opened_at
            if elapsed < self.recovery_seconds or self._trial_in_flight:
                raise CircuitBreakerOpen(self.name, max(0.0, self.recovery_seconds - elapsed))
            self._trial_in_flight = True

    def _record_failure(self, counted: bool = True) -> bool:
        """Xatoni qayd etadi va breaker SHU xato hisobiga ochilgan bo'lsa
        True qaytaradi (log shovqinini kamaytirish uchun faqat o'tish
        paytida yoziladi).

        `counted=False` — xato manba nosozligi hisoblanmaydi: hisoblagich
        o'smaydi, ochiq breaker esa yopiladi. Aks holda bir marta ochilgan
        breaker hech qachon tiklanmas edi — sinov chaqiruvi ham "xato" bilan
        tugab, uni darhol qayta ochib qo'yardi."""
        with self._lock:
            if self._trial_in_flight:
                self._trial_in_flight = False
                if not counted:
                    self._failures = 0
                    self._opened_at = None
                    return False
                self._opened_at = self._clock()
                return True
            if not counted:
                self._failures = 0
                return False
            self._failures += 1
            if self._failures == self.failure_threshold:
                self._opened_at = self._clock()
                return True
            return False

    def _record_success(self) -> bool:
        """Muvaffaqiyatdan so'ng breaker endi yopilgan bo'lsa True."""
        with self._lock:
            was_open = self._opened_at is not None
            self._failures = 0
            self._opened_at = None
            self._trial_in_flight = False
            return was_open

    def snapshot(self) -> dict:
        """Diagnostika uchun joriy holat (operatsion kuzatuv nuqtasi)."""
        with self._lock:
            return {
                "source": self.name,
                "open": self._opened_at is not None,
                "consecutive_failures": self._failures,
            }


# Host (yoki boshqa mantiqiy manba nomi) bo'yicha breaker reyestri:
# bitta saytga qaratilgan barcha chaqiruvlar bitta hisob-kitobni bo'lishadi.
_breakers: dict[str, CircuitBreaker] = {}
_breakers_lock = threading.Lock()


def breaker_for(name: str) -> CircuitBreaker:
    with _breakers_lock:
        breaker = _breakers.get(name)
        if breaker is None:
            breaker = _breakers[name] = CircuitBreaker(name)
        return breaker


def reset_breakers() -> None:
    """Reyestrni tozalaydi — testlarning bir-biriga ta'sirini uzish uchun."""
    with _breakers_lock:
        _breakers.clear()


def breaker_statuses() -> list[dict]:
    """Barcha manbalar holati — "qaysi sayt hozir chetda" degan savolga
    javob beradigan diagnostika nuqtasi uchun."""
    with _breakers_lock:
        breakers = list(_breakers.values())
    return sorted((b.snapshot() for b in breakers), key=lambda s: s["source"])
