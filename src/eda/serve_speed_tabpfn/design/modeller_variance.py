"""Design scratch (agent 2): variance decomposition of first-serve speed, seasons <= 2023 only, by tour.

Reads speeds and clock days only (no match result). Point means (`pm_first` panel) unless stated.

Pieces, all in km/h^2 unless stated:
  1. per-serve noise s2: pooled within-match variance of single first serves in (spd1_sq), by tour and source
  2. two-way fixed effects y = a[player, season] + e[edition] + r (alternating means):
       - system offsets o[system] = n-weighted mean of e over the system's editions (within player-season contrasts, so
         no composition bias), and the spread of editions within a system (sampling variance removed)
       - day variance: var(r) - mean(s2/n) (match-to-match variation within player-season, net of edition)
  3. variogram within player and system on edition-corrected speeds: 0.5 (y_i - y_j)^2 minus the two matches' serve
     sampling variances, by lag bin; same event and different event apart; fitted by
        gamma(h) = nu + sf2 (1 - exp(-h ln2 / hl)) + q h      (different-event pairs add the edition variance)
  4. between-player spread of levels (player-season effects) and the year-to-year change of a player's level
  5. within-match shared component: correlation of the two players' residuals r in the same match
  6. x_raw anatomy (14-day minus 364-day, the registered statistic, side level): its variance, the predicted noise,
     and the persistence slope of the target match's own speed deviation on x_raw (the "signal share")

Run: ./python.sh src/eda/serve_speed_tabpfn/design/modeller_variance.py
Writes data/studies/serve_speed_tabpfn/design/modeller_variance.json and modeller_variogram.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.design import modeller_common as M  # noqa: E402

LAST = 2023
BINS = [0, 4, 8, 15, 29, 57, 113, 225, 365, 730, 1460, 4000]


def serve_noise(p: pd.DataFrame) -> dict:
    s = p[(p["basis"] == "pm") & p["pm_var"].notna()]
    out = {}
    for (t, src), d in s.groupby(["tour", "pm_src"]):
        out[f"{t}|{src}"] = {"rows": int(len(d)), "serve_sd": float(np.sqrt(((d["pm_n"] - 1) * d["pm_var"]).sum()
                                                                             / (d["pm_n"] - 1).sum())),
                             "mean_n": float(d["pm_n"].mean())}
    for t, d in s.groupby("tour"):
        out[f"{t}|all"] = {"rows": int(len(d)), "serve_sd": float(np.sqrt(((d["pm_n"] - 1) * d["pm_var"]).sum()
                                                                           / (d["pm_n"] - 1).sum()))}
        # player heterogeneity of the per-serve SD (players with >= 10 timed matches)
        g = d.groupby("player_id").apply(lambda x: pd.Series({"m": len(x), "sd": np.sqrt(((x["pm_n"] - 1) * x["pm_var"]).sum()
                                                                                         / (x["pm_n"] - 1).sum())}),
                                         include_groups=False)
        g = g[g["m"] >= 10]
        out[f"{t}|player_sd_quantiles"] = {q: float(g["sd"].quantile(q)) for q in (0.1, 0.25, 0.5, 0.75, 0.9)}
    return out


def two_way(p: pd.DataFrame, iters: int = 60) -> tuple[pd.DataFrame, dict]:
    """y = a[player, season] + e[edition] + r by alternating means; offsets and spreads per system."""
    d = p.copy()
    d["ps"] = d["player_id"] + "|" + d["year"].astype(str)
    # identifiable part: player-seasons with >= 2 editions
    k = d.groupby("ps")["tournament_id"].nunique()
    d = d[d["ps"].map(k) >= 2].copy()
    e = pd.Series(0.0, index=d["tournament_id"].unique())
    for _ in range(iters):
        a = (d["y"] - d["tournament_id"].map(e)).groupby(d["ps"]).mean()
        e = (d["y"] - d["ps"].map(a)).groupby(d["tournament_id"]).mean()
    d["a"] = d["ps"].map(a)
    d["e"] = d["tournament_id"].map(e)
    d["r"] = d["y"] - d["a"] - d["e"]
    return d, {}


def summarise_two_way(d: pd.DataFrame, s2: dict) -> dict:
    out = {}
    for t, g in d.groupby("tour"):
        ref = "pm_tour" if t == "atp" else "AO"
        ed = g.groupby(["system", "tournament_id"]).agg(e=("e", "first"), n=("e", "size"), year=("year", "first"))
        # sampling variance of an edition effect ~ var(r) / n (ignores the player-effect estimation error)
        vr = float(g["r"].var())
        sysoff = ed.groupby(level=0).apply(lambda x: np.average(x["e"], weights=x["n"]))
        sysoff = sysoff - sysoff.get(ref, 0.0)
        within = {}
        for sname, x in ed.groupby(level=0):
            if len(x) < 4:
                continue
            dev = x["e"] - np.average(x["e"], weights=x["n"])
            within[sname] = {"editions": int(len(x)), "sd_raw": float(dev.std()),
                             "sd_net": float(np.sqrt(max(dev.var() - (vr / x["n"]).mean(), 0.0)))}
        # per-edition table for the Slams (the AO 2024 check)
        slam_ed = ed.reset_index()
        slam_ed = slam_ed[slam_ed["system"].isin(["AO", "RG", "W", "USO"])]
        slam_ed["e_rel"] = slam_ed["e"] - slam_ed["system"].map(
            ed.groupby(level=0).apply(lambda x: np.average(x["e"], weights=x["n"])))
        s2t = s2[f"{t}|all"]["serve_sd"] ** 2
        samp = float((s2t / g["n"]).mean())
        # degrees-of-freedom correction for the fitted effects: var(r) underestimates by the share of fitted params
        n_obs, n_par = len(g), g["ps"].nunique() + g["tournament_id"].nunique()
        vr_corr = vr * n_obs / max(n_obs - n_par, 1)
        out[t] = {"rows": int(n_obs), "player_seasons": int(g["ps"].nunique()), "editions": int(g["tournament_id"].nunique()),
                  "system_offsets_vs_" + ref: {k: round(float(v), 2) for k, v in sysoff.items()},
                  "edition_sd_within_system": within,
                  "slam_edition_rel_offsets": {f"{r.system}{r.year}": round(float(r.e_rel), 2)
                                               for r in slam_ed.itertuples() if r.year >= 2019},
                  "resid_var_raw": vr, "resid_var_dfcorr": vr_corr, "serve_sampling_var_mean": samp,
                  "day_var_net": vr_corr - samp, "day_sd_net": float(np.sqrt(max(vr_corr - samp, 0.0)))}
    return out


def variogram(d: pd.DataFrame, s2: dict) -> pd.DataFrame:
    """Pairs within player and system on edition-corrected speeds (y - e), noise-corrected semivariance by lag."""
    rows = []
    for (t, sysn), g in d.groupby(["tour", "system"]):
        s2t = s2[f"{t}|all"]["serve_sd"] ** 2
        g = g[["player_id", "obs", "tournament_id", "y", "e", "n"]].copy()
        g["z"] = g["y"] - g["e"]
        g["k"] = np.arange(len(g))
        x = g.merge(g, on="player_id", suffixes=("_i", "_j"))
        x = x[x["k_i"] < x["k_j"]]
        x["h"] = (x["obs_j"] - x["obs_i"]).abs()
        x["same_event"] = x["tournament_id_i"] == x["tournament_id_j"]
        x["g_raw"] = 0.5 * (x["y_i"] - x["y_j"]) ** 2
        x["g_cor"] = 0.5 * (x["z_i"] - x["z_j"]) ** 2
        x["noise"] = 0.5 * (s2t / x["n_i"] + s2t / x["n_j"])
        x["bin"] = pd.cut(x["h"], BINS, right=False)
        a = x.groupby(["bin", "same_event"], observed=True).agg(
            pairs=("h", "size"), players=("player_id", "nunique"), h=("h", "mean"), g_raw=("g_raw", "mean"),
            g_cor=("g_cor", "mean"), noise=("noise", "mean")).reset_index()
        a["tour"], a["system"] = t, sysn
        rows.append(a)
    v = pd.concat(rows, ignore_index=True)
    v["g_raw_net"] = v["g_raw"] - v["noise"]
    v["g_cor_net"] = v["g_cor"] - v["noise"]
    return v


def pooled_variogram(v: pd.DataFrame) -> pd.DataFrame:
    w = v[v["pairs"] >= 30].copy()
    agg = w.groupby(["tour", "same_event", "bin"], observed=True).apply(
        lambda x: pd.Series({"pairs": x["pairs"].sum(), "h": np.average(x["h"], weights=x["pairs"]),
                             "g_raw_net": np.average(x["g_raw_net"], weights=x["pairs"]),
                             "g_cor_net": np.average(x["g_cor_net"], weights=x["pairs"])}), include_groups=False)
    return agg.reset_index()


def fit_variogram(pv: pd.DataFrame, col: str) -> dict:
    """Weighted least squares of gamma(h) = nu + ed*[different event] + sf2 (1 - 2^(-h/hl)) + q h on the pooled bins."""
    from scipy.optimize import least_squares
    out = {}
    for t, g in pv.groupby("tour"):
        h, y, w = g["h"].to_numpy(), g[col].to_numpy(), np.sqrt(g["pairs"].to_numpy())
        diff = (~g["same_event"].astype(bool)).to_numpy().astype(float)

        def res(th):
            nu, ed, sf2, hl, q = th
            return w * (nu + ed * diff + sf2 * (1 - 2 ** (-h / hl)) + q * h - y)

        best = None
        for hl0 in (7, 21, 60, 180):
            r = least_squares(res, x0=[4.0, 1.0, 4.0, hl0, 0.001], bounds=([0, 0, 0, 1, 0], [100, 50, 100, 2000, 1]))
            if best is None or r.cost < best.cost:
                best = r
        nu, ed, sf2, hl, q = best.x
        out[t] = {"nugget_day_var": nu, "edition_var": ed, "fast_state_var": sf2, "fast_half_life_days": hl,
                  "drift_var_per_year": q * 365.0, "bins": int(len(g))}
    return out


def levels(d: pd.DataFrame, s2: dict) -> dict:
    out = {}
    for t, g in d.groupby("tour"):
        ps = g.groupby(["player_id", "year"]).agg(a=("a", "first"), m=("a", "size"))
        vr = float(g["r"].var())
        # between-player spread of season levels, net of the level's sampling variance (resid var / matches)
        by_year = []
        for y, x in ps.groupby(level=1):
            if len(x) >= 30:
                by_year.append(max(x["a"].var() - (vr / x["m"]).mean(), 0.0))
        tau2 = float(np.mean(by_year)) if by_year else float("nan")
        # year-to-year change of the same player's level
        p2 = ps.reset_index()
        nxt = p2.merge(p2.assign(year=p2["year"] - 1), on=["player_id", "year"], suffixes=("", "_next"))
        ch = nxt["a_next"] - nxt["a"]
        ch_var_net = float(ch.var() - (vr / nxt["m"] + vr / nxt["m_next"]).mean())
        out[t] = {"between_player_sd": float(np.sqrt(tau2)), "player_seasons": int(len(ps)),
                  "yoy_pairs": int(len(nxt)), "yoy_change_sd_raw": float(ch.std()),
                  "yoy_change_sd_net": float(np.sqrt(max(ch_var_net, 0.0)))}
    return out


def height_link(d: pd.DataFrame) -> dict:
    mp = pd.read_parquet(M.PD.MATCH_PLAYERS, columns=["player_id", "height"])
    h = mp[(mp["height"] >= 150) & (mp["height"] <= 215)].groupby("player_id")["height"].median()
    out = {}
    for t, g in d.groupby("tour"):
        lv = g.groupby("player_id").agg(a=("a", "mean"), m=("a", "size"))
        lv = lv[lv["m"] >= 5].join(h, how="inner")
        if len(lv) > 30:
            r = float(np.corrcoef(lv["a"], lv["height"])[0, 1])
            out[t] = {"players": int(len(lv)), "corr_level_height": r, "r2": r * r,
                      "kmh_per_cm": float(np.polyfit(lv["height"], lv["a"], 1)[0])}
    return out


def within_match(d: pd.DataFrame) -> dict:
    out = {}
    w = d.pivot_table(index="match_id", columns="side", values="r", aggfunc="first").dropna()
    tour = d.drop_duplicates("match_id").set_index("match_id")["tour"]
    for t in ("atp", "wta"):
        x = w[w.index.map(tour) == t]
        if len(x) > 50:
            out[t] = {"matches": int(len(x)), "corr_resid_A_B": float(np.corrcoef(x["A"], x["B"])[0, 1])}
    return out


def x_raw_anatomy(p: pd.DataFrame, s2: dict, off: dict) -> dict:
    """The registered side statistic for every timed player-match <= 2023 (earlier events + earlier rounds; obs within
    14 / 364 days), raw and system-centred, and the persistence of the target match's own speed deviation on it."""
    out = {}
    for t, g in p.groupby("tour"):
        g = g.sort_values(["player_id", "tdate", "tournament_id", "round_order"]).reset_index(drop=True)
        cen = g["y"] - g["system"].map(off.get(t, {})).fillna(0.0)
        res = []
        for pid, idx in g.groupby("player_id").indices.items():
            td, tid, ro, ob = (g["tdate"].to_numpy()[idx], g["tournament_id"].to_numpy()[idx],
                               g["round_order"].to_numpy()[idx], g["obs"].to_numpy()[idx])
            yv, nv, cv = g["y"].to_numpy()[idx], g["n"].to_numpy()[idx], cen.to_numpy()[idx]
            for k in range(len(idx)):
                earlier = (td < td[k]) | ((tid == tid[k]) & (ro < ro[k]))
                age = ob[k] - ob
                w52 = earlier & (age <= 364)
                if not w52.any():
                    continue
                w2 = earlier & (age <= 14)
                if not w2.any():
                    res.append((idx[k], np.nan, np.nan, 0, 0.0, (yv[w52] * nv[w52]).sum() / nv[w52].sum(),
                                (cv[w52] * nv[w52]).sum() / nv[w52].sum(), nv[w52].sum()))
                    continue
                m2 = (yv[w2] * nv[w2]).sum() / nv[w2].sum()
                m52 = (yv[w52] * nv[w52]).sum() / nv[w52].sum()
                c2 = (cv[w2] * nv[w2]).sum() / nv[w2].sum()
                c52 = (cv[w52] * nv[w52]).sum() / nv[w52].sum()
                res.append((idx[k], m2 - m52, c2 - c52, int(w2.sum()), nv[w2].sum(), m52, c52, nv[w52].sum()))
        r = pd.DataFrame(res, columns=["i", "x_raw", "x_cen", "k2", "n2", "m52", "c52", "n52"]).set_index("i")
        g = g.join(r, how="inner")
        g["dev_raw"] = g["y"] - g["m52"]
        g["dev_cen"] = (g["y"] - g["system"].map(off.get(t, {})).fillna(0.0)) - g["c52"]
        h = g[g["x_raw"].notna()]
        s2t = s2[f"{t}|all"]["serve_sd"] ** 2

        def slope(x, y):
            c = np.cov(x, y)
            return float(c[0, 1] / c[0, 0])

        o = {"targets_with_m52": int(len(g)), "with_x_raw": int(len(h)),
             "x_raw_sd": float(h["x_raw"].std()), "x_cen_sd": float(h["x_cen"].std()),
             "slope_dev_on_x_raw": slope(h["x_raw"], h["dev_raw"]),
             "slope_devcen_on_x_cen": slope(h["x_cen"], h["dev_cen"]),
             "corr_dev_x_raw": float(np.corrcoef(h["x_raw"], h["dev_raw"])[0, 1]),
             "corr_devcen_x_cen": float(np.corrcoef(h["x_cen"], h["dev_cen"])[0, 1]),
             "serve_sampling_var_of_m2_mean": float((s2t / h["n2"]).mean()),
             "by_k2": {}}
        for k2, x in h.groupby(np.minimum(h["k2"], 3)):
            o["by_k2"][int(k2)] = {"rows": int(len(x)), "x_cen_sd": float(x["x_cen"].std()),
                                   "slope": slope(x["x_cen"], x["dev_cen"]),
                                   "corr": float(np.corrcoef(x["x_cen"], x["dev_cen"])[0, 1])}
        # same-system-only windows: is the false drop at Slams visible? slope by target family
        o["by_target_family"] = {f: {"rows": int(len(x)), "slope_cen": slope(x["x_cen"], x["dev_cen"]),
                                     "slope_raw": slope(x["x_raw"], x["dev_raw"]),
                                     "mean_x_raw": float(x["x_raw"].mean()), "mean_x_cen": float(x["x_cen"].mean())}
                                 for f, x in h.groupby(h["family"].where(h["family"].eq("tour"), "slam"))}
        out[t] = o
    return out


