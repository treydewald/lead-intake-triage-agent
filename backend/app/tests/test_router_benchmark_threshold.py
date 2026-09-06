from __future__ import annotations

from app.core.config import settings


def test_confidence_threshold_returns_the_configured_value(client, monkeypatch):
    monkeypatch.setattr(settings, "confidence_threshold", 0.7)

    response = client.get("/benchmark/confidence-threshold")

    assert response.status_code == 200
    assert response.json() == {"confidence_threshold": 0.7}


def test_confidence_threshold_reflects_a_live_config_change(client, monkeypatch):
    monkeypatch.setattr(settings, "confidence_threshold", 0.85)

    response = client.get("/benchmark/confidence-threshold")

    assert response.status_code == 200
    assert response.json()["confidence_threshold"] == 0.85
