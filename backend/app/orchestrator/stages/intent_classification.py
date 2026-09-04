from __future__ import annotations

from typing import TYPE_CHECKING

from app.orchestrator.contracts import Stage
from app.orchestrator.state import ClassificationSlice, IntakeSlice

if TYPE_CHECKING:
    from app.orchestrator.tool_scope import ScopedToolProxy

_VALID_LABELS = frozenset({"buyer", "browser", "spam"})


def _build_lead_text(data: IntakeSlice) -> str:
    parts = [data.message_body or ""]
    for field in (data.name, data.phone, data.email):
        if field:
            parts.append(field)
    return "\n".join(parts)


def _is_valid_response(response: object) -> bool:
    if not isinstance(response, dict):
        return False
    label = response.get("intent_label")
    confidence = response.get("confidence_score")
    if label not in _VALID_LABELS:
        return False
    return isinstance(confidence, (int, float)) and 0.0 <= confidence <= 1.0


class IntentClassificationStage(Stage[IntakeSlice, ClassificationSlice]):
    """Feature 03: classifies a normalized lead's intent via a local Ollama model.

    Reads Feature 02's `intake` slice but writes its own `classification` slice — the
    first stage to use `input_slice` (see `Stage.effective_input_slice`). A recoverable,
    per-spec-expected failure (tool call error, or an invalid/out-of-set response) is
    encoded as a `"classification_failed"` sentinel in the output slice rather than
    raised, so it flows through the existing confidence-threshold routing into Human
    Review instead of halting the run — see `.claude/portfolio-reference.md`'s Key
    Decisions (set by `architecture-plan-feature-03.md`).
    """

    name = "intent_classification"
    input_schema = IntakeSlice
    output_schema = ClassificationSlice
    allowed_tools = frozenset({"ollama_classify"})
    state_slice = "classification"
    input_slice = "intake"

    def run(self, data: IntakeSlice, tools: "ScopedToolProxy") -> ClassificationSlice:
        if data.empty_message:
            return ClassificationSlice(
                intent_label=None, confidence_score=0.0, model_used="empty_message_short_circuit"
            )

        lead_text = _build_lead_text(data)

        response: object = None
        for _attempt in range(2):
            try:
                response = tools.call("ollama_classify", lead_text)
            except Exception:
                response = None
                continue
            if _is_valid_response(response):
                return ClassificationSlice(
                    intent_label=response["intent_label"],
                    confidence_score=float(response["confidence_score"]),
                    model_used="ollama_local",
                )

        return ClassificationSlice(intent_label=None, confidence_score=0.0, model_used="classification_failed")
