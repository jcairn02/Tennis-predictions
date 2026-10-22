#!/usr/bin/env bash
# The package steps of 16 Oct 2026 (docs/studies/men_lower_level_fill/process_log.md, § 3, steps 1-3), after the
# candidate's build and checks (build_candidate.sh): the weekly feed's identity rule screen on the candidate's samples
# (src/eda/data_gaps_2026/feed.py's auto_verdicts and screen, written as identity_verdicts.csv, by = rule) and READY;
# the derive to the men's scope, results only; its checks and READY; then the coverage condition for added matches and
# the near-pair listing (src/eda/men_lower_level_fill/conditions_new.py).
# Usage, from the repository root: bash data/studies/men_lower_level_fill/package_steps.sh
set -u
REPO=/c/Users/zerom/Documents/Tennis-predictions
cd "$REPO" || exit 1
B=src/eda/lower_level_evidence/candidate_stage0.py; P=C:/Users/zerom/tnr_mlf/candidates; L=MLF20261016; K=${L}_pkg
OUT=data/studies/men_lower_level_fill; S="--status-log $OUT/status.log"
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
echo "$(stamp) identity screen $L"
./python.sh - "$P/$L" > "$OUT/screen_$L.log" 2>&1 <<'EOF' || { echo "$(stamp) screen failed"; exit 1; }
import json
import sys
from pathlib import Path
sys.path.insert(0, ".")
from src.eda.data_gaps_2026 import feed as F
cand = Path(sys.argv[1])
v = F.auto_verdicts(cand)
sc = F.screen(v)
print(json.dumps({"verdicts": v.groupby(["kind", "source", "verdict"]).size().rename("n").reset_index()
                  .to_dict("records"), **sc}, indent=1))
v.to_csv(cand / ("identity_verdicts.csv" if sc["pass"] else "identity_verdicts_rule_failed.csv"), index=False)
sys.exit(0 if sc["pass"] else 4)
EOF
echo "$(stamp) ready $L"
./python.sh $B --label $L --out $P/$L --ready $S > "$OUT/ready_$L.log" 2>&1 || { echo "$(stamp) ready failed"; exit 1; }
echo "$(stamp) derive $K"
./python.sh $B --label $K --out $P/$K --derive-from $P/$L --keep-tours atp \
  --keep-since atp:CH:2010-01-01:2025-12-31,atp:CHQ:2010-01-01:2025-12-31,atp:ITF:2010-01-01:2026-05-31 \
  --results-only atp:CH,atp:CHQ,atp:ITF $S > "$OUT/derive_$K.log" 2>&1 || { echo "$(stamp) derive failed"; exit 1; }
echo "$(stamp) checks $K"
./python.sh $B --label $K --out $P/$K --checks $S > "$OUT/checks_$K.log" 2>&1 || { echo "$(stamp) checks failed"; exit 1; }
echo "$(stamp) ready $K"
./python.sh $B --label $K --out $P/$K --ready $S > "$OUT/ready_$K.log" 2>&1 || { echo "$(stamp) ready (derived) failed"; exit 1; }
echo "$(stamp) conditions $K"
./python.sh src/eda/men_lower_level_fill/conditions_new.py --candidate $P/$K --out $OUT/package > "$OUT/conditions_new.log" 2>&1
echo "$(stamp) conditions exit $?"
echo "$(stamp) DONE"
