"""Nozik adapter: eski `from app.config import ...` import joylarini buzmasdan
sozlamalarni `config` paketidan (env/.env — PROFILE bo'yicha)
oladi. Yangi kod `from config import settings` ishlatsa ham bo'ladi.
"""

from config import settings

from app.schedule import parse_times

def _sqlalchemy_url(url: str) -> str:
    """Railway/Heroku `postgres://` yoki `postgresql://` beradi — SQLAlchemy
    esa o'rnatilgan drayverni (psycopg 3) aniq ko'rsatishni talab qiladi."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = _sqlalchemy_url(settings.DATABASE_URL)
FETCH_INTERVAL_MINUTES = settings.FETCH_INTERVAL_MINUTES
# Kunlik jadval (config/base.py:scrape_times) — bir marta parse qilinadi;
# format xatosi settings qurilishidayoq ValueError bilan startapni oldindan
# o'ldiradi, jimgina interval rejimiga siljimaydi.
SCRAPE_TIMES = parse_times(settings.scrape_times)
PROFILE = settings.profile

ANTHROPIC_API_KEY = settings.anthropic_api_key or settings.claude_api_key
ANTHROPIC_WORKSPACE_ID = settings.anthropic_workspace_id
AI_MODEL = settings.ai_model
AI_EFFORT = settings.ai_effort

# Frontend endi alohida repo/serverda ishlaydi (masalan http://localhost:5500
# orqali static server bilan), shuning uchun brauzer buni boshqa origin deb
# ko'radi va CORS ruxsati kerak. env/.env'da vergul bilan ajratilgan satr
# saqlanadi, bu yerda ro'yxatga ajratiladi.
FRONTEND_ORIGINS = [origin.strip() for origin in settings.FRONTEND_ORIGINS.split(",") if origin.strip()]

# Proksi ortidagi haqiqiy mijoz IP'si — uvicorn'ning proxy_headers mexanizmi
# faqat shu ro'yxatdagi manzillarning X-Forwarded-For'ini o'qiydi
# (ishlatilgan joy: main.py — yozuv limiterlari haqiqiy IP bo'yicha).
FORWARDED_ALLOW_IPS = settings.forwarded_allow_ips
