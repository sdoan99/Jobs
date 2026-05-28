# Schema — Plan Conventions (Living Plan)

> Adapted from `/home/ubuntu/brain/schema.md` (brain page conventions) for implementation plans that evolve across sessions.

## Two-Layer Structure

Every plan has two layers, separated by `---`:

**Above the line — Plan State.** The current live view. Status of every task, what's been tried, what failed, where to pick up next. Rewritten as work progresses.

**Below the line — Session Log.** Append-only, reverse-chronological. Every session's activity, errors encountered, decisions made, and what's next. Never rewrite — only append.

---

## Template

```markdown
---
title: Plan — <Short Name>
status: proposed | active | stalled | completed | abandoned
created: YYYY-MM-DDThh:mm:ssZ
last_updated: YYYY-MM-DDThh:mm:ssZ
last_session: YYYY-MM-DDThh:mm:ssZ
plan_file: /path/to/this/file
source_docs:
  - /path/to/relevant/doc.md
  - /path/to/another/doc.md
---

# Plan: <Short Name>

> One-line executive summary of what this plan accomplishes.

## Context

- **Why this exists:** What problem does it solve?
- **Scope:** What's in bounds, what's explicitly out of bounds.
- **Dependencies:** What else must be true or done before this can ship.

## Task Status

> Current state. Rewritten on each session. Each task is a concrete deliverable with verification.

### [x] Completed
- [x] **T1 — Short name** (YYYY-MM-DD) — Result summary. Key files: `path/to/file`. Verification: how we know it works.

### [~] In Progress
- [~] **T2 — Short name** — What's left. Current blockers.

### [!] Blocked / Errors
- [!] **T3 — Short name**
  - **Error:** What went wrong (error message, observed behavior).
  - **Root cause hypothesis:** What we think causes it.
  - **Tried:**
    - `attempt 1 (YYYY-MM-DD)`: What we did → outcome.
    - `attempt 2 (YYYY-MM-DD)`: What else we tried → outcome.
  - **Next attempt:** The next thing to try.
  - **Related files:** `path/to/file:NNN` (relevant line numbers).

### [ ] Not Started
- [ ] **T4 — Short name** — What it is, acceptance criteria.

## File Manifest

| Path | Purpose | Status |
|------|---------|--------|
| `src/adapter/datafeed.js` | Core UDF datafeed | modified |
| `src/adapter/history-provider.js` | History bar fetch | modified |
| `src/adapter/streaming.js` | WebSocket streaming | pending |
| `src/adapter/test.cjs` | Unit tests | added |

Status values: `untouched` / `modified` / `added` / `deleted` / `pending`

## Verification Checklist

- [ ] Syntax check (`node --check <file>`)
- [ ] Unit tests pass (`node test.cjs`)
- [ ] Integration test (reload page, verify chart renders)
- [ ] Regressions checked (existing features still work)

## Exit Criteria (Plan-Level Definition of Done)

> The whole plan ships when ALL of these are true. Not per-task — plan-wide. Prevents scope creep and gives a clear "stop line."

- [ ] **C1 — Primary objective:** One-sentence description of what the plan must achieve to be considered complete.
- [ ] **C2 — Stakeholder acceptance:** Who signs off and what they need to see (demo, test output, deploy).
- [ ] **C3 — Rollback confidence:** We can revert to the pre-plan state within N minutes if something goes wrong in production.
- [ ] **C4 — Observability:** The change is visible in logs / metrics / dashboards post-deploy.
- [ ] **C5 — Next-team handoff:** Documentation or summary produced for whoever inherits this work.
- [ ] **C6 — Edge-case coverage:** Known edge cases from the plan's `## Context` section are handled or explicitly deferred.

## Open Questions

- **Q1:** Question that needs answering before proceeding.
- **Q2:** Another open question.

## Decision Log

> Consolidated, above-the-line record of every meaningful decision made during the plan. This is the single source of truth for "why did we do it this way" — no scanning session logs required.

