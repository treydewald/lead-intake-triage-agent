# Disabled Features — Lead Intake Triage Agent

One entry per feature disabled in `.claude/feature-audit.md`, with the reasoning in full (the audit
table stays terse; this file is where the "why" lives if it needs more than one line).

---

## MCP servers (all)

**Disabled:** 2026-09-04
**Reason:** This project's two external integrations (HubSpot CRM, local Ollama LLM) are both
plain HTTP APIs the backend calls directly via `httpx`/the `ollama` Python client — see
`.claude/portfolio-reference.md`'s Key Decisions for why the official HubSpot SDK was also skipped
in favor of direct calls. Neither integration point benefits from an MCP-server wrapper, and
enabling any MCP server would add overhead to every prompt in this project's many remaining
sessions for no corresponding value.
**Alternative used instead:** Direct `httpx` calls (HubSpot) and the `ollama` package (local LLM),
implemented in `backend/app/` during Step 6.
