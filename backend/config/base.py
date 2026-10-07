from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# sof hisob moduli (loyiha modulini import qilmaydi) — bu yerdan import
# sikl yaratmaydi
from app.schedule import parse_times


class BaseAppSettings(BaseSettings):
    app_name: str = "bank-news"
    app_version: str = "1.0.0"
    profile: str

    # Maydon shakli shu yerda — qiymatlar env/.env'dan keladi, kodda yozilmaydi
    DATABASE_URL: str
    FETCH_INTERVAL_MINUTES: int = 60
    # Kunlik skreyping jadvali (user talabi 2026-09-29: "kuniga faqat 2 marta
    # ... ertalab 9 da va abeddan keyin 2 da") — vergul bilan HH:MM, soat huquqi
    # Asia/Tashkent. Bo'sh satr = jadval o'chiq, FETCH_INTERVAL_MINUTES
    # interval rejimiga qaytadi. Bu maydon darvoza/pacer O'RNINI BOSHMAIDI:
    # scrape_active_window va min_host_interval_seconds ishlayveradi (faqat
    # tug'ma soniyasi aniq bo'lmaydi — 09:00 ham shu oynaning ichida).
    scrape_times: str = "09:00,14:00"
    # Tashqi manbalarga chiqish siyosati (app/outbound.py). Bank sayti bank
    # ishlamaydigan vaqtda yangilanmaydi: tunda so'rash ma'lumot bermaydi,
    # faqat "bu IP nega kuniga 24 soat so'rayapti" degan savolni tug'diradi,
    # bloklanib qolsak esa javob bermaydigan manbalar soni OSHADI (chunki
    # bloklangan sayt ham endi timeout beradi). Bo'sh satr = cheklov yo'q.
    # Vaqt mahalliy — Asia/Tashkent (UTC+5, siljish yo'q).
    scrape_active_window: str = "07:00-21:00"
    # Bitta hostga yo'nalgan ketma-ket so'rovlar orasidagi eng qisqa tanaffus
    # (soatning bir xil soniyasida qaytalanadigan naqsh — anti-bot uchun eng
    # aniq belgi). 0 = tanaffus o'chiq.
    min_host_interval_seconds: float = 2.0
    # Vergul bilan ajratilgan CORS ro'yxati (ro'yxatga app/config.py da ajratiladi)
    FRONTEND_ORIGINS: str = "http://localhost:5500,http://127.0.0.1:5500"
    # Backend oldida proksi (front nginx / ingress) turgani uchun
    # `request.client.host` doim proksi manzili bo'ladi — rate limiter
    # hammasini bitta IP deb hisoblardi. uvicorn X-Forwarded-For'ni FAQAT
    # shu ro'yxatdagi bevosita mijozdan kelganda o'qiydi va unda o'ngdan
    # birinchi ishonchsiz manzilni oladi (nginx o'z oldidagi haqiqiy mijozni
    # oxirga qo'shadi — mijoz soxta yozma qo'shsa ham chapda qoladi).
    # Standart — loopback + RFC1918: tashqaridan keladigan TCP ulanishning
    # o'zi bu tarmoqlardan bo'la olmaydi, shu bois `*` (hammasiga ishonish)
    # talab qilmaydi; kerak bo'lsa env orqali toraytiriladi.
    forwarded_allow_ips: str = "127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

    log_level: str = "INFO"

    sentry_dsn: str = ""

    # AI mahsulot tavsiyasi (app/product_recommendation.py) — Claude API.
    # Kalit env/.env'dan keladi; bo'sh bo'lsa tavsiya endpoint'i 503
    # qaytaradi, qolgan ilova odatdagidek ishlaydi.
    anthropic_api_key: str = ""
    # Xuddi shu kalitning muqobil nomi (.env'da CLAUDE_API_KEY deb yozilsa).
    claude_api_key: str = ""
    # Kalit biror workspace'ga bog'lanmagan (org darajasidagi) bo'lsa,
    # Anthropic har so'rovda workspace ID'sini talab qiladi.
    anthropic_workspace_id: str = ""
    ai_model: str = "claude-opus-5-5"
    # Claude'ning fikrlash chuqurligi: low | medium | high | xhigh | max.
    ai_effort: Literal["low", "medium", "high", "xhigh", "max"] = "high"

    @model_validator(mode="after")
    def _check_scrape_times(self) -> "BaseAppSettings":
        """`SCRAPE_TIMES=09.00` kabi yozuv startapni o'ldirishi kerak:
        parse bunday satrni ko'rmaganida jadval jimgina o'chib, interval
        rejimi (soatiga bir) ishga tushar va "kuniga 2 marta" talabi
        monitoringga chiqmasdan buzilar edi. Xuddi shu parse app/config.py
        da ham chaqiriladi — bu yerdagi maqsad xatoni env qatlamidayoq,
        ilova qurilmasidan oldin ko'rsatish."""
        parse_times(self.scrape_times)
        return self

    @property
    def full_app_name(self) -> str:
        return f"{self.app_name}-{self.profile}"

    model_config = SettingsConfigDict(
        extra="allow",
        env_file=".env",
        env_file_encoding="utf-8",
    )
