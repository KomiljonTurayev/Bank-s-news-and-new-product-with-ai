"""Tashqi manbalarga CHIQISH siyosati: faollik darvozasi + host orasidagi oraliq.

Muammo breaker yechmaydigan tomondan keladi: breaker faqat javob BERMAGAN
manbani chetga suradi, lekin bizning maqsadimiz teskarisi — manbani asrab
ozgarcha, bloklamay turib ma'lumot olish. ~40 ta host (bank saytlari,
cbu.uz, depozit.uz) kuniga bir necha marta, soatning bir xil soniyasida,
kechasi-yu kunduzi so'ralsa, WAF/anti-bot uchun bu bitta skript emas,
avtomatlashtirilgan hujum ko'rinishi. Biz bloklanganda esa javob bermaydigan
manbalar ko'payadi — ya'ni breaker kech, eng ko'p bo'lganda bizni chetda
qoldiradi, xolos.

Shu sabab tashqariga chiqish ikki qoidaga bo'ysunadi:

* faollik darvozasi — bank saytlari bank ishlamaydigan vaqtda yangilanmaydi,
  tunda so'rash ma'lumot bermaydi, faqat "nima uchun bu IP shu qadar ko'p
  so'rayapti" degan savol tug'diradi. Shu oynadan tashqarida skreyping sikli
  umuman boshlanmaydi (interaktiv API so'rovlari esa javob beradi —
  foydalanuvchi kirib kelgan lahzada loyiha "faol").
* host orasidagi oraliq — bitta hostga ketma-ket so'rovlar orasida majburiy
  tanaffus, hamda har sikl boshlanishi biroz sochiladi (jitter). Bir xil
  soniyada keladigan so'rov qatori inson xatti-harakatida uchramaydi.

Ikkala qoida ham sozlanadigan: `SCRAPE_ACTIVE_WINDOW` bo'sh qoldirilsa
skreyping 24/7 davomiy, `MIN_HOST_INTERVAL_SECONDS=0` bo'lsa oraliq
o'chiriladi.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from datetime import date, datetime, time as wall_time, timedelta, timezone

from config import settings

logger = logging.getLogger(__name__)

# O'zbekiston vaqti — UTC+5, 1992 yildan beri yoz/qish siljishi yo'q.
# `zoneinfo("Asia/Tashkent")` emas: u Windows'da (ishlab chiqish mashinasi,
# CI) tashqi `tzdata` paketisiz kalit xatosi beradi, bu yerda esa uchunchoq
# qo'shimcha bog'liqlik kerak emas.
TASHKENT = timezone(timedelta(hours=5), "Asia/Tashkent")


def _parse_wall_clock(text: str) -> wall_time:
    hours, minutes = text.split(":", 1)
    value = wall_time(int(hours), int(minutes))
    return value


class ActiveWindow:
    """Skreypingga ruxsat berilgan mahalliy vaqt oralig'i.

    `""` (yoki yaroqsiz satr) — cheklovsiz: darvoza hamisha ochiq. Bunday
    xulosa aynan shu tomonga qilinadi — sozlamada printer xatosi
    skreypingni jimlik bilan butunlay o'chirib qo'ymasligi kerak, aksincha
    shovqinli log bilan ochiq holatda qoladi."""

    def __init__(self, start: wall_time | None, end: wall_time | None):
        self.start = start
        self.end = end

    @classmethod
    def parse(cls, spec: str) -> "ActiveWindow":
        spec = (spec or "").strip()
        if not spec:
            return cls(None, None)
        try:
            start_text, end_text = spec.split("-", 1)
            window = cls(_parse_wall_clock(start_text.strip()), _parse_wall_clock(end_text.strip()))
        except (ValueError, TypeError):
            logger.warning(
                "SCRAPE_ACTIVE_WINDOW=%r ajratib bo'lmadi (namuna: 07:00-21:00) — "
                "cheklov olib tashlandi, skreyping 24/7 davom etadi", spec,
            )
            return cls(None, None)
        if window.start == window.end:
            logger.warning(
                "SCRAPE_ACTIVE_WINDOW=%r: boshlanish va tugash bir xil — butun kun "
                "yopiq degani, bu odatda xato. Skreyping to'xtaydi; 24/7 uchun "
                "maydonni bo'sh qoldiring.", spec,
            )
        return window

    def __str__(self) -> str:
        if self.unrestricted:
            return "24/7"
        return f"{self.start:%H:%M}-{self.end:%H:%M}"

    @property
    def unrestricted(self) -> bool:
        return self.start is None

    def contains(self, moment: datetime) -> bool:
        """`moment` (istalgan ozona) oyna ichidami? Oyna kechani bosib
        o'tsa (`22:00-06:00`) ikki qism hisoblanadi."""
        if self.unrestricted:
            return True
        start, end = self.start, self.end
        if start is None or end is None:
            return True
        local = moment.astimezone(TASHKENT).time().replace(tzinfo=None)
        if start == end:
            # Oralikning uzunligi 0 — `parse` buni ogohlantirib, butun kun
            # yopiq deb talqin qiladi. Bu shoxoboche `start < end` bo'lmagani
            # uchun quyidagi "kechani bosib o'tish" shoxobchasiga tushib,
            # aksi che — 24/7 ochiq — bo'lib qolmasligi kerak.
            return False
        if start < end:
            return start <= local < end
        return local >= start or local < end

    def _window_slices(self, day: date) -> list[tuple[datetime, datetime]]:
        """Berilgan kun (mahalliy sana) uchun oyna kesmalari."""
        day_start = datetime.combine(day, wall_time.min, TASHKENT)
        if self.start is None or self.end is None:
            return [(day_start, day_start + timedelta(days=1))]
        start = day_start.replace(hour=self.start.hour, minute=self.start.minute)
        end = day_start.replace(hour=self.end.hour, minute=self.end.minute)
        if self.start == self.end:
            return []
        if self.start < self.end:
            return [(start, end)]
        # Kechani bosib o'tuvchi oyna: kun [00:00, end) + [start, 24:00).
        return [(day_start, end), (start, day_start + timedelta(days=1))]

    def open_seconds_between(self, since: datetime, until: datetime) -> float:
        """`since`dan `until`gacha bo'lgan vaqtning NECHTA soniyasi oyna
        ICHISIDA o'tdi.

        Monitoring shu soniyani ishlatadi: "oxirgi ma'lumot 14 soat oldin"
        degani tunda o'z-o'zidan yaman emas — u vaqtning 9 soati skreypingga
        ruxsat berilmagan oraliq edi. Oynani ayirish esa uzilishni yashirmaydi:
        kunlar bo'yi oyna ichida ham yangilanmagan bo'lsa, qolgan soniyalar
        baribir chegaradan oshadi."""
        if self.unrestricted:
            return max(0.0, (until - since).total_seconds())
        if until <= since:
            return 0.0
        total = 0.0
        first_local_day = since.astimezone(TASHKENT).date()
        last_local_day = until.astimezone(TASHKENT).date()
        day = first_local_day
        while day <= last_local_day:
            for slice_start, slice_end in self._window_slices(day):
                overlap_start = max(slice_start, since)
                overlap_end = min(slice_end, until)
                if overlap_end > overlap_start:
                    total += (overlap_end - overlap_start).total_seconds()
            day += timedelta(days=1)
        return total


