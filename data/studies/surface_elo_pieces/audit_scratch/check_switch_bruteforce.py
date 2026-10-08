"""Audit scratch: recompute season_n, days_since, prev_n, prev_res of pieces.parquet by brute force (one player history at
a time, written from the stated rules, not from asof_sums/prev_visible) for a random sample of player-rows, plus a
truncation probe: recompute pieces.surface_switch on the history cut before a week and compare (any value of an earlier
week that changes when LATER MATCHES ARE DELETED is a leak; the author's probe only flipped results, which cannot
move season_n, days_since or prev_n).

Run: ./python.sh data/studies/surface_elo_pieces/audit_scratch/check_switch_bruteforce.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import stage1_baselines as B  # noqa: E402
from src.eda.surface_elo_pieces import common as C  # noqa: E402
from src.eda.surface_elo_pieces import pieces as P  # noqa: E402

OUT = Path(__file__).resolve().parent
rng = np.random.default_rng(11)
m = pd.read_parquet(C.STAGE0, columns=P.STAGE0_COLS)
obs = pd.read_parquet(C.TIMING, columns=["match_id", "obs"]).set_index("match_id").reindex(m["match_id"])["obs"]
obs = obs.to_numpy(dtype="float64")
pc = pd.read_parquet(C.PIECES).set_index("match_id").reindex(m["match_id"]).reset_index()
p_over = B.expected(pc["R_a"].to_numpy(), pc["R_b"].to_numpy())

rows = P.player_rows(m, obs, p_over)
sw_ref = np.column_stack([np.column_stack([pc[f"{c}_a"], pc[f"{c}_b"]]).reshape(-1) for c in
                          ("season_n", "days_since", "prev_n", "prev_res")])

# ---------------- brute force on a sample of players
players = rows["pcode"].unique()
sample_players = rng.choice(players, size=400, replace=False)
sub = rows[rows["pcode"].isin(sample_players)].copy()
sub["ix"] = sub.index.to_numpy()
mism = {"season_n": 0, "days_since": 0, "prev_n": 0, "prev_res": 0}
checked = 0
examples = []
for pcode, g in sub.groupby("pcode"):
    g = g.sort_values("order")
    for _, r in g.iterrows():
        if r["surf"] < 0:
            continue
        checked += 1
        same = g[(g["surf"] == r["surf"]) & g["played"]]
        earlier_week = same["day"] < r["day"]
        same_event_earlier_round = (same["day"] == r["day"]) & (same["ev"] == r["ev"]) & (same["round_order"] < r["round_order"])
        vis = same[earlier_week | same_event_earlier_round]
        s_n = float((vis["year"] == r["year"]).sum())
        if len(vis):
            # an earlier round of the same event first, else the last row of the latest earlier week
            er = vis[(vis["day"] == r["day"]) & (vis["ev"] == r["ev"])]
            prev = (er if len(er) else vis[vis["day"] == vis["day"].max()]).sort_values(["ev", "round_order", "order"]).iloc[-1]
            d_s = max(r["obs"] - prev["obs"], 0.0)
        else:
            d_s = np.nan
        last = same[same["year"] == r["year"] - 1]
        p_n = float(len(last))
        p_r = float((last["won"].astype(float) - last["p_own"]).sum())
        got = sw_ref[r["ix"]]
        for name, want, have in (("season_n", s_n, got[0]), ("days_since", d_s, got[1]), ("prev_n", p_n, got[2]),
                                 ("prev_res", p_r, got[3])):
            ok = (np.isnan(want) and np.isnan(have)) or (np.isfinite(want) and np.isfinite(have) and abs(want - have) < 1e-6)
            if not ok:
                mism[name] += 1
                if len(examples) < 10:
                    examples.append({"pcode": int(pcode), "row": int(r["ix"]), "what": name, "want": want, "have": have})

# ---------------- truncation probe: delete every match from a cut week on, recompute, compare earlier weeks
week = m["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
weeks = np.unique(week)
cuts = rng.choice(weeks[(weeks >= np.quantile(weeks, 0.5))], size=4, replace=False)
trunc = []
for w in cuts:
    keep = week < w
    mm = m[keep].reset_index(drop=True)
    got = P.surface_switch(P.player_rows(mm, obs[keep], p_over[keep])).to_numpy()
    ref = sw_ref[np.repeat(keep, 2)]
    moved = ~np.all(np.isclose(got, ref, equal_nan=True), axis=1)
    trunc.append({"cut_week": str(np.datetime64(int(w), "D")), "rows_checked": int(len(ref)), "rows_moved": int(moved.sum())})

out = {"bruteforce_player_rows_checked": checked, "mismatches": mism, "examples": examples, "truncation_probe": trunc}
print(json.dumps(out, indent=1, default=float))
(OUT / "check_switch_bruteforce.json").write_text(json.dumps(out, indent=1, default=float))