def paired_offsets(p: pd.DataFrame, ref: str, window: int = 60) -> dict:
    """Within-player system offsets: each player-edition at a Slam family against the same player's matches in the
    reference system within +-window days (point means weighted by serves). Mean, median, SE over player-editions,
    overall and per edition year."""
    out = {}
    tour = p[p["system"] == ref]
    tg = {pid: g for pid, g in tour.groupby("player_id")}
    for fam in ("AO", "RG", "W", "USO"):
        rows = []
        for (pid, tid), g in p[p["system"] == fam].groupby(["player_id", "tournament_id"]):
            t = tg.get(pid)
            if t is None:
                continue
            t = t[(t["obs"] - g["obs"].mean()).abs() <= window]
            if len(t) >= 2:
                rows.append((int(g["year"].iloc[0]), np.average(g["y"], weights=g["n"]) - np.average(t["y"], weights=t["n"])))
        if not rows:
            continue
        d = pd.DataFrame(rows, columns=["year", "d"])
        out[fam] = {"player_editions": int(len(d)), "mean": float(d["d"].mean()), "median": float(d["d"].median()),
                    "se": float(d["d"].std() / np.sqrt(len(d))),
                    "by_year": {int(y): [int(len(x)), round(float(x["d"].mean()), 2)] for y, x in d.groupby("year")}}
    return out


