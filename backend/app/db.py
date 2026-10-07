from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

_is_sqlite = DATABASE_URL.startswith("sqlite")
# SQLite bir vaqtning o'zida faqat bitta yozuvchini qo'llaydi — 25+
# connector ThreadPoolExecutor'da parallel commit qilganda standart
# sozlamada darhol "database is locked" xatosi bilan yiqiladi (yozuv
# butunlay yo'qoladi). WAL rejimi o'quvchilarni yozuvchidan bloklamaydi,
# busy_timeout esa navbatdagi yozuvchiga darhol xato qaytarish o'rniga
# bir muddat kutib qayta urinishga majburlaydi.
engine = create_engine(DATABASE_URL, connect_args={"timeout": 30} if _is_sqlite else {})

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    Base.metadata.create_all(engine)
    # create_all() faqat yo'q jadvallarni yaratadi — allaqachon mavjud
    # jadvalga keyinroq qo'shilgan indekslarni o'zi qo'shmaydi, shu bois
    # har birini alohida, idempotent tarzda tekshirib yaratamiz.
    for table in Base.metadata.tables.values():
        for index in table.indexes:
            index.create(bind=engine, checkfirst=True)
