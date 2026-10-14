"""The speed adjustment's columns recomputed on the corrected speed history, for the rebuilt model's comparison.

The speed adjustment of the current best model reads spd_L_B (the 28-day form difference on the weekly feed's speeds,
serve_speed_tabpfn/adaptive/columns.parquet), built on the study's frozen panel. The corrections of 8 Oct
(docs/decisions/2026-10-08-corrupt-data-fixes.md) took 130 impossible speed records out of the live feed's history
(live/speed_panel_frozen_corrected.parquet). Here the study's own column builder (adaptive/columns.py, build) runs again
in memory with that corrected history in place of the frozen one, unchanged otherwise: the same frame matches (the
current model frame's 63,737), release days and constants. Nothing of the study is written.

Checks: the builder on the frozen panel reproduces columns.parquet exactly (every column), so the only difference is the
history.
Since 8 Oct 2026 (evening) the live feed's history (live_panel.frozen_panel) also holds the ATP's decrypted files of 2018
to Oct 2021 (docs/studies/infosys_atp_backfill/), so a rerun builds the columns on that history; the run of 8 Oct on the
corrected history alone is frozen in data/studies/current_best_model/reference_2026-10-08/.
Writes data/studies/model_rebuild/speed_columns_corrected.parquet (match_id and every spd_*/late_*/mode_* column) and
speed_columns_corrected.json (how many matches moved, by scenario).
Run: ./python.sh src/eda/model_rebuild/speed_columns.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.adaptive import columns as CO  # noqa: E402
from src.eda.serve_speed_tabpfn.live import live_panel as LP  # noqa: E402

OUT = ROOT / "data" / "studies" / "model_rebuild"


def main() -> int:
    stored = pd.read_parquet(CO.COLUMNS)
    base = CO.build(probes=False)["out"]
    pd.testing.assert_frame_equal(base.reset_index(drop=True), stored[base.columns].reset_index(drop=True),
                                  check_dtype=False)            # the builder reproduces the stored columns
    corrected = LP.frozen_panel()
    frozen_load = P.load_panel
    P.load_panel = lambda use_only=True: (corrected[corrected["use"].astype(bool)].reset_index(drop=True)
                                          if use_only else corrected)
    try:
        new = CO.build(probes=False)["out"]
    finally:
        P.load_panel = frozen_load
    OUT.mkdir(parents=True, exist_ok=True)
    new.to_parquet(OUT / "speed_columns_corrected.parquet", index=False)
    moved = {}
    for c in [c for c in new.columns if c.startswith("spd_")]:
        d = (new[c] - base[c]).abs()
        moved[c] = {"moved_0_01": int((d > 0.01).sum()), "moved_0_25": int((d > 0.25).sum()),
                    "moved_1": int((d >= 1).sum()), "max_abs": float(d.max())}
    meta = {"what": "adaptive/columns.py's build on the corrected speed history; the frozen run reproduced exactly",
            "history": str(LP.CORRECTED.relative_to(ROOT)), "rows": int(len(new)),
            "moved_units": moved,
            "mode_changes": {c: int((new[c] != base[c]).sum()) for c in new.columns if c.startswith("mode_")}}
    (OUT / "speed_columns_corrected.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps(meta, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
