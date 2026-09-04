from __future__ import annotations

import difflib
from typing import TYPE_CHECKING

from app.orchestrator.contracts import Stage
from app.orchestrator.state import EnrichmentSlice, IntakeSlice

if TYPE_CHECKING:
    from app.orchestrator.tool_scope import ScopedToolProxy

_MATCH_CONFIDENCE_THRESHOLD = 0.85
_MERGEABLE_FIELDS = ("name", "phone", "email")


class DataEnrichmentStage(Stage[IntakeSlice, EnrichmentSlice]):
    """Feature 04: fills missing lead fields via a read-only HubSpot contact search.

    Reads Feature 02's `intake` slice but writes its own `enrichment` slice (the second
    stage to use `input_slice`, after Feature 03). Exact-key match on phone/email is
    treated as definitive (`match_confidence=1.0`); a name-only query falls back to a
    `difflib`-scored fuzzy match, merged only above `_MATCH_CONFIDENCE_THRESHOLD`. Never
    overwrites a field Intake Parsing already populated — a conflicting lookup result is
    recorded in `conflicts`, not merged. A lookup failure (tool exception) is encoded as
    `lookup_error` rather than raised, so a HubSpot outage never halts the pipeline — see
    `.claude/portfolio-reference.md`'s Key Decisions (set by
    `architecture-plan-feature-04.md`), generalizing the same recoverable-failure rule
    Feature 03 established for its own LLM call.
    """

    name = "data_enrichment"
    input_schema = IntakeSlice
    output_schema = EnrichmentSlice
    allowed_tools = frozenset({"hubspot_search_contact"})
    state_slice = "enrichment"
    input_slice = "intake"

    def run(self, data: IntakeSlice, tools: "ScopedToolProxy") -> EnrichmentSlice:
        missing = [field for field in _MERGEABLE_FIELDS if getattr(data, field) is None]
        if not missing:
            return EnrichmentSlice()

        if data.phone is not None:
            query = {"phone": data.phone}
        elif data.email is not None:
            query = {"email": data.email}
        elif data.name is not None:
            query = {"name": data.name}
        else:
            return EnrichmentSlice(attempted_fields=missing)

        try:
            match = tools.call("hubspot_search_contact", **query)
        except Exception as exc:
            return EnrichmentSlice(attempted_fields=missing, lookup_error=str(exc))

        if match is None:
            return EnrichmentSlice(attempted_fields=missing)

        match_confidence = 1.0
        if "name" in query:
            match_confidence = difflib.SequenceMatcher(
                None, data.name.lower(), str(match.get("name", "")).lower()
            ).ratio()
            if match_confidence < _MATCH_CONFIDENCE_THRESHOLD:
                return EnrichmentSlice(attempted_fields=missing, match_confidence=match_confidence)

        resolved_fields: dict[str, object] = {}
        sources: dict[str, str] = {}
        conflicts: dict[str, object] = {}
        for field in _MERGEABLE_FIELDS:
            candidate = match.get(field)
            if candidate is None:
                continue
            current = getattr(data, field)
            if current is None:
                if field in missing:
                    resolved_fields[field] = candidate
                    sources[field] = "hubspot_search_contact"
            elif candidate != current:
                conflicts[field] = candidate

        return EnrichmentSlice(
            resolved_fields=resolved_fields,
            sources=sources,
            attempted_fields=missing,
            match_confidence=match_confidence,
            conflicts=conflicts,
        )
