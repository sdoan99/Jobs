#!/bin/bash
# generate-plans-tables.sh
# Generates plans-tables.md — a reference of all plan files across repos.
#
# OUTPUT FORMAT:
#   Code-block tables with 4 fixed-width columns:
#     Directory=40, File=52, Progress=10, Summary=48  (total 162 chars incl. pipes)
#   Unicode-safe: formatted via Python str.ljust (not bash printf %-Ns which
#   counts bytes not chars — multi-byte chars like em dash misalign columns).
#   All cell values must be ASCII-only to guarantee perfect pipe alignment.
#   When adding new columns, adjust the COL_WN variables and header list below.
OUTPUT="/home/ubuntu/Jobs/plans/plans-tables.md"

fmt_name() {
  local base
  base=$(basename "$1")
  base=$(echo "$base" | sed 's/^[0-9_-]*//' | sed 's/\.md$//' | sed 's/\.sh$//')
  echo "$base"
}

summary_of() {
  local f=$1
  local line
  line=$(grep -v '^[[:space:]]*$' "$f" | head -2 | tail -1)
  line=$(echo "$line" | sed 's/^#* *//' | sed 's/^\*\*//' | sed 's/\*\*$//' | sed 's/^Status: //')
  if [ -z "$line" ]; then
    echo "-"
  else
    echo "$line"
  fi
}

calc_progress() {
  local f=$1 total completed
  [ -r "$f" ] || { echo "-"; return; }
  total=$(grep -c '\- \[' "$f" 2>/dev/null)
  completed=$(grep -c '\- \[x\]' "$f" 2>/dev/null)
  total=${total:-0}; completed=${completed:-0}
  if [ "$total" -eq 0 ] 2>/dev/null; then echo "-"; return; fi
  echo "$(( completed * 100 / total ))%"
}

