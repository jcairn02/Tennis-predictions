#!/usr/bin/env bash
# The rebuild of 16 Oct 2026 and its switch (docs/studies/men_lower_level_fill/process_log.md, § 3, steps 5-7, and
# § 3a): the template on the day's tables with every accepted package and the feed (the men's lower-level fill among
# them), by the steps of the rebuild of 13-14 Oct (data/studies/data_gaps_2026/build_final.sh and switch_final.sh), in
# one detached script so a session's end cannot stop it and no two GPU jobs of it overlap (the 14 Oct deadlock):
#   0  the replay's view of Tennis My Life's dump, frozen at the start of the Stage 0 rebuild that wrote today's tables
#   1  build_template.sh's accepted route; post_build.sh; fits seeds 0-3 for 2019-2026
#   2  the harm check against template_2026-10-14 (its rule fixed before any build); then compare.py against the frozen
#      reference for the input check (not a gate)
#   3  harm by the rule: stop, no switch (the owner decides). No harm: fits seeds 4-15 for 2026 (the template check)
#   4  the switch, only if accepted.json is unchanged since the build (else a replay would merge other packages):
#      use_instance (its template check), checkpoint 2026-06-22, the replay check with the frozen dump view,
#      replay-compare, the live checkpoint 2026-09-21. A failed replay or compare puts the previous selection back.
#   5  the other seasons' seeds 4-15 (16-seed evaluations only)
# Usage, from the repository root: bash data/studies/men_lower_level_fill/build_template.sh [<sandbox> [<out folder>]]
set -u
REPO=/c/Users/zerom/Documents/Tennis-predictions
SB="${1:-C:/Users/zerom/tnr_tpl1016}"
OUT="${2:-data/studies/current_best_model/template_2026-10-16}"
INST=$(basename "$OUT")
FREEZE_AT=2026-10-14T21:19:58Z   # data/studies/data_continuity/rebuilds/2026-10-14T2119Z: the Stage 0 the build copies
FREEZE_DIR=C:/Users/zerom/tnr_dump_freeze_1016
WORK=C:/Users/zerom/tnr_daily_mlf
S=data/studies/men_lower_level_fill
SEL=data/studies/master_pipeline/selected_instance.json
ACC=data/studies/current_best_model/accepted_additions/accepted.json
cd "$REPO" || exit 1
mkdir -p "$OUT"
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
export RUN_CHAIN_SKIP_DIRS=daily_prediction     # the daily engine's TabPFN caches: no chain step reads them
export SURFACE_IOS_WORKERS="${SURFACE_IOS_WORKERS:-6}"
FITS="./python_tabpfn_local.sh src/eda/model_rebuild/fits.py --out $OUT"
# the list the build merged: written once, at the first start (a resumed run keeps it: resume_build.sh)
[ -f "$OUT/accepted_at_build.json" ] || cp "$ACC" "$OUT/accepted_at_build.json"
ACC_AT_BUILD=$(sha256sum "$OUT/accepted_at_build.json" | cut -d' ' -f1)

if [ ! -f "$FREEZE_DIR/freeze_dump.json" ]; then
  echo "$(stamp) dump view frozen at $FREEZE_AT into $FREEZE_DIR"
  ./python.sh -c "
import sys; sys.path.insert(0, '.')
from pathlib import Path
import pandas as pd
from src.eda.level_layer_adoption import freeze_dump as F
F.FREEZE = pd.Timestamp('$FREEZE_AT'); F.OUT = Path('$FREEZE_DIR')
sys.exit(F.main())
" > "$S/freeze_dump.log" 2>&1 || { echo "$(stamp) dump view failed"; exit 1; }
fi
if [ "${SKIP_BUILD:-0}" = "1" ]; then
  echo "$(stamp) build: done by resume_build.sh"
else
  echo "$(stamp) build (accepted route) in $SB"
  bash data/studies/level_layer_adoption/build_template.sh "$SB" "$OUT" 1 accepted > "$OUT/build.out" 2>&1 || { echo "$(stamp) build failed"; exit 1; }
fi
echo "$(stamp) post-build"
bash data/studies/level_layer_adoption/post_build.sh "$OUT" > "$OUT/post_build.out" 2>&1 || { echo "$(stamp) post-build failed"; exit 1; }
echo "$(stamp) fits: seeds 0-3, 2019-2026"
$FITS --seeds 0-3 --seasons 2019-2026 > "$OUT/fits.log" 2>&1 || { echo "$(stamp) fits failed"; exit 1; }
echo "$(stamp) harm check against template_2026-10-14"
./python.sh src/eda/men_lower_level_fill/harm.py --new "$OUT" > "$S/harm.out" 2>&1 || { echo "$(stamp) harm check failed to run"; exit 1; }
echo "$(stamp) compare.py against the frozen reference (the input check; not a gate)"
./python.sh src/eda/current_best_model/compare.py --candidate "$OUT" --out "$OUT/vs_reference_2026-10-08" > "$OUT/vs_reference.out" 2>&1 \
  || echo "$(stamp) compare.py failed (not a gate)"
