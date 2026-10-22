#!/usr/bin/env bash
# After build_template.sh: keep the chain's own frame and list (model_frame_chain.parquet, model_inputs_chain.json: the
# books'-average odds input, all 58 columns listed), then the decided odds input (Pinnacle first) and input list (57).
# Since 21 Oct 2026 this runs the notebook layer's finish_instance (src/pipeline/train.py), the one list of these steps:
# this script's own copy had no OddsTrader refresh, so the builds of 13-21 Oct priced their newest matches at the books'
# average while BetOnline's closes were on disk (docs/studies/in_season_retrain/process_log.md, 21 Oct). The odds step
# now brings OddsTrader's tables up to date itself and refuses a frame they do not cover.
# Usage: bash data/studies/level_layer_adoption/post_build.sh <folder> [<Stage 1 odds table, default the live one>]
set -eu
F="$1"; S1="${2:-}"
cd /c/Users/zerom/Documents/Tennis-predictions
./python.sh -c "
import sys; sys.path.insert(0, '.')
from src.pipeline.train import finish_instance
r = finish_instance(sys.argv[1], stage1=sys.argv[2] or None)
sys.exit(0 if r and all(x.ok for x in r) else 1)
" "$F" "$S1"
echo "post-build done: $F"
