# Plan Files Reference

Generated 2026-05-27 22:24


### Jobs / Schema Plans

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/Jobs/plans/inprogress                  | plans-schema                                         | 6%         | > Adapted from `/home/ubuntu/brain/schema.md`    |
|                                          |                                                      |            | (brain page conventions) for implementation      |
|                                          |                                                      |            | plans that evolve across sessions.               |
| ~/Jobs/plans/inprogress                  | plans-schema-extensions                              | 0%         | > Unresolved gaps from the review of `plan-      |
|                                          |                                                      |            | schema.md`. Not part of the schema yet; consider |
|                                          |                                                      |            | adopting these when you next revise the          |
|                                          |                                                      |            | template.                                        |
```

### Dataserver Plans

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/dataserver/plans/todo                  | plan-streaming-caching-audit                         | 0%         | title: Plan - Streaming Caching Audit            |
| ~/dataserver/plans/todo                  | plan-temporary-dataserver-shutdown-restart           | -          | Date: 2026-05-22                                 |
| ~/dataserver/plans/completed             | bug-scan-2026-05-23                                  | 100%       | title: Plan - dataserver lint shim repair        |
| ~/dataserver/plans/completed             | plan-fix-blofin-schwab-feed-integration-bugs         | 93%        | title: Plan - Fix BloFin and Schwab Feed         |
|                                          |                                                      |            | Integration Bugs                                 |
```

### Documentation Plans

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/documentation/plans/inprogress         | plan-schwab-tradingview-datafeed                     | 65%        | title: Plan - Schwab TradingView Datafeed        |
| ~/documentation/plans/todo               | plan-audit-blofin-vendor                             | -          | Date:** 2026-05-15                               |
| ~/documentation/plans/todo               | plan-bybit-vendor-integration                        | 0%         | Status:** Draft  \                               |
| ~/documentation/plans/todo               | plan-persistent-timeseries-store                     | 0%         | Date:** 2026-05-15                               |
| ~/documentation/plans/todo               | schwab-tradingview-dataserver-work-summary           | -          | Date: 2026-05-22                                 |
| ~/documentation/plans/todo               | tradingview-udf-datafeed-checklist                   | 0%         | Each item includes `[Context: line N]`           |
|                                          |                                                      |            | referencing                                      |
|                                          |                                                      |            | `/home/ubuntu/documentation/tradingview/charting |
|                                          |                                                      |            | library-context.txt`. Items marked               |
|                                          |                                                      |            | `[Supplementary]` are general best practices not |
|                                          |                                                      |            | prescribed by the TradingView docs.              |
| ~/documentation/plans/completed          | bug-scan-2026-05-23                                  | 90%        | 2|title: Plan - documentation bug scan no-action |
|                                          |                                                      |            | record                                           |
| ~/documentation/plans/completed          | plan-schwab-high-volume-ohlc-streaming               | -          | title: Plan - Schwab High-Volume 1-Minute OHLC   |
|                                          |                                                      |            | Streaming                                        |
```

### Project92 Plans

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/project92/plans/inprogress             | discordalerts-signal-journaling-integration          | 2%         | title: Plan - DiscordAlerts Signal Journaling    |
|                                          |                                                      |            | Integration                                      |
| ~/project92/plans/inprogress             | supabase-guest-regular-table-remediation             | 2%         | title: Plan - Supabase Guest/Regular Table       |
|                                          |                                                      |            | Remediation                                      |
| ~/project92/plans/inprogress             | tvadv-chart-best-practices-remediation               | 63%        | title: Plan - TVAdvChart TradingView Best-       |
|                                          |                                                      |            | Practices Remediation                            |
| ~/project92/plans/todo                   | Persistent_Memory_Integration                        | 0%         | Last Updated**: November 20, 2025                |
| ~/project92/plans/todo                   | alpaca-browser-client-to-dataserver-websocket-FRD    | -          | 1. Current Architecture (`browser-client.ts`)    |
| ~/project92/plans/todo                   | bug-scan-2026-05-23                                  | 0%         | 2|title: Plan - project92 lint failure           |
|                                          |                                                      |            | remediation                                      |
| ~/project92/plans/todo                   | calc-strat-integration                               | -          | > **For Hermes:** Use subagent-driven-           |
|                                          |                                                      |            | development skill to implement this plan task-   |
|                                          |                                                      |            | by-task.                                         |
| ~/project92/plans/todo                   | discord-before-marketdata-implementation-order       | -          | > **For Hermes:** Use subagent-driven-           |
|                                          |                                                      |            | development skill to implement the referenced    |
|                                          |                                                      |            | plans task-by-task.                              |
| ~/project92/plans/todo                   | discordalerts-signal-journaling-integration          | 0%         | title: Plan - DiscordAlerts Signal Journaling    |
|                                          |                                                      |            | Integration                                      |
| ~/project92/plans/todo                   | discordalertstrader-additional-feature-harvest       | -          | > For Hermes: Use this as a                      |
|                                          |                                                      |            | product/implementation planning reference for    |
|                                          |                                                      |            | integrating additional useful concepts from      |
|                                          |                                                      |            | `/home/ubuntu/DiscordAlertsTrader` into          |
|                                          |                                                      |            | `/home/ubuntu/project92`. Do not copy            |
|                                          |                                                      |            | DiscordAlertsTrader modules directly into        |
|                                          |                                                      |            | project92; extract project92-owned contracts and |
|                                          |                                                      |            | tests.                                           |
| ~/project92/plans/todo                   | goal                                                 | -          | Do not dump raw code into GBrain. Instead,       |
|                                          |                                                      |            | inspect the repository and create curated        |
|                                          |                                                      |            | markdown knowledge files that summarize          |
|                                          |                                                      |            | architecture, data flows, execution order,       |
|                                          |                                                      |            | shared dependencies, fragile assumptions,        |
|                                          |                                                      |            | duplicate logic, and refactor targets.           |
| ~/project92/plans/todo                   | marketdata-live-pricing-integration                  | -          | > **For Hermes:** Use subagent-driven-           |
|                                          |                                                      |            | development skill to implement this plan task-   |
|                                          |                                                      |            | by-task.                                         |
| ~/project92/plans/completed              | plan-schwab-udf-chart-widget-integration             | 82%        | title: Plan - Schwab UDF Chart Widget            |
|                                          |                                                      |            | Integration                                      |
```

