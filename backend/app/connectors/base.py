"""Connectorlarning umumiy shartnomasi va tayyor andoza (template) sinflari.

`BaseConnector` faqat ikkita mas'uliyatni talab qiladi: xom ma'lumotni
olish (`fetch_raw`) va uni normalizatsiya qilingan yozuvlarga aylantirish
(`parse`). Saqlash, guruhlash va natijani hisoblash — barcha connectorlar
uchun bir xil bo'lgani sababli shu yerda bir marta yozilgan.

Undan pastdagi andoza sinflar manbaning texnik turiga qarab (statik HTML
sahifa, JSON API, bir nechta mahsulot sahifasi, JS bilan render qilinadigan
sahifa) `fetch_raw`ni ham o'z zimmasiga oladi — natijada har bir bank
connectori faqat o'ziga xos bo'lgan narsani, ya'ni parse mantig'ini
e'lon qiladi."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, NamedTuple

from app.connectors.html_cards import CardLayout, base_url_of, parse_card_list
from app.connectors.http import HTTP, HttpFetcher
from app.db import SessionLocal
from app.rate_store import upsert_rates

logger = logging.getLogger(__name__)

# Yozuv ichidagi xizmatchi maydonlar: agregator manbalarda (depozit.uz)
# har bir yozuv o'z bankiga tegishli bo'lgani uchun bank kodi/segmenti
# connector darajasida emas, yozuv darajasida beriladi. Saqlashdan oldin
# olib tashlanadi — bular mahsulot ma'lumoti emas, marshrutlash belgisi.
BANK_CODE_OVERRIDE = "_bank_code"
SEGMENT_OVERRIDE = "_segment"


class RunResult(NamedTuple):
    """`BaseConnector.run()` natijasi.

    `total` — parse qilingan barcha record'lar soni (eski `run()` shunchaki
    shu sonni qaytargan, chaqiruvchilar bilan moslikni saqlash uchun
    `int(result)` ham ishlaydi). `inserted`/`unchanged` esa dedup natijasini
    ko'rsatadi — scheduler shu orqali "N yangi, M o'zgarishsiz" deb aniq
    log yoza oladi, buning o'rniga hammasini "saqlandi" deb yozib
    chalg'itmaydi."""

    total: int
    inserted: int
    unchanged: int

    def __int__(self) -> int:
        return self.total


def group_by_target(
    records: list[dict],
    default_bank_code: str,
    default_segment: str,
) -> dict[tuple[str, str], list[dict]]:
    """Yozuvlarni saqlanadigan manzili — (bank kodi, segment) — bo'yicha
    guruhlaydi va xizmatchi maydonlarni olib tashlaydi.

    Agregator connectorlar (masalan depozit.uz) bitta so'rovda bir nechta
    bankning taklifini qaytaradi, shu bois bank kodi har bir yozuvning
    o'zidan olinishi mumkin."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for record in records:
        record = dict(record)
        bank_code = record.pop(BANK_CODE_OVERRIDE, default_bank_code)
        segment = record.pop(SEGMENT_OVERRIDE, default_segment)
        groups.setdefault((bank_code, segment), []).append(record)
    return groups


class BaseConnector(ABC):
    """Bitta manba (bank sayti, API yoki agregator) uchun ma'lumot yig'uvchi."""

    bank_code: str
    product_type: str
    segment: str = "individual"  # individual (jismoniy shaxs) | business (yuridik shaxs)

    @abstractmethod
    def fetch_raw(self) -> Any:
        """Bankning API'sidan yoki sahifasidan xom ma'lumotni oladi."""

    @abstractmethod
    def parse(self, raw: Any) -> list[dict]:
        """Xom ma'lumotni normalizatsiya qilingan dict'lar ro'yxatiga aylantiradi."""

    def run(self) -> RunResult:
        records = self.parse(self.fetch_raw())
        inserted = self._save(records, datetime.now(timezone.utc))
        return RunResult(total=len(records), inserted=inserted, unchanged=len(records) - inserted)

    def _save(self, records: list[dict], fetched_at: datetime) -> int:
        """Yozuvlarni bitta tranzaksiyada saqlaydi va yangi qo'shilganlar
        sonini qaytaradi.

        `SessionLocal` ataylab modul darajasida qidiriladi (import vaqtida
        nomga bog'lanmaydi) — testlar shu nomni almashtirib, xotiradagi
        bazaga yo'naltira oladi."""
        groups = group_by_target(records, self.bank_code, self.segment)
        inserted = 0
        with SessionLocal() as session:
            for (bank_code, segment), group in groups.items():
                inserted += upsert_rates(session, bank_code, self.product_type, segment, group, fetched_at)
            session.commit()
        return inserted


