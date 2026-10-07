import logging
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from config import settings


def setup_sentry():
    sentry_logging = LoggingIntegration(
        level=logging.INFO,        # capture as breadcrumbs
        event_level=logging.ERROR  # send as Sentry events
    )
    sentry_sdk.init(
        dsn=settings.sentry_dsn,       # add this field to your settings if needed
        environment=settings.profile,  # "dev" or "prod" — same separation logic
        release=settings.app_version,
        integrations=[sentry_logging],
        # POST /api/auth/oneid body'sida bir martalik `code` va PKCE
        # `code_verifier` bor — default ("medium") 10KB gacha body Sentry
        # SaaS'ga ketkazadi. Xato eventi kalit almashinuvini transkript
        # qilib bermasligi uchun body HECH QACHON yuborilmaydi.
        max_request_body_size="never",
    )