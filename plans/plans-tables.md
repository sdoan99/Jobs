# Plan Files Reference

Generated 2026-05-22 19:20


### Jobs / Schema Plans

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/Jobs/plans                             | plans-schema-extensions                              | 0%         | > Unresolved gaps from the review of `plan-      |
|                                          |                                                      |            | schema.md`. Not part of the schema yet; consider |
|                                          |                                                      |            | adopting these when you next revise the          |
|                                          |                                                      |            | template.                                        |
| ~/Jobs/plans                             | plans-schema                                         | 6%         | > Adapted from `/home/ubuntu/brain/schema.md`    |
|                                          |                                                      |            | (brain page conventions) for implementation      |
|                                          |                                                      |            | plans that evolve across sessions.               |
| ~/Jobs/plans                             | plans-tables-20260522                                | 0%         | Generated 2026-05-22 19:19                       |
```

### Dataserver Plans

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/dataserver/plans                       | plan-streaming-caching-audit                         | 0%         | title: Plan - Streaming Caching Audit            |
| ~/dataserver/plans                       | plan-temporary-dataserver-shutdown-restart           | -          | Date: 2026-05-22                                 |
```

### Documentation Plans

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/documentation/plans                    | plan-audit-blofin-vendor                             | -          | Date:** 2026-05-15                               |
| ~/documentation/plans                    | plan-bybit-vendor-integration                        | 0%         | Status:** Draft  \                               |
| ~/documentation/plans                    | plan-persistent-timeseries-store                     | 0%         | Date:** 2026-05-15                               |
| ~/documentation/plans                    | plan-schwab-tradingview-datafeed                     | 65%        | title: Plan - Schwab TradingView Datafeed        |
| ~/documentation/plans                    | schwab-tradingview-dataserver-work-summary           | -          | Date: 2026-05-22                                 |
| ~/documentation/plans                    | tradingview-udf-datafeed-checklist                   | 0%         | Each item includes `[Context: line N]`           |
|                                          |                                                      |            | referencing                                      |
|                                          |                                                      |            | `/home/ubuntu/documentation/tradingview/charting |
|                                          |                                                      |            | library-context.txt`. Items marked               |
|                                          |                                                      |            | `[Supplementary]` are general best practices not |
|                                          |                                                      |            | prescribed by the TradingView docs.              |
| ~/documentation/plans/completed          | plan-schwab-high-volume-ohlc-streaming               | -          | title: Plan - Schwab High-Volume 1-Minute OHLC   |
|                                          |                                                      |            | Streaming                                        |
```

### Project92 Plans

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/project92/plans                        | calc-strat-integration                               | -          | > **For Hermes:** Use subagent-driven-           |
|                                          |                                                      |            | development skill to implement this plan task-   |
|                                          |                                                      |            | by-task.                                         |
| ~/project92/plans                        | marketdata-live-pricing-integration                  | -          | > **For Hermes:** Use subagent-driven-           |
|                                          |                                                      |            | development skill to implement this plan task-   |
|                                          |                                                      |            | by-task.                                         |
| ~/project92/plans                        | discordalerts-signal-journaling-integration          | -          | > **For Hermes:** Use subagent-driven-           |
|                                          |                                                      |            | development skill to implement this plan task-   |
|                                          |                                                      |            | by-task.                                         |
| ~/project92/plans                        | discord-before-marketdata-implementation-order       | -          | > **For Hermes:** Use subagent-driven-           |
|                                          |                                                      |            | development skill to implement the referenced    |
|                                          |                                                      |            | plans task-by-task.                              |
| ~/project92/plans                        | discordalertstrader-additional-feature-harvest       | -          | > For Hermes: Use this as a                      |
|                                          |                                                      |            | product/implementation planning reference for    |
|                                          |                                                      |            | integrating additional useful concepts from      |
|                                          |                                                      |            | `/home/ubuntu/DiscordAlertsTrader` into          |
|                                          |                                                      |            | `/home/ubuntu/project92`. Do not copy            |
|                                          |                                                      |            | DiscordAlertsTrader modules directly into        |
|                                          |                                                      |            | project92; extract project92-owned contracts and |
|                                          |                                                      |            | tests.                                           |
| ~/project92/plans                        | Persistent_Memory_Integration                        | 0%         | Last Updated**: November 20, 2025                |
| ~/project92/plans                        | alpaca-browser-client-to-dataserver-websocket-FRD    | -          | 1. Current Architecture (`browser-client.ts`)    |
| ~/project92/plans                        | discordalerts-signal-journaling-integration          | 0%         | title: Plan - DiscordAlerts Signal Journaling    |
|                                          |                                                      |            | Integration                                      |
| ~/project92/plans                        | goal                                                 | -          | Do not dump raw code into GBrain. Instead,       |
|                                          |                                                      |            | inspect the repository and create curated        |
|                                          |                                                      |            | markdown knowledge files that summarize          |
|                                          |                                                      |            | architecture, data flows, execution order,       |
|                                          |                                                      |            | shared dependencies, fragile assumptions,        |
|                                          |                                                      |            | duplicate logic, and refactor targets.           |
| ~/project92/plans/completed              | plan-schwab-udf-chart-widget-integration             | 82%        | title: Plan - Schwab UDF Chart Widget            |
|                                          |                                                      |            | Integration                                      |
```

