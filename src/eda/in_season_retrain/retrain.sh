#!/usr/bin/env bash
# A retrain the owner calls (the owner, 20 Oct 2026; docs/decisions/2026-10-09-adoption-by-change-class.md, its
# amendment; docs/studies/in_season_retrain/README.md): the current best model's template built on the day's tables,
# its live fit trained through the cut-off and stage 2 grown with it, then the switch. The steps of the rebuild of 16 Oct
# (data/studies/men_lower_level_fill/build_template.sh), in one detached script, so the end of a session or of VS Code
# cannot stop it and no two GPU jobs of it overlap:
#   0  the replay's view of Tennis My Life's dump, frozen at the start of the Stage 0 rebuild that wrote today's tables
#      (the latest data/studies/data_continuity/rebuilds/*/rebuild.json); accepted.json copied into the instance
#   1  the build (level_layer_adoption/build_template.sh, the accepted route; the daily engine's caches not copied)
#   2  post_build.sh: the Pinnacle-first odds input and the 57-input list (since 21 Oct 2026 the notebook's
#      finish_instance, whose odds step brings OddsTrader's tables up to date first and refuses a frame they do not
#      cover: the first retrain's newest matches had fallen back to the books' average with BetOnline's closes on disk)
#   3  the cut-off (training_rows.py --write; default the Stage 0 rebuild's day: results that surely finished before it)
#      and stage 2's speed table extended to every season-Y men's match, checked against the decided column
#      (in_season_retrain/speed_extend.py; the owner's condition 1); then every revision the owner decided for the
#      next retrain (current_best_model/pending_at_retrain.json, since 22 Oct 2026) checked in the build: missing, it
#      stops (no fits, no switch); after a switch they are marked applied
#   4  fits seeds 0-3, 2019 .. Y (the walk-forward fits: backtests, the harm check, stage 2's history)
#   5  the harm check against the instance in use (in_season_retrain/harm.py; harm = worse by more than 0.10 mLL with the
#      whole 95% interval below 0) and compare.py against the frozen reference (the input check; not a gate)
#   6  harm: stop, no switch (the owner decides). No harm: fits seeds 4-15 for Y (the template check needs them)
#   7  the replay registry's entry (its dump view), then the switch, only if accepted.json is unchanged since the build:
#      use_instance (its template check), checkpoint 2026-06-22, the replay of 13 Jul 2026, replay-compare (the guard of
#      16 Oct), a live checkpoint four weeks back. A failed replay or compare puts the previous selection back
#   8  the other seasons' seeds 4-15 (16-seed evaluations only)
# The first A4 after the switch builds the 16 TabPFN caches on the new rows (about 15 minutes, once) and, with Thinking
# on and SPEND_TOKENS, Thinking's paid season fit on the same rows (about 180k tokens).
# Before it: the data (notebook B5, B2, B4, then B6 with confirm=True), after the week's lower-level feed snapshot.
# Usage, from the repository root (the notebook's tp.retrain(confirm=True) starts it detached):
#   bash src/eda/in_season_retrain/retrain.sh [<instance name> [<sandbox> [<cut-off YYYY-MM-DD>]]]
set -u
REPO=/c/Users/zerom/Documents/Tennis-predictions
cd "$REPO" || exit 1
TODAY=$(date +%Y-%m-%d)
INST="${1:-template_$TODAY}"
SB="${2:-C:/Users/zerom/tnr_tpl$(date +%m%d)}"
OUT="data/studies/current_best_model/$INST"
REB=$(ls -d data/studies/data_continuity/rebuilds/*/ | tail -1)
FREEZE_AT=$(./python.sh -c "import json,sys; print(json.load(open(sys.argv[1]))['started_at'].replace('+00:00','Z'))" \
            "${REB}rebuild.json")
CUTOFF="${3:-${FREEZE_AT:0:10}}"
SEASON="${CUTOFF:0:4}"
FREEZE_DIR="C:/Users/zerom/tnr_dump_freeze_$(echo "${FREEZE_AT:5:5}" | tr -d '-')$(echo "${FREEZE_AT:11:5}" | tr -d ':')"
WORK=C:/Users/zerom/tnr_daily_retrain
S="data/studies/in_season_retrain/retrains/$INST"
SEL=data/studies/master_pipeline/selected_instance.json
ACC=data/studies/current_best_model/accepted_additions/accepted.json
PREV=$(./python.sh -c "import sys; sys.path.insert(0, '.'); from src.pipeline.train import active_instance; print(active_instance().name)")
# no selection, no instance in use to check the retrain against (there is no default since 22 Oct 2026)
[ -n "$PREV" ] || { echo "no live model is selected ($SEL): choose one with use_instance() before a retrain"; exit 1; }
LIVE_CKPT=$(date -d "-28 days" +%Y-%m-%d)
mkdir -p "$OUT" "$S"
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
export RUN_CHAIN_SKIP_DIRS=daily_prediction     # the daily engine's TabPFN caches (55 GB an instance): no chain step reads them
export SURFACE_IOS_WORKERS="${SURFACE_IOS_WORKERS:-6}"
FITS="./python_tabpfn_local.sh src/eda/model_rebuild/fits.py --out $OUT"
echo "$(stamp) retrain $INST: sandbox $SB; tables of $FREEZE_AT ($REB); cut-off $CUTOFF (season $SEASON); in use $PREV"
[ "$PREV" = "$INST" ] && { echo "$(stamp) $INST is the instance in use: give the retrain a new name"; exit 1; }
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
  echo "$(stamp) build: skipped (SKIP_BUILD=1, a resumed retrain)"
else
  echo "$(stamp) build (accepted route) in $SB"
  bash data/studies/level_layer_adoption/build_template.sh "$SB" "$OUT" 1 accepted > "$OUT/build.out" 2>&1 \
    || { echo "$(stamp) build failed: $OUT/build.out"; exit 1; }
fi
echo "$(stamp) post-build"
bash data/studies/level_layer_adoption/post_build.sh "$OUT" > "$OUT/post_build.out" 2>&1 \
  || { echo "$(stamp) post-build failed"; exit 1; }
echo "$(stamp) the cut-off $CUTOFF and the extended speed table"
./python.sh src/eda/current_best_model/training_rows.py --write "$OUT" --cutoff "$CUTOFF" \
  --timing "$SB/data/studies/match_timing/timing.parquet" > "$S/cutoff.log" 2>&1 || { echo "$(stamp) cut-off failed"; exit 1; }
./python.sh src/eda/in_season_retrain/speed_extend.py --instance "$OUT" --season "$SEASON" \
  --stage0 "$SB/data/studies/predictability_diagnostic/stage0_matches.parquet" \
  --timing "$SB/data/studies/match_timing/timing.parquet" > "$S/speed_extend.log" 2>&1 \
  || { echo "$(stamp) the speed table's check failed: $S/speed_extend.log (no grown stage 2 without it)"; exit 1; }
# the revisions the owner decided for this retrain (data/studies/current_best_model/pending_at_retrain.json; the owner,
# 22 Oct 2026: "aware of these intended revisions to the model, not simply adding the latest data"): each must be in
# the build's own Stage 0 and speed table, recorded in <instance>/revisions_at_build.json; else no fits, no switch
echo "$(stamp) the decided revisions pending at this retrain, in the build"
./python.sh src/eda/current_best_model/pending.py --check --stage0 "$SB/data/studies/predictability_diagnostic" \
  --instance "$OUT" --write > "$S/pending.log" 2>&1 \
  || { echo "$(stamp) a decided revision is not in the build: $S/pending.log (no fits, no switch)"; exit 1; }
echo "$(stamp) fits: seeds 0-3, 2019-$SEASON"
$FITS --seeds 0-3 --seasons "2019-$SEASON" > "$OUT/fits.log" 2>&1 || { echo "$(stamp) fits failed"; exit 1; }
echo "$(stamp) harm check against $PREV"
./python.sh src/eda/in_season_retrain/harm.py --new "$OUT" --on "data/studies/current_best_model/$PREV" \
  --last "$SEASON" > "$S/harm.out" 2>&1
HARM_EXIT=$?
echo "$(stamp) compare.py against the frozen reference (the input check; not a gate)"
./python.sh src/eda/current_best_model/compare.py --candidate "$OUT" --out "$OUT/vs_reference_2026-10-08" \
  > "$OUT/vs_reference.out" 2>&1 || echo "$(stamp) compare.py failed (not a gate)"
if [ "$HARM_EXIT" = "3" ]; then echo "$(stamp) HARM BY THE RULE: no switch; the owner decides ($S/harm.out)"; exit 0; fi
if [ "$HARM_EXIT" != "0" ]; then echo "$(stamp) the harm check failed to run ($S/harm.out): no switch"; exit 1; fi
echo "$(stamp) no harm by the rule"
echo "$(stamp) fits: seeds 4-15, $SEASON"
$FITS --seeds 4-15 --seasons "$SEASON" > "$OUT/fits_seeds4-15_$SEASON.log" 2>&1 || { echo "$(stamp) fits failed"; exit 1; }
./python.sh -c "
import json, sys
p = 'data/studies/daily_prediction/replay_views.json'
r = json.load(open(p, encoding='utf-8'))
r['$INST'] = {'dump_view': '$FREEZE_DIR', 'freeze': '$FREEZE_AT',
              'tables': '$REB (in_season_retrain/retrain.sh)'}
open(p, 'w', encoding='utf-8').write(json.dumps(r, indent=1) + '\n')
" || { echo "$(stamp) the replay registry entry failed"; exit 1; }
echo "$(stamp) READY FOR THE SWITCH"

switch() {
  # the 16 Oct script refused the switch when accepted.json changed during the build, because a replay then merged
  # today's list. Since 16 Oct 2026 a replay merges the instance's own record (accepted_at_build.json; daily
  # prediction process log, part 5), so a feed snapshot advanced mid-build (the 12:00 task) only reaches the next build;
  # live runs merge the newest list as always
  if [ "$(sha256sum "$ACC" | cut -d' ' -f1)" != "$ACC_AT_BUILD" ]; then
    echo "$(stamp) note: accepted.json changed since the build (a new feed snapshot): the replay uses the build's own list"
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
  # a Windows path (C:/...) for the python -c code below (16 Oct 2026: a /c/... path there reverted a passed switch)
  RUN="$(cygpath -m "$REPO")/data/studies/daily_prediction/runs/replay_2026-07-13_R16_$(date +%Y%m%dT%H%M%S)"
  echo "$(stamp) replay check into $RUN"
  DP_BASE_TREE="$SB" DP_INSTANCE="$INST" DP_WORK_TREE="$WORK" DP_FREEZE_DUMP="$FREEZE_DIR" \
    ./python.sh src/eda/daily_prediction/dp.py run_day --run "$RUN" --replay-week 2026-07-13 --replay-round R16 \
    --checkpoint 2026-06-22 >> "$S/switch.log" 2>&1 || { echo "$(stamp) replay failed"; return 2; }
  DP_BASE_TREE="$SB" DP_INSTANCE="$INST" DP_WORK_TREE="$WORK" DP_FREEZE_DUMP="$FREEZE_DIR" \
    ./python.sh src/eda/daily_prediction/dp.py replay-compare --run "$RUN" >> "$S/switch.log" 2>&1 \
    || { echo "$(stamp) replay-compare failed"; return 2; }
  ./python.sh -c "
import json, sys
r = json.load(open(r'$RUN/replay_compare.json'))
ok = (not r['missing_from_frame'] and r['ios_nan_pattern_equal'] and r['ios_max_abs_diff'] <= 1e-6
      and r['max_abs_diff'] <= 1e-4 and r['matches'] > 0)
print({k: r[k] for k in ('matches', 'inputs_bitwise', 'max_abs_diff', 'ios_max_abs_diff', 'matches_equal_on_every_input')}, 'ok', ok)
sys.exit(0 if ok else 1)
" >> "$S/switch.log" 2>&1 || { echo "$(stamp) the replay's inputs differ from the instance's frame"; return 2; }
  echo "$(stamp) replay check passed"
  echo "$(stamp) live checkpoint $LIVE_CKPT"
  ./python.sh -c "
import sys; sys.path.insert(0, '.')
import src.pipeline as tp
sys.exit(0 if tp.make_checkpoint('$LIVE_CKPT', tree='$SB').ok else 1)
" >> "$S/switch.log" 2>&1 || { echo "$(stamp) live checkpoint failed (the first live run makes one)"; return 0; }
  return 0
}
switch
case $? in
  0) echo "$(stamp) SWITCH DONE: the daily runs use $INST (trained through the cut-off $CUTOFF)"
     ./python.sh src/eda/current_best_model/pending.py --mark-applied "$INST" >> "$S/switch.log" 2>&1 \
       && echo "$(stamp) the revisions it carries are marked applied (pending_at_retrain.json)" \
       || echo "$(stamp) marking the revisions applied failed: $S/switch.log (mark them by hand)" ;;
  2) cp "$S/selected_instance_before.json" "$SEL"; echo "$(stamp) SWITCH REVERTED: the daily runs use $PREV again" ;;
  *) echo "$(stamp) not switched" ;;
esac
echo "$(stamp) fits: seeds 4-15, 2019-$((SEASON - 1))"
$FITS --seeds 4-15 --seasons "2019-$((SEASON - 1))" > "$OUT/fits_seeds4-15_2019-$((SEASON - 1)).log" 2>&1 \
  || { echo "$(stamp) fits (other seasons) failed"; exit 1; }
echo "$(stamp) DONE"