| # | Decision | Rationale | Alternative(s) Considered | Date |
|---|----------|-----------|---------------------------|------|
| 1 | Short description of what was decided | Why this was the right call | What else was on the table and why it was rejected | YYYY-MM-DD |

**Convention:** Add a row whenever a decision has meaningful trade-offs or a non-obvious answer. Trivial implementation choices (variable naming, formatting) don't need entries.

## See Also

- [Plan Name](path/to/related-plan.md) — related workstream
- [Brain Page: Concept](path/to/brain/page.md) — durable knowledge

---

## Session Log

> **Append-only.** Newest first. Each entry is one session's work.

### YYYY-MM-DDThh:mm:ssZ — Session: <short summary>

**Continuity from last session:**
- Last state: [completed / in-progress / blocked]
- Pickup point: Description of exactly where to pick up next time
- Re-read these files: `path/to/file`, `path/to/plan.md`

**Work done:**
1. Implemented T2 — changed how X works in `path/to/file`
2. Discovered edge case in Y — see Blocked section above

**Errors encountered:**
- `Error: <message>` — from `command`. Caused by: [what we learned]. Resolution: [fixed by / workaround / still open].

**Decisions made:**
- Decision: why → consequence.

**State changes:**
- T2: `not-started` → `in-progress`
- T3: `in-progress` → `blocked`

**Next session pick-up:**
- Start with T3 next-attempt plan above
- If T3 resolved, move to T4


### YYYY-MM-DDThh:mm:ssZ — Session: <initial plan creation>

**Work done:**
1. Authored plan based on analysis of ...
2. Discovered N bugs in existing code ...

**Errors encountered:**
- (none — this was plan creation)

**State changes:**
- All tasks: `not-started`

**Next session pick-up:**
- Start with T1: implement the first task
```

---

## Conventions

- **Status tags** in task names: `[x]` completed, `[~]` in progress, `[!]` blocked, `[ ]` not started.
- **Root cause hypothesis before next attempt.** Never write "try this" without first writing what you think is wrong.
- **Each error entry names what was tried.** A failed attempt without the hypothesis is noise. Write: "Tried X because we thought Y → outcome was Z."
- **File references include line numbers** when pointing at specific code (`path/to/file:NNN`).
- **Verification checklist is per-plan**, not one-size-fits-all. Customize for the task domain.
- **Session log entries are append-only.** Do not back-edit old entries — that destroys the audit trail. Rewrite only the top-level Plan State section above the `---`.
- **If a root cause is definitive (found, confirmed), promote it to a GBrain page** and link from the plan. The plan tracks process; the brain tracks knowledge.
- **Every session entry starts with continuity.** The first sub-bullet tells the reader (future you or another agent) what was happening last time and what to read first. This is what makes it survive cross-session.

## When to Create a New Plan

Create one when a task needs **3+ sessions** or has **high error risk** (new domain, complex integration, multiple dependencies). For simple one-session tasks, a todo list or inline work suffices.

## When to Archive

Set status to `completed` or `abandoned`. Move the file to `Jobs/plans/archived/` if it's done. Keep it in place if it might get reactivated.

## Relation to Kanban

This plan format fills a different niche than Hermes Kanban:

| Aspect | This plan format | Hermes Kanban |
|--------|-----------------|---------------|
| **Best for** | Single-agent iterative debugging | Multi-profile routed pipelines |
| **Context retention** | Full agent context across iterations | Worker starts fresh each dispatch |
| **Overhead per iteration** | Low — append a log line | Medium — create/claim/complete cycle |
| **Parallelism** | None — one agent working | Fan-out across profiles |
| **Cross-session persistence** | Manual (plan file + session log) | Automatic (SQLite board) |
| **Error history** | Rich log with hypotheses | Run outcomes only |

Use the plan format for deep debugging and implementation iterations. Use Kanban when you need to route work across specialists.
