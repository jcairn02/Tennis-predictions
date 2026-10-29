"""Task 5: reliability, description only. Split-half reliability across players of candidate rally rates, inside the
52-week window ending 31 Dec 2025 and the one ending 18 Oct 2026 (the data's end), with P9 and without it.

The atoms with P9 are atoms.parquet (P9 first where sources overlap). Without P9, a match P9 gave takes its points from
the next source that carries it (match_sources.parquet, chosen_without_p9), or drops out. For each window and arm, each
player with at least MIN_MATCHES matches with rally data in the window has the matches split at random into two halves
(50 splits); per half, a rate is the sum of its numerators over the sum of its denominators; the split-half correlation
is Pearson's across players (players with a positive denominator in both halves), averaged over the splits. Also given:
the Spearman-Brown value for the whole window, 2r / (1 + r); a chance band (the 97.5% point of r with the second
halves shuffled across players, 200 shuffles of the first split); the players and the mean denominator per half.

Rates (per player, from the atoms; serve points exclude double faults where a rally length is asked for):
    srv_by2, srv_by4, srv_9p    serve points ending by shot 2, by shot 4, at 9 shots or more
    srv_won_b1..b4              serve points won, by band (1-2, 3-4, 5-8, 9+)
    ret_won_b1..b4              return points won, by band
    srv_mean_rally, ret_mean_rally   mean rally length (capped at 9 / 10) on serve, on return
    net_rate, net_won           net approaches per point with net flags; net points won

The shot-level study's split-half values (data/studies/shot_level/stage1_reliability.csv: men, all years, players with
30+ matches, alternate halves) are listed beside them for the nearest statistics. No match result is read.

Run:  ./python.sh src/eda/p9_point_details/build_reliability.py      (after build_atoms.py; a few minutes)
Writes data/studies/p9_point_details/build/reliability.csv and reliability.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.p9_point_details import build_atoms as BA  # noqa: E402
from src.eda.p9_point_details import build_common as B  # noqa: E402
from src.eda.p9_point_details import build_points as BP  # noqa: E402

MIN_MATCHES = 6
SPLITS = 50
SHUFFLES = 200
WINDOWS = {"2025": (pd.Timestamp("2025-01-02"), pd.Timestamp("2025-12-31")),
           "2026": (pd.Timestamp("2025-10-21"), pd.Timestamp("2026-10-18"))}
NEAREST = {"srv_by2": None, "srv_by4": "srv_quick (rally points won within 4 shots, on serve)",
           "srv_9p": "long_share (points of 5+ shots, a style)", "srv_won_b4": "rally9 (points of 9+ won)",
           "ret_won_b4": "rally9 (points of 9+ won)", "srv_won_b3": "rally5 (points of 5+ won)",
           "ret_won_b3": "rally5 (points of 5+ won)", "ret_won_b1": "ret_quick (return points won within 4 shots)",
           "net_rate": "net_rate", "net_won": "net_won", "srv_mean_rally": "long_share (style)",
           "ret_mean_rally": "long_share (style)"}
SHOT_LEVEL_STAT = {"srv_by4": "srv_quick", "srv_9p": "long_share", "srv_won_b4": "rally9", "ret_won_b4": "rally9",
                   "srv_won_b3": "rally5", "ret_won_b3": "rally5", "ret_won_b1": "ret_quick", "net_rate": "net_rate",
                   "net_won": "net_won", "srv_mean_rally": "long_share", "ret_mean_rally": "long_share"}


def rate_parts(a: pd.DataFrame) -> dict[str, tuple[pd.Series, pd.Series]]:
    nd = a["srv_b1"] + a["srv_b2"] + a["srv_b3"] + a["srv_b4"]
    out = {"srv_by2": (a["srv_b1"], nd), "srv_by4": (a["srv_b1"] + a["srv_b2"], nd), "srv_9p": (a["srv_b4"], nd)}
    for b in range(1, 5):
        out[f"srv_won_b{b}"] = (a[f"srv_w_b{b}"], a[f"srv_b{b}"])
        out[f"ret_won_b{b}"] = (a[f"ret_w_b{b}"], a[f"ret_b{b}"])
    out["srv_mean_rally"] = (a["srv_rally_sum"], a["srv_rally_n"])
    out["ret_mean_rally"] = (a["ret_rally_sum"], a["ret_rally_n"])
    cov = a["net_cov"].eq(1)
    out["net_rate"] = (a["net_app"].where(cov, 0), a["net_pts"].where(cov, 0))
    out["net_won"] = (a["net_won"].where(cov, 0), a["net_app"].where(cov, 0))
    return out


def without_p9_atoms(atoms: pd.DataFrame) -> pd.DataFrame:
    """Atoms of the arm without P9: P9's matches replaced by the next carrying source's, or dropped."""
    ms = pd.read_parquet(B.OUT / "match_sources.parquet")
    p9_matches = set(ms.loc[ms["chosen_all"] & ms["source"].eq("p9"), "match_id"])
    repl = ms[ms["chosen_without_p9"] & ms["match_id"].isin(p9_matches)]
    links = pd.read_parquet(B.OUT / "links.parquet")
    links = links[links["match_id_s0"].notna()]
    s0 = B.stage0_men(["player_a_id", "player_b_id", "tournament_date", "tournament_id", "round", "round_order",
                       "level", "qualifying", "surface", "best_of"], 2018)
    parts = []
    for source, g in repl.groupby("source"):
        keys = set(g["src_key"])
        p = BP.atp_points(source) if source in B.ATP_SOURCES else BP.shot_level_points(source, keys)
        p = p[p["key"].isin(keys) & (p["rally"] >= 0)]
        o = BP.orient(p, links[links["source"].eq(source)], s0[["match_id", "player_a_id", "player_b_id"]])
        o["rally_c"] = B.capped(o["rally"]).astype("int16")
        o["band"] = B.band_of(o["rally"])
        o["source"] = source
        parts.append(o.drop(columns=["player_a_id", "player_b_id", "a1"]))
    rp = pd.concat(parts, ignore_index=True) if parts else None
    keep = atoms[~atoms["match_id"].isin(p9_matches)]
    if rp is None:
        return keep
    return pd.concat([keep, BA.atoms(rp, s0)], ignore_index=True)


def split_half(a: pd.DataFrame, rng: np.random.Generator) -> list[dict]:
    counts = a.groupby("player_id").size()
    keep = counts[counts >= MIN_MATCHES].index
    a = a[a["player_id"].isin(keep)].reset_index(drop=True)
    parts = rate_parts(a)
    pid = a["player_id"].to_numpy()
    n_by = a.groupby("player_id")["player_id"].transform("size").to_numpy()
    res = {k: [] for k in parts}
    extra = {k: {} for k in parts}
    for s in range(SPLITS):
        u = rng.random(len(a))
        rank = pd.Series(u).groupby(pid).rank(method="first").to_numpy()
        half = (rank > n_by // 2).astype(int)
        for k, (num, den) in parts.items():
            g = pd.DataFrame({"p": pid, "h": half, "n": num.to_numpy(), "d": den.to_numpy()}).groupby(["p", "h"])[
                ["n", "d"]].sum().unstack()
            g = g[(g[("d", 0)] > 0) & (g[("d", 1)] > 0)]
            if len(g) < 30:
                res[k].append(np.nan)
                continue
            r0 = (g[("n", 0)] / g[("d", 0)]).to_numpy()
            r1 = (g[("n", 1)] / g[("d", 1)]).to_numpy()
            res[k].append(float(np.corrcoef(r0, r1)[0, 1]))
            if s == 0:
                perm = [np.corrcoef(r0, rng.permutation(r1))[0, 1] for _ in range(SHUFFLES)]
                extra[k] = {"players": int(len(g)), "chance_hi": float(np.quantile(perm, 0.975)),
                            "mean_den_per_half": float(np.concatenate([g[("d", 0)], g[("d", 1)]]).mean())}
    out = []
    for k, v in res.items():
        v = np.array(v, dtype=float)
        r = float(np.nanmean(v)) if np.isfinite(v).any() else np.nan
        out.append({"rate": k, "split_half_r": r, "r_sd_over_splits": float(np.nanstd(v)),
                    "spearman_brown": 2 * r / (1 + r) if np.isfinite(r) else np.nan,
                    "players_with_min_matches": int(len(keep)), **extra[k]})
    return out


def main() -> int:
    atoms = pd.read_parquet(B.OUT / "atoms.parquet")
    atoms["tournament_date"] = pd.to_datetime(atoms["tournament_date"])
    wo = without_p9_atoms(atoms)
    wo["tournament_date"] = pd.to_datetime(wo["tournament_date"])
    rng = np.random.default_rng(20261028)
    rows = []
    for wname, (lo, hi) in WINDOWS.items():
        for arm, a in (("with_p9", atoms), ("without_p9", wo)):
            w = a[(a["tournament_date"] >= lo) & (a["tournament_date"] <= hi)]
            for r in split_half(w, rng):
                rows.append({"window_end": wname, "arm": arm, "matches_in_window": int(w["match_id"].nunique()), **r})
            B.log(f"{wname} {arm}: done")
    t = pd.DataFrame(rows)
    sl = pd.read_csv(B.SHOT_LEVEL / "stage1_reliability.csv")
    sl = sl[sl["tour"].eq("atp")].set_index("statistic")["split_half_r"]
    t["shot_level_nearest"] = t["rate"].map(NEAREST)
    t["shot_level_r_men"] = t["rate"].map(SHOT_LEVEL_STAT).map(sl)
    t.to_csv(B.OUT / "reliability.csv", index=False)
    piv = t.pivot_table(index="rate", columns=["window_end", "arm"], values="split_half_r")
    B.write_json(B.OUT / "reliability.json", {"min_matches": MIN_MATCHES, "splits": SPLITS,
                                               "windows": {k: [str(v[0].date()), str(v[1].date())]
                                                           for k, v in WINDOWS.items()},
                                               "rows": t.to_dict(orient="records")})
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(piv.round(3).to_string())
        print(t.pivot_table(index="rate", columns=["window_end", "arm"], values="players").to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
