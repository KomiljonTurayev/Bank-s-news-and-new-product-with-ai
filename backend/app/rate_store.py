"""BankRate yozuvlarini dedup/upsert qilib saqlash — barcha connectorlar
(`app/connectors/base.py`) shu bir xil mantiqdan foydalanadi."""

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BankRate


def _fingerprint(data: dict) -> str:
    return json.dumps(data, sort_keys=True, default=str)


def record_identity(data: dict) -> tuple:
    """Bitta record'ni (bank_code, product_type, segment) doirasida
    boshqalaridan ajratadigan kalit.

    "name" barcha mahsulot turlarida mavjud emas — valyuta yozuvlarida
    o'rniga "code"/"side" bor (masalan CBUConnector: {"code": "USD", ...},
    "name" umuman yo'q). Faqat "name"ga tayansak, bitta bankning barcha
    valyutalari (USD, EUR, RUB, ...) bitta kalitga to'planib qolardi.
    "source"/"category" esa bitta (bank_code, product_type, segment)ni bir
    nechta mustaqil connector to'ldirganda (masalan bankning o'z sayti VA
    depozit.uz agregatori) ularni bir-biridan ajratish uchun kerak."""
    return (
        data.get("source"),
        data.get("category"),
        data.get("name") or data.get("code"),
        data.get("side"),
    )


def upsert_rates(
    session: Session,
    bank_code: str,
    product_type: str,
    segment: str,
    records: list[dict],
    fetched_at: datetime,
) -> int:
    """`records`ni (bank_code, product_type, segment) uchun saqlaydi.

    Har bir record o'zining `record_identity()` kaliti bo'yicha eng so'nggi
    saqlangan holati bilan solishtiriladi: aynan bir xil bo'lsa yangi qator
    qo'shilmasdan faqat `fetched_at` yangilanadi, farq qilsa yangi qator
    qo'shiladi — aks holda jadval har chaqiriqda o'zgarmas ma'lumot bilan
    cheksiz o'sib boraveradi.

    Diqqat: bitta (bank_code, product_type, segment) kombinatsiyasini bir
    nechta mustaqil connector (masalan bankning o'z sayti VA depozit.uz
    agregatori) navbatma-navbat to'ldirishi mumkin — shu bois solishtirish
    "oxirgi partiya"ning butun to'plami bo'yicha emas, balki har record
    o'zining `record_identity()`si bo'yicha ALOHIDA qilinadi. Aks holda har
    connector navbatdagisi yozganda avvalgisining natijasini "farqli" deb
    hisoblab, cheksiz dublikat qator qo'shib yuborar edi.

    Qaytaradi: yangi qo'shilgan qatorlar soni (0 — hech narsa o'zgarmagan).
    """
    existing_rows = list(session.scalars(
        select(BankRate).where(
            BankRate.bank_code == bank_code,
            BankRate.product_type == product_type,
            BankRate.segment == segment,
        )
    ))

    latest_by_identity: dict[tuple, BankRate] = {}
    for row in existing_rows:
        identity = record_identity(row.data)
        current = latest_by_identity.get(identity)
        if current is None or row.fetched_at > current.fetched_at:
            latest_by_identity[identity] = row

    inserted = 0
    for record in records:
        identity = record_identity(record)
        existing = latest_by_identity.get(identity)
        if existing is not None and _fingerprint(existing.data) == _fingerprint(record):
            existing.fetched_at = fetched_at
            continue

        session.add(BankRate(
            bank_code=bank_code,
            product_type=product_type,
            segment=segment,
            data=record,
            fetched_at=fetched_at,
        ))
        inserted += 1

    return inserted
