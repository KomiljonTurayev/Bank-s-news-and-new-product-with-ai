from datetime import datetime, timedelta, timezone

from app.models import BankRate
from app.rate_store import upsert_rates


def test_upsert_rates_no_duplicate_on_identical_repeat_call(session_factory):
    fetched_at = datetime.now(timezone.utc)
    with session_factory() as session:
        inserted = upsert_rates(session, "SQB", "deposit", "individual", [{"name": "A", "rate": "10%"}], fetched_at)
        session.commit()
        assert inserted == 1

        inserted_again = upsert_rates(
            session, "SQB", "deposit", "individual", [{"name": "A", "rate": "10%"}], fetched_at + timedelta(minutes=1)
        )
        session.commit()
        assert inserted_again == 0

        rows = session.query(BankRate).all()
        assert len(rows) == 1


def test_upsert_rates_two_independent_sources_do_not_stomp_each_other_across_runs(session_factory):
    # Bitta (bank_code, product_type, segment)ni ikkita mustaqil connector
    # (masalan bankning o'z sayti VA depozit.uz agregatori) navbatma-navbat
    # to'ldirishi mumkin. Har ikkalasi ham o'zgarmagan bo'lsa, bir necha
    # marta ketma-ket chaqirilganda ham qatorlar soni ikkitadan oshmasligi
    # kerak (avval "oxirgi partiya"ning butun to'plami solishtirilgani
    # sabab, har chaqiriqda ikkalasi ham "farqli" deb topilib, cheksiz
    # dublikat qo'shilib borar edi).
    site_record = {"name": "Standart", "source": "sqb.uz", "rate": "20%"}
    aggregator_record = {"name": "Standart", "source": "depozit.uz", "rate": "19%"}

    with session_factory() as session:
        t0 = datetime.now(timezone.utc)
        for i in range(4):
            fetched_at = t0 + timedelta(minutes=i)
            upsert_rates(session, "SQB", "deposit", "individual", [site_record], fetched_at)
            upsert_rates(session, "SQB", "deposit", "individual", [aggregator_record], fetched_at)
            session.commit()

        rows = session.query(BankRate).all()
        assert len(rows) == 2
        assert {r.data["source"] for r in rows} == {"sqb.uz", "depozit.uz"}


def test_upsert_rates_inserts_new_row_when_a_record_actually_changes(session_factory):
    with session_factory() as session:
        t0 = datetime.now(timezone.utc)
        upsert_rates(session, "SQB", "deposit", "individual", [{"name": "A", "rate": "10%"}], t0)
        session.commit()

        t1 = t0 + timedelta(minutes=1)
        inserted = upsert_rates(session, "SQB", "deposit", "individual", [{"name": "A", "rate": "12%"}], t1)
        session.commit()

        assert inserted == 1
        rows = session.query(BankRate).all()
        assert len(rows) == 2
        assert {r.data["rate"] for r in rows} == {"10%", "12%"}


def test_upsert_rates_keeps_records_without_a_name_field_distinct(session_factory):
    # Valyuta yozuvlarida "name" yo'q ("code" bor) — identity shu holatda
    # ham har bir kodni alohida saqlashi kerak, aks holda ular bitta
    # kalitga to'planib, bir-birini yozib yuborardi.
    with session_factory() as session:
        fetched_at = datetime.now(timezone.utc)
        inserted = upsert_rates(
            session,
            "CBU",
            "currency",
            "individual",
            [{"code": "USD", "rate": 12700}, {"code": "EUR", "rate": 13700}],
            fetched_at,
        )
        session.commit()

        assert inserted == 2
        rows = session.query(BankRate).all()
        assert {r.data["code"] for r in rows} == {"USD", "EUR"}


def test_sqlite_pragmas_set_properly():
    from sqlalchemy import text
    from app.db import engine, _is_sqlite

    if not _is_sqlite:
        return

    with engine.connect() as conn:
        journal = conn.execute(text("PRAGMA journal_mode")).scalar()
        assert str(journal).lower() in ("wal", "memory")
        busy_timeout = conn.execute(text("PRAGMA busy_timeout")).scalar()
        assert busy_timeout >= 30000
        synchronous = conn.execute(text("PRAGMA synchronous")).scalar()
        # 1 corresponds to NORMAL in SQLite
        assert synchronous in (1, 2)
