"""Sozlamalar: PROFILE bo'yicha klass tanlanadi, qiymatlar muhit
o'zgaruvchilari / `.env` faylidan o'qiladi (Railway'da — Variables)."""

import os
from functools import lru_cache

from dotenv import load_dotenv

# PROFILE ham .env'dan o'qilishi uchun qaror qabul qilishdan oldin yuklanadi
# (pydantic-settings faqat maydon qiymatlari uchun o'qiydi).
load_dotenv()

from .dev import DevSettings  # noqa: E402
from .prod import ProdSettings  # noqa: E402

_PROFILES = {"dev": DevSettings, "prod": ProdSettings}


@lru_cache
def get_settings():
    # Standart qiymat yo'q (fail-closed): PROFILE unutilgan serverda ilova
    # jimgina dev'ga (sqlite, DEBUG log) tushib ishlab ketmasligi uchun.
    # Lokal ishlashda .env'ga PROFILE=dev yoziladi.
    profile = os.environ.get("PROFILE", "").strip().lower()
    if not profile:
        raise ValueError(f"PROFILE is not set — must be one of {list(_PROFILES)} (local: PROFILE=dev in .env)")
    if profile not in _PROFILES:
        raise ValueError(f"Unknown PROFILE '{profile}' — must be one of {list(_PROFILES)}")
    return _PROFILES[profile]()


settings = get_settings()
