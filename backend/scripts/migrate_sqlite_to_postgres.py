"""Mavjud `bank_news.db` (SQLite) faylidagi ma'lumotni yangi (server) bazaga
ko'chiradi — SQLite'dan PostgreSQL'ga bir martalik o'tish uchun.

Ishlatilishi:
    python scripts/migrate_sqlite_to_postgres.py "<SQLAlchemy URL>"
    (postgresql+psycopg driveri; foydalanuvchi/parolni repo fayllariga
    yozmang — ulanish manzilini ochiq muhitdan oling.)

Diqqat: nishon bazadagi jadvallar bo'sh emasligini oldindan tekshirmaydi —
qayta ishga tushirilsa, har jadval avval tozalanadi (DELETE), so'ng qaytadan
to'ldiriladi, shu bois xavfsiz qayta ishga tushiriladi (idempotent)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, select  # noqa: E402

from app.db import Base  # noqa: E402
from app.models import BankRate, CustomProduct  # noqa: E402

_SQLITE_URL = "sqlite:///bank_news.db"
_BATCH_SIZE = 2000


def _migrate_table(source_engine, target_engine, model) -> int:
    table = model.__table__

    with source_engine.connect() as src_conn:
        rows = [dict(row) for row in src_conn.execute(select(table)).mappings().all()]

    with target_engine.begin() as dst_conn:
        dst_conn.execute(table.delete())
        for start in range(0, len(rows), _BATCH_SIZE):
            batch = rows[start : start + _BATCH_SIZE]
            if batch:
                dst_conn.execute(table.insert(), batch)

        # Bulk insert aniq id qiymatlarini yozadi, lekin Postgres'ning
        # avtomatik ID ketma-ketligi (sequence) bundan xabardor bo'lmay
        # qoladi — keyingi INSERT (masalan yangi mahsulot qo'shilganda)
        # eski, allaqachon band id'dan boshlab urinib, PRIMARY KEY
        # ziddiyatiga uchraydi. Shu bois sequence'ni jadvaldagi eng katta
        # id'ga moslab qo'yamiz.
        if target_engine.dialect.name == "postgresql" and rows:
            max_id = max(row["id"] for row in rows)
            dst_conn.exec_driver_sql(
                f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), {max_id})"
            )

    return len(rows)


def migrate(target_url: str) -> None:
    source_engine = create_engine(_SQLITE_URL)
    target_engine = create_engine(target_url)
    Base.metadata.create_all(target_engine)

    for model in (BankRate, CustomProduct):
        count = _migrate_table(source_engine, target_engine, model)
        print(f"{model.__tablename__}: {count} ta yozuv ko'chirildi")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Foydalanish: python scripts/migrate_sqlite_to_postgres.py <target_database_url>")
        sys.exit(1)
    migrate(sys.argv[1])
