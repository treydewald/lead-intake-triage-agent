from __future__ import annotations

from typing import TYPE_CHECKING

from app.orchestrator.contracts import Stage
from app.orchestrator.state import CrmWriteSlice, MergedIntakeEnrichment

if TYPE_CHECKING:
    from app.orchestrator.tool_scope import ScopedToolProxy


class HubSpotCrmWriteStage(Stage[MergedIntakeEnrichment, CrmWriteSlice]):
    """Feature 05: writes the merged lead record into HubSpot's live sandbox.

    Reads two upstream slices at once (`intake`, `enrichment`) via `input_slices` — the
    first stage to need this — falling back from Intake's own fields to Enrichment's
    `resolved_fields` for whatever Intake left null, per the read-time merge rule Feature
    04's plan established. Write-only: `allowed_tools` is `hubspot_write` alone, never
    `hubspot_search_contact` (Feature 04's tool), even though `hubspot_write` internally
    reuses `search_contact` for its own dedupe lookup — reuse happens at the Python
    function level, not the tool-scoping level.

    Deliberately **no** try/except around the tool call: a `HubSpotWriteError` (or any
    other exception) propagates straight out of `run()`, letting `_make_node`'s existing
    exception handler mark this lead's run `FAILED` — the owning feature's spec wants a
    write failure after retries are exhausted to halt the run, not continue to
    Notification as if the write succeeded. See `.claude/portfolio-reference.md`'s Key
    Decisions (reworded by `architecture-plan-feature-05.md`).
    """

    name = "hubspot_crm_write"
    input_schema = MergedIntakeEnrichment
    output_schema = CrmWriteSlice
    allowed_tools = frozenset({"hubspot_write"})
    state_slice = "crm_write"
    input_slices = ("intake", "enrichment")

    def run(self, data: MergedIntakeEnrichment, tools: "ScopedToolProxy") -> CrmWriteSlice:
        phone = data.intake.phone or data.enrichment.resolved_fields.get("phone")
        email = data.intake.email or data.enrichment.resolved_fields.get("email")
        name = data.intake.name or data.enrichment.resolved_fields.get("name")

        properties = {"email": email, "phone": phone, "firstname": name}

        result = tools.call("hubspot_write", phone=phone, email=email, properties=properties)

        return CrmWriteSlice(
            hubspot_record_id=result["id"],
            write_status=result["status"],
            dedupe_key_used=result["dedupe_key_used"],
            dedupe_uncertain=result["dedupe_uncertain"],
            retry_count=result["retry_count"],
        )
