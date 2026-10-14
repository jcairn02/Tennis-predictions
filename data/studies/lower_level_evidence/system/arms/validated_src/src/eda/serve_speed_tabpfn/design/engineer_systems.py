"""Design R1 (speed-data engineer), step 5: measuring-system and edition effects on player-match first-serve speeds, by a
result-free decomposition. Values only; reads no match result.

Model (weighted least squares, alternating projections):
    y_i = alpha_{tour, player, season} + gamma_{edition} + e_i
    y_i  harmonised player-match mean of first serves in (engineer_panel0: key statistics - 0.5, AO match centre + 0.5)
    edition = (tour, tournament_id, main draw | qualifying, basis group: point mean | ATP key statistic)
    weight  = 1 / (tau^2 + s^2 / n), s = the within-match sd of first-serve speeds, tau^2 = the match-to-match variance
              beyond sampling (both estimated from the first pass)
Player-seasons with a single timed match carry no information on gamma and are dropped. Within each tour and season the
gammas are identified up to a constant; each season is normalised so that its Slam main draws average 0 (weighted by
their player-matches). Offsets of families are weighted means of their editions' gammas, reported as differences from
the tour-level Infosys point-mean family where it exists.

Fits: (a) seasons <= 2021, (b) seasons <= 2023 (candidates for freezing), (c) all seasons 2011-2026 (description only:
2024-2026 values and distributions, never frozen).

Run: ./python.sh src/eda/serve_speed_tabpfn/design/engineer_systems.py
Writes data/studies/serve_speed_tabpfn/design/engineer_systems.json and engineer_editions.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402

PANEL0 = EC.OUT / "engineer_panel0.parquet"
S_SERVE = 12.4          # median within-match sd of first serves in (engineer_basis.json), km/h


def prepare(p: pd.DataFrame) -> pd.DataFrame:
    p = p[~p["implausible"]].copy()
    p["event"] = np.where(p["slam"].ne(""), p["slam"], p["tournament_id"].str.split("-", n=1).str[1])
    p["draw"] = np.where(p["qualifying"].astype(bool), "Q", "M")
    p["bgroup"] = np.where(p["basis"].eq("keystat_atp"), "ks", "pts")
    p["edition"] = p["tour"] + "|" + p["tournament_id"] + "|" + p["draw"] + "|" + p["bgroup"]
    p["ps"] = p["tour"] + "|" + p["player_id"].astype(str) + "|" + p["year"].astype(str)
    p["family"] = np.where(p["slam"].ne(""), p["slam"], "tour_" + p["bgroup"])
    return p


def fit(d: pd.DataFrame, tau2: float | None = None, iters: int = 500, tol: float = 1e-6) -> tuple[pd.DataFrame, dict]:
    d = d.copy()
    # drop single-match player-seasons (repeat: dropping can create new singletons only through editions, not here)
    d = d[d.groupby("ps")["ps"].transform("size") > 1]
    n = d["n1"].clip(lower=1).to_numpy(float)
    w = n.copy() if tau2 is None else 1.0 / (tau2 + S_SERVE ** 2 / n)
    y = d["spd1"].to_numpy(float)
    ps_c, ps_u = pd.factorize(d["ps"])
    ed_c, ed_u = pd.factorize(d["edition"])
    wsum_ps = np.bincount(ps_c, weights=w)
    wsum_ed = np.bincount(ed_c, weights=w)
    g = np.zeros(len(ed_u))
    a = np.bincount(ps_c, weights=w * y) / wsum_ps
    for it in range(iters):
        a = np.bincount(ps_c, weights=w * (y - g[ed_c])) / wsum_ps
        g_new = np.bincount(ed_c, weights=w * (y - a[ps_c])) / wsum_ed
        # keep the per-(tour, season) level in alpha: normalise below, after convergence
        delta = np.max(np.abs(g_new - g))
        g = g_new
        if delta < tol:
            break
    resid = y - a[ps_c] - g[ed_c]
    d["resid"], d["w"] = resid, w
    ed = pd.DataFrame({"edition": ed_u, "gamma": g, "wsum": wsum_ed})
    meta = d.drop_duplicates("edition").set_index("edition")[["tour", "year", "event", "draw", "bgroup", "family",
                                                              "slam", "tournament_id", "tournament_name", "surface",
                                                              "indoor", "level"]]
    ed = ed.join(meta, on="edition")
    ed["player_matches"] = ed["edition"].map(d.groupby("edition").size())
    # normalise: within each tour x season, the Slam main-draw editions average 0 (weighted by player-matches)
    ref = ed[ed["slam"].ne("") & ed["draw"].eq("M")]
    c = ref.groupby(["tour", "year"]).apply(lambda x: np.average(x["gamma"], weights=x["player_matches"]))
    ed["gamma"] = ed["gamma"] - ed.set_index(["tour", "year"]).index.map(c).to_numpy(float)
    # approximate standard errors: residual variance per weight, plus the player-season means' noise
    phi = float(np.sum(w * resid ** 2) / max(len(y) - len(ps_u) - len(ed_u), 1))
    var_a = phi / wsum_ps
    num = np.bincount(ed_c, weights=w ** 2 * (phi / w + var_a[ps_c]))
    ed["se"] = np.sqrt(num / wsum_ed ** 2)
    info = {"iterations": it + 1, "player_matches": int(len(y)), "player_seasons": int(len(ps_u)),
            "editions": int(len(ed_u)), "dispersion_phi": round(phi, 4)}
    return ed, info, d


def tau2_from(d: pd.DataFrame) -> float:
    """Match-to-match variance beyond sampling: mean(resid^2) - s^2 mean(1/n), with a degrees-of-freedom inflation."""
    k = d.groupby("ps")["ps"].transform("size").to_numpy(float)
    r2 = d["resid"].to_numpy() ** 2 * k / (k - 1)          # each player-season mean uses up one degree of freedom
    return float(max(np.mean(r2) - S_SERVE ** 2 * np.mean(1.0 / d["n1"].clip(lower=1)), 1.0))


def family_table(ed: pd.DataFrame) -> list[dict]:
    rows = []
    for (tour, fam, draw), g in ed.groupby(["tour", "family", "draw"]):
        rows.append({"tour": tour, "family": fam, "draw": draw, "editions": int(len(g)),
                     "player_matches": int(g["player_matches"].sum()),
                     "offset_vs_slam_mean": round(float(np.average(g["gamma"], weights=g["player_matches"])), 3),
                     "edition_sd": round(float(g["gamma"].std()), 3) if len(g) > 1 else None,
                     "median_se": round(float(g["se"].median()), 3)})
    t = pd.DataFrame(rows)
    for tour in t["tour"].unique():
        base = t[(t["tour"] == tour) & (t["family"] == "tour_pts") & (t["draw"] == "M")]
        if len(base):
            t.loc[t["tour"] == tour, "offset_vs_tour_pts_main"] = (t.loc[t["tour"] == tour, "offset_vs_slam_mean"]
                                                                   - float(base["offset_vs_slam_mean"].iloc[0])).round(3)
    return t.to_dict(orient="records")


def components(ed: pd.DataFrame) -> dict:
    """Tour-level main-draw point-mean editions (men): persistent event part vs year-specific part, net of noise."""
    t = ed[(ed["tour"] == "atp") & (ed["family"] == "tour_pts") & (ed["draw"] == "M") & (ed["player_matches"] >= 20)]
    if len(t) < 10:
        return {}
    tot = float(t["gamma"].var() - (t["se"] ** 2).mean())
    multi = t.groupby("event").filter(lambda x: len(x) >= 2)
    within = multi.groupby("event")["gamma"].apply(lambda x: ((x - x.mean()) ** 2).sum())
    dfw = multi.groupby("event").size() - 1
    v_year = float(within.sum() / dfw.sum() - (multi["se"] ** 2).mean())
    by_event = (t.groupby("event").agg(name=("tournament_name", "last"), years=("year", lambda x: sorted(set(x))),
                                       mean_gamma=("gamma", "mean"), sd_gamma=("gamma", "std"),
                                       indoor=("indoor", "last"), surface=("surface", "last"))
                .sort_values("mean_gamma").round(3))
    return {"editions": int(len(t)), "events": int(t["event"].nunique()),
            "sd_edition_effects_raw": round(float(t["gamma"].std()), 3),
            "mean_se": round(float(t["se"].mean()), 3),
            "var_total_net_of_noise": round(tot, 3), "var_year_specific_net": round(v_year, 3),
            "var_event_persistent_net": round(tot - v_year, 3),
            "sd_event_persistent": round(float(np.sqrt(max(tot - v_year, 0))), 3),
            "sd_year_specific": round(float(np.sqrt(max(v_year, 0))), 3),
            "by_indoor": t.groupby("indoor")["gamma"].agg(["size", "mean", "std"]).round(3).reset_index()
            .astype({"indoor": str}).to_dict(orient="records"),
            "by_surface": t.groupby("surface")["gamma"].agg(["size", "mean", "std"]).round(3).reset_index()
            .to_dict(orient="records"),
            "slowest_events": by_event.head(8).reset_index().to_dict(orient="records"),
            "fastest_events": by_event.tail(8).reset_index().to_dict(orient="records")}


def qual_vs_main(ed: pd.DataFrame) -> list[dict]:
    k = ed.pivot_table(index=["tour", "tournament_id", "bgroup", "family", "year"], columns="draw", values="gamma")
    k = k.dropna(subset=["M", "Q"]) if {"M", "Q"} <= set(k.columns) else k.iloc[0:0]
    k["q_minus_m"] = k["Q"] - k["M"]
    return (k.reset_index().groupby(["tour", "family", "bgroup"])["q_minus_m"].agg(["size", "mean", "median", "std"])
            .round(3).reset_index().to_dict(orient="records"))


def run(p: pd.DataFrame, last: int, label: str) -> dict:
    d = p[p["year"] <= last]
    ed0, _, d0 = fit(d)
    tau2 = tau2_from(d0)
    ed, info, d1 = fit(d, tau2=tau2)
    info["tau2"] = round(tau2, 3)
    info["tau"] = round(float(np.sqrt(tau2)), 3)
    ed["fit"] = label
    out = {"info": info, "families": family_table(ed), "tour_components": components(ed),
           "qual_minus_main": qual_vs_main(ed)}
    slam = ed[ed["slam"].ne("") & ed["draw"].eq("M")].sort_values(["tour", "slam", "year"])
    out["slam_editions"] = slam[["tour", "slam", "year", "bgroup", "gamma", "se", "player_matches"]].round(3).to_dict(
        orient="records")
    # residual spread by n (noise model check)
    d1 = d1.assign(nb=pd.cut(d1["n1"], [0, 20, 30, 40, 60, 80, 400]))
    out["resid_sd_by_n"] = (d1.groupby("nb", observed=True)["resid"].agg(["size", "std"]).round(3).reset_index()
                            .astype({"nb": str}).to_dict(orient="records"))
    return out, ed


def main() -> None:
    p = prepare(pd.read_parquet(PANEL0))
    res = {"reads_results": False, "model": __doc__.split("Model")[1].split("Fits:")[0].strip()}
    eds = []
    for last, label in ((2021, "le2021"), (2023, "le2023"), (2026, "all_descriptive")):
        EC.log(f"fit {label}")
        out, ed = run(p, last, label)
        res[label] = out
        eds.append(ed)
        fam = pd.DataFrame(out["families"])
        EC.log(f"  {out['info']}\n{fam.to_string(index=False)}")
    pd.concat(eds).round(4).to_csv(EC.OUT / "engineer_editions.csv", index=False)
    (EC.OUT / "engineer_systems.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
