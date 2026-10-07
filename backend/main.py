import os
import threading
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config as AlembicConfig

from app.api import app
from app.config import FORWARDED_ALLOW_IPS
from app.db import init_db
from app.scheduler import startup_scrape, start_scheduler
from logging_config import setup_logging
from sentry import setup_sentry

setup_logging()
setup_sentry()


def run_migrations() -> None:
    # Absolut yo'llar: ishga tushish papkasidan (docker WORKDIR, systemd va
    # h.k.) qat'i nazar, noto'g'ri joydan o'qimaslik uchun.
    backend_dir = Path(__file__).resolve().parent
    cfg = AlembicConfig(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    run_migrations()
    # create_all() migratsiyadan keyin no-op bo'ladi, lekin eski
    # index-idempotentlik halqasi sifatida qolaveradi.
    init_db()
    # Birinchi skreyping fonda ishlaydi — server portni darhol tinglay
    # boshlaydi. Jadval yoqiqda boot "reja tashqarisidagi tashqi chiqish"
    # bo'lmasligi kerak: startup_scrape() faqat o'tkazib yuborilgan soat
    # bo'lsa qoplaydi (crash-restart shunda ishlaydi), aks holda keyingi
    # soat kutiriladi — interval rejimida avilgidek darhol skreyping qiladi.
    threading.Thread(target=startup_scrape, daemon=True).start()
    start_scheduler()
    # Konteynerda tarmoq interfeysiga bog'lanish env orqali sozlanadi
    # (HOST); localhost'da ishga tushirish uchun "127.0.0.1", Railway ichki
    # IPv6 tarmog'i uchun "::" beriladi.
    # proxy_headers: oldda nginx bo'lgani uchun `request.client.host` proksi
    # bo'lib qolardi — limiterlar barcha mijozlarni bitta IP deb hisoblardi.
    # Endi uvicorn X-Forwarded-For'ni faqat FORWARDED_ALLOW_IPS ro'yxatidagi
    # proksilardan o'qib, `scope["client"]`ni haqiqiy mijozga almashtiradi
    # (ro'yxatdan tashqaridan kelsa header butunlay e'tiborsiz qolinadi,
    # shu bois tashqaridan soxta XFF bilan limiterdan qochib bo'lmaydi).
    uvicorn.run(
        app,
        host=os.environ.get("HOST", "0.0.0.0"),  # NOSONAR — konteynerda interfeys HOST env orqali beriladi, 0.0.0.0 bind shart
        # Railway kabi PaaS portni PORT orqali beradi.
        port=int(os.environ.get("PORT", "8000")),
        proxy_headers=True,
        forwarded_allow_ips=FORWARDED_ALLOW_IPS,
    )
