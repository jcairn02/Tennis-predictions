"""Block B-CLUTCH, persistent non-iid scoring skill (I-009, I-026, I-027): a signed-sum composite, weight 0.5.

I-009 (+)  the games route minus the points route (MAT-C2), in the final family's remainder form (r = z_C2 - z_C1 minus
           its per-tour projection on the 58 inputs fitted on 2013-2018, no outcomes); z_C2 = logit P_iid with each player's
           service-game rate h_XY = expit(mu_hold + O^hold_X - D^hold_Y) (surface IOS) carried through sets and the match,
           tiebreaks at the serve-point rate whose hold is h (stage4_features.serve_rate_for_hold); z_C1 as in I-008.
I-026 (+)  big-point return skill x the scarcity of break points (MEC-18): x = Delta b * (s - mean_disc s),
           Delta b = Stage 4's bigpoint_return|single (A - B; shrunk importance-weighted minus plain return points won in
           earlier Grand Slam point files: own history, safe), s = betabar_c / betahat_AB, betahat_AB = the mean of the
           expected break points per service game under the iid model at p_AB and p_BA (surface IOS spw),
           betabar_c its tour x surface mean on 2014-2021 rows. Stage 4 stores only A - B, so prepare carries it as
           halves (+Delta b/2, -Delta b/2): a representation device whose swap is exact (orientation verified: Stage 4's
           age and height differences equal the panel's A - B exactly).
I-027 (+)  resilience excess (MEC-19): R_P = sum_j e_j / (sum_j d_j + K_R) over P's earlier point-by-point matches
           released (lf + 1) by the match's es, e_j = (consolidations - consolidation chances x the hold rate of P's
           other service games in match j) + (breaks back - break-back chances x the break rate of P's other return
           games in j); counts from shot_level/stage1_match_stats (point-by-point), rates from Stage 0's box score of the
           same match. K_R by method of moments on 2010-2018 player totals (statistics only). x = R_A - R_B.
Controls: z_C1, iosO_hold, iosD_hold, prod_hold (I-009); Delta b (I-026); form_hold, form_brk (I-027);
miss_R_A - miss_R_B; nearest inputs. eta-modulators: s (centred), 1[Delta b missing], 1[R missing for either].
Prechecks (result-free): I-009 split-half reliability of the per-player hold residual (holds minus service games x
game(p) at the match's own serve-point rate; 50+ matches a half; gate 0.3), 2010-2018; I-027 split-half carry-over of
the excess (gate > 0.1), 2010-2018. Reads no result. Run (diagnostics): ./python.sh src/eda/feature_interactions/
features/f08_clutch.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.features import f01_structure_lib as S  # noqa: E402
from src.eda.feature_interactions.features.f03_composition import z_c1  # noqa: E402

STAGE4 = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage4_features.parquet"
MATCH_STATS = ROOT / "data" / "studies" / "shot_level" / "stage1_match_stats.parquet"
# K_R by method of moments on 2010-2018 player totals (eb_constant_r): men tau^2 <= 0 (no between-player variance, K
# infinite; capped here), women K = 1,921 chances. Irrelevant while I-027 is dropped (KEEP below).
K_R = {"atp": 10000.0, "wta": 1921.0}
STD_CLUTCH = ("prod_bp_saved", "prod_first_won")   # nearest to the kept block (diagnostics)
# Result-free prechecks (2010-2018; diagnostics): I-009's per-player hold residual has split-half r 0.16 (men, 521
# players) and 0.27 (women, 108) at 50+ matches a half, below its 0.3 gate (Spearman-Brown 0.28 and 0.43; the raw
# correlation is the reading used for every gate here); I-027's excess has split-half r -0.07 (men) and -0.01 (women)
# at 15+ matches a half (gate > 0.1) and no between-player variance for men. Both are dropped by the block rule;
# B-CLUTCH keeps I-026. Flip to restore.
KEEP = {"I-009": False, "I-026": True, "I-027": False}


def z_c2(P: pd.DataFrame) -> np.ndarray:
    from src.eda.predictability_diagnostic.stage4_features import serve_rate_for_hold
    ha, hb = S.pt(P, "hold", "a", "b"), S.pt(P, "hold", "b", "a")
    return S.match_logit(serve_rate_for_hold(ha), serve_rate_for_hold(hb), S.num(P, "best_of"), S.rule(P))


def x_i009(P: pd.DataFrame) -> np.ndarray:
    """The final family's remainder form: z_C2 - z_C1 minus its per-tour projection on the 58 inputs (2013-2018 fit)."""
    return S.resid_on_58(P, z_c2(P) - z_c1(P), by_tour=True)


