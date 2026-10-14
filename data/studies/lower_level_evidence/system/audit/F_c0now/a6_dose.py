"""Role E audit of C0_now, part 6: how much of the model frame the additions reach, by tour and season (the expected
unevenness). For each frame match: does either player have, in the 365 days before its tournament date, (a) new matches,
(b) new box scores (new matches with one, or the box layer's completions), (c) a new match with a player of the other
tour's id (the cross-tour crosswalk defect). Counts and dates only.
Run: ./python.sh data/studies/lower_level_evidence/system/audit/F_c0now/a6_dose.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from src.eda.lower_level_evidence import common as LC  # noqa: E402

AUD = ROOT / "data/studies/lower_level_evidence/system/audit/F_c0now"
CAND = ROOT / "data/studies/lower_level_evidence/system/stage0/C0_now"
EPOCH = pd.Timestamp("1970-01-01")
m = pd.read_parquet(CAND / "stage0_matches.parquet", columns=["match_id", "tour", "tournament_date", "has_box",
                                                               "player_a_id", "player_b_id"])
ref = pd.read_parquet(LC.STAGE0_DIR / "stage0_matches.parquet", columns=["match_id", "has_box"])
m["new"] = ~m["match_id"].isin(set(ref["match_id"]))
L = pd.read_parquet(CAND / "box_layers.parquet", columns=["match_id", "applied", "reference_match"])
done = set(L.loc[L["applied"].astype(bool), "match_id"])
m["new_box"] = (m["new"] & m["has_box"].astype(bool)) | m["match_id"].isin(done)
pa, pb = m["player_a_id"].str.split(":").str[0], m["player_b_id"].str.split(":").str[0]
m["cross"] = m["new"] & ((pa != m["tour"]) | (pb != m["tour"]))
p = pd.concat([m[["match_id", "tournament_date", "new", "new_box", "cross"]].assign(pid=m["player_a_id"]),
               m[["match_id", "tournament_date", "new", "new_box", "cross"]].assign(pid=m["player_b_id"])],
              ignore_index=True)
p["day"] = (pd.to_datetime(p["tournament_date"]) - EPOCH).dt.days.astype("int64")
f = pd.read_parquet(LC.FRAME, columns=["match_id", "tour", "season", "tournament_date"])
f = f.merge(m[["match_id", "player_a_id", "player_b_id"]], on="match_id")
fr = pd.concat([f[["match_id", "tour", "season", "tournament_date"]].assign(pid=f["player_a_id"]),
                f[["match_id", "tour", "season", "tournament_date"]].assign(pid=f["player_b_id"])], ignore_index=True)
fr["day"] = (pd.to_datetime(fr["tournament_date"]) - EPOCH).dt.days.astype("int64")
codes, _ = pd.factorize(pd.concat([p["pid"], fr["pid"]], ignore_index=True))
pc, fc = codes[:len(p)].astype(np.int64), codes[len(p):].astype(np.int64)
big = np.int64(100000)
for name in ("new", "new_box", "cross"):
    mask = p[name].to_numpy()
    keys = np.sort(pc[mask] * big + p["day"].to_numpy()[mask])
    hi = np.searchsorted(keys, fc * big + fr["day"].to_numpy(), side="left")        # strictly earlier weeks
    lo = np.searchsorted(keys, fc * big + (fr["day"].to_numpy() - 365), side="left")
    fr[name] = hi - lo
per = fr.groupby("match_id").agg(tour=("tour", "first"), season=("season", "first"),
                                 any_new=("new", lambda s: bool((s > 0).any())),
                                 any_new_box=("new_box", lambda s: bool((s > 0).any())),
                                 any_cross=("cross", lambda s: bool((s > 0).any())),
                                 n_new=("new", "sum"))
out = per.groupby(["tour", "season"]).agg(frame=("any_new", "size"), with_new_365=("any_new", "mean"),
                                          with_new_box_365=("any_new_box", "mean"),
                                          with_cross_tour_365=("any_cross", "sum"),
                                          mean_new_matches_365=("n_new", "mean")).round(3).reset_index()
out.to_csv(AUD / "frame_reach_by_tour_season.csv", index=False)
print(out.to_string(index=False))
(AUD / "a6_results.json").write_text(json.dumps(out.to_dict("records"), indent=1, default=str), encoding="utf-8")
