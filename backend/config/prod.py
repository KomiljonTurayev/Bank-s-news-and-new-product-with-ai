from .base import BaseAppSettings


class ProdSettings(BaseAppSettings):
    profile: str = "prod"
