from __future__ import annotations

import json

import app.benchmark.harness as harness_module
from app.benchmark.dataset import DatasetItem
from app.core.config import Settings
from app.orchestrator import confidence_scoring
from app.orchestrator.state import IntakeSlice

_SETTINGS = Settings(ollama_model="test-model")

_SMALL_DATASET = [
    DatasetItem(
        case_id="buyer-test",
        category="buyer",
        expected_label="buyer",
        intake=IntakeSlice(source_channel="web_form", message_body="buyer message"),
    ),
    DatasetItem(
        case_id="browser-test",
        category="browser",
        expected_label="browser",
        intake=IntakeSlice(source_channel="web_form", message_body="browser message"),
    ),
    DatasetItem(
        case_id="ambiguous-test",
        category="ambiguous",
        expected_label=None,
        intake=IntakeSlice(source_channel="web_form", message_body="ambiguous message"),
    ),
]


def _fake_register_default_tools(scripted_responses):
    responses = iter(scripted_responses)

    def fake_ollama_classify(lead_text: str, temperature: float = 0.0) -> dict:
        item = responses.__next__()
        if isinstance(item, Exception):
            raise item
        return item

    def fake_register(registry, settings):
        registry.register("ollama_classify", fake_ollama_classify)

    return fake_register


def test_run_benchmark_produces_hand_computed_accuracy_and_consistency(monkeypatch, db_session_factory):
    # Order matches _SMALL_DATASET x repeats=2: buyer x2, browser x2, ambiguous x2. Each
    # harness-level "attempt" is one `IntentClassificationStage.run()` call. A successful
    # primary classification now also issues one best-effort confirmation call (see
    # `confidence_scoring.py`), so each successful attempt consumes 2 scripted responses
    # (primary + confirmation, scripted identically so consistency=1.0/agreement). The
    # deliberate failure below scripts two raises to exhaust the stage's own internal
    # primary-call retry and reach the `classification_failed` sentinel (label=None,
    # confidence=0.0) — a failed primary call never attempts a confirmation call.
    scripted = [
        {"intent_label": "buyer", "confidence_score": 0.9},  # buyer attempt 1: primary
        {"intent_label": "buyer", "confidence_score": 0.9},  # buyer attempt 1: confirmation
        {"intent_label": "buyer", "confidence_score": 0.9},  # buyer attempt 2: primary
        {"intent_label": "buyer", "confidence_score": 0.9},  # buyer attempt 2: confirmation
        {"intent_label": "browser", "confidence_score": 0.8},  # browser attempt 1: primary (correct)
        {"intent_label": "browser", "confidence_score": 0.8},  # browser attempt 1: confirmation
        RuntimeError("boom"),  # browser attempt 2, internal sub-attempt 1: raises
        RuntimeError("boom"),  # browser attempt 2, internal sub-attempt 2: raises -> failed
        {"intent_label": "browser", "confidence_score": 0.7},  # ambiguous attempt 1: primary
        {"intent_label": "browser", "confidence_score": 0.7},  # ambiguous attempt 1: confirmation
        {"intent_label": "browser", "confidence_score": 0.7},  # ambiguous attempt 2: primary (consistent)
        {"intent_label": "browser", "confidence_score": 0.7},  # ambiguous attempt 2: confirmation
    ]
    monkeypatch.setattr(harness_module, "BENCHMARK_DATASET", _SMALL_DATASET)
    monkeypatch.setattr(
        harness_module, "register_default_tools", _fake_register_default_tools(scripted)
    )

    run = harness_module.run_benchmark(repeats=2, session_factory=db_session_factory, settings=_SETTINGS)

    # Non-ambiguous total attempts = 2 items x 2 repeats = 4; correct = 2 (buyer) + 1 (browser) = 3.
    assert run.total_cases == 3
    assert run.repeats == 2
    assert run.model_used == "test-model"
    assert run.accuracy == 3 / 4

    # Consistent items = buyer (both "buyer") + ambiguous (both "browser") = 2 of 3 items.
    assert run.consistency == 2 / 3

    cases_by_id = {case.case_id: case for case in run.cases}

    buyer_confidence = confidence_scoring.combine(
        0.9, confidence_scoring.lexical_signal("buyer message", "buyer", has_contact_info=False), 1.0
    )
    browser_confidence = confidence_scoring.combine(
        0.8, confidence_scoring.lexical_signal("browser message", "browser", has_contact_info=False), 1.0
    )
    ambiguous_confidence = confidence_scoring.combine(
        0.7, confidence_scoring.lexical_signal("ambiguous message", "browser", has_contact_info=False), 1.0
    )

    buyer_case = cases_by_id["buyer-test"]
    assert buyer_case.correct is True
    assert buyer_case.consistent is True
    assert buyer_case.predicted_label == "buyer"
    assert json.loads(buyer_case.attempts_json) == [
        {"label": "buyer", "confidence": buyer_confidence},
        {"label": "buyer", "confidence": buyer_confidence},
    ]

    browser_case = cases_by_id["browser-test"]
    assert browser_case.correct is True  # first attempt matched expected label
    assert browser_case.consistent is False  # second attempt failed
    assert json.loads(browser_case.attempts_json) == [
        {"label": "browser", "confidence": browser_confidence},
        {"label": None, "confidence": 0.0},  # stage's own classification_failed sentinel
    ]

    ambiguous_case = cases_by_id["ambiguous-test"]
    assert ambiguous_case.is_ambiguous is True
    assert ambiguous_case.correct is None  # never forced into correct/incorrect
    assert ambiguous_case.consistent is True
    assert json.loads(ambiguous_case.attempts_json) == [
        {"label": "browser", "confidence": ambiguous_confidence},
        {"label": "browser", "confidence": ambiguous_confidence},
    ]


def test_ambiguous_items_never_counted_in_accuracy_denominator(monkeypatch, db_session_factory):
    dataset = [
        DatasetItem(
            case_id="ambiguous-only",
            category="ambiguous",
            expected_label=None,
            intake=IntakeSlice(source_channel="web_form", message_body="ambiguous message"),
        ),
    ]
    monkeypatch.setattr(harness_module, "BENCHMARK_DATASET", dataset)
    monkeypatch.setattr(
        harness_module,
        "register_default_tools",
        # 3 repeats x (primary + confirmation) = 6 scripted responses.
        _fake_register_default_tools(
            [{"intent_label": "buyer", "confidence_score": 0.5}] * 6
        ),
    )

    run = harness_module.run_benchmark(repeats=3, session_factory=db_session_factory, settings=_SETTINGS)

    assert run.accuracy == 0.0  # no non-ambiguous attempts exist; must not divide by zero either
    assert run.cases[0].correct is None


def test_deliberately_failing_case_counts_as_incorrect_not_excluded(monkeypatch, db_session_factory):
    dataset = [
        DatasetItem(
            case_id="always-fails",
            category="buyer",
            expected_label="buyer",
            intake=IntakeSlice(source_channel="web_form", message_body="buyer message"),
        ),
    ]
    monkeypatch.setattr(harness_module, "BENCHMARK_DATASET", dataset)
    # 2 repeats x 2 internal sub-attempts each (the stage's own retry) = 4 raises needed
    # to force both harness-level attempts to the classification_failed sentinel.
    monkeypatch.setattr(
        harness_module,
        "register_default_tools",
        _fake_register_default_tools([RuntimeError("unreachable")] * 4),
    )

    run = harness_module.run_benchmark(repeats=2, session_factory=db_session_factory, settings=_SETTINGS)

    assert run.accuracy == 0.0
    assert run.cases[0].correct is False
    assert run.cases[0].consistent is False