# ─────────────────────────────────────────────────────────────────────
# Manba turiga qarab tayyor andozalar
# ─────────────────────────────────────────────────────────────────────
class HtmlPageConnector(BaseConnector):
    """Bitta statik HTML sahifadan o'qiydigan connector."""

    http: HttpFetcher = HTTP
    url: str

    @property
    def base_url(self) -> str:
        """Nisbiy havolalarni to'liq manzilga aylantirish uchun asos.
        Sayt havolalarni boshqa (masalan "www"siz) hostda bersa, connector
        buni qayta belgilaydi."""
        return base_url_of(self.url)

    def fetch_raw(self) -> str:
        return self.http.text(self.url)

    def parse(self, raw: str) -> list[dict]:
        return self.parse_html(raw, self.base_url)

    @abstractmethod
    def parse_html(self, html: str, base_url: str) -> list[dict]:
        """Sahifa HTML'ini yozuvlarga aylantiradi."""


class CardListConnector(HtmlPageConnector):
    """Mahsulotlar takrorlanuvchi kartalar ro'yxati sifatida berilgan sayt —
    parse mantig'i to'liq `layout` e'loni bilan ifodalanadi."""

    layout: CardLayout

    def parse_html(self, html: str, base_url: str) -> list[dict]:
        return parse_card_list(html, self.layout, base_url)


class JsonApiConnector(BaseConnector):
    """Ochiq JSON API'dan o'qiydigan connector. `url` — foydalanuvchiga
    ko'rsatiladigan sahifa manzili, `api_url` — haqiqiy so'rov manzili
    (ko'p saytlarda ular boshqa-boshqa)."""

    http: HttpFetcher = HTTP
    url: str
    api_url: str
    params: dict[str, Any] | None = None

    def fetch_raw(self) -> Any:
        return self.http.json(self.api_url, self.params)

    def parse(self, raw: Any) -> list[dict]:
        return self.parse_payload(raw, self.url)

    @abstractmethod
    def parse_payload(self, payload: Any, url: str) -> list[dict]:
        """API javobini yozuvlarga aylantiradi."""


class MultiPageConnector(BaseConnector):
    """Ro'yxat sahifasi yo'q (yoki unda raqamlar berilmagan) banklar uchun —
    har bir mahsulot o'z alohida sahifasidan olinadi.

    Bitta sahifaning ochilmasligi ham, ichidagi markup'ning o'zgarishi ham
    butun bankni ma'lumotsiz qoldirmasligi kerak: ochilmagan sahifa
    `HttpFetcher.pages`da, parse qilinmayan sahifa esa `parse`da o'tkazib
    yuboriladi."""

    http: HttpFetcher = HTTP
    urls: list[str]

    @property
    def log_label(self) -> str:
        return type(self).__name__

    def fetch_raw(self) -> list[tuple[str, str]]:
        return self.http.pages(self.urls, self.log_label)

    def parse(self, raw: list[tuple[str, str]]) -> list[dict]:
        records = []
        for url, html in raw:
            # Bitta sahifani o'qib bo'lmasa (sayt dizayni o'zgargan, markup
            # kutilmaganda) qolgan sahifalar saqlanib qolishi kerak — aks
            # holda bitta sahifadagi xato butun bankni ma'lumotsiz qoldiradi.
            try:
                records.extend(self.parse_page(html, url))
            except Exception:
                logger.exception("%s: %s sahifasi parse qilinmadi, o'tkazib yuborildi", self.log_label, url)
        return records

    @abstractmethod
    def parse_page(self, html: str, url: str) -> list[dict]:
        """Bitta mahsulot sahifasini yozuvlarga aylantiradi."""


class RenderedPageConnector(HtmlPageConnector):
    """JavaScript bilan client-tomonda render qilinadigan sahifa — oddiy
    so'rov bo'sh skelet qaytargani uchun headless brauzer orqali ochiladi
    (`app/connectors/playwright_fetch.py`)."""

    def fetch_raw(self) -> str:
        from app.connectors.playwright_fetch import fetch_rendered_html

        return fetch_rendered_html(self.url)