def bp_per_game(p) -> np.ndarray:
    """Expected break points faced per service game under iid, serve-point probability p (0-40, 15-40, 30-40 and
    every advantage to the receiver): q^3 + 4pq^3 + 10p^2q^3 + 20p^3q^3 * q/(1 - 2pq). 0.59 at p = 0.62, 0.33 at 0.70."""
    p = np.asarray(p, float)
    q = 1 - p
    return q ** 3 + 4 * p * q ** 3 + 10 * p ** 2 * q ** 3 + 20 * p ** 3 * q ** 3 * q / (1 - 2 * p * q)


def scarcity(P: pd.DataFrame) -> np.ndarray:
    beta = 0.5 * (bp_per_game(S.pt(P, "spw", "a", "b")) + bp_per_game(S.pt(P, "spw", "b", "a")))
    d, k = S.disc(P), S.cell_keys(P)
    cm = pd.Series(k).map(pd.Series(beta[d]).groupby(k[d]).mean()).to_numpy(dtype=float)
    return cm / beta


def x_i026(P: pd.DataFrame) -> np.ndarray:
    db = S.num(P, "f08_bigpt_a") - S.num(P, "f08_bigpt_b")
    return db * S.centre_disc(P, scarcity(P), None)


def _opp_cols(L: pd.DataFrame, cols: list[str]) -> dict:
    """The opponent's value of each column for every history row (the other row of the same match)."""
    key = L["match_id"].astype(str).to_numpy()
    out = {}
    for c in cols:
        v = S.num(L, c)
        a = pd.Series(v[L["side"].to_numpy() == "A"], index=key[L["side"].to_numpy() == "A"])
        b = pd.Series(v[L["side"].to_numpy() == "B"], index=key[L["side"].to_numpy() == "B"])
        a, b = a[~a.index.duplicated()], b[~b.index.duplicated()]
        out[c] = np.where(L["side"].to_numpy() == "A", pd.Series(key).map(b).to_numpy(dtype=float),
                          pd.Series(key).map(a).to_numpy(dtype=float))
    return out


def resilience_rows(L: pd.DataFrame) -> pd.DataFrame:
    """Per history row with point-by-point counts: the excess e and the chances d (see the module docstring)."""
    ms = pd.read_parquet(MATCH_STATS, columns=["match_id", "player_id", "consolidate_n", "consolidate_d",
                                               "break_back_n", "break_back_d"])
    ms["match_id"], ms["player_id"] = ms["match_id"].astype(str), ms["player_id"].astype(str)
    ms = ms.drop_duplicates(["match_id", "player_id"])
    base = L[["match_id", "player_id", "tour", "es", "lf", "k", "tournament_date"]].copy()
    base["match_id"], base["player_id"] = base["match_id"].astype(str), base["player_id"].astype(str)
    opp = _opp_cols(L, ["sv_gms", "bp_faced", "bp_saved"])
    sv, bf, bs = S.num(L, "sv_gms"), S.num(L, "bp_faced"), S.num(L, "bp_saved")
    base["holds"], base["sv"] = sv - (bf - bs), sv
    base["breaks"], base["rg"] = opp["bp_faced"] - opp["bp_saved"], opp["sv_gms"]
    R = base.merge(ms, on=["match_id", "player_id"], how="inner")
    cn, cd = R["consolidate_n"].to_numpy(float), R["consolidate_d"].to_numpy(float)
    bn, bd = R["break_back_n"].to_numpy(float), R["break_back_d"].to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        h_o = (R["holds"].to_numpy(float) - cn) / (R["sv"].to_numpy(float) - cd)
        b_o = (R["breaks"].to_numpy(float) - bn) / (R["rg"].to_numpy(float) - bd)
    e = (cn - cd * h_o) + (bn - bd * b_o)
    ok = np.isfinite(e) & (cd + bd > 0) & (h_o >= 0) & (h_o <= 1) & (b_o >= 0) & (b_o <= 1)
    R["e"], R["d"] = np.where(ok, e, np.nan), np.where(ok, cd + bd, np.nan)
    return R[ok].reset_index(drop=True)


