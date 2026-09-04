from __future__ import annotations

import pytest

from app.orchestrator.stages.hubspot_crm_write import HubSpotCrmWriteStage
from app.orchestrator.state import EnrichmentSlice, IntakeSlice, MergedIntakeEnrichment
from app.orchestrator.tool_scope import ToolRegistry


def _proxy(tool_fn) -> "object":
    registry = ToolRegistry()
    registry.register("hubspot_write", tool_fn)
    stage = HubSpotCrmWriteStage()
    return registry.scoped_proxy(stage.allowed_tools, stage.name)


def _merged(*, intake: IntakeSlice, enrichment: EnrichmentSlice | None = None) -> MergedIntakeEnrichment:
    return MergedIntakeEnrichment(intake=intake, enrichment=enrichment or EnrichmentSlice())


def test_successful_create_produces_crm_write_slice():
    data = _merged(intake=IntakeSlice(source_channel="web_form", email="jane@example.com"))
    proxy = _proxy(
        lambda **kwargs: {
            "id": "hs-1",
            "status": "created",
            "dedupe_key_used": "email",
            "dedupe_uncertain": False,
            "retry_count": 0,
        }
    )

    result = HubSpotCrmWriteStage().run(data, proxy)

    assert result.hubspot_record_id == "hs-1"
    assert result.write_status == "created"
    assert result.dedupe_key_used == "email"
    assert result.dedupe_uncertain is False
    assert result.retry_count == 0


def test_retried_then_succeeded_write_reflected_verbatim():
    data = _merged(intake=IntakeSlice(source_channel="web_form", phone="5551234567"))
    proxy = _proxy(
        lambda **kwargs: {
            "id": "hs-2",
            "status": "updated",
            "dedupe_key_used": "phone",
            "dedupe_uncertain": False,
            "retry_count": 1,
        }
    )

    result = HubSpotCrmWriteStage().run(data, proxy)

    assert result.write_status == "updated"
    assert result.retry_count == 1


def test_run_reraises_write_error_from_tool_call_without_catching_it():
    data = _merged(intake=IntakeSlice(source_channel="web_form", email="jane@example.com"))

    def _always_raise(**kwargs):
        raise RuntimeError("HubSpot write failed after 3 retries")

    proxy = _proxy(_always_raise)

    with pytest.raises(RuntimeError, match="HubSpot write failed"):
        HubSpotCrmWriteStage().run(data, proxy)


def test_enrichment_fallback_email_used_when_intake_email_is_none():
    data = _merged(
        intake=IntakeSlice(source_channel="web_form", name="Jane Doe", email=None),
        enrichment=EnrichmentSlice(resolved_fields={"email": "jane@example.com"}),
    )
    captured: dict = {}

    def _capture(**kwargs):
        captured.update(kwargs)
        return {"id": "hs-3", "status": "created", "dedupe_key_used": "email", "dedupe_uncertain": False, "retry_count": 0}

    proxy = _proxy(_capture)

    HubSpotCrmWriteStage().run(data, proxy)

    assert captured["email"] == "jane@example.com"
    assert captured["properties"]["firstname"] == "Jane Doe"


def test_intake_field_takes_priority_over_enrichment_fallback():
    data = _merged(
        intake=IntakeSlice(source_channel="web_form", email="from-intake@example.com"),
        enrichment=EnrichmentSlice(resolved_fields={"email": "from-enrichment@example.com"}),
    )
    captured: dict = {}

    def _capture(**kwargs):
        captured.update(kwargs)
        return {"id": "hs-4", "status": "created", "dedupe_key_used": "email", "dedupe_uncertain": False, "retry_count": 0}

    proxy = _proxy(_capture)

    HubSpotCrmWriteStage().run(data, proxy)

    assert captured["email"] == "from-intake@example.com"
