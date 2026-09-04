# Seed Data — [PROJECT_NAME]

The realistic dataset this project's screenshots were captured against — entity names, counts, and
field values, as a plain fixture list, not an executable script. Written by `prompts/10_screenshot-
capture.md`'s Step 6.8 the first time it constructs data for capture; read back by that same step (and
by Step 11/12 or a Continual Refinement round) so a later session reconstructs the *same* dataset
deterministically instead of reverse-engineering it by pixel-inspecting committed screenshots. Full
spec: `docs/claude-directory-spec.md`'s `seed-data.md` entry.

**Update this file whenever the seeded data changes materially** — a new entity type, a renamed field,
a different data volume. A stale fixture list is worse than none: it looks authoritative but no longer
matches what the screenshots actually show.

---

## Entities

[One subsection per entity/table the seeded data populates. Example shape below — replace with the
real dataset the first time Step 10 runs; delete the example once real entries exist.]

### [Entity name, e.g. "Users"]
- Count: [N]
- Field values used: [name/email/role/etc. — enough that another session could recreate an equivalent
  record without guessing]

### [Entity name, e.g. "Orders"]
- Count: [N]
- Field values used: [...]

---

## How it was seeded

[One or two sentences: which script/UI flow created this data — e.g. "via `scripts/seed.py`" or "by
hand through the signup + create-order flow, no seed script exists yet."]
