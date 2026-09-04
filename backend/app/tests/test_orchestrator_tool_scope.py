import pytest

from app.orchestrator.errors import OutOfScopeToolError
from app.orchestrator.stages.data_enrichment import DataEnrichmentStage
from app.orchestrator.stages.hubspot_crm_write import HubSpotCrmWriteStage
from app.orchestrator.tool_scope import ToolRegistry


def test_scoped_proxy_allows_declared_tool():
    registry = ToolRegistry()
    registry.register("ollama_classify", lambda text: "buyer")

    proxy = registry.scoped_proxy(frozenset({"ollama_classify"}), "intent_classification")

    assert proxy.call("ollama_classify", "hi") == "buyer"


def test_classification_stage_proxy_rejects_hubspot_write_call():
    """Direct test for the project's Critical risk: a stage must not reach a tool
    outside its declared contract, even when the tool exists in the registry."""
    registry = ToolRegistry()
    registry.register("ollama_classify", lambda text: "buyer")
    registry.register("hubspot_write", lambda record: {"id": "123"})

    proxy = registry.scoped_proxy(frozenset({"ollama_classify"}), "intent_classification")

    with pytest.raises(OutOfScopeToolError):
        proxy.call("hubspot_write", {"email": "a@b.com"})


def test_out_of_scope_call_is_rejected_not_silently_ignored():
    registry = ToolRegistry()
    registry.register("hubspot_write", lambda record: {"id": "123"})
    proxy = registry.scoped_proxy(frozenset(), "data_enrichment")

    with pytest.raises(OutOfScopeToolError):
        proxy.call("hubspot_write", {})


def test_data_enrichment_stage_proxy_rejects_hubspot_write_call():
    """The real `DataEnrichmentStage` (not a bare `frozenset()`) must not be able to
    reach `hubspot_write` - the concrete demonstration of the project's Critical risk
    using two tools on the *same* external system (see architecture-plan-feature-04.md)."""
    registry = ToolRegistry()
    registry.register("hubspot_search_contact", lambda **kwargs: None)
    registry.register("hubspot_write", lambda record: {"id": "123"})
    stage = DataEnrichmentStage()

    proxy = registry.scoped_proxy(stage.allowed_tools, stage.name)

    assert proxy.call("hubspot_search_contact") is None
    with pytest.raises(OutOfScopeToolError):
        proxy.call("hubspot_write", {"email": "a@b.com"})


def test_hubspot_crm_write_stage_proxy_rejects_hubspot_search_contact_call():
    """The real `HubSpotCrmWriteStage` (write-only) must not be able to reach
    `hubspot_search_contact`, even though its own underlying `hubspot_write` tool
    internally calls `search_contact` for its dedupe lookup — reuse happens at the Python
    function level, not the tool-scoping level (see architecture-plan-feature-05.md)."""
    registry = ToolRegistry()
    registry.register("hubspot_search_contact", lambda **kwargs: None)
    registry.register("hubspot_write", lambda **kwargs: {"id": "123"})
    stage = HubSpotCrmWriteStage()

    proxy = registry.scoped_proxy(stage.allowed_tools, stage.name)

    assert proxy.call("hubspot_write") == {"id": "123"}
    with pytest.raises(OutOfScopeToolError):
        proxy.call("hubspot_search_contact")


def test_unregistered_tool_name_raises_key_error_even_if_declared_allowed():
    registry = ToolRegistry()
    proxy = registry.scoped_proxy(frozenset({"not_registered"}), "some_stage")

    with pytest.raises(KeyError):
        proxy.call("not_registered")
