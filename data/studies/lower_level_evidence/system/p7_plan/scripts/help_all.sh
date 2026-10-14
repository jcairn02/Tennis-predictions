#!/usr/bin/env bash
# G's dry run, step 1: --help of every command the P7 plan cites, one process at a time. Outputs in p7_plan/help/.
# Left out on purpose (no argument parser: "--help" would run the job itself):
#   src/eda/match_timing/probe.py (main reads sys.argv for --slice/--cuts only, then runs the probe, ~13 min)
#   src/eda/surface_ios/probe.py (main takes no argument and runs the probe, ~22 min)
#   src/eda/lower_level_evidence/relationship_report.py (main takes no argument and rewrites role B's report tables)
cd /c/Users/zerom/Documents/Tennis-predictions || exit 1
OUT=data/studies/lower_level_evidence/system/p7_plan/help
: > "$OUT/exit_codes.tsv"
for s in \
  src/eda/lower_level_evidence/candidate_stage0.py \
  src/eda/lower_level_evidence/relationship.py \
  src/eda/lower_level_evidence/classify.py \
  src/eda/lower_level_evidence/system_sandbox.py \
  src/eda/lower_level_evidence/system_arms.py \
  src/eda/lower_level_evidence/system_new_arms.py \
  src/eda/lower_level_evidence/system_gates.py \
  src/eda/lower_level_evidence/system_g5.py \
  src/eda/lower_level_evidence/system_fits.py \
  src/eda/lower_level_evidence/system_pairs.py \
  src/eda/lower_level_evidence/level_layer_ios.py \
  src/eda/lower_level_evidence/level_layer_ios_checks.py \
  src/eda/lower_level_evidence/refresh.py \
  src/eda/lower_level_evidence/incoming.py \
  src/eda/lower_level_evidence/composition.py \
  src/eda/lower_level_evidence/translation.py \
  src/eda/model_rebuild/run_chain.py \
  src/eda/model_rebuild/fits.py \
  src/eda/current_best_model/compare.py \
  src/eda/current_best_model/history.py \
  src/eda/current_best_model/reference.py ; do
  name=$(basename "$s" .py)
  start=$(date +%s)
  ./python.sh "$s" --help > "$OUT/${name}.txt" 2>&1
  rc=$?
  echo -e "${s}\t${rc}\t$(( $(date +%s) - start ))s" >> "$OUT/exit_codes.tsv"
done
cat "$OUT/exit_codes.tsv"