def tour_variogram(p: pd.DataFrame, system: str, s2: float, ks_extra: float = 0.0) -> tuple[pd.DataFrame, dict]:
    """Variogram within player inside one tour-level system (no cross-system offsets), edition-corrected by the
    edition's mean deviation from players' own system means (all players, diagnostics only), with a robust
    (Cressie-Hawkins) version for heavy-tailed bases. Fit: gamma_same = nu + sf2 (1 - 2^(-h/hl)) + q h;
    gamma_diff = gamma_same + g2 (event-specific player effect + leftover edition)."""
    from scipy.optimize import least_squares
    g = p[p["system"] == system][["player_id", "obs", "tournament_id", "y", "n", "year"]].copy()
    g["dev"] = g["y"] - g.groupby("player_id")["y"].transform("mean")
    ed = g.groupby("tournament_id")["dev"].mean()
    g["z"] = g["y"] - g["tournament_id"].map(ed)
    g["k"] = np.arange(len(g))
    x = g.merge(g, on="player_id", suffixes=("_i", "_j"))
    x = x[x["k_i"] < x["k_j"]]
    x["h"] = (x["obs_j"] - x["obs_i"]).abs()
    x["same_event"] = x["tournament_id_i"] == x["tournament_id_j"]
    x["dz"] = x["z_i"] - x["z_j"]
    x["dy"] = x["y_i"] - x["y_j"]
    x["noise"] = 0.5 * (s2 / x["n_i"] + s2 / x["n_j"]) + ks_extra
    x["bin"] = pd.cut(x["h"], BINS, right=False)

    def ch(v):
        a = np.abs(v.to_numpy()) ** 0.5
        nn = len(a)
        return 0.5 * a.mean() ** 4 / (0.457 + 0.494 / nn)

    a = x.groupby(["bin", "same_event"], observed=True).agg(
        pairs=("h", "size"), h=("h", "mean"), g_raw=("dy", lambda v: 0.5 * (v ** 2).mean()),
        g_cor=("dz", lambda v: 0.5 * (v ** 2).mean()), g_cor_rob=("dz", ch), noise=("noise", "mean")).reset_index()
    for c in ("g_raw", "g_cor", "g_cor_rob"):
        a[c + "_net"] = a[c] - a["noise"]
    a["system"] = system
    fits = {}
    for col in ("g_cor_net", "g_cor_rob_net", "g_raw_net"):
        w_ = a[a["pairs"] >= 30]
        h, y, wt = w_["h"].to_numpy(), w_[col].to_numpy(), np.sqrt(w_["pairs"].to_numpy())
        diff = (~w_["same_event"].astype(bool)).to_numpy().astype(float)

        def res(th):
            nu, g2, sf2, hl, q = th
            return wt * (nu + g2 * diff + sf2 * (1 - 2 ** (-h / hl)) + q * h - y)

        best = None
        for hl0 in (14, 45, 120, 365):
            r = least_squares(res, x0=[8.0, 5.0, 5.0, hl0, 0.001], bounds=([0, 0, 0, 3, 0], [100, 60, 100, 3000, 1]))
            if best is None or r.cost < best.cost:
                best = r
        nu, g2, sf2, hl, q = best.x
        fits[col] = {"nugget_day_var": nu, "event_specific_var": g2, "slow_state_var": sf2,
                     "slow_half_life_days": hl, "drift_var_per_year": q * 365.0}
    return a, fits


