"""Natijasi tez-tez o'zgarmaydigan, olish qimmat (masalan tashqi HTTP
so'rov) bo'lgan hisoblashlarni belgilangan muddatgacha keshlab turadigan
umumiy (generic) yordamchi.

Chidamllilik siyosati — bitta tashqi manba uzilganda butun so'rov
qulamasligi uchun:

* stale-while-revalidate — TTL tugagach yangilash xato bersa, oxirgi
  muvaffaqiyatli qiymat qaytariladi (xato chaqiruvchiga tarqalmaydi);
* single-flight — yangilashni faqat BITTA oqim bajaradi. Eski qiymat bo'lsa,
  qolgan so'rovlar uni darrov oladi va yuklovchini kutmaydi: bitta
  sekillangan yoki o'lik manba butun threadpool'ni bloklamaydi;
* backoff — oldinda hech qanday qiymat bo'lmagan (sovuq kesh) holatda,
  muvaffaqiyatsizlikdan keyin `retry_backoff_seconds` davomida chaqiruv tez
  rad etiladi, o'lik manbaga urinishlar soni ko'payib ketmaydi;
* kutish chegarasi — navbatdagi oqim yetakchi yuklovchini cheksiz kutmaydi
  (`refresh_wait_seconds`). Transport timeouti ham yordam bermagan holatda
  (javobsiz proksi, o'lik DNS) thread pool bir manba uchun to'lib
  qolmasligi kerak — buning uchun kutuvchi bor eski qiymatni oladi, sovuq
  keshda esa `TimeoutError` beradi.
"""

import logging
import threading
import time
from collections.abc import Callable
from typing import Generic, NamedTuple, TypeVar, cast

log = logging.getLogger(__name__)

T = TypeVar("T")

_MISSING = object()


class _Decision(NamedTuple):
    """`TTLCache.get`ning lock ostidagi bir martalik qarori (hit/miss hisobi).

    `value` `_MISSING` bo'lmasa — javob tayyor, hech narsa kutish yoki yuklash
    kerak emas. `value` `_MISSING` bo'lsa davom etamiz: `lead` haqiqiy bo'lsa
    yuklash shu oqimning bo'yniga tushadi, aks holda `event` yetakchi oqimni
    bildiradi. Ya'ni `value == _MISSING` bo'lgan har bir qarorda `event`
    albatta mavjud (shu bois `get` uni tekshirmasdan ishlatadi).
    """

    value: object
    event: threading.Event | None
    lead: bool


