"""Probe (`/actuator/health`) DB holatiga bog'liq emasligi tekshiruvi."""

import pytest
from fastapi.testclient import TestClient

from app.api import app


@pytest.fixture
def db_down(monkeypatch):
    def boom():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("app.routers.meta.SessionLocal", boom)


def test_actuator_health_ignores_database(db_down):
    response = TestClient(app).get("/actuator/health")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_api_health_reads_database_when_available(session_factory):
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "stale"


def test_api_health_fails_when_database_is_down(db_down):
    response = TestClient(app, raise_server_exceptions=False).get("/api/health")

    assert response.status_code == 500


def test_api_health_reports_image_commit(session_factory, monkeypatch):
    monkeypatch.setenv("GIT_COMMIT", "deadbee")

    body = TestClient(app).get("/api/health").json()

    assert body["git_commit"] == "deadbee"


def test_api_health_commit_defaults_to_dev_without_build_arg(session_factory, monkeypatch):
    monkeypatch.delenv("GIT_COMMIT", raising=False)

    body = TestClient(app).get("/api/health").json()

    assert body["git_commit"] == "dev"
