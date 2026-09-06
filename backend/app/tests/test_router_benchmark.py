from __future__ import annotations

import pytest

import app.benchmark.harness as harness_module
from app.benchmark.dataset import DatasetItem
from app.orchestrator import confidence_scoring
from app.orchestrator.state import IntakeSlice
from app.routers.benchmark import get_session_factory
from main import app

_SMALL_DATASET = [
    DatasetItem(
        case_id="buyer-test",
        category="buyer",
        expected_label="buyer",
        intake=IntakeSlice(source_channel="web_form", message_body="buyer message"),
    ),
    DatasetItem(
        case_id="spam-test",
        category="spam",
        expected_label="spam",
        intake=IntakeSlice(source_channel="web_form", message_body="spam message"),
    ),
]


def _fake_register_default_tools(scripted_responses):
    responses = iter(scripted_responses)

    def fake_ollama_classify(lead_text: str, temperature: float = 0.0) -> dict:
        item = next(responses)
        if isinstance(item, Exception):
            raise item
        return item

    def fake_register(registry, settings):
        registry.register("ollama_classify", fake_ollama_classify)

    return fake_register


@pytest.fixture(autouse=True)
def _override_session_factory(db_session_factory):
    app.dependency_overrides[get_session_factory] = lambda: db_session_factory
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _small_scripted_dataset(monkeypatch):
    monkeypatch.setattr(harness_module, "BENCHMARK_DATASET", _SMALL_DATASET)
    monkeypatch.setattr(
        harness_module,
        "register_default_tools",
        # Each successful classification issues a primary + confirmation call (scripted
        # identically so they agree) — see `confidence_scoring.py`.
        _fake_register_default_tools(
            [
                {"intent_label": "buyer", "confidence_score": 0.9},  # buyer: primary
                {"intent_label": "buyer", "confidence_score": 0.9},  # buyer: confirmation
                {"intent_label": "browser", "confidence_score": 0.4},  # spam: primary (misclassified)
                {"intent_label": "browser", "confidence_score": 0.4},  # spam: confirmation
            ]
        ),
    )


def test_post_run_computes_and_persists_accuracy(client):
    response = client.post("/benchmark/run", params={"repeats": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["total_cases"] == 2
    assert body["accuracy"] == 0.5  # 1 of 2 non-ambiguous attempts correct
    assert len(body["cases"]) == 2


def test_get_runs_lists_newest_first_without_case_detail(client):
    client.post("/benchmark/run", params={"repeats": 1})

    response = client.get("/benchmark/runs")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert "cases" not in body["items"][0]


def test_get_run_detail_lists_every_misclassified_case_with_predicted_and_actual_label(client):
    created = client.post("/benchmark/run", params={"repeats": 1}).json()

    response = client.get(f"/benchmark/runs/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    misclassified = [c for c in body["cases"] if c["correct"] is False]
    assert len(misclassified) == 1
    assert misclassified[0]["case_id"] == "spam-test"
    assert misclassified[0]["expected_label"] == "spam"
    assert misclassified[0]["predicted_label"] == "browser"
    expected_confidence = confidence_scoring.combine(
        0.4, confidence_scoring.lexical_signal("spam message", "browser", has_contact_info=False), 1.0
    )
    assert misclassified[0]["confidence"] == expected_confidence


def test_get_run_detail_404_for_unknown_run(client):
    response = client.get("/benchmark/runs/does-not-exist")
    assert response.status_code == 404
