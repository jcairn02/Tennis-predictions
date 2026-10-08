"""Red team (S3): leak probes on the FROZEN B-INJ builder (f26's prepare + combine, unchanged), project convention
(src/eda/match_timing/probe.py): for a cut day D, every history match that surely started after D (es > D) has its
result REVERSED (winner flag and the two players' box scores exchanged, retired_self recomputed) or is REMOVED; every
model match that surely finished by D (lf <= D) must keep every per-player prepare column and every raw member
difference (tol 1e-9). Own-match check: the model matches starting on one day have their OWN results reversed; their own
values must not move (players with two matches that day are left out).

No result is related to anything: values are compared with values. Only 2013-2024 (history cut at 20 Dec 2024).
Writes data/studies/feature_interactions/redteam/probe.json.
Run: ./python.sh src/eda/feature_interactions/redteam/binj_probe.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen_batch as B  # noqa: E402
from src.eda.feature_interactions.features import f20_fatigue as F  # noqa: E402
from src.eda.feature_interactions.g5_build import spec_of  # noqa: E402
from src.eda.feature_interactions.history import long_table  # noqa: E402
from src.eda.feature_interactions.panel import panel  # noqa: E402

BOX = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced", "tpw_n", "tpw_d",
       "spw_n", "spw_d", "rpw_n", "rpw_d"]
CUTS = ["2016-07-06", "2019-01-23", "2020-01-29", "2020-09-09", "2022-07-06", "2024-01-24"]
DAY0 = pd.Timestamp("1970-01-01")


def day(s: str) -> float:
    return float((pd.Timestamp(s) - DAY0).days)


def build(spec, P, L) -> dict:
    F.clear_cache()
    new = spec["prepare"](P, L)
    r = B.evaluate(spec, P.assign(**new))
    out = {k: np.asarray(v, float) for k, v in new.items()}
    out.update({f"tab_{n}": np.asarray(a, float) for n, (a, _, _) in r["tabpfn"].items()})
    return out


def reverse(L: pd.DataFrame, rows: np.ndarray) -> pd.DataFrame:
    """Reverse the results of the matches owning `rows` (both players' rows must be in rows)."""
    L1 = L.copy()
    sub = L1.loc[rows, ["match_id"]].copy()
    sub["i"] = rows
    pair = sub.groupby("match_id")["i"].agg(list)
    pair = pair[pair.map(len) == 2]
    a = np.array([p[0] for p in pair]); b = np.array([p[1] for p in pair])
    for c in BOX:
        va, vb = L1.loc[a, c].to_numpy(), L1.loc[b, c].to_numpy()
        L1.loc[a, c], L1.loc[b, c] = vb, va
    idx = np.r_[a, b]
    L1.loc[idx, "won"] = ~L1.loc[idx, "won"].astype(bool)
    L1["retired_self"] = (L1["status"] == "retired") & ~L1["won"].astype(bool)
    return L1


def remove(L: pd.DataFrame, rows: np.ndarray) -> pd.DataFrame:
    L2 = L.drop(index=rows).reset_index(drop=True)
    g = L2.groupby("player_id")
    L2["k"] = g.cumcount()
    L2["obs_mono"] = g["obs"].cummax()
    g = L2.groupby("player_id")
    L2["rest_days"] = L2["obs_mono"] - g["obs_mono"].shift(1)
    L2["rest_min"] = L2["es"] - g["lf"].shift(1)
    return L2


def moved(base: dict, alt: dict, mask: np.ndarray) -> dict:
    out = {}
    for k in base:
        d = np.abs(base[k] - alt[k])
        nanmis = np.isfinite(base[k]) != np.isfinite(alt[k])
        bad = (d > 1e-9) | nanmis
        out[k] = int((bad & mask).sum())
    return out


def main() -> int:
    warnings.simplefilter("ignore")
    spec = spec_of("B-INJ")
    L = long_table()
    P = panel(max_season=2024).drop(columns=["a_won"])
    base = build(spec, P, L)
    es_m, lf_m = P["es"].to_numpy(float), P["lf"].to_numpy(float)
    res = {"cuts": {}, "own": {}}
    for cut in CUTS:
        D = day(cut)
        later = np.flatnonzero(L["es"].to_numpy(float) > D)
        early = lf_m <= D
        late_m = es_m > D
        for kind, Lx in (("reverse", reverse(L, later)), ("remove", remove(L, later))):
            alt = build(spec, P, Lx)
            mv_early, mv_late = moved(base, alt, early), moved(base, alt, late_m)
            res["cuts"][f"{cut}_{kind}"] = {"later_history_rows": int(len(later)), "early_model": int(early.sum()),
                                            "early_moved_max": max(mv_early.values()), "early_moved": mv_early,
                                            "late_moved": mv_late}
            C.log(f"{cut} {kind}: early moved max {max(mv_early.values())}; later moved {mv_late}")
    # own-match reversal: the busiest model-match day of several seasons
    dday = np.floor(es_m)
    seasons = P["season"].to_numpy()
    for yr in (2014, 2017, 2020, 2021, 2023, 2024):
        m = seasons == yr
        d0 = pd.Series(dday[m]).value_counts().index[0]
        S = np.flatnonzero(m & (dday == d0))
        ids = set(P["match_id"].astype(str).to_numpy()[S])
        rowsL = np.flatnonzero(L["match_id"].astype(str).isin(ids).to_numpy())
        pl = L.loc[rowsL, "player_id"].value_counts()
        twice = set(pl[pl > 1].index)
        keep_ids = set(L.loc[rowsL][~L.loc[rowsL, "player_id"].isin(twice)].groupby("match_id").filter(
            lambda g: len(g) == 2)["match_id"].astype(str))
        rowsL = np.flatnonzero(L["match_id"].astype(str).isin(keep_ids).to_numpy())
        alt = build(spec, P, reverse(L, rowsL))
        own = P["match_id"].astype(str).isin(keep_ids).to_numpy()
        mv_own = moved(base, alt, own)
        mv_after = moved(base, alt, es_m > d0 + 1)
        res["own"][str(pd.Timestamp(DAY0 + pd.Timedelta(days=float(d0))).date())] = {
            "own_matches": int(own.sum()), "own_moved_max": max(mv_own.values()), "own_moved": mv_own,
            "later_moved": mv_after}
        C.log(f"own {yr} day {d0}: {int(own.sum())} matches, own moved max {max(mv_own.values())}; later {mv_after}")
    C.write_json(C.OUT / "redteam" / "probe.json", res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
