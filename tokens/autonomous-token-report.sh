#!/usr/bin/env bash
#==============================================================================
# autonomous-token-report.sh
# 
# Generates a token usage report for all non-human-prompted Hermes Agent 
# AI activity — every automated LLM job:
#   • cron jobs (all scheduled runs)
#   • delegated subagents (delegate_task from cron/automated contexts)
#   • spawned Hermes CLI processes (hermes chat -q, background spawns)
#   • webhook-triggered sessions
#
# Excludes: human-prompted CLI sessions (even if they used delegate_task).
#
# Reports are saved as /home/ubuntu/Jobs/token-report-<date>.txt
#
# Usage:
#   ./autonomous-token-report.sh              # last 6 hours (default)
#   ./autonomous-token-report.sh 24           # last 24 hours
#   ./autonomous-token-report.sh 1h           # last 1 hour
#   ./autonomous-token-report.sh "2026-05-16" # since date
#==============================================================================
set -euo pipefail

STATE_DB="${HOME}/.hermes/state.db"
AGENT_LOG="${HOME}/.hermes/logs/agent.log"
REPORT_DIR="${HOME}/Jobs"

# ---- Parse window argument ----
WINDOW_ARG="${1:-6h}"

case "$WINDOW_ARG" in
  *h)   HOURS="${WINDOW_ARG%h}"; SINCE_EPOCH=$(python3 -c "import time; print(time.time() - ${HOURS}*3600)") ;;
  *d)   DAYS="${WINDOW_ARG%d}";  SINCE_EPOCH=$(python3 -c "import time; print(time.time() - ${DAYS}*86400)") ;;
  *m)   MINS="${WINDOW_ARG%m}";  SINCE_EPOCH=$(python3 -c "import time; print(time.time() - ${MINS}*60)") ;;
  *)    SINCE_EPOCH=$(python3 -c "
from datetime import datetime, timezone; 
d=datetime.fromisoformat('${WINDOW_ARG}'); 
print(d.replace(tzinfo=timezone.utc).timestamp())") ;;
esac

OUTFILE="${REPORT_DIR}/token-report-$(date -u +%Y%m%d_%H%M%S).txt"

mkdir -p "${REPORT_DIR}"

# ---- Generate report (Python) ----
python3 << PYEOF
import sqlite3, os, time, re
from datetime import datetime, timezone
from collections import defaultdict

db_path = os.path.expanduser("${STATE_DB}")
log_path = os.path.expanduser("${AGENT_LOG}")
report_path = os.path.expanduser("${OUTFILE}")
window_epoch = float(${SINCE_EPOCH})

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# =========================================================
# 1. COLLECT SESSIONS IN WINDOW
# =========================================================
rows = conn.execute("""
    SELECT id, source, model, started_at, ended_at, message_count, tool_call_count,
           input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
           reasoning_tokens, estimated_cost_usd, actual_cost_usd, api_call_count,
           title, billing_provider
    FROM sessions
    WHERE (started_at >= ? OR ended_at >= ?)
    ORDER BY started_at
""", (window_epoch, window_epoch)).fetchall()

# =========================================================
# 2. CATEGORIZE SESSIONS
# =========================================================
cron_sessions = []      # Cron job runs (automated)
cli_human = []          # Human-prompted CLI (excluded)
cli_auto = []           # Autonomous non-cron (webhook, API, spawned)

for r in rows:
    sid = r['id'] or ''
    src = r['source'] or ''
    title = r['title'] or ''
    
    if 'cron' in sid.lower() or src == 'cron':
        cron_sessions.append(r)
    elif src in ('webhook', 'api', 'mcp'):
        cli_auto.append(r)
    elif any(kw in title.lower() for kw in ['delegate', 'subagent', 'spawn', 'background', 'auto', 'scheduled', 'batch']):
        cli_auto.append(r)
    else:
        cli_human.append(r)

# =========================================================
# 3. SCAN AGENT LOG FOR DELEGATE & SPAWN ACTIVITY
# =========================================================
delegate_count = 0
auto_delegate_count = 0
cron_delegate_count = 0
spawned_hermes_count = 0
spawned_from_cron = 0

try:
    with open(log_path) as f:
        for line in f:
            m = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            if not m:
                continue
            try:
                ts = datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
            except:
                continue
            if ts < window_epoch:
                continue
            
            low = line.lower()
            
            # delegate_task calls
            if 'delegate_task' in low and 'completed' in low:
                delegate_count += 1
                sid_m = re.search(r'\[([^\]]+)\]', line)
                if sid_m:
                    sess = sid_m.group(1)
                    if 'cron' in sess.lower():
                        cron_delegate_count += 1
                        auto_delegate_count += 1
                    else:
                        auto_delegate_count += 1
            
            # spawned CLI processes (hermes chat -q, background spawns)
            if ('hermes chat' in low or 'hermes -q' in low or 'spawn' in low):
                spawned_hermes_count += 1
                if 'cron' in line:
                    spawned_from_cron += 1
except:
    pass

# =========================================================
# 4. CRON JOB CONFIG (from cronjob list already known)
# =========================================================
# These are hardcoded from the cronjob listing:
known_cron = {
    '326abe6efae8': {'name': 'live-sync', 'schedule': 'every 15m', 'llm': True},
    '3eefaccdd67c': {'name': 'signal-detector-sweep', 'schedule': 'every 30m', 'llm': True},
    '6b16bb707a8c': {'name': 'auto-update-check', 'schedule': '0 9 * * *', 'llm': True},
    '9359301e8a87': {'name': 'weekly-brain-health', 'schedule': '0 6 * * 1', 'llm': True},
    'dac2c86dc988': {'name': 'nightly-dream-cycle', 'schedule': '0 2 * * *', 'llm': False, 'script': 'gbrain-nightly-dream-cycle.sh'},
    '3ee4241aebea': {'name': 'daily-brain-backup', 'schedule': '0 3 * * *', 'llm': False, 'script': 'gbrain-postgres-export-backup.sh'},
    '95b166882d19': {'name': 'gbrain-watchdog', 'schedule': 'every 15m', 'llm': False, 'script': 'gbrain-watchdog.sh'},
}

no_agent_jobs = [v for v in known_cron.values() if not v['llm']]

# =========================================================
# 5. HELPERS
# =========================================================
def fmt_ts(ts):
    if ts:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%H:%M:%S')
    return '--:--:--'

def fmt_dur(start, end):
    if start and end:
        d = end - start
        return f'{d:.0f}s' if d < 120 else f'{d/60:.1f}m'
    return '-'

def sum_tokens(rl):
    inp = sum(r['input_tokens'] or 0 for r in rl)
    out = sum(r['output_tokens'] or 0 for r in rl)
    cr = sum(r['cache_read_tokens'] or 0 for r in rl)
    cw = sum(r['cache_write_tokens'] or 0 for r in rl)
    rsn = sum(r['reasoning_tokens'] or 0 for r in rl)
    calls = sum(r['api_call_count'] or 0 for r in rl)
    msgs = sum(r['message_count'] or 0 for r in rl)
    tools = sum(r['tool_call_count'] or 0 for r in rl)
    return inp, out, cr, cw, rsn, calls, msgs, tools

def avg_or_zero(values):
    n = len(values)
    return sum(values)/n if n > 0 else 0

def identify_job(sid):
    """Map session ID prefix to job name."""
    if 'cron_3eefaccdd67c' in sid:
        return 'signal-detector-sweep', '3eefaccdd67c'
    elif 'cron_326abe6efae8' in sid:
        return 'live-sync', '326abe6efae8'
    return sid[:30], None

# =========================================================
# 6. BUILD REPORT
# =========================================================
lines = []
def L(s=""):
    lines.append(s)

period_start = datetime.fromtimestamp(window_epoch, tz=timezone.utc)
period_end = datetime.fromtimestamp(time.time(), tz=timezone.utc)

L("╔══════════════════════════════════════════════════════════════════════════════╗")
L("║            Automated AI Token Usage Report (non-human LLM jobs)            ║")
L("╚══════════════════════════════════════════════════════════════════════════════╝")
L("")
L(f"  Period:  {period_start.strftime('%Y-%m-%d %H:%M:%S')} UTC")
L(f"     to:   {period_end.strftime('%Y-%m-%d %H:%M:%S')} UTC")
L(f"  Duration: {period_end - period_start}")
L(f"  Source:   hermes SQLite state DB + agent log cross-reference")
L("")

# ---- SECTION A: EXECUTIVE SUMMARY ----
L("═══ EXECUTIVE SUMMARY ═══════════════════════════════════════════════════════")
L("")

# Compute totals
ci, co, cr, cw, crea, ccalls, cmsgs, ctools = sum_tokens(cron_sessions)
ai, ao, ar, aw, area, acalls, amsgs, atools = sum_tokens(cli_auto)
tot_inp = ci + ai
tot_out = co + ao
tot_sessions = len(cron_sessions) + len(cli_auto)

col1 = 46
L(f"  {'LLM-driven cron sessions:':<{col1}} {len(cron_sessions):>4} runs")
L(f"  {'Max possible cron runs (6h window):':<{col1}} "
  f"{'20 (live-sync every 15m) + 12 (signal-detector every 30m) = 32'}")
L(f"  {'Autonomous CLI/webhook sessions:':<{col1}} {len(cli_auto)}")
L(f"  {'Delegated subagent calls (auto):':<{col1}} {delegate_count} total, {auto_delegate_count} auto-sourced")
L(f"  {'Spawned Hermes instances:':<{col1}} {spawned_hermes_count}")
L(f"  {'No-agent script jobs (free):':<{col1}} {len(no_agent_jobs)} (no LLM cost)")
L("")
L(f"  {'Total Input Tokens (LLM):':<{col1}} {tot_inp:>10,}")
L(f"  {'Total Output Tokens (LLM):':<{col1}} {tot_out:>10,}")
L(f"  {'Total Cache Read Tokens:':<{col1}} {cr + ar:>10,}")
L(f"  {'Total Reasoning Tokens:':<{col1}} {crea + area:>10,}")
L(f"  {'Grand Total LLM Tokens:':<{col1}} {tot_inp+tot_out:>10,}")
L(f"  {'Total API Calls:':<{col1}} {ccalls + acalls:>4}")
L(f"  {'Total Messages:':<{col1}} {cmsgs + amsgs:>4}")
L(f"  {'Total Tool Calls:':<{col1}} {ctools + atools:>4}")
L("")

# ---- SECTION B: CRON JOB BREAKDOWN ----
L("═══ CRON JOB BREAKDOWN ══════════════════════════════════════════════════════")
L("")

# Group by job
cron_by_job = defaultdict(list)
for r in cron_sessions:
    jname, jid = identify_job(r['id'])
    cron_by_job[jname].append(r)

for job_name in sorted(cron_by_job.keys()):
    sessions = cron_by_job[job_name]
    ji, jo, jr, jw, jrea, jcalls, jmsgs, jtools = sum_tokens(sessions)
    inps = [r['input_tokens'] or 0 for r in sessions]
    outs = [r['output_tokens'] or 0 for r in sessions]
    durs = [r['ended_at'] - r['started_at'] for r in sessions if r['started_at'] and r['ended_at']]
    
    L(f"  ▶ {job_name}")
    L(f"    {'Runs in window:':<25s} {len(sessions)}")
    L(f"    {'Total input tokens:':<25s} {ji:>8,}")
    L(f"    {'Total output tokens:':<25s} {jo:>8,}")
    L(f"    {'Total cache read:':<25s} {jr:>8,}")
    L(f"    {'Total reasoning:':<25s} {jrea:>8,}")
    if inps:
        L(f"    {'Avg input/run:':<25s} {avg_or_zero(inps):>8,.0f}")
        L(f"    {'Avg output/run:':<25s} {avg_or_zero(outs):>8,.0f}")
        L(f"    {'Min input:':<25s} {min(inps):>8,}")
        L(f"    {'Max input:':<25s} {max(inps):>8,}")
    if durs:
        L(f"    {'Avg run duration:':<25s} {avg_or_zero(durs):>8,.0f}s")
        L(f"    {'Min duration:':<25s} {min(durs):>8.0f}s")
        L(f"    {'Max duration:':<25s} {max(durs):>8.0f}s")
    L(f"    {'API calls:':<25s} {jcalls}")
    L(f"    {'Tool calls:':<25s} {jtools}")
    L(f"    {'Messages:':<25s} {jmsgs}")
    L("")

# Expected vs actual cron runs for LLM jobs
cron_schedule_map = {
    'live-sync': 24,            # every 15m × 6h = 24
    'signal-detector-sweep': 12,  # every 30m × 6h = 12
    'auto-update-check': 1,
    'weekly-brain-health': 1,
}
L("  — Cron Schedule Compliance —")
hours_in_window = (period_end - period_start).total_seconds() / 3600
for job_name in sorted(cron_by_job.keys()):
    sessions = cron_by_job[job_name]
    actual = len(sessions)
    expected = cron_schedule_map.get(job_name, 0)
    # Adjust expected for non-standard window sizes
    if job_name == 'live-sync':
        expected = int(hours_in_window * 4)      # 4 runs/hour
    elif job_name == 'signal-detector-sweep':
        expected = int(hours_in_window * 2)      # 2 runs/hour
    pct = (actual / expected * 100) if expected else 0
    status = "✓" if actual >= expected else "!"
    L(f"    {job_name:40s}  {actual:>2}/{expected:<2} runs  ({pct:>5.0f}%)  {status}")
L("")

# ---- SECTION C: DETAILED RUN LOG ----
L("═══ DETAILED RUN LOG (all cron runs) ════════════════════════════════════════")
L("")
L(f"  {'Time':>8s}  {'Dur':>6s}  {'Job':^40s}  {'Input':>7s}  {'Output':>7s}  {'API':>4s}  {'Model':^20s}")
L("  " + "-"*105)
for r in cron_sessions:
    inp = r['input_tokens'] or 0
    out = r['output_tokens'] or 0
    calls = r['api_call_count'] or 0
    jname, jid = identify_job(r['id'])
    model = (r['model'] or '?')[:20]
    L(f"  {fmt_ts(r['started_at']):>8s}  {fmt_dur(r['started_at'], r['ended_at']):>6s}  {jname:40s}  {inp:>7,}  {out:>7,}  {calls:>4}  {model:20s}")
L("")

ci_def, co_def = ci, co  # already computed
L(f"  CRON TOTALS:  {len(cron_sessions)} sessions")
L(f"    Input:  {ci:>10,}    Output: {co:>10,}    CacheRead: {cr:>10,}    Reasoning: {crea:>10,}")
L(f"    API: {ccalls:>4}  Msgs: {cmsgs:>4}  Tools: {ctools:>4}  Total LLM Tokens: {ci+co:>10,}")
L("")

# ---- SECTION D: NO-AGENT (SCRIPT-ONLY) JOBS ----
L("═══ NO-AGENT CRON JOBS (script-only — zero LLM cost) ════════════════════════")
L("")
L("  These cron jobs use no_agent=true and run shell scripts directly —")
L("  no LLM conversation loop, zero token consumption by design:")
L("")
L(f"  {'Job Name':25s}  {'Schedule':16s}  {'Script Used'}")
L(f"  {'-'*25}  {'-'*16}  {'-'*40}")
for j in no_agent_jobs:
    L(f"  {j['name']:25s}  {j['schedule']:16s}  {j['script']}")
L("")
L("  Note: These jobs do not create session entries in the state database")
L("  since they have no LLM conversation. Their script execution is managed")
L("  directly by the cron scheduler.")
L("")

# ---- SECTION E: DELEGATED SUBAGENTS ----
L("═══ DELEGATED SUBAGENTS (delegate_task) ═════════════════════════════════════")
L("")
L(f"  Total delegate_task calls in window:  {delegate_count}")
L(f"    From cron/automated sessions:        {cron_delegate_count}")
L(f"    From human CLI sessions:             {delegate_count - cron_delegate_count}")
L("")
if cron_delegate_count > 0:
    L("  ⚠ These subagents ran autonomously. Their token consumption is")
    L("    included within the parent cron session's totals above (delegate_task")
    L("    shares the parent session's context and token accounting).")
if delegate_count - cron_delegate_count > 0:
    L("  (Human-prompted delegate_task calls excluded from automated totals.)")
L("")

# ---- SECTION F: SPAWNED HERMES / BACKGROUND CLI ----
L("═══ SPAWNED HERMES CLI INSTANCES ════════════════════════════════════════════")
L("")
L(f"  Spawned Hermes processes detected: {spawned_hermes_count}")
L(f"    From cron context:               {spawned_from_cron}")
L(f"    From human context:              {spawned_hermes_count - spawned_from_cron}")
L("")
if spawned_hermes_count > 0:
    L("  ⚠ These are standalone hermes CLI processes spawned via terminal,")
    L("    tmux, or background execution. Each creates its own session entry.")
L("")
if spawned_hermes_count == 0:
    L("  (No Hermes CLI instances were spawned autonomously in this window.)")
L("")

# ---- SECTION G: AUTONOMOUS CLI/WEBHOOK ----
if cli_auto:
    L("═══ AUTONOMOUS CLI / WEBHOOK SESSIONS ══════════════════════════════════════")
    L("")
    for r in cli_auto:
        inp = r['input_tokens'] or 0
        out = r['output_tokens'] or 0
        calls = r['api_call_count'] or 0
        L(f"  {fmt_ts(r['started_at'])} | {r['id'][:50]} | In:{inp:>7,} Out:{out:>7,} | {r['title'] or '-'}")
    L("")
    L(f"  AUTO CLI TOTALS: Input={ai:,} Output={ao:,} APIcalls={acalls}")
    L("")
else:
    L("═══ AUTONOMOUS CLI / WEBHOOK SESSIONS ══════════════════════════════════════")
    L("")
    L("  (None found — all CLI sessions in this window were human-initiated.)")
    L("")

# ---- SECTION H: MODEL USAGE BREAKDOWN ----
L("═══ MODEL USAGE BREAKDOWN ═══════════════════════════════════════════════════")
L("")

model_stats = defaultdict(lambda: {'inp': 0, 'out': 0, 'calls': 0, 'sessions': 0})
for r in cron_sessions:
    m = r['model'] or 'unknown'
    model_stats[m]['inp'] += r['input_tokens'] or 0
    model_stats[m]['out'] += r['output_tokens'] or 0
    model_stats[m]['calls'] += r['api_call_count'] or 0
    model_stats[m]['sessions'] += 1

for r in cli_auto:
    m = r['model'] or 'unknown'
    model_stats[m]['inp'] += r['input_tokens'] or 0
    model_stats[m]['out'] += r['output_tokens'] or 0
    model_stats[m]['calls'] += r['api_call_count'] or 0
    model_stats[m]['sessions'] += 1

L(f"  {'Model':^25s}  {'Sessions':>8s}  {'Input':>10s}  {'Output':>10s}  {'Total':>10s}  {'API Calls':>8s}")
L("  " + "-"*80)
for m, s in sorted(model_stats.items()):
    tot = s['inp'] + s['out']
    L(f"  {m:25s}  {s['sessions']:>8}  {s['inp']:>10,}  {s['out']:>10,}  {tot:>10,}  {s['calls']:>8}")
L("")

# ---- SECTION I: SCOPE CHECK (what was examined) ----
L("═══ SCOPE & METHODOLOGY ════════════════════════════════════════════════════")
L("")
L("  Data sources examined:")
L("    1. Hermes SQLite state DB  — all sessions with started_at/ended_at in window")
L("    2. Agent log               — delegate_task completes, spawned processes")
L("    3. Cron job list           — all active scheduled jobs and their configurations")
L("")
L("  Activity types counted as 'automated / non-human':")
L("    ✓ Cron job runs (scheduled, LLM-driven)")
L("    ✓ Webhook / API / MCP-triggered sessions")
L("    ✓ delegate_task subagents called from cron/automated sessions")
L("    ✓ Spawned Hermes CLI instances from automated contexts")
L("")
L("  Activity types EXCLUDED:")
L("    ✗ Human CLI sessions (even if they used delegate_task)")
L("    ✗ No-agent script jobs (no LLM consumption)")
L("    ✗ Proxy/third-party LLM calls through gbrain or other tools")
L("      (not tracked in Hermes state DB)")

# Write report
with open(report_path, 'w') as f:
    f.write('\n'.join(lines) + '\n')

print(f"Report written to {report_path}")
print(f"  {tot_sessions} automated sessions")
print(f"  {tot_inp:,} input tokens")
print(f"  {tot_out:,} output tokens")
print(f"  {tot_inp+tot_out:,} total LLM tokens")

conn.close()
PYEOF
