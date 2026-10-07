"""Bitta mijoz (masalan IP manzil) uchun oynali (sliding window) so'rov
chegaralovchi — hisob tizimi yo'qligi sababli hech bo'lmasa bitta manba
bazani spam yozuvlar bilan cheksiz to'ldirib, DoS holatiga olib
kelishining oldini olish uchun ishlatiladi."""

import math
import threading
import time
from collections import OrderedDict, deque

# Bitta RateLimiter nusxasi saqlaydigan noyob kalitlar (masalan, IP
# manzillar) sonining qattiq chegarasi. Ko'p sonli turli kalitlardan
# so'rov yog'dirib xotirani cheksiz o'stirishga (DoS) yo'l qo'ymaslik
# uchun ishlatiladi — chegaraga yetganda eng uzoq vaqt ishlatilmagan
# kalit(lar) hali navbatida turgan urinishlari bo'lsa ham chiqarib
# tashlanadi (LRU).
_MAX_TRACKED_KEYS = 5000


class RateLimiter:
    """`limit` ta so'rovdan ko'pini har bir kalit uchun `window_seconds`
    oynada o'tkazmaydi. Bir nechta endpoint/resurs uchun mustaqil holatga
    ega bo'lishi kerak bo'lsa, har biriga o'z `RateLimiter` nusxasi
    yaratiladi."""

    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: "OrderedDict[str, deque]" = OrderedDict()
        # FastAPI sync endpointlarni threadpool orqali bir vaqtda bir nechta
        # so'rov uchun parallel chaqiradi — shu bois tekshirish ("len(hits)
        # >= limit") va yozish ("hits.append") ikki alohida amal sifatida
        # emas, bitta lock ostida ATOM tarzda bajarilishi kerak, aks holda
        # bir xil kalitdan bir vaqtda kelgan bir nechta so'rov chegaradan
        # sal-pal oshib ketishiga yo'l qo'yishi mumkin edi.
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Ruxsat berilsa `True` (va shu urinish hisoblanadi), chegara
        oshgan bo'lsa `False` qaytaradi."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits.get(key)
            if hits is None:
                hits = self._hits[key] = deque()
            else:
                # LRU tartibini yangilash: hozir ishlatilgan kalit eng
                # "yangi" hisoblanib, keyinroq chiqarib tashlanadigan
                # navbatning oxiriga o'tadi.
                self._hits.move_to_end(key)
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            while len(self._hits) > _MAX_TRACKED_KEYS:
                # Eng uzoq vaqt ishlatilmagan kalitni chiqarib tashlaymiz
                # (bo'sh yoki bo'lmasin) — shu bilan kalitlar soni har
                # doim qattiq chegaradan oshmasligi kafolatlanadi.
                self._hits.popitem(last=False)
            return True

    def retry_after(self, key: str) -> int:
        """`allow()` `False` qaytargandan keyin: shu kalitning kovagi
        ochilishiga kamida necha BUTUN soniya qolganini qaytaradi (0 =
        kutish shart emas). HTTP `Retry-After` sarlavhasi uchun — mijoz
        kar qayta-urinish qilmasligi uchun. Holatni o'zgartirmaydi."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits.get(key)
            if not hits:
                return 0
            # Kovak bo'shashi — eng eski urinish oynadan chiqqanda bo'ladi.
            # Chiqish sharti `allow()`dagi bilan BIR XIL bo'lishi kerak
            # (`age > window`, qat'iy): age aynan window'ga teng paytda hit
            # hali sanaladi, shu bois `ceil(...)=0` chiqadigan shu chekkada
            # ham "1s kuting" deyishimiz shart — aks holda Retry-After:0 ga
            # ishongan mijoz darhol qayta urilib yana 429 olardi.
            age = now - hits[0]
            if age > self.window_seconds:
                return 0
            return max(1, math.ceil(self.window_seconds - age))

    def refund(self, key: str) -> bool:
        """Avval hisoblangan bitta urinishni qaytaradi — kirish ESHIKLARI
        uchun: limit muvaffaqiyatli so'rovdan emas, *yig'-tirik muvaffaqiyatsiz*
        so'rovdan himoya qiladi. Muvaffaqiyatli kirishni ham hisoblab qo'ysak,
        bitta NAT chiqish IPidan kiradigan ofis foydalanuvchilari qonuniy
        kirishlar bilan o'z xizmatlarini soatlab bloklab qo'yishari mumkin.
        Oynada qaytariladigan urinish bo'lsa `True`; bo'shlikda chaqirish
        manfiyga ketmaydi — `False`."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits.get(key)
            if not hits:
                return False
            # `allow()` qanday ko'rsa, shu ko'zda: oynadan chiqqan hit allaqachon
            # bevazekt — uni "qaytardik" deb hisoblamaymiz.
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if not hits:
                return False
            hits.pop()
            return True

    def reset(self) -> None:
        """Barcha kalitlar uchun holatni tozalaydi — asosan testlarda
        ishlatiladi. `allow()` kabi lock ostida: qo'lda yangi bo'sh
        lug'atni biriktirish lock'siz bo'lsa, parallel `allow()` o'z
        urinishini tashlab ketilgan eski lug'atga yozib, hisobni yo'qotardi
        (yarim aralash holat)."""
        with self._lock:
            self._hits = OrderedDict()