### Hermes Plans

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/.hermes/plans/todo                     | kanban-dashboard                                     | -          | Goal                                             |
| ~/.hermes/plans/todo                     | prevent-gbrain-pglite-lock-errors                    | -          | Date: 2026-05-15T17:41:19Z                       |
```

### Hermes Agent Plans

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/.hermes/hermes-agent/docs/plans        | acp-zed-edit-approval-diffs                          | -          | > **For Hermes:** Use subagent-driven-           |
|                                          |                                                      |            | development skill to implement this plan task-   |
|                                          |                                                      |            | by-task.                                         |
| ~/.hermes/hermes-agent/plans/todo        | gemini-oauth-provider                                | -          | Goal                                             |
| ~/.hermes/hermes-agent/docs/plans        | telegram-dm-user-managed-multisession-topics         | -          | > **For Hermes:** Use test-driven-development    |
|                                          |                                                      |            | for implementation. Use subagent-driven-         |
|                                          |                                                      |            | development only after this plan is split into   |
|                                          |                                                      |            | small reviewed tasks.                            |
| ~/.hermes/hermes-                        | s6-overlay-dynamic-subagent-gateways                 | 89%        | > **Status: shipped.** Phases 0–5 landed via PR  |
| agent/docs/plans/completed               |                                                      |            |                                                  |
```

### Brain / Docs Index Plans

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/brain/docs/adapter/plans/todo          | index                                                | -          | description: "Planned features and improvement   |
|                                          |                                                      |            | tracks for the adapter"                          |
| ~/brain/docs/backend/plans/todo          | index                                                | -          | slug: backend/plans/index                        |
| ~/brain/docs/discord-alerts-             | index                                                | -          | type: docs                                       |
| trader/plans/todo                        |                                                      |            |                                                  |
| ~/brain/docs/project92/plans/todo        | index                                                | 0%         | last_updated: 2026-05-11                         |
```

### gstack Test Fixtures

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/gstack/test/fixtures/plans/todo        | ui-heavy-feature                                     | -          | Context                                          |
```

---
_Excludes SKILL.md, generated reference files, and utility scripts._