class TTLCache(Generic[T]):
    """`loader()` natijasini `ttl_seconds` muddatgacha eslab qoladi.

    Muddat o'tgach birinchi `get()` qayta yuklaydi; yuklash xato bersa va
    avvalgi muvaffaqiyatli natija bo'lsa, o'sha eski qiymat qaytariladi.
    """

    def __init__(
        self,
        loader: Callable[[], T],
        ttl_seconds: float,
        *,
        retry_backoff_seconds: float = 0.0,
        refresh_wait_seconds: float = 30.0,
        name: str = "cache",
    ):
        self._loader = loader
        self._ttl_seconds = ttl_seconds
        self._retry_backoff_seconds = retry_backoff_seconds
        self._refresh_wait_seconds = refresh_wait_seconds
        self._name = name
        self._value: T | object = _MISSING
        self._loaded_at: float = 0.0
        self._failed_at: float | None = None
        self._last_error: BaseException | None = None
        # FastAPI sync endpointlar threadpool orqali parallel chaqiriladi —
        # lock bo'lmasa, kesh muddati tugagan zumda bir nechta so'rov
        # bir vaqtda "eskirgan" deb topib, HAMMASI qimmat loader()ni
        # (masalan cbu.uz'ga onlab HTTP so'rov) mustaqil qayta ishga
        # tushirib yuborishi mumkin edi (thundering herd).
        self._lock = threading.Lock()
        self._inflight: threading.Event | None = None

    def get(self) -> T:
        while True:
            decision = self._decide()
            if decision.value is not _MISSING:
                return cast(T, decision.value)
            if decision.lead:
                return self._load_as_leader()
            served = self._await_leader(cast(threading.Event, decision.event))
            if served is not _MISSING:
                return cast(T, served)
            # Kutish muvaffaqiyatli tugadi — yetakchi yuklashni yakunladi,
            # shu bois holatni qayta baholaymiz (kalit endi yangi bo'lishi mumkin).

    def _decide(self) -> _Decision:
        """Holatni BITTA marta lock ostida o'qib, keyingi qadamni yechadi.

        Qaror lock ICHIDA qabul qilinadi — tekshiruv bilan uni bajarish orasida
        boshqa oqim holatni o'zgartirib yubormasligi uchun (aks holda ikki oqim
        bir vaqtda o'zini "saylovchi" deb hisoblardi va qimmat yuklovchi ikki
        marta ishga tushardi). Kutish va yuklash esa bu yerdan KEYIN, lock
        tashqarisida bajariladi.
        """
        with self._lock:
            if self._is_fresh():
                return _Decision(self._value, None, False)
            if self._inflight is not None:
                return self._decide_behind_leader()
            if self._in_backoff():
                return self._decide_in_backoff()
            # Saylovchi bizmiz: hodisani oldindan ro'yxatga olamiz — biz hali
            # yuklab bo'lmaguncha boshqa oqim "manba bo'sh"deb ikkinchi
            # yuklovchini ishga tushirmasligi uchun.
            event = self._inflight = threading.Event()
            return _Decision(_MISSING, event, True)

    def _decide_behind_leader(self) -> _Decision:
        """Kalitni hozir boshqa bir oqim yangilab turibdi.

        Qo'ldagi (muddati o'tgan) qiymat fon yangilanishini kutmasdan beriladi
        — foydalanuvchi sekin manba uchun bir necha soniyalik bloklanmasligi
        kerak. Qiymat umuman bo'lmasa yetakchining hodisasini kutamiz.

        Chaqiruvchi lockni ushlab turgan bo'ladi (qayta kirib bo'lmaydi).
        """
        if self._value is _MISSING:
            return _Decision(_MISSING, self._inflight, False)
        return _Decision(self._value, None, False)

    def _decide_in_backoff(self) -> _Decision:
        """Baza ketma-ket xatolardan keyin tanaffusda (breaker ochiq).

        Maqsad — buzilgan manbaga har bir so'rovda urilib o'tirmaslik. Bu faqat
        "hech narsa yo'q" holatiga tegishli: qo'ldagi eski qiymat bo'lsa, uni
        breakerning holati yo'q qilmaydi — foydalanuvchi javobsiz qolmaydi.

        Chaqiruvchi lockni ushlab turgan bo'ladi (qayta kirib bo'lmaydi).
        """
        if self._value is not _MISSING:
            return _Decision(self._value, None, False)
        raise self._last_error  # type: ignore[misc]

    def _load_as_leader(self) -> T:
        """Saylovchi oqim manbani chaqiradi.

        Bu — eng sekin qism, shu bois lock BUTUNLAY ochilmagan holda bajariladi;
        aks holda yuklanayotgan bitta kalit butun threadpool'ni (boshqa
        kalitlarning so'rovlarini ham) to'xtatib qo'yardi.
        """
        try:
            value = self._loader()
        except BaseException as error:
            # Yangilashga urinib ko'rgan oqim ham qo'ldagi eski qiymatni oladi —
            # aks holda manba bir lahzaga uzilib qolganda javobda 502 bo'lardi,
            # holbuki ko'rsatadigan ma'lumotimiz bor.
            self._record_failure(error)
            served = self._stale_value()
            if served is not _MISSING:
                return cast(T, served)
            raise
        self._record_success(value)
        return value

    def _await_leader(self, event: threading.Event) -> object:
        """Yetakchi yuklovchini `refresh_wait_seconds` muddatigacha kutadi.

        Natija `_MISSING` bo'lsa — yetakchi ishini tugatdi va holat qayta
        baholanadi. Muddat tugasa qo'ldagi eski qiymat bilan qanoatlanamiz; u
        ham bo'lmasa `TimeoutError`: cheksiz kutish bir javobsiz manba butun
        thread pool'ni osib qo'yishiga olib kelardi.
        """
        if event.wait(self._refresh_wait_seconds):
            return _MISSING
        return self._stale_value_or_timeout()

    def _stale_value_or_timeout(self) -> object:
        served = self._stale_value()
        if served is not _MISSING:
            return served
        raise TimeoutError(
            f"kesh '{self._name}': yangilanish "
            f"{self._refresh_wait_seconds:g}s ichida tugamadi"
        )

    def _stale_value(self) -> object:
        """Qo'ldagi (muddati o'tgan) qiymatni qaytaradi; yo'qligi `_MISSING`
        bilan bildiriladi.

        Yetakchi yuklashni endi tugatgan bo'lsa, aynan shu yerda yangi qiymat
        ko'rinadi — shuning uchun kutish tugagan lahzada eski deb o'qilgan
        holat qayta tekshiriladi.

        Diqqat: lockni O'ZI oladi, ya'ni faqat lock tashqarisidagi chaqiruvda
        ishlatiladi — `_decide_behind_leader`/`_decide_in_backoff` uni qo'llana
        olmaydi, chunki `_lock` qayta kirilmaydigan `threading.Lock`.
        """
        with self._lock:
            return self._value

    def _is_fresh(self) -> bool:
        return self._value is not _MISSING and time.time() - self._loaded_at <= self._ttl_seconds

    def _in_backoff(self) -> bool:
        return bool(
            self._retry_backoff_seconds
            and self._failed_at is not None
            and time.time() - self._failed_at < self._retry_backoff_seconds
        )

    def _record_success(self, value: T) -> None:
        with self._lock:
            self._value = value
            self._loaded_at = time.time()
            self._failed_at = None
            self._last_error = None
            self._release_inflight()

    def _record_failure(self, error: BaseException) -> None:
        with self._lock:
            self._failed_at = time.time()
            self._last_error = error
            self._release_inflight()
            stale = self._value is not _MISSING
        log.warning(
            "kesh '%s'ni yangilab bo'lmadi (%s); %s",
            self._name,
            error.__class__.__name__,
            "eski qiymat xizmat qiladi" if stale else "ma'lumot yo'q",
        )

    def _release_inflight(self) -> None:
        event, self._inflight = self._inflight, None
        if event is not None:
            event.set()
