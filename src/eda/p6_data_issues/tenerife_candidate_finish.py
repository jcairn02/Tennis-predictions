"""The Tenerife harm check's candidate after lane 1 (docs/decisions/2026-10-14-p6-data-issues.md, point 1): the frame as
the reference built it, then the records.

The reference of 8 Oct 2026 predates the women's indoor fill (9 Oct), which build_frame.py now applies by default. As the
Roland Garros candidate did (its "lane 1i", docs/studies/rg_first_serve_recount/README.md, section 10.3, step 10), the
base frame is rebuilt with --indoor-men-only, then the frames that read it (the leak-proof frame, the Elo frames), so that
the candidate differs from the reference by the date correction alone. Then lane 3 and --collect.

The fits (./python_tabpfn_local.sh src/eda/model_rebuild/fits.py --out <out> --seeds 0-3 --seasons 2019-2024) and the
reading (compare.py --candidate <out>; adoption_read.py --kind repair) run after this, as separate commands.

Run: MODEL_REBUILD_SANDBOX=C:/Users/zerom/tnr_sb_tenerife ./python.sh src/eda/p6_data_issues/tenerife_candidate_finish.py \
        --out data/studies/current_best_model/2026-10-14_tenerife_dates
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if not os.environ.get("MODEL_REBUILD_SANDBOX"):
    raise SystemExit("set MODEL_REBUILD_SANDBOX to the candidate's sandbox")

from src.eda.model_rebuild import run_chain as R  # noqa: E402  (reads MODEL_REBUILD_SANDBOX at import)

R.LANES["1i"] = [("thinking_frame_indoor_men_only", "src/eda/tabpfn_thinking/build_frame.py --indoor-men-only"),
                 ("leakproof_frame_after_indoor_men_only", "src/eda/tabpfn_leakproof/build_frame.py"),
                 ("elo_frames_after_indoor_men_only", "src/eda/surface_elo_pieces/build_frames.py")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = ROOT / a.out
    for lane in ("1i", "3"):
        code = R.run_lane(lane, None, out)
        if code:
            return code
    R.collect(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
