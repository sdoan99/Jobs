# Hermes Token Usage Report — ALL TIME

*Generated: 2026-05-16 21:09 UTC  |  Source: ~/.hermes/state.db*

## 1. Cron LLM Jobs

*115 sessions across 3 jobs*

| Job Name | Runs | Input | Output | Total |
| --- | --- | --- | --- | --- |
| signal-detector-sweep | 37 | 1.45M | 128.1K | 1.58M |
| live-sync | 77 | 359.4K | 30.4K | 389.9K |
| auto-update-check | 1 | 3.6K | 179 | 3.8K |

### signal-detector-sweep — 1.58M total

| Model | Runs | Input | Output | Total |
| --- | --- | --- | --- | --- |
| gpt-5.5 | 37 | 1.45M | 128.1K | 1.58M |

### live-sync — 389.9K total

| Model | Runs | Input | Output | Total |
| --- | --- | --- | --- | --- |
| gpt-5.5 | 77 | 359.4K | 30.4K | 389.9K |

### auto-update-check — 3.8K total

| Model | Runs | Input | Output | Total |
| --- | --- | --- | --- | --- |
| gpt-5.5 | 1 | 3.6K | 179 | 3.8K |

## 2. Pipeline Hermes Calls

*1 sessions in 1 provider/model groups*

| Provider | Model | Calls | Input | Output | Total | Source |
| --- | --- | --- | --- | --- | --- | --- |
| opencode-zen | deepseek-v4-flash-free | 1 | 18.4K | 225 | 18.6K | Sports_Trend fallback |

## 3. Agent CLI + Subagent Children

*19 parent sessions, 45 child subagent sessions*

| Model | Parents | Children | Parent Input | Parent Output | Child Input | Child Output | Total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gpt-5.5 | 9 | 19 | 1.57M | 99.8K | 1.67M | 99.7K | 3.44M |
| deepseek-v4-flash | 3 | 12 | 429.0K | 136.9K | 763.8K | 107.1K | 1.44M |
| deepseek-v4-flash-free | 3 | 10 | 385.2K | 48.2K | 582.2K | 79.4K | 1.10M |
| gpt-5.4-mini | 3 | 3 | 286.1K | 15.6K | 114.1K | 11.8K | 427.5K |
| gpt-5.3-codex | 1 | 1 | 161.3K | 10.3K | 19.0K | 2.4K | 193.0K |

### Top 25 Parent Sessions by Total Tokens

| Session ID (last 20) | Model | Parent Tokens | Children Tokens | # Children | Total |
| --- | --- | --- | --- | --- | --- |
| 260511_035732_8a86c4 | deepseek-v4-flash | 120.8K | 445.8K | 5 | 566.6K |
| 260515_184514_afbbcf | gpt-5.5 | 268.9K | 252.1K | 1 | 521.0K |
| 260515_230828_e0c7f1 | gpt-5.5 | 233.8K | 254.8K | 2 | 488.5K |
| 260515_161223_e72a3d | deepseek-v4-flash-free | 125.2K | 343.7K | 8 | 468.9K |
| 260510_230638_4c9613 | deepseek-v4-flash | 239.5K | 225.5K | 4 | 465.0K |
| 260515_162955_6acb50 | deepseek-v4-flash-free | 196.7K | 218.4K | 1 | 415.1K |
| 260507_231030_4e7ebd | deepseek-v4-flash | 205.6K | 199.6K | 3 | 405.2K |
| 260511_052018_863603 | gpt-5.5 | 263.2K | 105.2K | 1 | 368.4K |
| 260516_031526_eac9d7 | gpt-5.5 | 155.4K | 76.0K | 2 | 231.5K |
| 260515_183553_247256 | gpt-5.5 | 178.6K | 52.4K | 1 | 231.0K |
| 260511_171213_23df19 | gpt-5.5 | 183.5K | 46.7K | 1 | 230.2K |
| 260516_024515_96fc9f | gpt-5.5 | 122.8K | 104.4K | 1 | 227.1K |
| 260511_222441_838130 | gpt-5.4-mini | 200.5K | 17.0K | 1 | 217.5K |
| 260514_052156_f1263f | deepseek-v4-flash-free | 111.6K | 99.5K | 1 | 211.1K |
| 260512_052649_b501f2 | gpt-5.3-codex | 171.6K | 21.4K | 1 | 193.0K |
| 260511_161921_b033d4 | gpt-5.5 | 141.2K | 28.9K | 1 | 170.1K |
| 260516_174234_eaebef | gpt-5.5 | 122.5K | 28.2K | 1 | 150.6K |
| 260513_231259_a6bdd0 | gpt-5.4-mini | 49.9K | 95.8K | 1 | 145.8K |
| 260516_173526_b9425b | gpt-5.4-mini | 51.2K | 13.0K | 1 | 64.3K |

