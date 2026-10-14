"""Stage 3, part 1: each player's pre-match values, side by side, for the diagnostics of Stage 3 ("is it the method or
the data?").

Stage 2's features are A - B differences, which is what the shared harness scores. The diagnostics need each player's
own values: a point-level model sets the server's serve traits against the returner's return traits, and a flexible
learner can only find a matchup if it sees both players separately. This script rebuilds Stage 2's features with the
same averages, constants and time rule (stage2_features.build) and keeps, for every pool match, side A's and side B's
values. It adds the box-score reference the diagnostics compare against: each player's serve and return points won in
the same three memories (Stage 0's box counts, the same machinery), and the earlier study's pre-match serve-point
forecasts from the serve/return ratings (stage3_ratings.parquet: p_serve_a, p_serve_b).

The targets of the point-level diagnostic come along: each side's serve points won and served in the match itself
(Stage 0's box score). They are the match's result at the level of points; the features never read them.

Run:  ./python.sh src/eda/shot_level/stage3_sides.py   (a few minutes)
Writes data/studies/shot_level/stage3_sides.parquet (one row per pool match).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.shot_level import common as S  # noqa: E402
from src.eda.shot_level import stage2_features as F  # noqa: E402
from src.eda.shot_level import stats as T  # noqa: E402

BOX = {"spw": ("spw_n", "spw_d"), "rpw": ("rpw_n", "rpw_d")}


def box_forms(rows: pd.DataFrame) -> dict:
    """Each player's serve and return points won (Stage 0's box score) in the three memories, centred on the tour's
    surface average and shrunk with an empirical-Bayes K, as the shot-level statistics are: {name: (values, denominators)}."""
    mp = C.load_match_players(["match_id", "side", "spw_n", "spw_d", "rpw_n", "rpw_d"], with_order=False)
    rows = rows.merge(mp, on=["match_id", "side"], how="left")
    out = {}
    for s, (nc, dc) in BOX.items():
        n, d = rows[nc].fillna(0).to_numpy(), rows[dc].fillna(0).to_numpy()
        ok = d > 0
        tour, sf, yr = rows["tour"].to_numpy(), rows["surface"].to_numpy(), rows["year"].to_numpy()
        mus, mut = np.zeros(len(rows)), np.zeros(len(rows))
        K = {}
        for t in C.TOURS:
            mt = (tour == t) & ok & (yr <= 2018)
            mu_t = n[mt].sum() / d[mt].sum()
            mut[tour == t] = mu_t
            for x in F.SURFACES:
                ms = mt & (sf == x)
                mus[(tour == t) & (sf == x)] = n[ms].sum() / d[ms].sum() if d[ms].sum() >= 1000 else mu_t
            g = pd.DataFrame({"p": rows["pcode"].to_numpy()[mt], "y": yr[mt], "n": n[mt], "d": d[mt]})
            g = g.groupby(["p", "y"])[["n", "d"]].sum()
            K[t] = F.eb_constant(g["n"].to_numpy(), g["d"].to_numpy(), "share")
        Fm = F.forms(rows, np.column_stack([np.where(ok, n - d * mus, 0.0), np.where(ok, d, 0.0)]))
        k = np.where(tour == "atp", K["atp"], K["wta"])
        for f, arr in Fm.items():
            r = arr[:, 0] / (arr[:, 1] + k)
            out[f"{s}|box|{f}"] = (F.scale(s, mut + r), arr[:, 1])
        out[f"_{s}_target"] = (n, d)
    return out


def main() -> int:
    S.log("rows, averages, constants (as Stage 2)")
    rows = F.load_rows()
    opp = np.where(np.isnan(rows["opp_row"].to_numpy(dtype=float)), 0, rows["opp_row"]).astype(int)
    mu = F.averages(rows)
    K = F.constants(rows, opp)
    S.log("features per player-match")
    vals, dens = F.build(rows, mu, K)
    S.log("box-score serve and return points in the same memories")
    bx = box_forms(rows)
    from src.eda.ufc_ideas import common as U
    pool = pd.read_parquet(U.STAGE4_FEATURES, columns=U.POOL_COLS)
    pos = pd.Series(np.arange(len(rows)), index=pd.MultiIndex.from_arrays([rows["match_id"], rows["side"]]))
    ia = pos.reindex(pd.MultiIndex.from_arrays([pool["match_id"], np.full(len(pool), "A")])).to_numpy().astype(int)
    ib = pos.reindex(pd.MultiIndex.from_arrays([pool["match_id"], np.full(len(pool), "B")])).to_numpy().astype(int)
    out = {}
    for name, v in vals.items():
        if name.startswith("_"):
            continue
        dn = dens[name]
        out[f"A|{name}"] = v[ia].astype("float32")
        out[f"B|{name}"] = v[ib].astype("float32")
        out[f"A|{name}|has"] = (dn[ia] > 0)
        out[f"B|{name}|has"] = (dn[ib] > 0)
    for name, (v, dn) in bx.items():
        if name.startswith("_"):
            continue
        out[f"A|{name}"] = v[ia].astype("float32")
        out[f"B|{name}"] = v[ib].astype("float32")
        out[f"A|{name}|has"] = (dn[ia] > 0)
        out[f"B|{name}|has"] = (dn[ib] > 0)
    tn, td = bx["_spw_target"]
    out["A_spw_n"], out["A_spw_d"] = tn[ia], td[ia]
    out["B_spw_n"], out["B_spw_d"] = tn[ib], td[ib]
    sides = pd.concat([pool, pd.DataFrame(out, index=pool.index)], axis=1)
    rat = pd.read_parquet(C.OUT / "stage3_ratings.parquet", columns=["match_id", "p_serve_a", "p_serve_b", "mu_logit"])
    m = C.load_matches(["match_id", "tournament_date", "best_of", "surface", "level", "tournament_name", "qualifying"])
    sides = sides.merge(rat, on="match_id", how="left").merge(m, on="match_id", how="left")
    sides.to_parquet(S.OUT / "stage3_sides.parquet", index=False)
    S.log(f"wrote stage3_sides.parquet: {len(sides)} matches, {len(sides.columns)} columns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
