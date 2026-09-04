# Feature Audit — Lead Intake Triage Agent

Full process: `docs/token-discipline.md` §7. Run once at Step 4 bootstrap, review once per
pipeline iteration touching this project.

---

## 2026-09-04 Audit

| Feature | Status | Reason | Re-evaluate |
|---|---|---|---|
| Google Drive MCP / any MCP server | Disabled (never enabled) | Project integrates with HubSpot (direct `httpx` REST calls) and Ollama (local HTTP API) — neither benefits from an MCP wrapper; no other external system is in scope this round | If a future step adds a system better served by an existing MCP server |
| Post-change validation hook (`.claude/settings.json` `hooks`) | Not wired | Project tooling (pytest/vitest/oxlint) runs fine as a manual Step 6 discipline per `docs/plan-execute-review.md`; no non-noisy hook integration point identified yet | If Step 6 finds the manual discipline is being skipped in practice |
| Project-specific subagents (`.claude/agents/`) | None defined | No task in Steps 4-9 needs isolation or genuine parallelism yet | If Step 6's worker pool orchestration benefits from a dedicated per-stage subagent |

**Estimated token savings:** Avoids MCP server overhead on every prompt (would apply to every
session on this project, of which there will be many across Steps 6-16); avoids hook-fired
summaries with no actionable output.

Detail behind each decision: `.claude/disabled-features.md`.
