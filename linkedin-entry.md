LINKEDIN PROJECT ENTRY
======================

Title
Lead Intake Triage Agent — Multi-Stage LangGraph AI Pipeline with HubSpot CRM Integration & Human-in-the-Loop Review

Date Range
Sep 2026 – Sep 2026

Description
▪ Architected a six-stage LangGraph pipeline (Intake → Intent Classification → Data Enrichment → HubSpot CRM Write → Human Review → Outcome Notification), each stage an isolated contract with a test-verified, enforced tool-scoping boundary.
▪ Engineered a confidence-gated human-in-the-loop workflow: runs complete automatically once local-LLM classification clears a configurable threshold, or pause into a concurrency-safe review queue (approve/edit/reject) actionable in-app or via signature-verified Slack buttons.
▪ Built idempotent, dedupe-safe HubSpot CRM integration via upsert-by-dedupe-key writes, so reprocessing a lead never creates a duplicate contact record.
▪ Implemented resumable and retryable pipeline runs: a paused run resumes via a second compiled LangGraph graph at the paused stage; a failed run retries from the stage that failed, both reusing the primary run's machinery.
▪ Designed a FastAPI + SQLAlchemy backend exposing intake, observability, human-review, benchmark, analytics, and notification APIs, with Alembic-managed schema migrations.
▪ Developed a classification-accuracy benchmark harness (22-item labeled dataset, attempt-level accuracy and item-level consistency across repeats) plus a threshold simulator previewing a candidate threshold before changing it live.
▪ Delivered a React 19 + TypeScript + Tailwind v4 frontend: lead observability, a human review console, a benchmark dashboard with trend visualization, and an aggregate funnel/reviewer-throughput dashboard, fully responsive.
▪ Instrumented full observability: per-lead stage-trace timelines, merged multi-run and review-action history, and in-app plus external Slack notifications for every terminal outcome.
▪ Validated the system with 231 passing automated tests (171 backend, 60 frontend; 98%/89% statement coverage), clean TypeScript/build checks, 0 axe-core accessibility violations, and a fully unit-tested inbound signature-verification trust boundary.

Skills
• Full-Stack Development
• Python
• FastAPI
• React
• TypeScript
• Large Language Models (LLM)
• API Integration

Ready to Post: YES
Character Count: 1963/2000 chars

---

**Updated 2026-09-06 (Continued Development, Features 16-19):** Rewrote the description bullets to
name four capabilities shipped across four CD rounds since this entry was last generated — retryable
failed runs, Slack-based approve/reject, a confidence-threshold simulator, and a funnel/reviewer-
throughput dashboard — none of which this entry had ever mentioned (prior test-count-only refreshes
to `README.md`/`portfolio-description.md` never touched this file). Test count refreshed 182 → 231
(171 backend + 60 frontend), matching `portfolio-description.md`'s same-day update. Re-measured at
1963/2000 chars after trimming verbose phrasing throughout to fit the new claims.