### Hermes Plans

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/.hermes/plans                          | prevent-gbrain-pglite-lock-errors                    | -          | Date: 2026-05-15T17:41:19Z                       |
| ~/.hermes/plans                          | kanban-dashboard                                     | -          | Goal                                             |
```

### Hermes Agent Plans

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/.hermes/hermes-agent/docs/plans        | telegram-dm-user-managed-multisession-topics         | -          | > **For Hermes:** Use test-driven-development    |
|                                          |                                                      |            | for implementation. Use subagent-driven-         |
|                                          |                                                      |            | development only after this plan is split into   |
|                                          |                                                      |            | small reviewed tasks.                            |
| ~/.hermes/hermes-agent/docs/plans        | acp-zed-edit-approval-diffs                          | -          | > **For Hermes:** Use subagent-driven-           |
|                                          |                                                      |            | development skill to implement this plan task-   |
|                                          |                                                      |            | by-task.                                         |
| ~/.hermes/hermes-agent/plans             | gemini-oauth-provider                                | -          | Goal                                             |
```

### GitNexus Plans

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/GitNexus/docs/plans                    | feat-cobol-full-language-coverage-plan               | 0%         | title: "feat: Complete COBOL language feature    |
|                                          |                                                      |            | coverage for maximum knowledge graph value"      |
| ~/GitNexus/docs/superpowers/plans        | pr626-high-fixes                                     | 0%         | > **For agentic workers:** REQUIRED SUB-SKILL:   |
|                                          |                                                      |            | Use superpowers:subagent-driven-development      |
|                                          |                                                      |            | (recommended) or superpowers:executing-plans to  |
|                                          |                                                      |            | implement this plan task-by-task. Steps use      |
|                                          |                                                      |            | checkbox (`- [ ]`) syntax for tracking.          |
```

### Brain / Docs Index Plans

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/brain/docs/project92/plans             | index                                                | 0%         | last_updated: 2026-05-11                         |
| ~/brain/docs/discord-alerts-trader/plans | index                                                | -          | type: docs                                       |
| ~/brain/docs/adapter/plans               | index                                                | -          | description: "Planned features and improvement   |
|                                          |                                                      |            | tracks for the adapter"                          |
| ~/brain/docs/backend/plans               | index                                                | -          | slug: backend/plans/index                        |
```

### gstack Test Fixtures

```
| Directory                                | File                                                 | Progress   | Summary                                          |
|------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------|
| ~/gstack/test/fixtures/plans             | ui-heavy-feature                                     | -          | Context                                          |
```

---
_Excludes SKILL.md, generated reference files, and utility scripts._
