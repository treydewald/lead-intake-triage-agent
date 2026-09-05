from __future__ import annotations

from dataclasses import dataclass

from app.orchestrator.state import IntakeSlice


@dataclass(frozen=True)
class DatasetItem:
    """One labeled test lead. `expected_label` is `None` only for `category == "ambiguous"`
    items — every buyer/browser/spam item must carry a ground-truth label, per
    architecture-plan-feature-09.md's dataset validation requirement."""

    case_id: str
    category: str  # "buyer" | "browser" | "spam" | "ambiguous"
    expected_label: str | None
    intake: IntakeSlice


def _lead(message_body: str, **kwargs: object) -> IntakeSlice:
    return IntakeSlice(source_channel="web_form", message_body=message_body, **kwargs)


# Ships as a Python-literal fixture (not a DB seed) so the benchmark is runnable with
# zero setup beyond a working Ollama install, per the project's free-by-default
# constraint (architecture-plan-feature-09.md's Feature-Specific Requirements).
BENCHMARK_DATASET: list[DatasetItem] = [
    DatasetItem(
        case_id="buyer-001",
        category="buyer",
        expected_label="buyer",
        intake=_lead("I want to buy a 3-bedroom house in the next 30 days, budget is $450k."),
    ),
    DatasetItem(
        case_id="buyer-002",
        category="buyer",
        expected_label="buyer",
        intake=_lead("Ready to make an offer today if the numbers work. Can we schedule a showing?"),
    ),
    DatasetItem(
        case_id="buyer-003",
        category="buyer",
        expected_label="buyer",
        intake=_lead("Pre-approved for a mortgage, looking to close within the month."),
    ),
    DatasetItem(
        case_id="buyer-004",
        category="buyer",
        expected_label="buyer",
        intake=_lead("Please send me the purchase agreement, I'd like to move forward now."),
    ),
    DatasetItem(
        case_id="buyer-005",
        category="buyer",
        expected_label="buyer",
        intake=_lead("My family and I need to be under contract before the school year starts."),
    ),
    DatasetItem(
        case_id="buyer-006",
        category="buyer",
        expected_label="buyer",
        intake=_lead("Cash offer, no financing needed, want to close as fast as possible."),
    ),
    DatasetItem(
        case_id="browser-001",
        category="browser",
        expected_label="browser",
        intake=_lead("Just curious what homes look like in this neighborhood, not in a rush."),
    ),
    DatasetItem(
        case_id="browser-002",
        category="browser",
        expected_label="browser",
        intake=_lead("Might be interested in buying sometime next year, still researching areas."),
    ),
    DatasetItem(
        case_id="browser-003",
        category="browser",
        expected_label="browser",
        intake=_lead("Can you send general pricing info? Not ready to talk to an agent yet."),
    ),
    DatasetItem(
        case_id="browser-004",
        category="browser",
        expected_label="browser",
        intake=_lead("Window shopping for now, just want to see what's out there."),
    ),
    DatasetItem(
        case_id="browser-005",
        category="browser",
        expected_label="browser",
        intake=_lead("No timeline yet, just checking listings out of curiosity."),
    ),
    DatasetItem(
        case_id="browser-006",
        category="browser",
        expected_label="browser",
        intake=_lead("Thinking about it long-term, maybe in a couple years."),
    ),
    DatasetItem(
        case_id="spam-001",
        category="spam",
        expected_label="spam",
        intake=_lead("CONGRATULATIONS!! You've WON a free vacation, click here now!!!"),
    ),
    DatasetItem(
        case_id="spam-002",
        category="spam",
        expected_label="spam",
        intake=_lead("Buy cheap watches and sunglasses at wholesale prices, visit our site."),
    ),
    DatasetItem(
        case_id="spam-003",
        category="spam",
        expected_label="spam",
        intake=_lead("Increase your website traffic instantly with our SEO service, reply now."),
    ),
    DatasetItem(
        case_id="spam-004",
        category="spam",
        expected_label="spam",
        intake=_lead("Hot singles in your area want to meet you tonight, click the link."),
    ),
    DatasetItem(
        case_id="spam-005",
        category="spam",
        expected_label="spam",
        intake=_lead("URGENT: your account has been suspended, verify your password immediately."),
    ),
    DatasetItem(
        case_id="spam-006",
        category="spam",
        expected_label="spam",
        intake=_lead("Earn $5000 a week from home with this one simple trick, no experience needed."),
    ),
    DatasetItem(
        case_id="ambiguous-001",
        category="ambiguous",
        expected_label=None,
        intake=_lead("Hey, following up on our conversation."),
    ),
    DatasetItem(
        case_id="ambiguous-002",
        category="ambiguous",
        expected_label=None,
        intake=_lead("Is this still available?"),
    ),
    DatasetItem(
        case_id="ambiguous-003",
        category="ambiguous",
        expected_label=None,
        intake=_lead("Not sure, let me think about it and get back to you."),
    ),
    DatasetItem(
        case_id="ambiguous-004",
        category="ambiguous",
        expected_label=None,
        intake=_lead("Okay thanks."),
    ),
]
