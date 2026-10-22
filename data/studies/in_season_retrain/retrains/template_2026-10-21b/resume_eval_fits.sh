#!/usr/bin/env bash
# The corrected retrain's evaluation-only fits (seeds 4-15, 2019-2025), deferred to 03:00 (21 Oct 2026): after the
# switch, a bet day started while they ran would have waited on them for the card (up to 6 h; the long-jobs rule:
# evaluation-only fits at a quiet time). A fit already on disk is never redone.
cd /c/Users/zerom/Documents/Tennis-predictions || exit 1
L=data/studies/in_season_retrain/retrains/template_2026-10-21b.log
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
secs=$(( $(date -d 'tomorrow 03:00' +%s) - $(date +%s) ))
echo "$(stamp) evaluation fits deferred: waiting $secs s (to 03:00 local)" >> "$L"
sleep "$secs"
echo "$(stamp) fits: seeds 4-15, 2019-2025 (resumed)" >> "$L"
./python_tabpfn_local.sh src/eda/model_rebuild/fits.py --out data/studies/current_best_model/template_2026-10-21b \
  --seeds 4-15 --seasons 2019-2025 >> data/studies/current_best_model/template_2026-10-21b/fits_seeds4-15_2019-2025.log 2>&1 \
  && echo "$(stamp) DONE" >> "$L" || echo "$(stamp) fits (other seasons) failed" >> "$L"
