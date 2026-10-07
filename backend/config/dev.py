from .base import BaseAppSettings


class DevSettings(BaseAppSettings):
    profile: str = "dev"
    log_level: str = "DEBUG"

    # Lokal prototip sqlite bilan ishlaydi; haqiqiy qiymat .env'dan keladi
    DATABASE_URL: str = "sqlite:///bank_news.db"
