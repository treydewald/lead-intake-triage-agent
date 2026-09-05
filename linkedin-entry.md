LINKEDIN PROJECT ENTRY
======================

Title
Lead Intake Triage Agent — Multi-Stage LangGraph AI Pipeline with HubSpot CRM Integration & Human-in-the-Loop Review

Date Range
Sep 2026 – Sep 2026

Description
▪ Architected a six-stage LangGraph state-machine pipeline (Intake → Intent Classification → Data Enrichment → HubSpot CRM Write → Human Review → Outcome Notification), each stage implementing an isolated contract, its own state schema slice, and an enforced, test-verified tool-scoping boundary blocking cross-stage tool access.
▪ Engineered a confidence-gated human-in-the-loop workflow: runs complete automatically once a local LLM's intent classification clears a configurable confidence threshold, and pause into a concurrency-safe review queue (approve/edit/reject) when it doesn't.
▪ Built idempotent, dedupe-safe HubSpot CRM integration using upsert-by-dedupe-key writes, so reprocessing a lead never creates a duplicate contact record.
▪ Implemented resumable pipeline runs that persist full state as a JSON snapshot and resume through a second compiled LangGraph graph starting at the paused stage, reusing the primary run's stage machinery.
▪ Designed a FastAPI + SQLAlchemy backend exposing intake (web form, email, callback), observability, human-review, benchmark, and notification APIs, with Alembic-managed schema migrations.
▪ Developed a classification-accuracy benchmark harness that runs the Intent Classification stage standalone against a 22-item labeled dataset, tracking attempt-level accuracy and item-level consistency across repeats.
▪ Delivered a React 19 + TypeScript + Tailwind v4 frontend with lead observability, a human review console, and a benchmark dashboard with trend visualization — fully responsive across desktop and mobile viewports.
▪ Instrumented full observability: per-lead stage-trace timelines, merged multi-run and review-action history, and in-app plus external webhook notifications for every terminal outcome.
▪ Validated the system with 156 passing automated tests (138 backend, 18 frontend), clean TypeScript/build checks, 0 axe-core accessibility violations, and triaged dependency vulnerability scans.

Skills
• Full-Stack Development
• Python
• FastAPI
• React
• TypeScript
• Large Language Models (LLM)
• API Integration

Ready to Post: YES
Character Count: 1957/2000 chars
