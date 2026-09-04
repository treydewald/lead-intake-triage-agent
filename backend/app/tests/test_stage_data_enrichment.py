from __future__ import annotations

from app.orchestrator.stages.data_enrichment import DataEnrichmentStage
from app.orchestrator.state import IntakeSlice
from app.orchestrator.tool_scope import ToolRegistry


def _proxy(tool_fn) -> "object":
    registry = ToolRegistry()
    registry.register("hubspot_search_contact", tool_fn)
    stage = DataEnrichmentStage()
    return registry.scoped_proxy(stage.allowed_tools, stage.name)


def test_missing_email_resolved_via_phone_exact_match():
    data = IntakeSlice(source_channel="web_form", name="Jane Doe", phone="5551234567", email=None)
    proxy = _proxy(lambda **kwargs: {"email": "jane@example.com"})

    result = DataEnrichmentStage().run(data, proxy)

    assert result.resolved_fields["email"] == "jane@example.com"
    assert result.sources["email"] == "hubspot_search_contact"
    assert result.match_confidence == 1.0


def test_all_fields_present_is_a_no_op_pass_through():
    data = IntakeSlice(source_channel="web_form", name="Jane Doe", phone="5551234567", email="jane@example.com")
    proxy = _proxy(lambda **kwargs: (_ for _ in ()).throw(AssertionError("tool should not be called")))

    result = DataEnrichmentStage().run(data, proxy)

    assert result.resolved_fields == {}
    assert result.sources == {}
    assert result.attempted_fields == []


def test_lookup_failure_is_encoded_as_lookup_error_not_raised():
    data = IntakeSlice(source_channel="web_form", name="Jane Doe", phone="5551234567", email=None)

    def _always_raise(**kwargs):
        raise RuntimeError("HubSpot timeout")

    proxy = _proxy(_always_raise)

    result = DataEnrichmentStage().run(data, proxy)

    assert result.lookup_error == "HubSpot timeout"
    assert result.resolved_fields == {}


def test_conflicting_field_is_recorded_not_merged():
    # `name` is missing (so mergeable); `email` is already populated and must never be
    # overwritten even though the fake match returns a conflicting value for it.
    data = IntakeSlice(source_channel="web_form", name=None, phone="5551234567", email="jane@example.com")
    proxy = _proxy(lambda **kwargs: {"email": "different@example.com", "name": "Jane Doe"})

    result = DataEnrichmentStage().run(data, proxy)

    assert result.conflicts == {"email": "different@example.com"}
    assert "email" not in result.resolved_fields
    assert result.resolved_fields.get("name") == "Jane Doe"


def test_name_only_query_below_threshold_produces_no_merge():
    data = IntakeSlice(source_channel="web_form", name="Jane Doe", phone=None, email=None)
    proxy = _proxy(lambda **kwargs: {"name": "Someone Else Entirely"})

    result = DataEnrichmentStage().run(data, proxy)

    assert result.resolved_fields == {}
    assert result.match_confidence is not None
    assert result.match_confidence < 0.85


def test_name_only_query_at_or_above_threshold_merges_fields():
    data = IntakeSlice(source_channel="web_form", name="Jane Doe", phone=None, email=None)
    proxy = _proxy(lambda **kwargs: {"name": "Jane Doe", "phone": "5551234567"})

    result = DataEnrichmentStage().run(data, proxy)

    assert result.match_confidence == 1.0
    assert result.resolved_fields["phone"] == "5551234567"
    assert result.sources["phone"] == "hubspot_search_contact"


def test_no_match_result_leaves_fields_missing():
    data = IntakeSlice(source_channel="web_form", name="Jane Doe", phone="5551234567", email=None)
    proxy = _proxy(lambda **kwargs: None)

    result = DataEnrichmentStage().run(data, proxy)

    assert result.resolved_fields == {}
    assert result.attempted_fields == ["email"]


def test_no_identifying_field_available_returns_attempted_with_no_query():
    data = IntakeSlice(source_channel="callback", name=None, phone=None, email=None)
    proxy = _proxy(lambda **kwargs: (_ for _ in ()).throw(AssertionError("tool should not be called")))

    result = DataEnrichmentStage().run(data, proxy)

    assert result.attempted_fields == ["name", "phone", "email"]
    assert result.resolved_fields == {}