def active_window() -> ActiveWindow:
    return ActiveWindow.parse(settings.scrape_active_window)


class HostPacer:
    """Har bir host uchun ketma-ket so'rovlar orasidagi majburiy oraliq.

    Oraliq O'RTADA, ya'ni navbat oldindan band qilinadi: 8 ishchi thread bir
    vaqtda "hozir bo'ladimi" deb so'rasa, hammasi bir vaqtda uyg'onib bir xil
    lahzada urilib qolmasligi kerak. Shuningdek har band qilishga tasodifiy
    qo'shimcha qo'shiladi — soatlarning bir xil soniyasida takrorlanadigan
    naqsh anti-bot uchun eng aniq belgi."""

    def __init__(
        self,
        min_interval_seconds: float,
        jitter_ratio: float = 0.5,
        clock=time.monotonic,
        sleep=time.sleep,
        rng=random.random,
    ):
        self.min_interval_seconds = min_interval_seconds
        self.jitter_ratio = jitter_ratio
        self._clock = clock
        self._sleep = sleep
        self._rng = rng
        self._lock = threading.Lock()
        self._next_allowed: dict[str, float] = {}

    def acquire(self, host: str) -> float:
        """`host`ga so'rov yuborishga ruxsat olinadi; kutishga to'g'ri
        kelgan soniyalar qaytariladi (chaqiruvchi nomidan uyquga ketiladi)."""
        if self.min_interval_seconds <= 0:
            return 0.0
        with self._lock:
            now = self._clock()
            # Host bilan ilk uchrashuv — tanaffus yo'q: darvozadan o'tish
            # kutish uchun emas, ketma-ketlikni tartibga solish uchun.
            allowed = self._next_allowed.get(host, now)
            waited = max(0.0, allowed - now)
            interval = self.min_interval_seconds * (1.0 + self.jitter_ratio * self._rng())
            self._next_allowed[host] = max(allowed, now) + interval
        if waited:
            self._sleep(waited)
        return waited


_pacer = HostPacer(settings.min_host_interval_seconds)


def reset_pacer() -> None:
    """Testlar orasida tanaffus tarixini tozalash uchun."""
    global _pacer
    _pacer = HostPacer(settings.min_host_interval_seconds)


def wait_for_host(host: str) -> float:
    return _pacer.acquire(host)


def policy_snapshot(now: datetime | None = None) -> dict:
    """Joriy tashqariga chiqish siyosati — monitoring "nima uchun data
    yangilanmadi" degan savolga javobni shu yerdan oladi."""
    moment = now or datetime.now(timezone.utc)
    window = active_window()
    return {
        "scrape_window": str(window),
        "scrape_active_now": window.contains(moment),
        "min_host_interval_seconds": settings.min_host_interval_seconds,
    }
