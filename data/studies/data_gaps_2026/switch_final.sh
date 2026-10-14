#!/usr/bin/env bash
# After use_instance("template_2026-10-14", tree=C:/Users/zerom/tnr_tpl1014) (process log, § 3 addendum 2, step 6):
# the replay's checkpoint, the replay check with Tennis My Life's dump held as the final build read it (the frozen view
# C:/Users/zerom/tnr_dump_freeze_1014, freeze 2026-10-14T04:12:16Z; the notebook's replay_check would hold the 8 Oct
# view, and its runner clears DP_* settings, so the engine's own commands are run here with the same variables plus
# DP_FREEZE_DUMP), then the live checkpoint. Launched in a window of its own.
# Usage, from the repository root: bash data/studies/data_gaps_2026/switch_final.sh
set -u
REPO=/c/Users/zerom/Documents/Tennis-predictions
cd "$REPO" || exit 1
L=data/studies/data_gaps_2026/switch_final.log
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
TREE=C:/Users/zerom/tnr_tpl1014
INST=template_2026-10-14
echo "$(stamp) checkpoint 2026-06-22" >> "$L"
./python.sh -c "
import sys; sys.path.insert(0, '.')
import src.pipeline as tp
r = tp.make_checkpoint('2026-06-22', tree='$TREE')
sys.exit(0 if r.ok else 1)
" >> "$L" 2>&1 || { echo "$(stamp) checkpoint failed" >> "$L"; exit 1; }
RUN="C:/Users/zerom/Documents/Tennis-predictions/data/studies/daily_prediction/runs/replay_2026-07-13_R16_$(date +%Y%m%dT%H%M%S)"
echo "$(stamp) replay into $RUN" >> "$L"
export DP_BASE_TREE="$TREE" DP_INSTANCE="$INST" DP_WORK_TREE=C:/Users/zerom/tnr_daily_nb DP_FREEZE_DUMP=C:/Users/zerom/tnr_dump_freeze_1014
./python.sh src/eda/daily_prediction/dp.py run_day --run "$RUN" --replay-week 2026-07-13 --replay-round R16 --checkpoint 2026-06-22 >> "$L" 2>&1 || { echo "$(stamp) replay failed" >> "$L"; exit 1; }
./python.sh src/eda/daily_prediction/dp.py replay-compare --run "$RUN" >> "$L" 2>&1 || { echo "$(stamp) replay-compare failed" >> "$L"; exit 1; }
unset DP_BASE_TREE DP_INSTANCE DP_WORK_TREE DP_FREEZE_DUMP
echo "$(stamp) checkpoint 2026-09-21" >> "$L"
./python.sh -c "
import sys; sys.path.insert(0, '.')
import src.pipeline as tp
r = tp.make_checkpoint('2026-09-21', tree='$TREE')
sys.exit(0 if r.ok else 1)
" >> "$L" 2>&1 || { echo "$(stamp) live checkpoint failed" >> "$L"; exit 1; }
echo "$(stamp) SWITCH DONE" >> "$L"
