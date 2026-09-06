from __future__ import annotations

import json
from typing import Protocol

_SYSTEM_PROMPT = (
    "You classify inbound sales leads by intent. Read the lead's message and reply with "
    'JSON of the exact shape {"intent_label": <label>, "confidence_score": <float>}, where '
    "<label> is exactly one of \"buyer\", \"browser\", or \"spam\", and <confidence_score> "
    "is a number between 0.0 and 1.0 reflecting how confident you are in that label. Reply "
    "with only the JSON object, no other text."
)


class _ChatClient(Protocol):
    def chat(self, model: str, messages: list[dict[str, str]], format: str, options: dict[str, object]) -> dict:
        ...


def classify_intent(client: _ChatClient, model: str, lead_text: str, temperature: float = 0.0) -> dict:
    """Issue one Ollama chat call and return the parsed response dict. Structured
    (format="json"); `temperature` defaults to 0 (deterministic), used for the primary
    classification call. `IntentClassificationStage` also issues a second, best-effort
    confirmation call at a nonzero temperature (see `confidence_scoring.py`) through this
    same binding to sample self-consistency for its composite confidence score. No retry/
    validation logic here — that is `IntentClassificationStage`'s responsibility, keeping
    this binding thin and swappable."""
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": lead_text},
        ],
        format="json",
        options={"temperature": temperature},
    )
    content = response["message"]["content"]
    return json.loads(content)
