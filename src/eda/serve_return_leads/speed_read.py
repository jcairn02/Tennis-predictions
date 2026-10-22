"""Serve/return leads, the speed builder's readings: each speed column against seen results, through readings.py only
(tournament dates before 29 Jul 2026; readings.seen_frame / read / fit_joint). Directions were registered in
docs/studies/serve_return_leads/team/speed_builder.md § 1 before this ran.

    spd_L_B (+)        the stage's 28-day first-serve form, for comparison
    spd2_L_B (+)       second-serve 28-day form (primary of the memo); spd2_T_B (+) its 14-day version
    gap_L_B (+)        the form of the per-match first - second gap
    fade_dev_14 (+)    the previous match's late-minus-early first-serve speed, against own normal
    fault_dev_28 (-)   fault speed minus serve-in speed, last 28 days, against own normal: 2025-26 only (descriptive)
    joint              spd_L_B with spd2_L_B, and spd_L_B with gap_L_B (added before reading), beyond the close,
                       2025-26 and 2013-24

Run: ./python.sh src/eda/serve_return_leads/speed_read.py
Writes data/studies/serve_return_leads/speed/readings.csv, readings_joint.csv, readings.json
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_return_leads import readings as R  # noqa: E402

OUT = ROOT / "data" / "studies" / "serve_return_leads" / "speed"
REGISTERED = {"spd_L_B": +1, "spd2_L_B": +1, "spd2_T_B": +1, "gap_L_B": +1, "fade_dev_14": +1, "fault_dev_28": -1}
SOURCES = {"spd_L_B": "builder_columns.parquet", "spd2_L_B": "builder_columns.parquet",
           "spd2_T_B": "builder_columns.parquet", "gap_L_B": "builder_columns.parquet",
           "fade_dev_14": "fade_dev_14.parquet", "fault_dev_28": "fault_dev_28.parquet"}
ONLY_2025_26 = {"fault_dev_28"}


def aligned(frame: pd.DataFrame, col: str) -> np.ndarray:
    v = pd.read_parquet(OUT / SOURCES[col], columns=["match_id", col]).astype({"match_id": str})
    s = v.drop_duplicates("match_id").set_index("match_id")[col]
    return s.reindex(frame["match_id"]).to_numpy(float)


def main() -> int:
    started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    f = R.seen_frame("atp")
    assert f["tournament_date"].max() < pd.Timestamp("2026-07-29")
    X = {c: aligned(f, c) for c in REGISTERED}
    pres = {c: {w: float(np.mean(np.isfinite(X[c][f["season"].between(a, b).to_numpy()])
                                 & (X[c][f["season"].between(a, b).to_numpy()] != 0)))
                for w, (a, b) in R.WINDOWS.items()} for c in REGISTERED}
    parts = []
    for c, sign in REGISTERED.items():
        win = {"2025-26": R.WINDOWS["2025-26"]} if c in ONLY_2025_26 else None
        parts.append(R.read(f, X[c], c, sign, windows=win))
    long = pd.concat(parts, ignore_index=True)
    long.to_csv(OUT / "readings.csv", index=False)
    joint = []
    for pair in (("spd_L_B", "spd2_L_B"), ("spd_L_B", "gap_L_B")):
        for w in ("2025-26", "2013-24"):
            a, b = R.WINDOWS[w]
            m = f["season"].between(a, b).to_numpy()
            S = np.column_stack([X[c][m] * REGISTERED[c] for c in pair])
            j = R.fit_joint(f[m].reset_index(drop=True), S, base="L", names=list(pair))
            j["window"], j["pair"] = w, "+".join(pair)
            joint.append(j)
    joint = pd.concat(joint, ignore_index=True)
    joint.to_csv(OUT / "readings_joint.csv", index=False)
    meta = {"started_utc": started, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "frame_rows_men": int(len(f)), "last_tournament_date": str(f["tournament_date"].max().date()),
            "registered_directions": REGISTERED, "present_share_nonzero": pres,
            "files": {k: str((OUT / v).relative_to(ROOT)) for k, v in SOURCES.items()}}
    (OUT / "readings.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    w = long.pivot_table(index=["candidate", "form", "base"], columns="window", values="z")
    order = [k for k in R.WINDOWS if k in w.columns]
    with pd.option_context("display.width", 200):
        print(w[order].round(2).to_string())
        print(joint.round(3).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
