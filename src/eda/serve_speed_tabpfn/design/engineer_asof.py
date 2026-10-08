"""Design R1 (speed-data engineer), step 9: a prototype of leak-proof (clock-following) edition offsets, and how the
centring choice moves the per-player 14-day-minus-364-day first-serve change. Values only; reads no match result.

As-of offsets. For a snapshot day D and a tour, fit on the player-matches RELEASED by D (lf + 1 <= D) with obs within
364 days before D:
    y_i = alpha_player + gamma_edition + e_i,  weights 1 / (tau^2 + s^2 / n_i)   (tau^2 = 22, s = 12.4: engineer_systems)
    edition = (tournament_id, main | qualifying, point mean | key statistic); each gamma shrunk toward its family's mean
    (family = Slam name or 'tour', x draw) with a prior worth K player-matches; reference: the snapshot's men's tour-level
    main-draw editions (when they hold 200+ player-matches), else its Slam main draws, average 0.
A target t reads the snapshot at D = es_t: each history match h in its windows is centred by gamma_{edition(h)}(es_t).
An edition with no released match by es_t takes its family's mean (the prior). Only pooled quantities (gamma) follow the
clock; the player's own matches are own history (safe by construction).

Centrings compared (per frame side with both windows): raw (x_raw); frozen family offsets fitted on seasons <= 2023
(engineer_systems 'le2023': tour/Slam x draw x basis); as-of edition offsets (above).

Run: ./python.sh src/eda/serve_speed_tabpfn/design/engineer_asof.py
Writes data/studies/serve_speed_tabpfn/design/engineer_asof.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402
from src.eda.serve_speed_tabpfn.design import engineer_coverage as COV  # noqa: E402

PANEL0 = EC.OUT / "engineer_panel0.parquet"
TAU2, S_SERVE, K_PRIOR = 22.0, 12.4, 25.0
SHORT, LONG = 14.0, 364.0


def load_panel() -> pd.DataFrame:
    p = pd.read_parquet(PANEL0)
    p = p[~p["implausible"] & (p["n1"] >= 10)].copy()
    p["draw"] = np.where(p["qualifying"].astype(bool), "Q", "M")
    p["bgroup"] = np.where(p["basis"].eq("keystat_atp"), "ks", "pts")
    p["fam"] = np.where(p["slam"].ne(""), p["slam"], "tour") + "_" + p["draw"]
    p["edition"] = p["tournament_id"] + "|" + p["draw"] + "|" + p["bgroup"]
    p["w"] = 1.0 / (TAU2 + S_SERVE ** 2 / p["n1"].clip(lower=1))
    p["rel"] = p["lf"] + 1
    p["tdate"] = p["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    return p.reset_index(drop=True)


class Snapshots:
    """Edition offsets of one tour, fitted per snapshot day on released player-matches within 364 days."""

    def __init__(self, p: pd.DataFrame, tour: str):
        q = p[p["tour"].eq(tour)].sort_values("rel").reset_index(drop=True)
        self.q = q
        self.rel, self.obs = q["rel"].to_numpy(float), q["obs"].to_numpy(float)
        self.y, self.w = q["spd1"].to_numpy(float), q["w"].to_numpy(float)
        self.pid = pd.factorize(q["player_id"])[0]
        self.ed, self.ed_u = pd.factorize(q["edition"])
        self.fam_of_ed = q.drop_duplicates("edition").set_index("edition").loc[self.ed_u, "fam"].to_numpy()
        self.tour_main = np.array([f == "tour_M" for f in self.fam_of_ed])
        self.slam_main = np.array([f.endswith("_M") and f != "tour_M" for f in self.fam_of_ed])
        self.cache: dict[float, np.ndarray] = {}

    def at(self, day: float, iters: int = 60) -> np.ndarray:
        """gamma for every edition of the tour as of `day` (NaN where the edition has no released match: use prior)."""
        if day in self.cache:
            return self.cache[day]
        m = (self.rel <= day) & (self.obs >= day - LONG)
        g_all = np.full(len(self.ed_u), np.nan)
        if m.sum() < 50:
            self.cache[day] = g_all
            return g_all
        y, w, pc, ec = self.y[m], self.w[m], self.pid[m], self.ed[m]
        pu, pi = np.unique(pc, return_inverse=True)
        eu, ei = np.unique(ec, return_inverse=True)
        fam = self.fam_of_ed[eu]
        fu, fi = np.unique(fam, return_inverse=True)
        wp = np.bincount(pi, weights=w)
        we = np.bincount(ei, weights=w)
        g = np.zeros(len(eu))
        for _ in range(iters):
            a = np.bincount(pi, weights=w * (y - g[ei])) / wp
            r = np.bincount(ei, weights=w * (y - a[pi]))
            fm = np.bincount(fi, weights=r) / np.maximum(np.bincount(fi, weights=we), 1e-12)   # family means
            g_new = (r + K_PRIOR * np.mean(w) * fm[fi]) / (we + K_PRIOR * np.mean(w))
            if np.max(np.abs(g_new - g)) < 1e-5:
                g = g_new
                break
            g = g_new
        n_ed = np.bincount(ei)
        ref = self.tour_main[eu]
        if np.bincount(ei, weights=np.ones(len(ei)))[ref].sum() < 200:
            ref = self.slam_main[eu]
        if ref.any():
            g = g - np.average(g[ref], weights=n_ed[ref])
        g_all[eu] = g
        # family means for editions without released matches (prior), stored in a side table
        self.cache[day] = g_all
        self.fam_cache = getattr(self, "fam_cache", {})
        fmean = pd.Series(g, index=eu).groupby(fam).mean()
        self.fam_cache[day] = fmean.to_dict()
        return g_all

    def offset(self, day: float, edition_idx: np.ndarray) -> np.ndarray:
        g = self.at(day)[edition_idx]
        miss = np.isnan(g)
        if miss.any():
            fmean = self.fam_cache.get(day, {})
            g[miss] = [fmean.get(self.fam_of_ed[e], 0.0) for e in edition_idx[miss]]
        return g


def learning_curves(snap: dict, p: pd.DataFrame) -> list[dict]:
    """gamma(D) of chosen editions, day by day from their first day to 10 days after, against the estimate 30 days on."""
    out = []
    picks = [("atp", "W", 2025), ("atp", "USO", 2026), ("atp", "AO", 2024), ("atp", "RG", 2026), ("wta", "W", 2025),
             ("wta", "USO", 2026), ("wta", "AO", 2024)]
    for tour, slam, yr in picks:
        s = snap[tour]
        e = p[(p["tour"] == tour) & (p["slam"] == slam) & (p["year"] == yr) & (p["draw"] == "M")]
        if e.empty:
            continue
        ed_name = e["edition"].mode().iloc[0]
        idx = int(np.flatnonzero(s.ed_u == ed_name)[0])
        d0, d1 = float(e["es"].min()), float(e["lf"].max())
        final = float(s.at(d1 + 30)[idx])
        rel_n = []
        for d in np.arange(d0, d1 + 11):
            g = float(s.offset(d, np.array([idx]))[0])
            n_rel = int(((s.q["edition"] == ed_name) & (s.rel <= d)).sum())
            rel_n.append({"day": int(d - d0), "released": n_rel, "gamma": round(g, 2)})
        out.append({"tour": tour, "edition": f"{slam} {yr}", "final_gamma_30d_after": round(final, 2),
                    "curve": rel_n})
    return out


def windows(t: pd.DataFrame, p: pd.DataFrame, snap: dict, frozen: dict) -> pd.DataFrame:
    """Per target side: m14 - m364 under raw, frozen-family and as-of-edition centring (n-weighted means of first
    serves in, as x_raw)."""
    sides = pd.concat([t.assign(side="A", player_id=t["player_a_id"]), t.assign(side="B", player_id=t["player_b_id"])],
                      ignore_index=True)
    sides["tdate"] = sides["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    tm = pd.read_parquet(EC.TIMING, columns=["match_id", "es"])
    remap = EC.id_map()
    sides["nid"] = sides["match_id"].map(lambda x: remap.get(x, x))
    sides = sides.merge(tm.rename(columns={"match_id": "nid"}), on="nid", how="left")
    p = p.copy()
    p["frozen"] = [frozen.get(f"{t_}|{f}|{b}", np.nan) for t_, f, b in zip(p["tour"], p["fam"], p["bgroup"])]
    p["edix"] = -1
    for tour, s in snap.items():
        mm = p["tour"].eq(tour)
        p.loc[mm, "edix"] = pd.Index(s.ed_u).get_indexer(p.loc[mm, "edition"])
    groups = {k: g for k, g in p.groupby((p["tour"] + "|" + p["player_id"].astype(str)).to_numpy())}
    keys = (sides["tour"] + "|" + sides["player_id"].astype(str)).to_numpy()
    res = np.full((len(sides), 6), np.nan)
    n_unreleased = np.zeros(len(sides))
    for i in range(len(sides)):
        g = groups.get(keys[i])
        if g is None:
            continue
        earlier = (g["tdate"].to_numpy() < sides["tdate"].iat[i]) | (
            (g["tournament_id"].to_numpy() == sides["tournament_id"].iat[i])
            & (g["round_order"].to_numpy() < sides["round_order"].iat[i]))
        age = sides["obs"].iat[i] - g["obs"].to_numpy(float)
        w14, w364 = earlier & (age <= SHORT), earlier & (age <= LONG)
        if not w14.any():
            continue
        n1 = g["n1"].to_numpy(float)
        y = g["spd1"].to_numpy(float)
        fz = g["frozen"].to_numpy(float)
        s = snap[sides["tour"].iat[i]]
        off = s.offset(float(sides["es"].iat[i]), g["edix"].to_numpy()[w364])
        ao = np.zeros(len(g))
        ao[w364] = off
        gi = s.at(float(sides["es"].iat[i]))
        n_unreleased[i] = np.isnan(gi[g["edix"].to_numpy()[w14]]).sum()
        for j, yy in enumerate((y, y - np.nan_to_num(fz), y - ao)):
            m14 = np.sum(n1[w14] * yy[w14]) / np.sum(n1[w14])
            m364 = np.sum(n1[w364] * yy[w364]) / np.sum(n1[w364])
            res[i, j] = m14 - m364
        res[i, 3] = w14.sum()
        res[i, 4] = w364.sum()
    sides[["x_raw", "x_frozen", "x_asof", "k14", "k364", "_"]] = res
    sides["unreleased_editions_in_14d"] = n_unreleased
    return sides


def main() -> None:
    t0 = time.time()
    p = load_panel()
    snap = {tour: Snapshots(p, tour) for tour in ("atp", "wta")}
    res = {"reads_results": False, "tau2": TAU2, "s_serve": S_SERVE, "k_prior_player_matches": K_PRIOR}
    EC.log("learning curves")
    res["learning_curves"] = learning_curves(snap, p)
    for c in res["learning_curves"]:
        EC.log(f"  {c['tour']} {c['edition']}: final {c['final_gamma_30d_after']}; "
               + ", ".join(f"d{x['day']}:{x['gamma']}({x['released']})" for x in c["curve"][:16]))
    # frozen family offsets (<= 2023) from engineer_systems
    sysj = json.loads((EC.OUT / "engineer_systems.json").read_text(encoding="utf-8"))
    frozen = {}
    for r in sysj["le2023"]["families"]:
        fam = r["family"]
        base = "tour" if fam.startswith("tour_") else fam
        b = "ks" if fam == "tour_ks" else "pts"
        frozen[f"{r['tour']}|{base}_{r['draw']}|{b}"] = r["offset_vs_slam_mean"]
    # Slam qualifying absent before 2024: the Slam's main-draw offset; tour ks families as fitted
    for tour in ("atp", "wta"):
        for sl in ("AO", "RG", "W", "USO"):
            for b in ("pts", "ks"):
                frozen.setdefault(f"{tour}|{sl}_Q|{b}", frozen.get(f"{tour}|{sl}_M|pts", 0.0))
                frozen.setdefault(f"{tour}|{sl}_M|{b}", frozen.get(f"{tour}|{sl}_M|pts", 0.0))
        for d in ("M", "Q"):
            frozen.setdefault(f"{tour}|tour_{d}|ks", frozen.get(f"{tour}|tour_{d}|pts", frozen.get("atp|tour_M|pts")))
            frozen.setdefault(f"{tour}|tour_{d}|pts", frozen.get(f"atp|tour_{d}|pts", 0.0))
    res["frozen_offsets_le2023"] = frozen
    EC.log("frame windows under three centrings (2014-2026)")
    ft = COV.frame_targets()
    ft = ft[ft["season"] >= 2014]
    sides = windows(ft, p, snap, frozen)
    ok = sides[sides["x_raw"].notna()].copy()
    ok["period"] = np.select([ok["season"] <= 2021, ok["season"] <= 2024], ["2014-21", "2022-24"], "2025-26")
    ok["slam"] = ok["level"].eq("GS")
    rows = []
    for (tour, per, sl), g in ok.groupby(["tour", "period", "slam"]):
        c = g[["x_raw", "x_frozen", "x_asof"]].corr()
        rows.append({"tour": tour, "period": per, "slam": bool(sl), "sides": int(len(g)),
                     "sd_raw": round(float(g["x_raw"].std()), 3), "sd_frozen": round(float(g["x_frozen"].std()), 3),
                     "sd_asof": round(float(g["x_asof"].std()), 3),
                     "mean_raw": round(float(g["x_raw"].mean()), 3), "mean_asof": round(float(g["x_asof"].mean()), 3),
                     "corr_raw_asof": round(float(c.loc["x_raw", "x_asof"]), 3),
                     "corr_frozen_asof": round(float(c.loc["x_frozen", "x_asof"]), 3),
                     "share_abs_raw_minus_asof_gt3": round(float(((g["x_raw"] - g["x_asof"]).abs() > 3).mean()), 3),
                     "share_abs_frozen_minus_asof_gt3": round(float(((g["x_frozen"] - g["x_asof"]).abs() > 3)
                                                                .mean()), 3),
                     "share_with_unreleased_edition_in_14d": round(float((g["unreleased_editions_in_14d"] > 0)
                                                                         .mean()), 3)})
    res["centring_comparison_frame_sides"] = rows
    # the match feature: A - B where both sides have both windows
    a = ok[ok["side"].eq("A")].set_index("match_id")
    b = ok[ok["side"].eq("B")].set_index("match_id")
    mm = a[["tour", "period", "slam"]].join((a[["x_raw", "x_frozen", "x_asof"]] - b[["x_raw", "x_frozen", "x_asof"]]),
                                            how="inner")
    mrows = []
    for (tour, per, sl), g in mm.groupby(["tour", "period", "slam"]):
        c = g[["x_raw", "x_frozen", "x_asof"]].corr()
        mrows.append({"tour": tour, "period": per, "slam": bool(sl), "matches": int(len(g)),
                      "sd_raw": round(float(g["x_raw"].std()), 3), "sd_asof": round(float(g["x_asof"].std()), 3),
                      "corr_raw_asof": round(float(c.loc["x_raw", "x_asof"]), 3),
                      "corr_frozen_asof": round(float(c.loc["x_frozen", "x_asof"]), 3),
                      "share_abs_raw_minus_asof_gt3": round(float(((g["x_raw"] - g["x_asof"]).abs() > 3).mean()), 3)})
    res["centring_comparison_frame_matches_AminusB"] = mrows
    EC.log(pd.DataFrame(mrows).to_string(index=False))
    res["seconds"] = round(time.time() - t0, 1)
    res["snapshots_fitted"] = {k: len(v.cache) for k, v in snap.items()}
    (EC.OUT / "engineer_asof.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    EC.log(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