def main() -> None:
    M.log("panel (point means first), seasons <= 2023")
    p = M.panel("pm_first")
    p = p[p["year"] <= LAST].copy()
    s2 = serve_noise(p)
    M.log(f"serve noise: { {k: round(v['serve_sd'], 2) for k, v in s2.items() if 'serve_sd' in v} }")
    d, _ = two_way(p)
    tw = summarise_two_way(d, s2)
    M.log("two-way done")
    v = variogram(d, s2)
    pv = pooled_variogram(v)
    pv.to_csv(M.OUT / "modeller_variogram.csv", index=False)
    vg_cor = fit_variogram(pv, "g_cor_net")
    vg_raw = fit_variogram(pv, "g_raw_net")
    M.log(f"variogram fit (edition-corrected): {vg_cor}")
    lv = levels(d, s2)
    hl = height_link(d)
    wm = within_match(d)
    # offsets for centring: within-player paired (+-60 days) against the tour system (men); women have no tour system
    pk = M.panel("ks_first")
    pk = pk[pk["year"] <= LAST].copy()
    po_pm = paired_offsets(p[p["tour"] == "atp"], "pm_tour")
    po_ks = paired_offsets(pk[pk["tour"] == "atp"], "ks_tour")
    M.log(f"paired offsets vs pm_tour: { {k: round(v['mean'], 2) for k, v in po_pm.items()} }")
    off = {"atp": {k: v["mean"] for k, v in po_pm.items()} | {"pm_tour": 0.0}, "wta": {}}
    xa = x_raw_anatomy(p, s2, off)
    s2m = s2["atp|all"]["serve_sd"] ** 2
    vt_pm, fit_pm = tour_variogram(p[p["tour"] == "atp"], "pm_tour", s2m)
    vt_ks, fit_ks = tour_variogram(pk[pk["tour"] == "atp"], "ks_tour", s2m, ks_extra=1 / 12)
    pd.concat([vt_pm, vt_ks]).to_csv(M.OUT / "modeller_variogram_tour.csv", index=False)
    M.log(f"tour variogram fits: pm {fit_pm}; ks {fit_ks}")
    res = {"seasons": f"<= {LAST}", "panel": "pm_first", "serve_noise": s2, "two_way": tw,
           "variogram_fit_edition_corrected": vg_cor, "variogram_fit_raw": vg_raw, "levels": lv, "height": hl,
           "within_match": wm, "paired_offsets_vs_pm_tour": po_pm, "paired_offsets_vs_ks_tour": po_ks,
           "tour_variogram_fit_pm": fit_pm, "tour_variogram_fit_ks": fit_ks, "x_raw_anatomy": xa}
    (M.OUT / "modeller_variance.json").write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=float)[:6000])
    print(pv.to_string())


if __name__ == "__main__":
    main()
