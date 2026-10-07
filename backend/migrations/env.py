from sqlalchemy import engine_from_config, pool

from alembic import context

# `fileConfig()` ATAYLAB chaqirilmaydi: main.py bu ini bilan
# `command.upgrade()`ni ishga tushirganda, fileConfig mavjud logging
# listener'larini o'chirib, ilovaning o'z sozlamasini buzardi.
from app.config import DATABASE_URL
from app.db import Base
import app.models  # noqa: F401 — jadvallarni Base.metadata'ga ro'yxatdan o'tkazadi

config = context.config
# % interpolatsiyasidan saqlanish uchun to'g'ridan-to'g'ri attributes orqali
# emas, set_main_option yetarli (URL'da % bo'lmasa ham).
config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # SQLite'da ALTER cheklangan — autogenerate qilgan keyingi
        # migratsiyalar barcha rejimda ishshi uchun render_as_batch=True.
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
