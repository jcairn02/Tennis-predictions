"""E1 mechanism gate, step 2: the registered estimates (data/studies/point_sequence/med_prereg.md).

Run:  ./python.sh src/eda/point_sequence/med_estimate.py [--perms 500]

Reads med_pairs.parquet (med_build.py). Writes med_results.json, med_results.csv and med_placebo.csv.

Families
    primary     {TREATED, INJURY} x {M1, M2}, Holm over the four discovery p-values; pass rule of prereg section 6
    controls    TOILET (negative control) and OPP_TREATED (mirror), among TREATED = 0 pairs
    placebo     TREATED permuted within season x result of t x minutes decile
    secondary   fade markers (FSI, DF, TEMPO) against M2(t+1) - M2(t-1), Holm over three
Directions: M1 = risk ratio, > 1 = exposed players retire / give walkovers more; M2 = shift in percentage points of
serve points won against the pre-match expectation, negative = exposed players serve worse.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import common as C  # noqa: E402
from src.eda.point_sequence import med_stats as S  # noqa: E402

OUT = C.OUT
T0 = time.time()
DAYS_BINS = [-0.01, 1.5, 2.5, 4.5, 7.5, 14.5, 21.01]
DAYS_LABELS = ["0-1", "2", "3-4", "5-7", "8-14", "15-21"]
SURF = ["Hard", "Clay", "Grass", "other"]
LEVELS = ["T250", "T1000F", "T500", "CH", "other"]
NEXT_LEVELS = ["T250", "T1000F", "T500", "CH", "GS", "ITF", "other"]


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# Data and covariates

def load() -> pd.DataFrame:
    p = pd.read_parquet(OUT / "med_pairs.parquet")
    p = p[p["logged"] & p["next_le21"] & ~p["next_holdout"]].copy()
    p["days_cat"] = pd.cut(p["gap"], DAYS_BINS, labels=DAYS_LABELS).astype(str)
    disc = p["window"].eq("discovery") & ~p["own_ret"]
    cuts = np.quantile(p.loc[disc, "minutes_t"], np.linspace(0, 1, 11)[1:-1])
    p["min_dec"] = np.searchsorted(cuts, p["minutes_t"].to_numpy(), side="right")
    pcuts = np.quantile(p.loc[disc, "n_pts"], np.linspace(0, 1, 11)[1:-1])
    p["pts_dec"] = np.searchsorted(pcuts, p["n_pts"].to_numpy(), side="right")
    med_age = float(p.loc[disc, "age_x"].median())
    p["age_missing"] = p["age_x"].isna().astype(float)
    p["age_c"] = (p["age_x"] - med_age).fillna(0.0)
    p["age_c2"] = p["age_c"] ** 2
    p["won_t"] = p["t_won"].astype(float)
    p["qual_t"] = p["qualifying"].astype("boolean").fillna(False).astype(float)
    p["surface_n"] = p["surface_n"].astype(str).where(p["surface_n"].astype(str).isin(SURF), "other")
    p["surface_t"] = p["surface_t"].astype(str).where(p["surface_t"].astype(str).isin(SURF), "other")
    nl = p["n_level"].astype(str).replace({"T1000": "T1000F", "FIN": "T1000F", "TEAM": "other"})
    p["next_level"] = nl.where(nl.isin(NEXT_LEVELS), "other")
    p["stratum_perm"] = p["season"].astype(int).astype(str) + "|" + p["won_t"].astype(int).astype(str) + "|" + \
        p["min_dec"].astype(str)
    p.attrs["minutes_cuts"] = cuts.tolist()
    p.attrs["points_cuts"] = pcuts.tolist()
    p.attrs["age_median"] = med_age
    return p


PS_NUM = ["age_c", "age_c2", "age_missing", "qual_t", "won_t", "p_serve", "opp_p_serve"]
PS_CAT = {"level_group": LEVELS, "surface_t": SURF, "min_dec": list(range(10))}


def add_ps(d: pd.DataFrame, x: str) -> tuple[pd.DataFrame, dict]:
    """Propensity of exposure x fitted on the discovery rows of its contrast; quintile cuts from discovery."""
    d = d.copy()
    X, names = S.design(d, PS_NUM, PS_CAT, drop_empty=False)
    disc = d["window"].eq("discovery").to_numpy()
    keep = X[disc].std(axis=0) > 0
    keep[0] = True
    beta = S.logit_fit(d.loc[disc, x].astype(float).to_numpy(), X[disc][:, keep])
    d["ps"] = S.logit_predict(beta, X[:, keep])
    cuts = np.quantile(d.loc[disc, "ps"], [0.2, 0.4, 0.6, 0.8])
    d["ps_q"] = np.searchsorted(cuts, d["ps"].to_numpy(), side="right")
    info = {"fit_rows": int(disc.sum()), "exposed_fit_rows": int(d.loc[disc, x].sum()),
            "ps_mean_exposed": float(d.loc[d[x].astype(bool), "ps"].mean()) if d[x].any() else None,
            "ps_mean_unexposed": float(d.loc[~d[x].astype(bool), "ps"].mean())}
    return d, info


def outcome_design(d: pd.DataFrame, x: str, minutes: str = "min_dec", extra_cat: dict | None = None):
    cat = {minutes: list(range(10)), "days_cat": DAYS_LABELS, "surface_n": SURF, "ps_q": list(range(5))}
    if extra_cat:
        cat.update(extra_cat)
    return S.design(d, ["age_c", "age_c2", "age_missing", "won_t"], cat, first=[x])


def fit_cell(d: pd.DataFrame, x: str, endpoint: str, **kw) -> dict:
    """One registered estimate: M1 (modified Poisson, RR) or M2 (WLS, pp), player-clustered."""
    if endpoint == "M1":
        d = d[d["m1"].notna()]
        n1 = int(d[x].sum())
        ev1 = int(d.loc[d[x].astype(bool), "m1"].sum())
        ev0 = int(d.loc[~d[x].astype(bool), "m1"].sum())
        base = {"n": int(len(d)), "n_exposed": n1, "events_exposed": ev1, "events_unexposed": ev0,
                "rate_exposed": ev1 / n1 if n1 else None,
                "rate_unexposed": ev0 / (len(d) - n1) if len(d) > n1 else None,
                "players": int(d["player_id"].nunique())}
        if n1 == 0 or ev1 == 0:
            return {**base, "est": None, "lo": None, "hi": None, "p": 1.0, "note": "not estimable (D3)"}
        X, names = outcome_design(d, x, **kw)
        fit = S.poisson_fit(d["m1"].to_numpy(float), X, d["player_id"].to_numpy(object))
        out = S.coef_summary(fit, 1, log_scale=True)
        return {**base, **out, "converged": fit["converged"], "k": X.shape[1]}
    d = d[d["n_m2"].notna() & (d["n_svpt"] > 0)]
    n1 = int(d[x].sum())
    w = d["n_svpt"].to_numpy(float)
    xe = d[x].astype(bool).to_numpy()
    base = {"n": int(len(d)), "n_exposed": n1, "players": int(d["player_id"].nunique()),
            "crude_exposed": float(np.average(d.loc[xe, "n_m2"], weights=w[xe])) if n1 else None,
            "crude_unexposed": float(np.average(d.loc[~xe, "n_m2"], weights=w[~xe]))}
    if n1 < 2:
        return {**base, "est": None, "lo": None, "hi": None, "p": 1.0, "note": "not estimable"}
    X, names = outcome_design(d, x, **kw)
    fit = S.wls_fit(d["n_m2"].to_numpy(float), X, w, d["player_id"].to_numpy(object))
    return {**base, **S.coef_summary(fit, 1), "k": X.shape[1]}


def contrast_frame(p: pd.DataFrame, exposure: str, include_own_ret: bool = False) -> pd.DataFrame:
    d = p if include_own_ret else p[~p["own_ret"]]
    if exposure == "treated":
        return d
    if exposure == "injury":
        return d[d["injury"] | ~d["treated"]]
    if exposure in ("toilet", "opp_treated"):
        return d[~d["treated"]]
    raise ValueError(exposure)


def covers_null(r: dict, endpoint: str) -> bool | None:
    if r.get("lo") is None:
        return None
    null = 1.0 if endpoint == "M1" else 0.0
    return bool(r["lo"] <= null <= r["hi"])


# ------------------------------------------------------------------------------------------------
# Placebo

def placebo(d: pd.DataFrame, endpoint: str, perms: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    if endpoint == "M1":
        d = d[d["m1"].notna()]
    else:
        d = d[d["n_m2"].notna() & (d["n_svpt"] > 0)]
    X, names = outcome_design(d, "treated")
    y = (d["m1"] if endpoint == "M1" else d["n_m2"]).to_numpy(float)
    w = d["n_svpt"].to_numpy(float)
    cl = d["player_id"].to_numpy(object)
    x = d["treated"].astype(float).to_numpy()
    codes = pd.factorize(d["stratum_perm"])[0]
    by = np.argsort(codes, kind="stable")
    ests, ps = [], []
    for _ in range(perms):
        sh = np.lexsort((rng.random(len(codes)), codes))
        xp = np.empty_like(x)
        xp[by] = x[sh]
        X[:, 1] = xp
        if endpoint == "M1":
            fit = S.poisson_fit(y, X, cl)
            r = S.coef_summary(fit, 1, log_scale=True)
        else:
            fit = S.wls_fit(y, X, w, cl)
            r = S.coef_summary(fit, 1)
        ests.append(r["est"])
        ps.append(r["p"])
    return {"ests": np.array(ests), "ps": np.array(ps)}


# ------------------------------------------------------------------------------------------------
# Secondary family

def secondary(p: pd.DataFrame) -> tuple[list[dict], dict]:
    d = p[~p["own_ret"] & p["t_wta_seq"] & p["n_m2"].notna() & p["p_m2"].notna() & (p["n_svpt"] > 0)
          & (p["p_svpt"] > 0) & (p["prev_gap"] <= 21)].copy()
    d["dd"] = d["n_m2"] - d["p_m2"]
    d["w_dd"] = 1.0 / (1.0 / d["n_svpt"] + 1.0 / d["p_svpt"])
    cat = {"min_dec": list(range(10)), "days_cat": DAYS_LABELS, "surface_n": SURF}
    rows = []
    for marker in ("fsi", "dfault", "tempo"):
        z = f"fade_z_{marker}"
        for window in ("discovery", "replication"):
            g = d[(d["window"] == window) & d[z].notna()]
            for target, ycol, wcol in (("did", "dd", "w_dd"), ("forward", "n_m2", "n_svpt"),
                                       ("reverse", "p_m2", "p_svpt")):
                X, names = S.design(g, ["age_c", "age_c2", "age_missing", "won_t"], cat, first=[z])
                fit = S.wls_fit(g[ycol].to_numpy(float), X, g[wcol].to_numpy(float),
                                g["player_id"].to_numpy(object))
                rows.append({"family": "secondary", "exposure": marker, "endpoint": target, "window": window,
                             "n": int(len(g)), "players": int(g["player_id"].nunique()),
                             **S.coef_summary(fit, 1)})
    disc_p = [next(r["p"] for r in rows if r["exposure"] == m and r["endpoint"] == "did"
                   and r["window"] == "discovery") for m in ("fsi", "dfault", "tempo")]
    adj = S.holm(disc_p)
    decision = {}
    for m, h in zip(("fsi", "dfault", "tempo"), adj):
        dsc = next(r for r in rows if r["exposure"] == m and r["endpoint"] == "did" and r["window"] == "discovery")
        rep = next(r for r in rows if r["exposure"] == m and r["endpoint"] == "did" and r["window"] == "replication")
        dsc["holm_p"] = h
        decision[m] = {"holm_p": h, "discovery_coef": dsc["est"], "replication_coef": rep["est"],
                       "pass": bool(h < 0.05 and dsc["est"] < 0 and rep["est"] < 0)}
    return rows, {"triples": {w: int((d["window"] == w).sum()) for w in ("discovery", "replication")},
                  "decision": decision, "pass": any(v["pass"] for v in decision.values())}


# ------------------------------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--perms", type=int, default=500)
    args = ap.parse_args()
    p = load()
    log(f"pairs (logged, t+1 <= 21 d, outside the holdout): {len(p):,}")
    res: dict = {"prereg": "data/studies/point_sequence/med_prereg.md",
                 "directions": {"M1": "risk ratio; > 1 = exposed players retire or give a walkover in t+1 more",
                                "M2": "shift in pp of serve points won vs pre-match p_serve; negative = exposed "
                                      "players serve worse in t+1",
                                "secondary": "pp of [M2(t+1) - M2(t-1)] per SD of fade; negative = more fading "
                                             "-> serves worse next, relative to before"},
                 "cuts": {"minutes": p.attrs["minutes_cuts"], "points": p.attrs["points_cuts"],
                          "age_median": p.attrs["age_median"]}}
    rows: list[dict] = []
    ps_info = {}
    frames = {}
    for x in ("treated", "injury", "toilet", "opp_treated"):
        d, info = add_ps(contrast_frame(p, x), x)
        frames[x] = d
        ps_info[x] = info
        for endpoint in ("M1", "M2"):
            for window in ("discovery", "replication"):
                r = fit_cell(d[d["window"] == window], x, endpoint)
                fam = "primary" if x in ("treated", "injury") else ("negative_control" if x == "toilet" else "mirror")
                rows.append({"family": fam, "exposure": x, "endpoint": endpoint, "window": window,
                             "variant": "registered", **r})
    res["propensity"] = ps_info
    log("registered cells done")

    # Holm and the pass rule
    def cell(x, e, w, variant="registered"):
        return next(r for r in rows if r["exposure"] == x and r["endpoint"] == e and r["window"] == w
                    and r["variant"] == variant)

    keys = [("treated", "M1"), ("treated", "M2"), ("injury", "M1"), ("injury", "M2")]
    adj = S.holm([cell(x, e, "discovery")["p"] for x, e in keys])
    toilet_null = {(e, w): covers_null(cell("toilet", e, w), e) for e in ("M1", "M2")
                   for w in ("discovery", "replication")}
    strict_toilet = all(v is True for v in toilet_null.values())
    decision = {}
    for (x, e), h in zip(keys, adj):
        dsc, rep = cell(x, e, "discovery"), cell(x, e, "replication")
        dsc["holm_p"] = h
        est_d, est_r = dsc.get("est"), rep.get("est")
        if e == "M1":
            magnitude = est_d is not None and est_d >= 1.5
            same_side = est_r is not None and est_r > 1
        else:
            magnitude = est_d is not None and est_d <= -0.5
            same_side = est_r is not None and est_r < 0
        tnull = bool(toilet_null[(e, "discovery")] and toilet_null[(e, "replication")])
        conds = {"holm_p_lt_0.05": bool(h < 0.05), "magnitude": bool(magnitude), "replication_same_side":
                 bool(same_side), "toilet_null_same_endpoint_both_windows": tnull}
        decision[f"{x}|{e}"] = {"holm_p": h, "discovery": est_d, "replication": est_r, **conds,
                                "pass": all(conds.values()), "pass_strict_toilet": all(conds.values()) and
                                strict_toilet}
    res["decision"] = decision
    res["toilet_null"] = {f"{e}|{w}": v for (e, w), v in toilet_null.items()}
    res["gate_pass"] = any(v["pass"] for v in decision.values())
    res["gate_pass_strict"] = any(v["pass_strict_toilet"] for v in decision.values())
    log(f"gate pass: {res['gate_pass']} (strict reading: {res['gate_pass_strict']})")

    # placebo: TREATED permuted within season x result x minutes decile
    plc_rows = []
    res["placebo"] = {}
    for endpoint in ("M1", "M2"):
        for wi, window in enumerate(("discovery", "replication")):
            d = frames["treated"][frames["treated"]["window"] == window]
            pl = placebo(d, endpoint, args.perms, seed=1000 + 10 * wi + (endpoint == "M2"))
            obs = cell("treated", endpoint, window)
            null = 1.0 if endpoint == "M1" else 0.0
            if endpoint == "M1":
                dev_obs = abs(np.log(obs["est"])) if obs.get("est") else np.nan
                dev_pl = np.abs(np.log(pl["ests"]))
            else:
                dev_obs = abs(obs["est"] - null)
                dev_pl = np.abs(pl["ests"] - null)
            res["placebo"][f"{endpoint}|{window}"] = {
                "perms": args.perms, "mean": float(np.mean(pl["ests"])),
                "median": float(np.median(pl["ests"])),
                "q025": float(np.quantile(pl["ests"], 0.025)), "q975": float(np.quantile(pl["ests"], 0.975)),
                "share_nominal_p_lt_0.05": float(np.mean(pl["ps"] < 0.05)),
                "observed": obs.get("est"),
                "perm_p_two_sided": float((1 + np.sum(dev_pl >= dev_obs)) / (1 + len(dev_pl)))}
            plc_rows += [{"endpoint": endpoint, "window": window, "perm": i, "est": e, "p": q}
                         for i, (e, q) in enumerate(zip(pl["ests"], pl["ps"]))]
            log(f"placebo {endpoint} {window} done")
    pd.DataFrame(plc_rows).to_csv(OUT / "med_placebo.csv", index=False)

    # pre-declared sensitivities (TREATED and INJURY)
    for x in ("treated", "injury"):
        base = frames[x]
        own, _ = add_ps(contrast_frame(p, x, include_own_ret=True), x)
        for window in ("discovery", "replication"):
            bw = base[base["window"] == window]
            variants = {
                "incl_own_retirement": (own[own["window"] == window], {}),
                "points_decile": (bw, {"minutes": "pts_dec"}),
                "next_level_covariate": (bw, {"extra_cat": {"next_level": NEXT_LEVELS}}),
                "stratum_fresh": (bw[bw["fresh_stale"] == "fresh"], {}),
                "stratum_stale": (bw[bw["fresh_stale"] == "stale"], {}),
            }
            for vname, (dv, kw) in variants.items():
                for endpoint in ("M1", "M2"):
                    try:
                        r = fit_cell(dv, x, endpoint, **kw)
                    except np.linalg.LinAlgError as err:
                        r = {"note": f"fit failed: {err}"}
                    rows.append({"family": "sensitivity", "exposure": x, "endpoint": endpoint, "window": window,
                                 "variant": vname, **r})
            r = fit_cell(bw[bw["n_completed"].astype(bool)], x, "M2")
            rows.append({"family": "sensitivity", "exposure": x, "endpoint": "M2", "window": window,
                         "variant": "completed_next_only", **r})
            dm = bw[bw["m1"].notna()]
            mh = S.mh_rr(dm["m1"], dm[x].astype(int), dm["won_t"].astype(int).astype(str) + "|" +
                         dm["ps_q"].astype(str))
            rows.append({"family": "sensitivity", "exposure": x, "endpoint": "M1", "window": window,
                         "variant": "mantel_haenszel", "n": int(len(dm)), "n_exposed": int(dm[x].sum()), **mh})
    log("sensitivities done")

    # descriptive: any next match within 21 days, by exposure (withdrawals before a draw)
    allp = pd.read_parquet(OUT / "med_pairs.parquet")
    lt = allp[allp["logged"] & ~allp["own_ret"] & ~allp["next_holdout"]]
    desc = {}
    for window, g in lt.groupby("window"):
        for x in ("treated", "injury", "toilet"):
            ref = g[~g["treated"]] if x != "treated" else g
            e = ref[ref[x]] if x == "toilet" else g[g[x]]     # TOILET among TREATED = 0, as in its contrast
            u = ref[~ref[x]]
            desc[f"{x}|{window}"] = {"exposed_n": int(len(e)), "exposed_share_next_le21": float(e["next_le21"].mean())
                                     if len(e) else None, "reference_n": int(len(u)),
                                     "reference_share_next_le21": float(u["next_le21"].mean())}
        for res_name, sub in (("t_won", g[g["t_won"]]), ("t_lost", g[~g["t_won"]])):
            e, u = sub[sub["treated"]], sub[~sub["treated"]]
            desc[f"treated_{res_name}|{window}"] = {"exposed_n": int(len(e)),
                                                    "exposed_share_next_le21": float(e["next_le21"].mean()),
                                                    "reference_n": int(len(u)),
                                                    "reference_share_next_le21": float(u["next_le21"].mean())}
    res["next_within_21d"] = desc

    # descriptive (not registered): M1 split into retirements and walkovers given, crude, per exposure contrast
    comp = {}
    for x in ("treated", "toilet", "opp_treated"):
        d = frames[x]
        for window, g in d.groupby("window"):
            xe = g[x].astype(bool)
            for kind in ("retired", "walkover"):
                ev = (g["m1"] == 1) & g["n_status"].astype(str).eq(kind)
                a, n1 = int(ev[xe].sum()), int(xe.sum())
                b, n0 = int(ev[~xe].sum()), int((~xe).sum())
                rr = (a / n1) / (b / n0) if a and b else float("nan")
                se = float(np.sqrt(1 / a - 1 / n1 + 1 / b - 1 / n0)) if a and b else float("nan")
                comp[f"{x}|{window}|{kind}"] = {
                    "exposed": f"{a}/{n1}", "unexposed": f"{b}/{n0}", "crude_rr": rr,
                    "lo": float(np.exp(np.log(rr) - 1.96 * se)) if a and b else None,
                    "hi": float(np.exp(np.log(rr) + 1.96 * se)) if a and b else None}
    res["m1_components_descriptive"] = comp

    # secondary family
    srows, sdec = secondary(p)
    rows += srows
    res["secondary"] = sdec
    log(f"secondary family pass: {sdec['pass']}")

    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "med_results.csv", index=False)
    res["table"] = rows
    C.write_json(OUT / "med_results.json", res)
    log("wrote med_results.json, med_results.csv, med_placebo.csv")
    show = tab[["family", "exposure", "endpoint", "window", "variant", "n", "n_exposed", "est", "lo", "hi", "p"]
               + (["holm_p"] if "holm_p" in tab.columns else [])]
    with pd.option_context("display.width", 250, "display.max_rows", 500, "display.max_columns", 30):
        print(show.to_string(float_format=lambda v: f"{v:.4g}"))
    import json
    print(json.dumps({k: res[k] for k in ("decision", "toilet_null", "gate_pass", "gate_pass_strict", "placebo",
                                          "next_within_21d", "m1_components_descriptive", "secondary",
                                          "propensity")}, indent=1, default=str))


if __name__ == "__main__":
    main()
