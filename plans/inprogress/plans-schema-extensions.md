# Schema Extensions — Proposed for Future Plan Iterations

> Unresolved gaps from the review of `plan-schema.md`. Not part of the schema yet; consider adopting these when you next revise the template.

---

## 1. Owner / Responsible Party

Tasks and the plan itself currently have no owner field. For multi-dev or agent-human collaboration, this creates ambiguity.

**Proposed addition to frontmatter:**

```yaml
---
owner: <name-or-agent-id>
---
```

**Proposed per-task owner convention:**

```
- [ ] **T4 — Short name** (owner: @name) — What it is, acceptance criteria.
```

---

## 2. Assumptions Register

Plans are built on assumptions that may be wrong. Without an explicit place to track them, implicit beliefs become surprise blockers.

**Proposed section (after Context / before Task Status):**

```markdown
## Assumptions

> Explicitly stated guesses that, if wrong, would change the plan's approach or viability.
> If an assumption is confirmed wrong, strike it through and create a plan task to address it.

| # | Assumption | Confidence | Risk if Wrong | Status |
|---|------------|------------|---------------|--------|
| 1 | The API returns paginated results | High | Would need batching logic | unconfirmed |
| 2 | Postgres < 15 supports this index syntax | Medium | Need alternative DDL | confirmed |
```

---

## 3. Link to the Hermes `writing-plans` Skill

The plan schema lives alongside the `writing-plans` skill but doesn't reference it. Any agent or human tasked with creating a plan needs to know the pairing.

**Proposed See-Also entry:**

```
- [Writing Plans (Hermes Skill)](skill://writing-plans) — agent workflow for authoring plans following this schema
```

---

## 4. Rollback / Recovery Convention

When a task goes sideways and needs to be reverted, there's no convention for tracking it. Without that, the session log buries the reversal and the plan state above the line never reflects that something was tried and undone.

**Option A — Reverted Tasks section (above the line):**

```markdown
## Reverted

| Task | What Was Tried | Why Reverted | Date |
|------|----------------|--------------|------|
| T2   | Switched to library X | Broken on Safari 15 | 2026-05-15 |
```

**Option B — New status tag `[r]` for reverted:**

```
- [r] **T2 — Short name** — Attempted library X, reverted due to Safari compatibility (2026-05-15).
```

**Combined advice:** Use Option A for significant reversals (library swaps, architecture changes). Use Option B for quick test-and-discard cycles.

---

## 5. GBrain Integration Workflow

The plan conventions say "promote definitive root causes to GBrain pages" but provide no systematic workflow. For anyone who uses GBrain as their durable knowledge store, this is the bridge between ephemeral session logs and permanent knowledge.

**Proposed section (above the line, after See Also or Decision Log):**

```markdown
## GBrain Integration

> One row per discovery that earned a permanent brain page. Prevents repeating the same research across plans.

| Discovered In | Page Slug | Topic | Date |
|---------------|-----------|-------|------|
| this plan, T3 | `engineering/datafeed-timestamp-bug` | Datafeed timestamp normalization quirk | 2026-05-10 |

**Workflow:**
1. When a root cause is definitively confirmed → create a GBrain page
2. When a non-obvious workaround is found → create a GBrain page
3. Link back to this plan from the GBrain page via `## See Also`
4. Add a row to this table so other plans can discover it
```

---

*Last updated: 2026-05-17*
