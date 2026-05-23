#!/usr/bin/env python3
"""
per-job-token-usage-all-time.py — Hermes token usage analysis by category.

Analyzes ~/.hermes/state.db (SQLite, sessions table) and ~/.hermes/cron/jobs.json
to produce a categorized breakdown of token consumption across:
  - Cron LLM jobs (grouped by job name, per-model breakdown)
  - Pipeline Hermes calls (provider/model groups with source classification)
  - Agent CLI parents + subagent children (model-level and top-25 parent sessions)
  - Human CLI sessions
  - Telegram sessions
  - Grand total with category percentages

Output formats:
  --format plain   : clean markdown tables (| col | col |)
  --format box     : ASCII box art tables (┌─┬─┐ style)

Usage:
  python3 per-job-token-usage-all-time.py                   # --all-time, stdout, plain
  python3 per-job-token-usage-all-time.py --hours 24         # last 24 hours
  python3 per-job-token-usage-all-time.py --format box        # box art output
  python3 per-job-token-usage-all-time.py --output report.md  # write to file
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone

# ─── Paths ────────────────────────────────────────────────────────────────────
STATE_DB = os.path.expanduser("~/.hermes/state.db")
JOBS_JSON = os.path.expanduser("~/.hermes/cron/jobs.json")

# ─── Cron job ID → name mapping ──────────────────────────────────────────────
def load_cron_jobs(path=JOBS_JSON):
    """Load cron jobs.json and return { job_hex_id: job_name }."""
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    mapping = {}
    for job in data.get("jobs", []):
        mapping[job["id"]] = job.get("name", job["id"])
    return mapping


def extract_cron_job_id(session_id):
    """Extract the 12-char hex job ID from a cron session_id like cron_3eefaccdd67c_..."""
    m = re.match(r"cron_([a-f0-9]{12})_", session_id)
    return m.group(1) if m else None


def fmt_tok(n):
    """Human-readable token count: 1.23M / 456.7K / 1234."""
    if n is None:
        return "0"
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


# ─── Database query ───────────────────────────────────────────────────────────
def query_sessions(db_path=STATE_DB, hours=None):
    """
    Fetch all sessions from state.db. Returns list of dicts.
    If hours is set, only sessions with started_at inside that window.
    """
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    where = ""
    params = []
    if hours:
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        where = "WHERE started_at >= ?"
        params = [cutoff]

    c.execute(f"""
        SELECT id, source, model, parent_session_id,
               started_at, ended_at, message_count,
               input_tokens, output_tokens, billing_provider
        FROM sessions {where}
        ORDER BY started_at ASC
    """, params)

    cols = [d[0] for d in c.description]
    rows = [dict(zip(cols, row)) for row in c.fetchall()]
    conn.close()
    return rows


# ─── Categorization ───────────────────────────────────────────────────────────
def categorize_sessions(rows, cron_job_map):
    """
    Classify each session into one of the 7 categories.
    Also identifies cron_noagent and zero_token sessions to exclude from main counts.

    Rules:
      cron_noagent: source='cron' AND (model IS NULL OR zero tokens)
      cron_llm:     source='cron' AND model IS NOT NULL AND tokens > 0
      zero_token:   NOT cron AND tokens = 0 (excluded from main counts)
      pipeline:     source='cli', no parent, no children, msg_count<=3,
                    billing in (opencode-zen, openai-codex), tokens>0
      agent_cli_parent: source='cli', no parent, has children
      subagent_child:   source='cli', has parent_session_id
                         NOTE: these may ALSO be parents (nested delegation chains)
      human_cli:   source='cli', no parent, no children, NOT pipeline
      telegram:    source='telegram'
      other:       everything else

    Returns (cats, child_counts) where cats is a dict of category-name -> list of row dicts.
    """
    # Pre-compute parent IDs — every session that has at least one child
    parent_ids = set()
    for r in rows:
        if r["parent_session_id"]:
            parent_ids.add(r["parent_session_id"])

    # Pre-compute child counts per parent
    child_counts = defaultdict(int)
    for r in rows:
        if r["parent_session_id"]:
            child_counts[r["parent_session_id"]] += 1

    cats = {
        "cron_llm": [],
        "cron_noagent": [],
        "pipeline_hermes": [],
        "agent_cli_parent": [],
        "subagent_child": [],
        "human_cli": [],
        "telegram": [],
        "other": [],
        "zero_token": [],
    }

    for r in rows:
        total_tokens = (r["input_tokens"] or 0) + (r["output_tokens"] or 0)
        source = r["source"]
        has_parent = bool(r["parent_session_id"])
        model = r.get("model")
        billing = r.get("billing_provider")
        msg_count = r.get("message_count", 0)

        # ── Step 1: Handle zero-token sessions ───────────────────────────────
        if total_tokens == 0:
            if source == "cron":
                # Cron with zero tokens (or no model — caught here too)
                cats["cron_noagent"].append(r)
            else:
                # Non-cron zero-token sessions
                cats["zero_token"].append(r)
            continue

        # ── Step 2: Source-based classification (tokens > 0) ──────────────────
        if source == "cron":
            # Should not reach here with no model since model IS NOT NULL
            # is the condition for cron_llm; fall through if somehow hit.
            if not model:
                cats["cron_noagent"].append(r)
                continue
            cats["cron_llm"].append(r)
            continue

        if source == "telegram":
            cats["telegram"].append(r)
            continue

        if source == "cli":
            if has_parent:
                # Subagent child — may ALSO be a parent in a delegation chain,
                # but we classify by the has_parent property as the spec says.
                cats["subagent_child"].append(r)
                continue

            # Top-level CLI (no parent) — check if it spawns children
            if r["id"] in parent_ids:
                cats["agent_cli_parent"].append(r)
                continue

            # No parent, no children — pipeline candidate
            is_pipeline = (
                billing in ("opencode-zen", "openai-codex")
                and msg_count <= 3
            )
            if is_pipeline:
                cats["pipeline_hermes"].append(r)
                continue

            # Everything else with no parent/children is human_cli
            cats["human_cli"].append(r)
            continue

        # Fallback for unexpected source values
        cats["other"].append(r)

    return cats, child_counts


# ─── Pipeline source classification ──────────────────────────────────────────
def classify_pipeline_source(billing_provider, model):
    """
    Classify a pipeline Hermes call into one of the three source types:
      - "FinEd copy gen"     : openai-codex with gpt-5.3/gpt-5.4
      - "Sports_Trend crop"  : big-pickle or minimax (any provider)
      - "Sports_Trend fallback" : everything else
    """
    if billing_provider == "openai-codex" and model in ("gpt-5.3-codex", "gpt-5.4", "gpt-5.4-mini"):
        return "FinEd copy gen"
    if model in ("big-pickle", "minimax"):
        return "Sports_Trend crop"
    return "Sports_Trend fallback"


# ─── Aggregation helpers ──────────────────────────────────────────────────────
def sum_tokens(rows):
    return sum(r["input_tokens"] or 0 for r in rows), sum(r["output_tokens"] or 0 for r in rows)


# ─── Visual bar ───────────────────────────────────────────────────────────────
def ascii_bar(frac, width=20):
    """Return a unicode bar using █ and ░ characters."""
    filled = round(frac * width)
    return "█" * filled + "░" * (width - filled)


# ─── Plain markdown report ────────────────────────────────────────────────────
def report_plain(cats, child_counts, cron_job_map, hours=None):
    """Generate clean markdown tables."""
    lines = []

    # ── Title & metadata ──────────────────────────────────────────────────────
    period = "ALL TIME" if hours is None else f"LAST {hours} HOURS"
    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"# Hermes Token Usage Report — {period}")
    lines.append(f"\n*Generated: {gen_time}  |  Source: ~/.hermes/state.db*")
    lines.append("")

    # Count excluded
    zero_tok_count = len(cats["zero_token"])
    cron_noagent_count = len(cats["cron_noagent"])

    exclude_sessions = cats["cron_noagent"] + cats["zero_token"]
    excluded_count = len(exclude_sessions)
    main_sessions = [r for r in sum(cats.values(), []) if r not in exclude_sessions]

    # ── 1. Cron LLM Jobs ──────────────────────────────────────────────────────
    cron_llm_rows = cats["cron_llm"]
    cron_job_groups = defaultdict(list)
    for r in cron_llm_rows:
        jid = extract_cron_job_id(r["id"])
        jname = cron_job_map.get(jid, jid or "unknown")
        cron_job_groups[jname].append(r)

    lines.append("## 1. Cron LLM Jobs")
    lines.append("")
    lines.append(f"*{len(cron_llm_rows)} sessions across {len(cron_job_groups)} jobs*")
    lines.append("")

    # Sort by total tokens descending
    cron_job_totals = {
        name: (len(rows), sum(r["input_tokens"] or 0 for r in rows),
               sum(r["output_tokens"] or 0 for r in rows))
        for name, rows in cron_job_groups.items()
    }
    sorted_jobs = sorted(cron_job_totals.items(),
                         key=lambda x: x[1][1] + x[1][2], reverse=True)

    lines.append("| Job Name | Runs | Input | Output | Total |")
    lines.append("| --- | --- | --- | --- | --- |")
    for name, (cnt, inp, out) in sorted_jobs:
        tot = inp + out
        lines.append(f"| {name} | {cnt} | {fmt_tok(inp)} | {fmt_tok(out)} | {fmt_tok(tot)} |")
    lines.append("")

    # Per-job model breakdown
    for name in [x[0] for x in sorted_jobs]:
        rows = cron_job_groups[name]
        model_groups = defaultdict(list)
        for r in rows:
            model_groups[r["model"]].append(r)

        total_job = sum(r["input_tokens"] or 0 for r in rows) + sum(r["output_tokens"] or 0 for r in rows)
        lines.append(f"### {name} — {fmt_tok(total_job)} total")
        lines.append("")
        lines.append("| Model | Runs | Input | Output | Total |")
        lines.append("| --- | --- | --- | --- | --- |")
        for model, mrows in sorted(model_groups.items(),
                                   key=lambda x: sum(r["input_tokens"] or 0 for r in x[1]) + sum(r["output_tokens"] or 0 for r in x[1]),
                                   reverse=True):
            cnt = len(mrows)
            inp = sum(r["input_tokens"] or 0 for r in mrows)
            out = sum(r["output_tokens"] or 0 for r in mrows)
            tot = inp + out
            lines.append(f"| {model} | {cnt} | {fmt_tok(inp)} | {fmt_tok(out)} | {fmt_tok(tot)} |")
        lines.append("")

    # ── 2. Pipeline Hermes Calls ──────────────────────────────────────────────
    pipeline_rows = cats["pipeline_hermes"]
    # Group by (billing_provider, model)
    pipeline_groups = defaultdict(list)
    for r in pipeline_rows:
        key = (r["billing_provider"], r["model"])
        pipeline_groups[key].append(r)

    lines.append("## 2. Pipeline Hermes Calls")
    lines.append("")
    lines.append(f"*{len(pipeline_rows)} sessions in {len(pipeline_groups)} provider/model groups*")
    lines.append("")

    # Sort by input tokens descending
    sorted_pipelines = sorted(
        pipeline_groups.items(),
        key=lambda x: sum(r["input_tokens"] or 0 for r in x[1]),
        reverse=True
    )

    lines.append("| Provider | Model | Calls | Input | Output | Total | Source |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for (prov, model), mrows in sorted_pipelines:
        cnt = len(mrows)
        inp = sum(r["input_tokens"] or 0 for r in mrows)
        out = sum(r["output_tokens"] or 0 for r in mrows)
        src = classify_pipeline_source(prov, model)
        lines.append(f"| {prov or '—'} | {model} | {cnt} | {fmt_tok(inp)} | {fmt_tok(out)} | {fmt_tok(inp+out)} | {src} |")
    lines.append("")

    # ── 3. Agent CLI + Subagent Children ──────────────────────────────────────
    parent_rows = cats["agent_cli_parent"]
    child_rows = cats["subagent_child"]

    # Build a comprehensive lookup: session ID → model for ALL sessions
    # (needed because nested delegation chains have subagent_child rows that
    #  are also parents — we need to find their model even though they're
    #  in the child category)
    all_session_models = {}
    for cat_list in cats.values():
        for r in cat_list:
            if r["id"]:
                all_session_models[r["id"]] = r["model"] or "unknown"

    # Model-level summary
    model_summary = defaultdict(lambda: {"parents": 0, "children": 0, "parent_in": 0, "parent_out": 0, "child_in": 0, "child_out": 0})
    for r in parent_rows:
        model = r["model"] or "unknown"
        model_summary[model]["parents"] += 1
        model_summary[model]["parent_in"] += r["input_tokens"] or 0
        model_summary[model]["parent_out"] += r["output_tokens"] or 0

    # Build parent → child mapping
    parent_child_map = defaultdict(list)
    for r in child_rows:
        parent_child_map[r["parent_session_id"]].append(r)

    for pid, children in parent_child_map.items():
        # Find the parent model using the comprehensive lookup
        parent_model = all_session_models.get(pid, "unknown")
        c_in = sum(c["input_tokens"] or 0 for c in children)
        c_out = sum(c["output_tokens"] or 0 for c in children)
        model_summary[parent_model]["children"] += len(children)
        model_summary[parent_model]["child_in"] += c_in
        model_summary[parent_model]["child_out"] += c_out

    total_parent_sessions = sum(m["parents"] for m in model_summary.values())
    total_child_sessions = sum(m["children"] for m in model_summary.values())

    lines.append("## 3. Agent CLI + Subagent Children")
    lines.append("")
    lines.append(f"*{total_parent_sessions} parent sessions, {total_child_sessions} child subagent sessions*")
    lines.append("")

    lines.append("| Model | Parents | Children | Parent Input | Parent Output | Child Input | Child Output | Total |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for model, m in sorted(model_summary.items(),
                           key=lambda x: x[1]["parent_in"]+x[1]["parent_out"]+x[1]["child_in"]+x[1]["child_out"],
                           reverse=True):
        p_in = m["parent_in"]
        p_out = m["parent_out"]
        c_in = m["child_in"]
        c_out = m["child_out"]
        total = p_in + p_out + c_in + c_out
        lines.append(f"| {model} | {m['parents']} | {m['children']} | {fmt_tok(p_in)} | {fmt_tok(p_out)} | {fmt_tok(c_in)} | {fmt_tok(c_out)} | {fmt_tok(total)} |")
    lines.append("")

    # Top 25 parent sessions by total tokens (parent + children)
    parent_totals = []
    for r in parent_rows:
        pid = r["id"]
        children = parent_child_map.get(pid, [])
        p_tok = (r["input_tokens"] or 0) + (r["output_tokens"] or 0)
        c_in = sum(c["input_tokens"] or 0 for c in children)
        c_out = sum(c["output_tokens"] or 0 for c in children)
        c_tok = c_in + c_out
        total = p_tok + c_tok
        parent_totals.append((pid, r["model"] or "unknown", p_tok, c_tok, len(children), total))

    parent_totals.sort(key=lambda x: x[5], reverse=True)

    lines.append("### Top 25 Parent Sessions by Total Tokens")
    lines.append("")
    lines.append("| Session ID (last 20) | Model | Parent Tokens | Children Tokens | # Children | Total |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for pid, model, p_tok, c_tok, n_child, total in parent_totals[:25]:
        sid_short = pid[-20:]
        lines.append(f"| {sid_short} | {model} | {fmt_tok(p_tok)} | {fmt_tok(c_tok)} | {n_child} | {fmt_tok(total)} |")
    lines.append("")

    # ── 4. Human CLI ──────────────────────────────────────────────────────────
    human_rows = cats["human_cli"]
    h_in, h_out = sum_tokens(human_rows)
    h_tok = h_in + h_out
    lines.append("## 4. Human CLI Sessions")
    lines.append("")
    lines.append(f"*{len(human_rows)} sessions, {fmt_tok(h_tok)} total tokens*")
    lines.append("")

    # Group by model
    model_groups = defaultdict(list)
    for r in human_rows:
        model_groups[r["model"] or "unknown"].append(r)

    lines.append("| Model | Sessions | Input | Output | Total |")
    lines.append("| --- | --- | --- | --- | --- |")
    for model, mrows in sorted(model_groups.items(),
                               key=lambda x: sum(r["input_tokens"] or 0 for r in x[1]) + sum(r["output_tokens"] or 0 for r in x[1]),
                               reverse=True):
        cnt = len(mrows)
        inp = sum(r["input_tokens"] or 0 for r in mrows)
        out = sum(r["output_tokens"] or 0 for r in mrows)
        lines.append(f"| {model} | {cnt} | {fmt_tok(inp)} | {fmt_tok(out)} | {fmt_tok(inp+out)} |")
    lines.append("")

    # ── 5. Telegram ───────────────────────────────────────────────────────────
    tg_rows = cats["telegram"]
    t_in, t_out = sum_tokens(tg_rows)
    lines.append("## 5. Telegram Sessions")
    lines.append("")
    if tg_rows:
        t_tot = t_in + t_out
        lines.append(f"*{len(tg_rows)} sessions, {fmt_tok(t_tot)} total tokens*")
        lines.append("")
        model_groups_tg = defaultdict(list)
        for r in tg_rows:
            model_groups_tg[r["model"] or "unknown"].append(r)
        lines.append("| Model | Sessions | Input | Output | Total |")
        lines.append("| --- | --- | --- | --- | --- |")
        for model, mrows in sorted(model_groups_tg.items(),
                                   key=lambda x: sum(r["input_tokens"] or 0 for r in x[1]) + sum(r["output_tokens"] or 0 for r in x[1]),
                                   reverse=True):
            cnt = len(mrows)
            inp = sum(r["input_tokens"] or 0 for r in mrows)
            out = sum(r["output_tokens"] or 0 for r in mrows)
            lines.append(f"| {model} | {cnt} | {fmt_tok(inp)} | {fmt_tok(out)} | {fmt_tok(inp+out)} |")
        lines.append("")
    else:
        lines.append("*No Telegram sessions found.*")
        lines.append("")

    # ── 6. Other ──────────────────────────────────────────────────────────────
    other_rows = cats["other"]
    if other_rows:
        o_in, o_out = sum_tokens(other_rows)
        lines.append("## 6. Other Sessions")
        lines.append("")
        lines.append(f"*{len(other_rows)} sessions, {fmt_tok(o_in+o_out)} total tokens*")
        lines.append("")

        model_groups_oth = defaultdict(list)
        for r in other_rows:
            model_groups_oth[r["model"] or "unknown"].append(r)
        lines.append("| Model | Sessions | Input | Output | Total |")
        lines.append("| --- | --- | --- | --- | --- |")
        for model, mrows in sorted(model_groups_oth.items(),
                                   key=lambda x: sum(r["input_tokens"] or 0 for r in x[1]) + sum(r["output_tokens"] or 0 for r in x[1]),
                                   reverse=True):
            cnt = len(mrows)
            inp = sum(r["input_tokens"] or 0 for r in mrows)
            out = sum(r["output_tokens"] or 0 for r in mrows)
            lines.append(f"| {model} | {cnt} | {fmt_tok(inp)} | {fmt_tok(out)} | {fmt_tok(inp+out)} |")
        lines.append("")

    # ── Grand Total ───────────────────────────────────────────────────────────
    # Categories included in grand total (not cron_noagent, not zero_token)
    category_rows = {
        "Cron LLM Jobs": cron_llm_rows,
        "Pipeline Hermes": pipeline_rows,
        "Agent CLI Parent": parent_rows,
        "Subagent Children": child_rows,
        "Human CLI": human_rows,
        "Telegram": tg_rows,
        "Other": other_rows,
    }

    grand_total_sessions = sum(len(v) for v in category_rows.values())
    grand_total_tokens = sum(
        sum(r["input_tokens"] or 0 for r in v) + sum(r["output_tokens"] or 0 for r in v)
        for v in category_rows.values()
    )

    lines.append("## Grand Total")
    lines.append("")
    lines.append(f"*{grand_total_sessions} total sessions ({excluded_count} excluded: {cron_noagent_count} cron_noagent + {zero_tok_count} zero_token)*")
    lines.append(f"*{fmt_tok(grand_total_tokens)} total tokens across all categories*")
    lines.append("")

    lines.append("| Category | Sessions | Input | Output | Total | % of Total | Bar |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    cat_order = sorted(
        category_rows.items(),
        key=lambda x: sum(r["input_tokens"] or 0 for r in x[1]) + sum(r["output_tokens"] or 0 for r in x[1]),
        reverse=True,
    )
    for cat_name, rows in cat_order:
        cnt = len(rows)
        inp = sum(r["input_tokens"] or 0 for r in rows)
        out = sum(r["output_tokens"] or 0 for r in rows)
        tot = inp + out
        pct = (tot / grand_total_tokens * 100) if grand_total_tokens > 0 else 0
        bar = ascii_bar(pct / 100)
        lines.append(f"| {cat_name} | {cnt} | {fmt_tok(inp)} | {fmt_tok(out)} | {fmt_tok(tot)} | {pct:.1f}% | {bar} |")

    lines.append(f"| **TOTAL** | **{grand_total_sessions}** | **{fmt_tok(grand_total_tokens)}** | — | — | **100%** | {ascii_bar(1.0)} |")
    lines.append("")

    # ── Visibility Gaps ───────────────────────────────────────────────────────
    lines.append("## Visibility Gaps")
    lines.append("")
    lines.append("The following token usage is **not captured** in this report:")
    lines.append("")
    lines.append("- **StratsPro_Tweet tweet gen calls** — These invoke `opencode` directly via subprocess, bypassing the Hermes session table entirely.")
    lines.append("- **News pipelines** — These also call `opencode` for tweet generation via subprocess; no Hermes session is created.")
    lines.append("- **Sports_Trend pipeline keeper** — This job is configured with `no_agent: true` (script-only). It runs `/home/ubuntu/.hermes/scripts/gbrain-postgres-export-backup.sh` and emits no LLM calls.")
    lines.append("- **All pipeline opencode subprocess calls** — Any pipeline that shells out to `opencode` or `codex` directly will have zero visibility in this database. Only Hermes-native session tracking (where the agent processes the prompt) is captured.")
    lines.append("- **Cron no_agent jobs** — `nightly-dream-cycle`, `daily-brain-backup`, and `gbrain-watchdog` run shell scripts with no LLM involvement. Their sessions appear with zero tokens and are excluded from totals.")
    lines.append("")
    lines.append("---")
    lines.append(f"*Report generated by per-job-token-usage-all-time.py at {gen_time}*")

    return "\n".join(lines)


# ─── Box-art report ────────────────────────────────────────────────────────────
def report_box(cats, child_counts, cron_job_map, hours=None):
    """Generate ASCII box-art formatted report with ┌─┬─┐ tables."""
    lines = []

    period = "ALL TIME" if hours is None else f"LAST {hours} HOURS"
    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    zero_tok_count = len(cats["zero_token"])
    cron_noagent_count = len(cats["cron_noagent"])
    excluded_count = cron_noagent_count + zero_tok_count

    # Helper: render a table row with width=100
    def b(t, width=98):
        """Center text in a box row."""
        return f"│ {t:<{width-2}s} │"

    def sep(char, widths, left="├", mid="┼", right="┤"):
        """Build a separator row with variable column widths."""
        parts = []
        for i, w in enumerate(widths):
            parts.append(char * w)
        return f"{left}{mid.join(parts)}{right}"

    def top_sep(widths):
        return sep("─", widths, "┌", "┬", "┐")

    def mid_sep(widths):
        return sep("─", widths, "├", "┼", "┤")

    def bot_sep(widths):
        return sep("─", widths, "└", "┴", "┘")

    def hdr_row(cells, widths):
        """Header row with centered cells."""
        parts = []
        for i, (cell, w) in enumerate(zip(cells, widths)):
            parts.append(f" {cell:^{w-2}s} ")
        return f"│{''.join(parts)}│"

    def data_row(cells, widths, aligns=None):
        """Data row with optional alignment (default left)."""
        if aligns is None:
            aligns = ["<"] * len(cells)
        parts = []
        for i, (cell, w, a) in enumerate(zip(cells, widths, aligns)):
            content = str(cell)
            if a == ">":
                parts.append(f" {content:>{w-2}s} ")
            elif a == "^":
                parts.append(f" {content:^{w-2}s} ")
            else:
                parts.append(f" {content:<{w-2}s} ")
        return f"│{''.join(parts)}│"

    # ── Title banner ──────────────────────────────────────────────────────────
    lines.append("┌" + "─" * 96 + "┐")
    lines.append(b("HERMES TOKEN USAGE REPORT — " + period))
    lines.append(b(f"Generated: {gen_time}"))
    lines.append(b(f"Source: ~/.hermes/state.db"))
    lines.append("└" + "─" * 96 + "┘")
    lines.append("")

    # ── 1. Cron LLM Jobs ──────────────────────────────────────────────────────
    cron_llm_rows = cats["cron_llm"]
    cron_job_groups = defaultdict(list)
    for r in cron_llm_rows:
        jid = extract_cron_job_id(r["id"])
        jname = cron_job_map.get(jid, jid or "unknown")
        cron_job_groups[jname].append(r)

    cron_job_totals = {
        name: (len(rows), sum(r["input_tokens"] or 0 for r in rows),
               sum(r["output_tokens"] or 0 for r in rows))
        for name, rows in cron_job_groups.items()
    }
    sorted_jobs = sorted(cron_job_totals.items(),
                         key=lambda x: x[1][1] + x[1][2], reverse=True)

    # Table: Job Name (38), Runs (5), Input (9), Output (7), Total (9), Source (18), Usage (12)
    col_w = [38, 5, 9, 7, 9, 18, 12]
    lines.append("┌" + "─" * 96 + "┐")
    lines.append(b("SECTION 1: CRON LLM JOBS  │  " + str(len(cron_llm_rows)) + f" sessions across {len(sorted_jobs)} jobs"))
    lines.append("├" + "─" * 96 + "┤")
    lines.append(hdr_row(["Job Name", "Runs", "Input", "Output", "Total", "Source", "Usage %"], col_w))
    lines.append(mid_sep(col_w))
    for name, (cnt, inp, out) in sorted_jobs:
        tot = inp + out
        # Estimate job-level percentage of total cron LLM
        all_cron = sum(inp2+out2 for _, (_, inp2, out2) in sorted_jobs)
        pct = (tot / all_cron * 100) if all_cron > 0 else 0
        bar = ascii_bar(pct / 100, width=10)
        lines.append(data_row([name, str(cnt), fmt_tok(inp), fmt_tok(out), fmt_tok(tot),
                               "cron_llm", f"{pct:.1f}% {bar}"], col_w,
                              aligns=["<", ">", ">", ">", ">", "<", "<"]))
    lines.append(bot_sep(col_w))
    lines.append("")

    # Per-job model breakdown
    for name in [x[0] for x in sorted_jobs]:
        rows = cron_job_groups[name]
        model_groups = defaultdict(list)
        for r in rows:
            model_groups[r["model"]].append(r)

        all_job_tok = sum(r["input_tokens"] or 0 for r in rows) + sum(r["output_tokens"] or 0 for r in rows)
        lines.append("┌" + "─" * 96 + "┐")
        lines.append(b(f"{name} — {fmt_tok(all_job_tok)} total  [{len(rows)} runs]"))
        lines.append("├" + "─" * 96 + "┤")
        # Sub-table with fewer columns
        sub_w = [56, 8, 12, 10, 12]
        lines.append(hdr_row(["Model", "Runs", "Input", "Output", "Total"], sub_w))
        lines.append(mid_sep(sub_w))
        sorted_models = sorted(model_groups.items(),
                               key=lambda x: sum(r["input_tokens"] or 0 for r in x[1]) + sum(r["output_tokens"] or 0 for r in x[1]),
                               reverse=True)
        for model, mrows in sorted_models:
            cnt = len(mrows)
            inp = sum(r["input_tokens"] or 0 for r in mrows)
            out = sum(r["output_tokens"] or 0 for r in mrows)
            lines.append(data_row([model, str(cnt), fmt_tok(inp), fmt_tok(out), fmt_tok(inp+out)], sub_w,
                                  aligns=["<", ">", ">", ">", ">"]))
        lines.append(bot_sep(sub_w))
        lines.append("")

    # ── 2. Pipeline Hermes Calls ──────────────────────────────────────────────
    pipeline_rows = cats["pipeline_hermes"]
    pipeline_groups = defaultdict(list)
    for r in pipeline_rows:
        key = (r["billing_provider"], r["model"])
        pipeline_groups[key].append(r)

    sorted_pipelines = sorted(
        pipeline_groups.items(),
        key=lambda x: sum(r["input_tokens"] or 0 for r in x[1]),
        reverse=True
    )

    lines.append("┌" + "─" * 96 + "┐")
    lines.append(b(f"SECTION 2: PIPELINE HERMES CALLS  │  {len(pipeline_rows)} sessions"))
    lines.append("├" + "─" * 96 + "┤")
    pw = [16, 24, 6, 10, 8, 10, 24]
    lines.append(hdr_row(["Provider", "Model", "Calls", "Input", "Output", "Total", "Source Classification"], pw))
    lines.append(mid_sep(pw))
    for (prov, model), mrows in sorted_pipelines:
        cnt = len(mrows)
        inp = sum(r["input_tokens"] or 0 for r in mrows)
        out = sum(r["output_tokens"] or 0 for r in mrows)
        src = classify_pipeline_source(prov, model)
        lines.append(data_row([prov or "—", model, str(cnt), fmt_tok(inp), fmt_tok(out), fmt_tok(inp+out), src], pw,
                              aligns=["<", "<", ">", ">", ">", ">", "<"]))
    lines.append(bot_sep(pw))
    lines.append("")

    # ── 3. Agent CLI + Subagent Children ──────────────────────────────────────
    parent_rows = cats["agent_cli_parent"]
    child_rows = cats["subagent_child"]

    # Build a comprehensive lookup: session ID → model for ALL sessions
    all_session_models = {}
    for cat_list in cats.values():
        for r in cat_list:
            if r["id"]:
                all_session_models[r["id"]] = r["model"] or "unknown"

    model_summary = defaultdict(lambda: {"parents": 0, "children": 0, "parent_in": 0, "parent_out": 0, "child_in": 0, "child_out": 0})
    for r in parent_rows:
        model = r["model"] or "unknown"
        model_summary[model]["parents"] += 1
        model_summary[model]["parent_in"] += r["input_tokens"] or 0
        model_summary[model]["parent_out"] += r["output_tokens"] or 0

    parent_child_map = defaultdict(list)
    for r in child_rows:
        parent_child_map[r["parent_session_id"]].append(r)

    for pid, children in parent_child_map.items():
        parent_model = all_session_models.get(pid, "unknown")
        c_in = sum(c["input_tokens"] or 0 for c in children)
        c_out = sum(c["output_tokens"] or 0 for c in children)
        model_summary[parent_model]["children"] += len(children)
        model_summary[parent_model]["child_in"] += c_in
        model_summary[parent_model]["child_out"] += c_out

    total_parent_sessions = sum(m["parents"] for m in model_summary.values())
    total_child_sessions = sum(m["children"] for m in model_summary.values())

    lines.append("┌" + "─" * 96 + "┐")
    lines.append(b(f"SECTION 3: AGENT CLI + SUBAGENT CHILDREN  │  {total_parent_sessions} parents, {total_child_sessions} children"))
    lines.append("├" + "─" * 96 + "┤")
    aw = [26, 8, 8, 10, 10, 10, 10, 14]
    lines.append(hdr_row(["Model", "Parents", "Children", "Par In", "Par Out", "Ch In", "Ch Out", "Total"], aw))
    lines.append(mid_sep(aw))
    for model, m in sorted(model_summary.items(),
                           key=lambda x: x[1]["parent_in"]+x[1]["parent_out"]+x[1]["child_in"]+x[1]["child_out"],
                           reverse=True):
        p_in = m["parent_in"]
        p_out = m["parent_out"]
        c_in = m["child_in"]
        c_out = m["child_out"]
        total = p_in + p_out + c_in + c_out
        lines.append(data_row([model, str(m['parents']), str(m['children']),
                               fmt_tok(p_in), fmt_tok(p_out), fmt_tok(c_in), fmt_tok(c_out), fmt_tok(total)], aw,
                              aligns=["<", ">", ">", ">", ">", ">", ">", ">"]))
    lines.append(bot_sep(aw))
    lines.append("")

    # Top 25
    parent_totals = []
    for r in parent_rows:
        pid = r["id"]
        children = parent_child_map.get(pid, [])
        p_tok = (r["input_tokens"] or 0) + (r["output_tokens"] or 0)
        c_in = sum(c["input_tokens"] or 0 for c in children)
        c_out = sum(c["output_tokens"] or 0 for c in children)
        c_tok = c_in + c_out
        total = p_tok + c_tok
        parent_totals.append((pid, r["model"] or "unknown", p_tok, c_tok, len(children), total))

    parent_totals.sort(key=lambda x: x[5], reverse=True)

    lines.append("┌" + "─" * 96 + "┐")
    lines.append(b("TOP 25 PARENT SESSIONS BY TOTAL TOKENS"))
    lines.append("├" + "─" * 96 + "┤")
    tw = [22, 24, 12, 14, 10, 14]
    lines.append(hdr_row(["Session ID (last 20)", "Model", "Par Tok", "Ch Tok", "# Ch", "Total"], tw))
    lines.append(mid_sep(tw))
    for pid, model, p_tok, c_tok, n_child, total in parent_totals[:25]:
        sid_short = pid[-20:]
        lines.append(data_row([sid_short, model, fmt_tok(p_tok), fmt_tok(c_tok), str(n_child), fmt_tok(total)], tw,
                              aligns=["<", "<", ">", ">", ">", ">"]))
    lines.append(bot_sep(tw))
    lines.append("")

    # ── 4. Human CLI ──────────────────────────────────────────────────────────
    human_rows = cats["human_cli"]
    h_in, h_out = sum_tokens(human_rows)
    model_groups_h = defaultdict(list)
    for r in human_rows:
        model_groups_h[r["model"] or "unknown"].append(r)

    lines.append("┌" + "─" * 96 + "┐")
    lines.append(b(f"SECTION 4: HUMAN CLI SESSIONS  │  {len(human_rows)} sessions, {fmt_tok(h_in+h_out)} total"))
    lines.append("├" + "─" * 96 + "┤")
    hm = [42, 10, 12, 10, 12, 10]
    lines.append(hdr_row(["Model", "Sessions", "Input", "Output", "Total", "%"], hm))
    lines.append(mid_sep(hm))
    all_human_tok = h_in + h_out
    sorted_hm = sorted(model_groups_h.items(),
                       key=lambda x: sum(r["input_tokens"] or 0 for r in x[1]) + sum(r["output_tokens"] or 0 for r in x[1]),
                       reverse=True)
    for model, mrows in sorted_hm:
        cnt = len(mrows)
        inp = sum(r["input_tokens"] or 0 for r in mrows)
        out = sum(r["output_tokens"] or 0 for r in mrows)
        tot = inp + out
        pct = (tot / all_human_tok * 100) if all_human_tok > 0 else 0
        lines.append(data_row([model, str(cnt), fmt_tok(inp), fmt_tok(out), fmt_tok(tot), f"{pct:.1f}%"], hm,
                              aligns=["<", ">", ">", ">", ">", ">"]))
    lines.append(bot_sep(hm))
    lines.append("")

    # ── 5. Telegram ───────────────────────────────────────────────────────────
    tg_rows = cats["telegram"]
    if tg_rows:
        t_in, t_out = sum_tokens(tg_rows)
        model_groups_tg = defaultdict(list)
        for r in tg_rows:
            model_groups_tg[r["model"] or "unknown"].append(r)
        lines.append("┌" + "─" * 96 + "┐")
        lines.append(b(f"SECTION 5: TELEGRAM SESSIONS  │  {len(tg_rows)} sessions, {fmt_tok(t_in+t_out)} total"))
        lines.append("├" + "─" * 96 + "┤")
        tm = [42, 10, 12, 10, 12, 10]
        lines.append(hdr_row(["Model", "Sessions", "Input", "Output", "Total", "%"], tm))
        lines.append(mid_sep(tm))
        all_tg_tok = t_in + t_out
        sorted_tg = sorted(model_groups_tg.items(),
                           key=lambda x: sum(r["input_tokens"] or 0 for r in x[1]) + sum(r["output_tokens"] or 0 for r in x[1]),
                           reverse=True)
        for model, mrows in sorted_tg:
            cnt = len(mrows)
            inp = sum(r["input_tokens"] or 0 for r in mrows)
            out = sum(r["output_tokens"] or 0 for r in mrows)
            tot = inp + out
            pct = (tot / all_tg_tok * 100) if all_tg_tok > 0 else 0
            lines.append(data_row([model, str(cnt), fmt_tok(inp), fmt_tok(out), fmt_tok(tot), f"{pct:.1f}%"], tm,
                                  aligns=["<", ">", ">", ">", ">", ">"]))
        lines.append(bot_sep(tm))
        lines.append("")

    # ── 6. Other ──────────────────────────────────────────────────────────────
    other_rows = cats["other"]
    if other_rows:
        o_in, o_out = sum_tokens(other_rows)
        model_groups_oth = defaultdict(list)
        for r in other_rows:
            model_groups_oth[r["model"] or "unknown"].append(r)
        lines.append("┌" + "─" * 96 + "┐")
        lines.append(b(f"SECTION 6: OTHER SESSIONS  │  {len(other_rows)} sessions, {fmt_tok(o_in+o_out)} total"))
        lines.append("├" + "─" * 96 + "┤")
        om = [42, 10, 12, 10, 12, 10]
        lines.append(hdr_row(["Model", "Sessions", "Input", "Output", "Total", "%"], om))
        lines.append(mid_sep(om))
        all_oth_tok = o_in + o_out
        sorted_oth = sorted(model_groups_oth.items(),
                            key=lambda x: sum(r["input_tokens"] or 0 for r in x[1]) + sum(r["output_tokens"] or 0 for r in x[1]),
                            reverse=True)
        for model, mrows in sorted_oth:
            cnt = len(mrows)
            inp = sum(r["input_tokens"] or 0 for r in mrows)
            out = sum(r["output_tokens"] or 0 for r in mrows)
            tot = inp + out
            pct = (tot / all_oth_tok * 100) if all_oth_tok > 0 else 0
            lines.append(data_row([model, str(cnt), fmt_tok(inp), fmt_tok(out), fmt_tok(tot), f"{pct:.1f}%"], om,
                                  aligns=["<", ">", ">", ">", ">", ">"]))
        lines.append(bot_sep(om))
        lines.append("")

    # ── Grand Total ───────────────────────────────────────────────────────────
    category_rows = {
        "Cron LLM Jobs": cron_llm_rows,
        "Pipeline Hermes": pipeline_rows,
        "Agent CLI Parent": parent_rows,
        "Subagent Children": child_rows,
        "Human CLI": human_rows,
        "Telegram": tg_rows,
        "Other": other_rows,
    }

    grand_total_sessions = sum(len(v) for v in category_rows.values())
    grand_total_tokens = sum(
        sum(r["input_tokens"] or 0 for r in v) + sum(r["output_tokens"] or 0 for r in v)
        for v in category_rows.values()
    )

    lines.append("┌" + "─" * 96 + "┐")
    lines.append(b(f"GRAND TOTAL  │  {grand_total_sessions} sessions  │  {fmt_tok(grand_total_tokens)} tokens  │  ({excluded_count} excluded)"))
    lines.append("├" + "─" * 96 + "┤")
    gw = [22, 10, 12, 10, 12, 8, 22]
    lines.append(hdr_row(["Category", "Sessions", "Input", "Output", "Total", "%", "Bar"], gw))
    lines.append(mid_sep(gw))
    cat_order = sorted(
        category_rows.items(),
        key=lambda x: sum(r["input_tokens"] or 0 for r in x[1]) + sum(r["output_tokens"] or 0 for r in x[1]),
        reverse=True,
    )
    for cat_name, rows in cat_order:
        cnt = len(rows)
        inp = sum(r["input_tokens"] or 0 for r in rows)
        out = sum(r["output_tokens"] or 0 for r in rows)
        tot = inp + out
        pct = (tot / grand_total_tokens * 100) if grand_total_tokens > 0 else 0
        bar = ascii_bar(pct / 100, width=20)
        lines.append(data_row([cat_name, str(cnt), fmt_tok(inp), fmt_tok(out), fmt_tok(tot), f"{pct:.1f}%", bar], gw,
                              aligns=["<", ">", ">", ">", ">", ">", "<"]))
    lines.append(mid_sep(gw))
    lines.append(data_row(["TOTAL", str(grand_total_sessions), fmt_tok(grand_total_tokens), "—", "—", "100%", ascii_bar(1.0, width=20)], gw,
                          aligns=["<", ">", ">", ">", ">", ">", "<"]))
    lines.append(bot_sep(gw))
    lines.append("")

    # ── Visibility Gaps ───────────────────────────────────────────────────────
    lines.append("┌" + "─" * 96 + "┐")
    lines.append(b("VISIBILITY GAPS"))
    lines.append("├" + "─" * 96 + "┤")
    gaps = [
        "StratsPro_Tweet tweet gen calls — invoke opencode directly via subprocess,",
        "  bypassing the Hermes session table entirely.",
        "",
        "News pipelines — call opencode for tweet generation via subprocess;",
        "  no Hermes session is created.",
        "",
        "Sports_Trend pipeline keeper — no_agent: true (script-only).",
        "  No LLM calls captured.",
        "",
        "All pipeline opencode subprocess calls — any pipeline that shells out",
        "  to opencode or codex directly has zero visibility in this database.",
        "  Only Hermes-native session tracking is captured.",
        "",
        "Cron no_agent jobs (nightly-dream-cycle, daily-brain-backup, gbrain-watchdog)",
        "  run shell scripts with no LLM involvement. Excluded from totals.",
    ]
    for g in gaps:
        lines.append(b(g))
    lines.append("└" + "─" * 96 + "┘")
    lines.append("")
    lines.append(f"  Report generated by per-job-token-usage-all-time.py at {gen_time}")

    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Hermes token usage analysis by category.")
    parser.add_argument("--all-time", action="store_true", default=True,
                        help="Analyze all sessions (default)")
    parser.add_argument("--hours", type=int, default=None,
                        help="Analyze last N hours instead of all time")
    parser.add_argument("--format", choices=["plain", "box"], default="plain",
                        help="Output format: plain (markdown) or box (ASCII box art)")
    parser.add_argument("--output", type=str, default=None,
                        help="Write output to file instead of stdout")
    args = parser.parse_args()

    # Load data
    cron_job_map = load_cron_jobs()
    rows = query_sessions(STATE_DB, hours=args.hours)
    cats, child_counts = categorize_sessions(rows, cron_job_map)

    # Generate report
    if args.format == "box":
        report = report_box(cats, child_counts, cron_job_map, args.hours)
    else:
        report = report_plain(cats, child_counts, cron_job_map, args.hours)

    # Output
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            f.write(report)
            f.write("\n")
        print(f"Report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
