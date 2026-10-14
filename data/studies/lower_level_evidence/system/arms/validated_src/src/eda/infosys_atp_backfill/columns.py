"""The speed adjustment's columns on the augmented history (the ATP's decrypted files added). Reads no match result.

The current best model's adjustment reads spd_L (the 28-day form difference) on the corrected speed history; its
coefficients are fitted on spd_L_B, the weekly feed's release days (data/studies/model_rebuild/
speed_columns_corrected.parquet, src/eda/model_rebuild/speed_columns.py). Here the same builder
(serve_speed_tabpfn/adaptive/columns.py, build) runs on the corrected history, which must reproduce that file exactly,
and on the augmented history (history.py), unchanged otherwise: the same frame matches (the 63,737 of the model frame
the columns were built for), release days (latency/availability.parquet: a new tour-level row is released as any other,
the weekly scenario B, the daily D), constants and standardisers. So the only difference between the two is the new
source.

Writes data/studies/infosys_atp_backfill/speed_columns_augmented.parquet (match_id and every spd_*/late_*/mode_* column)
and columns.json (how many matches moved, by column and season).
Run: ./python.sh src/eda/infosys_atp_backfill/columns.py   (about 5 minutes)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.adaptive import columns as CO  # noqa: E402
from src.eda.serve_speed_tabpfn.live import live_panel as LP  # noqa: E402

OUT = ROOT / "data" / "studies" / "infosys_atp_backfill"
AUGMENTED = LP.BACKFILLED
COLUMNS = OUT / "speed_columns_augmented.parquet"
CORRECTED_COLUMNS = ROOT / "data" / "studies" / "model_rebuild" / "speed_columns_corrected.parquet"


def build_on(history: pd.DataFrame) -> pd.DataFrame:
    """adaptive/columns.py's build with `history` in place of the frozen panel."""
    frozen_load = P.load_panel
    P.load_panel = lambda use_only=True: (history[history["use"].astype(bool)].reset_index(drop=True)
                                          if use_only else history)
    try:
        return CO.build(probes=False)["out"]
    finally:
        P.load_panel = frozen_load


def main() -> int:
    stored = pd.read_parquet(CORRECTED_COLUMNS)
    base = build_on(pd.read_parquet(LP.CORRECTED))
    pd.testing.assert_frame_equal(base.reset_index(drop=True), stored[base.columns].reset_index(drop=True),
                                  check_dtype=False)            # the corrected history's columns, reproduced
    new = build_on(pd.read_parquet(AUGMENTED))
    OUT.mkdir(parents=True, exist_ok=True)
    new.to_parquet(COLUMNS, index=False)
    keys = P.load_frame_keys()[["match_id", "tour", "season"]]
    k = new[["match_id"]].merge(keys, on="match_id", how="left")
    moved, by_season = {}, {}
    for c in [c for c in new.columns if c.startswith("spd_")]:
        d = (new[c] - base[c]).abs()
        moved[c] = {"moved_0_01": int((d > 0.01).sum()), "moved_0_25": int((d > 0.25).sum()),
                    "moved_1": int((d >= 1).sum()), "max_abs": float(d.max())}
        if c in ("spd_L_B", "spd_L_D", "spd_L_A"):
            g = pd.DataFrame({"season": k["season"], "tour": k["tour"], "moved": d > 0.01,
                              "nonzero_before": base[c].abs() > 1e-12, "nonzero_after": new[c].abs() > 1e-12})
            g = g[g["tour"].eq("atp")]
            by_season[c] = {int(s): {"men_matches": int(len(x)), "moved_0_01": int(x["moved"].sum()),
                                     "nonzero_before": int(x["nonzero_before"].sum()),
                                     "nonzero_after": int(x["nonzero_after"].sum())}
                            for s, x in g.groupby("season")}
    meta = {"what": "adaptive/columns.py's build on the augmented history; the corrected history's columns reproduced",
            "history": AUGMENTED.relative_to(ROOT).as_posix(), "reference": CORRECTED_COLUMNS.relative_to(ROOT).as_posix(),
            "rows": int(len(new)), "moved_units": moved, "men_by_season": by_season,
            "mode_changes": {c: int((new[c] != base[c]).sum()) for c in new.columns if c.startswith("mode_")}}
    (OUT / "columns.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