collect_rows() {
  local dir label f name summary progress
  dir=$1
  label=$2
  if [ ! -d "$dir" ]; then return; fi
  for f in "$dir"/*; do
    [ -f "$f" ] || continue
    case "$(basename "$f")" in
      SKILL.md|plans-reference.md|plans-tables.md|generate-plans-ref.sh|generate-plans-tables.sh)
        continue ;;
    esac
    name=$(fmt_name "$f")
    summary=$(summary_of "$f")
    progress=$(calc_progress "$f")
    # sanitize em dashes — multi-byte chars misalign columns in terminals
    name=$(echo "$name" | sed 's/—/-/g')
    summary=$(echo "$summary" | sed 's/—/-/g')
    progress=$(echo "$progress" | sed 's/—/-/g')
    printf "%s\t%s\t%s\t%s\n" "$label" "$name" "$progress" "$summary"
  done
}

# Fixed column widths (Dir, File, Progress, Summary)
COL_W1=40
COL_W2=52
COL_W3=10
COL_W4=48

ascii_table() {
  local group_title="$1" tmp="$2"
  if [ ! -s "$tmp" ]; then return; fi

  echo "" >> "$OUTPUT"
  echo "### $group_title" >> "$OUTPUT"
  echo '' >> "$OUTPUT"
  echo "\`\`\`" >> "$OUTPUT"

  python3 -c "
import sys, textwrap

col_w = [$COL_W1, $COL_W2, $COL_W3, $COL_W4]
headers = ['Directory', 'File', 'Progress', 'Summary']

parts = []
for cw in col_w:
    parts.append('-' * (cw + 2))
sep = '|' + '|'.join(parts) + '|'

hdr = '| ' + ' | '.join(h.ljust(cw) for h, cw in zip(headers, col_w)) + ' |'
print(hdr)
print(sep)

with open(sys.argv[1]) as fh:
    for line in fh:
        line = line.rstrip('\n')
        if not line:
            continue
        fields = line.split('\t')
        while len(fields) < 4:
            fields.append('')
        a, b, d, c = fields[0], fields[1], fields[2], fields[3]

        aw = textwrap.wrap(a, col_w[0], break_long_words=False, break_on_hyphens=True) or [a]
        bw = textwrap.wrap(b, col_w[1], break_long_words=False, break_on_hyphens=True) or [b]
        dw = textwrap.wrap(d, col_w[2], break_long_words=False, break_on_hyphens=True) or [d]
        cw_text = textwrap.wrap(c, col_w[3], break_long_words=False, break_on_hyphens=True) or [c]

        aw = [l[:col_w[0]] for l in aw]
        bw = [l[:col_w[1]] for l in bw]
        dw = [l[:col_w[2]] for l in dw]
        cw_text = [l[:col_w[3]] for l in cw_text]

        max_lines = max(len(aw), len(bw), len(dw), len(cw_text))
        for i in range(max_lines):
            ca = (aw[i] if i < len(aw) else '')
            cb = (bw[i] if i < len(bw) else '')
            cd = (dw[i] if i < len(dw) else '')
            cc = (cw_text[i] if i < len(cw_text) else '')
            print('| ' + ' | '.join(v.ljust(cw) for v, cw in zip([ca, cb, cd, cc], col_w)) + ' |')
" "$tmp" >> "$OUTPUT"

  echo "\`\`\`" >> "$OUTPUT"
}

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

{
  echo "# Plan Files Reference"
  echo ""
  echo "Generated $(date '+%Y-%m-%d %H:%M')"
  echo ""
} > "$OUTPUT"

# ── TABLE ORDER ──
# Sections are ordered by dependency: foundational schemas first, then plans that
# depend on them, then standalone repos. Based on analysis of plan-file cross-refs:
#   Schema (Jobs) ──→ Dataserver ──→ Documentation ──→ Project92
# The remaining sections (Hermes, HermesAgent, GitNexus, Brain, gstack) have no
# cross-section dependencies and are grouped afterward.

# ── Group 1: Jobs / Schema Plans (foundational — schema referenced by other sections) ──
tmp1="$TMPDIR/g1"
collect_rows "/home/ubuntu/Jobs/plans" "~/Jobs/plans" >> "$tmp1"
ascii_table "Jobs / Schema Plans" "$tmp1"

# ── Group 2: Dataserver Plans (depends on schema; standalone beyond that) ──
tmp2="$TMPDIR/g2"
collect_rows "/home/ubuntu/dataserver/plans" "~/dataserver/plans" >> "$tmp2"
collect_rows "/home/ubuntu/dataserver/plans/completed" "~/dataserver/plans/completed" >> "$tmp2"
ascii_table "Dataserver Plans" "$tmp2"

# ── Group 3: Documentation Plans (prerequisite for Project92 Schwab integration) ──
tmp3="$TMPDIR/g3"
collect_rows "/home/ubuntu/documentation/plans" "~/documentation/plans" >> "$tmp3"
collect_rows "/home/ubuntu/documentation/plans/completed" "~/documentation/plans/completed" >> "$tmp3"
ascii_table "Documentation Plans" "$tmp3"

# ── Group 4: Project92 Plans (depends on Documentation OHLC prerequisite + Schema) ──
tmp4="$TMPDIR/g4"
collect_rows "/home/ubuntu/project92/plans" "~/project92/plans" >> "$tmp4"
collect_rows "/home/ubuntu/project92/plans/completed" "~/project92/plans/completed" >> "$tmp4"
ascii_table "Project92 Plans" "$tmp4"

# ── STANDALONE SECTIONS (no cross-section dependencies) ──

# ── Group 5: Hermes Plans ──
tmp5="$TMPDIR/g5"
for dir in /home/ubuntu/.hermes/plans /home/ubuntu/project92/.hermes/plans /home/ubuntu/DiscordAlertsTrader/.hermes/plans; do
  label=$(echo "$dir" | sed "s|/home/ubuntu/|~/|")
  collect_rows "$dir" "$label" >> "$tmp5"
done
ascii_table "Hermes Plans" "$tmp5"

# ── Group 6: Hermes Agent Plans (standalone) ──
tmp6="$TMPDIR/g6"
for dir in /home/ubuntu/.hermes/hermes-agent/docs/plans /home/ubuntu/.hermes/hermes-agent/plans; do
  label=$(echo "$dir" | sed "s|/home/ubuntu/|~/|")
  collect_rows "$dir" "$label" >> "$tmp6"
done
ascii_table "Hermes Agent Plans" "$tmp6"

# ── Group 7: GitNexus Plans (standalone) ──
tmp7="$TMPDIR/g7"
for dir in /home/ubuntu/GitNexus/docs/plans /home/ubuntu/GitNexus/docs/superpowers/plans; do
  label=$(echo "$dir" | sed "s|/home/ubuntu/|~/|")
  collect_rows "$dir" "$label" >> "$tmp7"
done
ascii_table "GitNexus Plans" "$tmp7"

# ── Group 8: Brain / Docs Index Plans (standalone indexes) ──
tmp8="$TMPDIR/g8"
for dir in /home/ubuntu/brain/docs/project92/plans /home/ubuntu/brain/docs/discord-alerts-trader/plans /home/ubuntu/brain/docs/adapter/plans /home/ubuntu/brain/docs/dataserver/plans /home/ubuntu/brain/docs/backend/plans; do
  label=$(echo "$dir" | sed "s|/home/ubuntu/|~/|")
  collect_rows "$dir" "$label" >> "$tmp8"
done
ascii_table "Brain / Docs Index Plans" "$tmp8"

# ── Group 9: gstack Fixtures (standalone) ──
tmp9="$TMPDIR/g9"
collect_rows "/home/ubuntu/gstack/test/fixtures/plans" "~/gstack/test/fixtures/plans" >> "$tmp9"
ascii_table "gstack Test Fixtures" "$tmp9"

echo "" >> "$OUTPUT"
echo "---" >> "$OUTPUT"
echo "_Excludes SKILL.md, generated reference files, and utility scripts._" >> "$OUTPUT"