## 4. Human CLI Sessions

*62 sessions, 5.69M total tokens*

| Model | Sessions | Input | Output | Total |
| --- | --- | --- | --- | --- |
| deepseek-v4-flash-free | 32 | 3.31M | 674.4K | 3.98M |
| deepseek-v4-flash | 23 | 943.5K | 129.3K | 1.07M |
| gpt-5.5 | 4 | 462.7K | 22.0K | 484.7K |
| gpt-5.4-mini | 2 | 130.2K | 5.3K | 135.5K |
| big-pickle | 1 | 13.9K | 352 | 14.3K |

## 5. Telegram Sessions

*No Telegram sessions found.*

## Grand Total

*242 total sessions (42 excluded: 37 cron_noagent + 5 zero_token)*
*14.27M total tokens across all categories*

| Category | Sessions | Input | Output | Total | % of Total | Bar |
| --- | --- | --- | --- | --- | --- | --- |
| Human CLI | 62 | 4.86M | 831.4K | 5.69M | 39.9% | ████████░░░░░░░░░░░░ |
| Subagent Children | 45 | 3.15M | 300.3K | 3.45M | 24.2% | █████░░░░░░░░░░░░░░░ |
| Agent CLI Parent | 19 | 2.83M | 310.8K | 3.14M | 22.0% | ████░░░░░░░░░░░░░░░░ |
| Cron LLM Jobs | 115 | 1.81M | 158.7K | 1.97M | 13.8% | ███░░░░░░░░░░░░░░░░░ |
| Pipeline Hermes | 1 | 18.4K | 225 | 18.6K | 0.1% | ░░░░░░░░░░░░░░░░░░░░ |
| Telegram | 0 | 0 | 0 | 0 | 0.0% | ░░░░░░░░░░░░░░░░░░░░ |
| Other | 0 | 0 | 0 | 0 | 0.0% | ░░░░░░░░░░░░░░░░░░░░ |
| **TOTAL** | **242** | **14.27M** | — | — | **100%** | ████████████████████ |

## Visibility Gaps

The following token usage is **not captured** in this report:

- **StratsPro_Tweet tweet gen calls** — These invoke `opencode` directly via subprocess, bypassing the Hermes session table entirely.
- **News pipelines** — These also call `opencode` for tweet generation via subprocess; no Hermes session is created.
- **Sports_Trend pipeline keeper** — This job is configured with `no_agent: true` (script-only). It runs `/home/ubuntu/.hermes/scripts/gbrain-postgres-export-backup.sh` and emits no LLM calls.
- **All pipeline opencode subprocess calls** — Any pipeline that shells out to `opencode` or `codex` directly will have zero visibility in this database. Only Hermes-native session tracking (where the agent processes the prompt) is captured.
- **Cron no_agent jobs** — `nightly-dream-cycle`, `daily-brain-backup`, and `gbrain-watchdog` run shell scripts with no LLM involvement. Their sessions appear with zero tokens and are excluded from totals.

---
*Report generated by per-job-token-usage-all-time.py at 2026-05-16 21:09 UTC*
