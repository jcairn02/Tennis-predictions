#!/usr/bin/env bash
# After build_template.sh: keep the chain's own frame and list (model_frame_chain.parquet, model_inputs_chain.json: the
# books'-average odds input, all 58 columns listed), then the decided odds input (Pinnacle first) and input list (57).
# Usage: bash data/studies/level_layer_adoption/post_build.sh <folder> [<Stage 1 odds table, default the live one>]
set -eu
F="$1"; S1="${2:-}"
cd /c/Users/zerom/Documents/Tennis-predictions
[ -f "$F/model_frame_chain.parquet" ] || cp "$F/model_frame.parquet" "$F/model_frame_chain.parquet"
[ -f "$F/model_inputs_chain.json" ] || cp "$F/model_inputs.json" "$F/model_inputs_chain.json"
if [ -n "$S1" ]; then
  ./python.sh src/eda/current_best_model/odds_input.py --apply "$F" --stage1 "$S1"
else
  ./python.sh src/eda/current_best_model/odds_input.py --apply "$F"
fi
./python.sh src/eda/current_best_model/template_inputs.py --apply "$F"
echo "post-build done: $F"
