from __future__ import annotations

import pytest

from app.orchestrator import confidence_scoring


def test_lexical_signal_rewards_keyword_hits_length_and_contact_info():
    sparse = confidence_scoring.lexical_signal("hi", "buyer", has_contact_info=False)
    rich = confidence_scoring.lexical_signal(
        "I want to buy this now and get a quote on pricing, please schedule a demo, "
        "here is my contact info for the invoice and contract",
        "buyer",
        has_contact_info=True,
    )

    assert 0.0 <= sparse <= 1.0
    assert 0.0 <= rich <= 1.0
    assert rich > sparse


def test_lexical_signal_is_deterministic():
    text = "I want to buy a house now"
    first = confidence_scoring.lexical_signal(text, "buyer", has_contact_info=True)
    second = confidence_scoring.lexical_signal(text, "buyer", has_contact_info=True)

    assert first == second


def test_lexical_signal_handles_unknown_label_gracefully():
    # No KeyError even though "unknown" has no keyword list registered.
    result = confidence_scoring.lexical_signal("hello there", "unknown", has_contact_info=False)
    assert 0.0 <= result <= 1.0


def test_lexical_signal_caps_keyword_contribution_at_two_hits():
    two_hits = confidence_scoring.lexical_signal("buy now, get a quote", "buyer", has_contact_info=False)
    many_hits = confidence_scoring.lexical_signal(
        "buy now, get a quote on pricing and cost, ready to sign up and schedule a demo",
        "buyer",
        has_contact_info=False,
    )
    # Both clear the 2-hit cap on the keyword component; any further difference in score
    # comes only from the length signal, not from keyword count growing unbounded.
    keyword_only_diff = many_hits - two_hits
    assert keyword_only_diff < 0.31  # 0.3 max possible from the length signal alone


def test_combine_with_consistency_uses_three_signal_weights():
    result = confidence_scoring.combine(self_reported=0.9, lexical=0.5, consistency=1.0)
    expected = (0.55 * 0.9) + (0.25 * 1.0) + (0.20 * 0.5)
    assert result == pytest.approx(expected)


def test_combine_disagreement_scores_lower_than_agreement():
    agree = confidence_scoring.combine(self_reported=0.9, lexical=0.5, consistency=1.0)
    disagree = confidence_scoring.combine(self_reported=0.9, lexical=0.5, consistency=0.0)

    assert disagree < agree


def test_combine_without_consistency_uses_fallback_two_signal_weights():
    result = confidence_scoring.combine(self_reported=0.9, lexical=0.5, consistency=None)
    expected = (0.70 * 0.9) + (0.30 * 0.5)
    assert result == pytest.approx(expected)


def test_combine_clamps_to_unit_interval():
    assert confidence_scoring.combine(self_reported=2.0, lexical=2.0, consistency=1.0) == 1.0
    assert confidence_scoring.combine(self_reported=-1.0, lexical=-1.0, consistency=0.0) == 0.0


def test_combine_produces_varied_output_across_realistic_inputs():
    """The problem this module exists to fix: a bare self-report clusters on round numbers
    (0.80/0.85/0.90). Blending in continuously-varying signals should not collapse back onto
    a handful of repeated values across a realistic input spread."""
    samples = [
        confidence_scoring.combine(0.9, confidence_scoring.lexical_signal(text, "buyer", has_contact_info=hc), c)
        for text, hc, c in [
            ("buy now please", False, 1.0),
            ("I would like to purchase this and get a quote on pricing", True, 1.0),
            ("just looking around, not sure yet, maybe later", False, 0.0),
            ("unsubscribe click here for free money", False, 1.0),
            ("hi", True, None),
        ]
    ]

    assert len(set(round(s, 4) for s in samples)) == len(samples)
