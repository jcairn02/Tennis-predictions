#!/usr/bin/env bash
# The switch's last step, run by hand after the script's guard misread its own path (process log, 17:58): the live
# checkpoint 2026-09-21 for template_2026-10-16 on its build tree (as switch_final.sh of 14 Oct made it).
set -u
cd /c/Users/zerom/Documents/Tennis-predictions || exit 1
stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
echo "$(stamp) live checkpoint 2026-09-21"
./python.sh -c "
import sys; sys.path.insert(0, '.')
import src.pipeline as tp
sys.exit(0 if tp.make_checkpoint('2026-09-21', tree='C:/Users/zerom/tnr_tpl1016').ok else 1)
" && echo "$(stamp) LIVE CHECKPOINT DONE" || echo "$(stamp) live checkpoint failed"
