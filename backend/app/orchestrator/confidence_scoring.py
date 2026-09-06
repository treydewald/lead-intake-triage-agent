from __future__ import annotations

"""Composite confidence scoring for `IntentClassificationStage` (see
architecture-plan-2026-09-06.md). A single LLM self-report, sampled deterministically, tends to
cluster on a small set of round numbers (0.80/0.85/0.90) rather than reflecting real, continuously-
varying evidence. These pure functions combine the self-report with two independently-varying
signals so `confidence_score` behaves like a real composite measurement instead — per
`.claude/portfolio-reference.md`'s Key Decisions, any future confidence-style value in this project
should follow the same pattern."""

_BUYER_KEYWORDS = (
    "buy", "purchase", "price", "pricing", "quote", "cost", "sign up", "ready to",
    "when can", "schedule", "demo", "trial", "invoice", "contract",
)
_SPAM_KEYWORDS = (
    "unsubscribe", "seo services", "loan", "crypto", "bitcoin", "click here",
    "act now", "free money", "winner", "viagra", "backlinks", "guaranteed rankings",
)
_BROWSER_KEYWORDS = (
    "just looking", "curious", "browsing", "not sure yet", "someday", "maybe later",
    "just checking", "wondering", "no rush",
)

_KEYWORDS_BY_LABEL: dict[str, tuple[str, ...]] = {
    "buyer": _BUYER_KEYWORDS,
    "spam": _SPAM_KEYWORDS,
    "browser": _BROWSER_KEYWORDS,
}

# Weights used when a confirmation sample is available.
SELF_REPORTED_WEIGHT = 0.55
CONSISTENCY_WEIGHT = 0.25
LEXICAL_WEIGHT = 0.20

# Fallback weights (confirmation call failed or was invalid) — renormalized across the two
# remaining signals rather than treating the missing one as zero.
FALLBACK_SELF_REPORTED_WEIGHT = 0.70
FALLBACK_LEXICAL_WEIGHT = 0.30

# Nonzero on purpose: a confirmation sample identical in every way to the primary call would
# always agree, making the consistency signal meaningless.
CONFIRMATION_TEMPERATURE = 0.6


def lexical_signal(lead_text: str, intent_label: str, *, has_contact_info: bool) -> float:
    """Deterministic, LLM-independent evidence for `intent_label`, derived purely from the
    lead's own text and contact fields. Exists so `confidence_score` is never authored entirely
    by one LLM self-report."""
    text = (lead_text or "").lower()
    word_count = len(text.split())

    keywords = _KEYWORDS_BY_LABEL.get(intent_label, ())
    keyword_hits = sum(1 for kw in keywords if kw in text)
    keyword_signal = min(keyword_hits / 2, 1.0)

    length_signal = min(word_count / 25, 1.0)

    contact_signal = 1.0 if has_contact_info else 0.4

    return (0.5 * keyword_signal) + (0.3 * length_signal) + (0.2 * contact_signal)


def combine(self_reported: float, lexical: float, consistency: float | None) -> float:
    """Blend the model's self-reported confidence with the lexical signal and, when available,
    a self-consistency sample (1.0 = confirmation call agreed on the label, 0.0 = disagreed).
    `consistency=None` (the confirmation call failed or was invalid) falls back to a two-signal
    blend rather than treating the missing signal as zero. Always clamped to [0.0, 1.0]."""
    if consistency is None:
        score = (FALLBACK_SELF_REPORTED_WEIGHT * self_reported) + (FALLBACK_LEXICAL_WEIGHT * lexical)
    else:
        score = (
            (SELF_REPORTED_WEIGHT * self_reported)
            + (CONSISTENCY_WEIGHT * consistency)
            + (LEXICAL_WEIGHT * lexical)
        )
    return max(0.0, min(1.0, score))