def resilience_state(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    R = resilience_rows(S.cut_history(L, P))
    ids = pd.Index(pd.unique(np.r_[R["player_id"].to_numpy(), P["player_a_id"].astype(str).to_numpy(),
                                   P["player_b_id"].astype(str).to_numpy()]))
    src = ids.get_indexer(R["player_id"])
    out = {}
    for side, col in (("a", "player_a_id"), ("b", "player_b_id")):
        tgt = ids.get_indexer(P[col].astype(str))
        sm = S.clock_sum(src, R["lf"].to_numpy(float) + 1.0, R[["e", "d"]].to_numpy(float), tgt, S.num(P, "es"))
        K = P["tour"].astype(str).map(K_R).to_numpy(dtype=float)
        out[f"f08_res_{side}"] = np.where(sm[:, 1] > 0, sm[:, 0] / (sm[:, 1] + K), np.nan)
        out[f"f08_resn_{side}"] = sm[:, 1]
    return out


def prepare_clutch(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    s4 = pd.read_parquet(STAGE4, columns=["match_id", "bigpoint_return|single"])
    s4["match_id"] = s4["match_id"].astype(str)
    db = P[["match_id"]].astype(str).merge(s4.drop_duplicates("match_id"), on="match_id", how="left")
    db = db["bigpoint_return|single"].to_numpy(dtype=float)
    return {"f08_bigpt_a": db / 2, "f08_bigpt_b": -db / 2} | resilience_state(P, L)


def combine_clutch(P: pd.DataFrame) -> dict:
    """The kept members' sum and the union of the kept members' controls (KEEP)."""
    ra, rb = S.ab(P, "f08_res")
    db = S.num(P, "f08_bigpt_a") - S.num(P, "f08_bigpt_b")
    members, cols, mods, tab = [], [], [], {}
    if KEEP["I-009"]:
        x09 = x_i009(P)
        members.append((x09, "+"))
        cols += [("z_C1", z_c1(P))] + [(f"in_{n}", S.num(P, f"in_{n}")) for n in ("iosO_hold", "iosD_hold", "prod_hold")]
        tab["f08_games_minus_points"] = (x09, "diff", None)
    if KEEP["I-026"]:
        x26 = x_i026(P)
        members.append((x26, "+"))
        cols += [("d_bigpoint", np.nan_to_num(db))]
        mods += [np.nan_to_num(S.centre_disc(P, scarcity(P), None)),
                 S.centre_disc(P, (~np.isfinite(db)).astype(float), None)]
        tab["f08_bigpoint_x_scarcity"] = (x26, "diff", None)
    if KEEP["I-027"]:
        x27 = ra - rb
        members.append((x27, "+"))
        cols += [(f"in_{n}", S.num(P, f"in_{n}")) for n in ("form_hold", "form_brk")] + [("miss_res", S.miss_diff(ra, rb))]
        mods += [S.centre_disc(P, (~(np.isfinite(ra) & np.isfinite(rb))).astype(float), None)]
        tab["f08_resilience"] = (x27, "diff", None)
    Cm, names = S.pack(cols + [(f"in_{n}", S.num(P, f"in_{n}")) for n in STD_CLUTCH])
    return {"x": S.signed_block(P, members), "controls": Cm, "control_names": names,
            "eta_mod_controls": np.column_stack(mods) if mods else None, "tabpfn": tab}


HYPOTHESES = [
    {"hid": "B-CLUTCH", "master": "+".join(k for k, v in KEEP.items() if v), "kind": "C", "sign": "+", "weight": 0.5, "trait": "slow",
     "deployment": "diff", "family": "02/05", "prepare": prepare_clutch, "combine": combine_clutch},
]


def _split_half(df: pd.DataFrame, val: str, units: str, min_matches: int) -> dict:
    """Per player (and tour): matches alternated by own order into two halves; the per-unit rate in each half; the
    correlation across players with at least `min_matches` matches in each half."""
    df = df.sort_values(["player_id", "k"]).copy()
    df["half"] = df.groupby("player_id").cumcount() % 2
    g = df.groupby(["tour", "player_id", "half"]).agg(v=(val, "sum"), u=(units, "sum"), n=(val, "size")).reset_index()
    w = g.pivot_table(index=["tour", "player_id"], columns="half", values=["v", "u", "n"]).dropna()
    out = {}
    for t in ("atp", "wta"):
        x = w.loc[t] if t in w.index.get_level_values(0) else None
        if x is None:
            continue
        x = x[(x[("n", 0)] >= min_matches) & (x[("n", 1)] >= min_matches)]
        r1, r2 = x[("v", 0)] / x[("u", 0)], x[("v", 1)] / x[("u", 1)]
        out[t] = {"players": int(len(x)), "split_half_r": float(np.corrcoef(r1, r2)[0, 1]) if len(x) > 10 else np.nan}
    return out


def i009_precheck(P: pd.DataFrame, L: pd.DataFrame, years=(2010, 2018)) -> dict:
    """Per-player hold residual: holds minus service games x game(p), p = the match's own serve-point share."""
    from src.eda.predictability_diagnostic.stage2_iid import game
    L = S.cut_history(L, P)
    yr = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    sv, bf, bs = S.num(L, "sv_gms"), S.num(L, "bp_faced"), S.num(L, "bp_saved")
    p = S.num(L, "spw_n") / S.num(L, "spw_d")
    res = (sv - (bf - bs)) - sv * game(np.clip(np.nan_to_num(p, nan=0.5), 0, 1))
    ok = (yr >= years[0]) & (yr <= years[1]) & np.isfinite(res) & (sv > 0) & np.isfinite(p)
    df = pd.DataFrame({"player_id": L["player_id"].astype(str), "tour": L["tour"].astype(str), "k": L["k"],
                       "res": res, "sv": sv})[ok]
    out = {"gate": 0.3, "min_matches_a_half": 50, "hold": _split_half(df, "res", "sv", 50)}
    opp = _opp_cols(L, ["sv_gms", "bp_faced", "bp_saved", "spw_n", "spw_d"])      # the return side, for information
    po = opp["spw_n"] / opp["spw_d"]
    rres = (opp["bp_faced"] - opp["bp_saved"]) - opp["sv_gms"] * (1 - game(np.clip(np.nan_to_num(po, nan=0.5), 0, 1)))
    ok2 = (yr >= years[0]) & (yr <= years[1]) & np.isfinite(rres) & (opp["sv_gms"] > 0) & np.isfinite(po)
    df2 = pd.DataFrame({"player_id": L["player_id"].astype(str), "tour": L["tour"].astype(str), "k": L["k"],
                        "res": rres, "sv": opp["sv_gms"]})[ok2]
    out["break (information)"] = _split_half(df2, "res", "sv", 50)
    for side in ("hold", "break (information)"):
        for t, v in out[side].items():
            r = v["split_half_r"]
            v["spearman_brown"] = float(2 * r / (1 + r)) if np.isfinite(r) else np.nan
    return out


def eb_constant_r(R: pd.DataFrame, years=(2010, 2018)) -> dict:
    """Method of moments on player totals (statistics only): tau^2 = between-player variance of the excess per chance
    beyond its sampling part, sigma^2 = the per-chance variance; K = sigma^2 / tau^2 (in chances)."""
    yr = pd.to_datetime(R["tournament_date"]).dt.year.to_numpy()
    out = {}
    for t in ("atp", "wta"):
        m = (yr >= years[0]) & (yr <= years[1]) & (R["tour"].astype(str).to_numpy() == t)
        g = R[m].groupby("player_id").agg(e=("e", "sum"), d=("d", "sum"), e2=("e", lambda v: float(np.sum(v ** 2))))
        g = g[g["d"] >= 20]
        sigma2 = float(g["e2"].sum() / g["d"].sum())
        rate = g["e"] / g["d"]
        mean = float(np.average(rate, weights=g["d"]))
        between = float(np.average((rate - mean) ** 2, weights=g["d"]))
        tau2 = between - float(np.average(sigma2 / g["d"], weights=g["d"]))
        out[t] = {"players": int(len(g)), "sigma2": sigma2, "tau2": tau2, "mean_excess_per_chance": mean,
                  "K": float(sigma2 / tau2) if tau2 > 0 else float("inf")}
    return out


def i027_precheck(P: pd.DataFrame, L: pd.DataFrame, years=(2010, 2018)) -> dict:
    R = resilience_rows(S.cut_history(L, P))
    yr = pd.to_datetime(R["tournament_date"]).dt.year.to_numpy()
    df = R[(yr >= years[0]) & (yr <= years[1])]
    return {"gate": 0.1, "eb": eb_constant_r(R, years),
            "split_half_15": _split_half(df, "e", "d", 15), "split_half_30": _split_half(df, "e", "d", 30),
            "rows": int(len(df))}


def diagnostics(P: pd.DataFrame, L: pd.DataFrame | None = None) -> dict:
    d = S.disc(P)
    ra, rb = S.ab(P, "f08_res")
    mem = {"I-009": x_i009(P), "I-026": x_i026(P), "I-027": ra - rb}
    out = {"members": {k: {"r2_on_58": S.r2_on_58(P, v), "nearest": S.nearest(P, v, 4),
                           "coverage_disc": float(np.isfinite(v[d]).mean()),
                           "coverage_rep": float(np.isfinite(v[P["season"].between(2022, 2024).to_numpy()]).mean())}
                       for k, v in mem.items()}}
    M = np.column_stack([np.nan_to_num(v[d]) for v in mem.values()])
    out["member_corr"] = np.round(np.corrcoef(M.T), 3).tolist()
    x = combine_clutch(P)["x"]
    out["block"] = {"r2_on_58": S.r2_on_58(P, x), "nearest": S.nearest(P, x, 5)}
    if L is not None:
        out["I-009 precheck"] = i009_precheck(P, L)
        out["I-027 precheck"] = i027_precheck(P, L)
    return out


if __name__ == "__main__":
    import json
    import warnings
    warnings.simplefilter("ignore")
    from src.eda.feature_interactions.history import long_table
    from src.eda.feature_interactions.panel import panel
    P = panel(max_season=2024)
    L = long_table()
    res = diagnostics(P.assign(**prepare_clutch(P, L)), L)
    print(S.write_diag("f08_clutch", res))
    print(json.dumps(res, indent=1, default=str)[:5000])
