"""Sentry konfiguratsiya guardi: so'rov body'si Sentry SaaS'ga tushmasligi
kerak. `POST /api/auth/oneid` body'sida bir martalik `code` va PKCE
`code_verifier` yuboriladi; SDK'ning default `max_request_body_size="medium"`
qiymati 10KB gacha body'ni event'ga iliqtirib tashqariga chiqaradi. Bu test
`sentry_sdk.init`ni to'sib, shu bitta kwarg'ni kuzatadi — tarmoq yo'q,
haqiqiy init bo'lmaydi."""
import sentry_sdk

import sentry as sentry_module


def test_setup_sentry_never_sends_request_body(monkeypatch):
    captured: dict = {}

    def fake_init(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(sentry_sdk, "init", fake_init)
    sentry_module.setup_sentry()

    assert captured.get("max_request_body_size") == "never"