HARM=$(./python.sh -c "import json; print(json.load(open('$S/harm/new_vs_on.json'))['harm'])")
if [ "$HARM" != "False" ]; then echo "$(stamp) HARM BY THE RULE ($HARM): no switch; the owner decides"; exit 0; fi
echo "$(stamp) no harm by the rule"
echo "$(stamp) fits: seeds 4-15, 2026"
$FITS --seeds 4-15 --seasons 2026 > "$OUT/fits_seeds4-15_2026.log" 2>&1 || { echo "$(stamp) fits failed"; exit 1; }
echo "$(stamp) READY FOR THE SWITCH"

switch() {
  if [ "$(sha256sum "$ACC" | cut -d' ' -f1)" != "$ACC_AT_BUILD" ]; then
    echo "$(stamp) accepted.json changed since the build: NO SWITCH (a replay would merge other packages)"; return 1
  fi
  cp "$SEL" "$S/selected_instance_before.json"
  ./python.sh -c "
import sys; sys.path.insert(0, '.')
import src.pipeline as tp
tp.use_instance('$INST', tree='$SB')
" > "$S/switch.log" 2>&1 || { echo "$(stamp) use_instance refused (its template check): NO SWITCH"; return 1; }
  echo "$(stamp) selected $INST; checkpoint 2026-06-22"
  ./python.sh -c "
import sys; sys.path.insert(0, '.')
import src.pipeline as tp
sys.exit(0 if tp.make_checkpoint('2026-06-22', tree='$SB').ok else 1)
" >> "$S/switch.log" 2>&1 || { echo "$(stamp) checkpoint failed"; return 2; }
  # a Windows path (C:/...): Git Bash converts /c/... in a native program's arguments, but not inside the python -c
  # code below, where Windows Python cannot open it (16 Oct 2026: the guard's FileNotFoundError reverted a switch whose
  # replay had passed; process log, 17:58)
  RUN="$(cygpath -m "$REPO")/data/studies/daily_prediction/runs/replay_2026-07-13_R16_$(date +%Y%m%dT%H%M%S)"
  echo "$(stamp) replay check into $RUN"
  DP_BASE_TREE="$SB" DP_INSTANCE="$INST" DP_WORK_TREE="$WORK" DP_FREEZE_DUMP="$FREEZE_DIR" \
    ./python.sh src/eda/daily_prediction/dp.py run_day --run "$RUN" --replay-week 2026-07-13 --replay-round R16 \
    --checkpoint 2026-06-22 >> "$S/switch.log" 2>&1 || { echo "$(stamp) replay failed"; return 2; }
  DP_BASE_TREE="$SB" DP_INSTANCE="$INST" DP_WORK_TREE="$WORK" DP_FREEZE_DUMP="$FREEZE_DIR" \
    ./python.sh src/eda/daily_prediction/dp.py replay-compare --run "$RUN" >> "$S/switch.log" 2>&1 \
    || { echo "$(stamp) replay-compare failed"; return 2; }
  # replay-compare always exits 0: its reading decides (14 Oct's switch read 4.5e-6 at most, the IOS inputs exact; the
  # owner's 1e-6 for the IOS inputs; every replayed match in the frame)
  ./python.sh -c "
import json, sys
r = json.load(open(r'$RUN/replay_compare.json'))
ok = (not r['missing_from_frame'] and r['ios_nan_pattern_equal'] and r['ios_max_abs_diff'] <= 1e-6
      and r['max_abs_diff'] <= 1e-4 and r['matches'] > 0)
print({k: r[k] for k in ('matches', 'inputs_bitwise', 'max_abs_diff', 'ios_max_abs_diff', 'matches_equal_on_every_input')}, 'ok', ok)
sys.exit(0 if ok else 1)
" >> "$S/switch.log" 2>&1 || { echo "$(stamp) the replay's inputs differ from the instance's frame"; return 2; }
  echo "$(stamp) replay check passed"
  echo "$(stamp) live checkpoint 2026-09-21"
  ./python.sh -c "
import sys; sys.path.insert(0, '.')
import src.pipeline as tp
sys.exit(0 if tp.make_checkpoint('2026-09-21', tree='$SB').ok else 1)
" >> "$S/switch.log" 2>&1 || { echo "$(stamp) live checkpoint failed (the first live run makes one)"; return 0; }
  return 0
}
switch
case $? in
  0) echo "$(stamp) SWITCH DONE: the daily runs use $INST" ;;
  2) cp "$S/selected_instance_before.json" "$SEL"; echo "$(stamp) SWITCH REVERTED: the daily runs use the previous instance again" ;;
  *) echo "$(stamp) not switched" ;;
esac
echo "$(stamp) fits: seeds 4-15, 2019-2025"
$FITS --seeds 4-15 --seasons 2019-2025 > "$OUT/fits_seeds4-15_2019-2025.log" 2>&1 || { echo "$(stamp) fits (other seasons) failed"; exit 1; }
echo "$(stamp) DONE"
