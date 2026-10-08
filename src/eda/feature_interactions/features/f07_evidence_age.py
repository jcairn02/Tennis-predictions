"""Block B7 (evidence and staleness weighting; I-023, I-031, I-032, I-048; weight 1, trait fixed: height) and B-AGE
(I-070 alone after I-068's gate; weight 0.5), as the final family (round 2) fixes them: signed sums, each member divided
by its 2014-2021 SD and multiplied by its declared sign.

B7, "unknown is not average"
  I-023 (+) height as the serve prior for thin histories (MEC-16): x = Delta[K_h/(n + K_h) (beta_h (h - hbar) - O^ace)],
            n = Stage 3's rated serve points, O^ace = srf_O_eff_ace; beta_h, hbar per tour from players with >= 5,000
            rated serve points on 2013-2018 panel rows (O^ace on height: statistics only); K_h chosen on the result-free
            next-match ace forecast of thin histories (n < 1,000), 2013-2018 pool matches (see TUNED).
  I-031 (+) re-anchor the two-week form on the long level (MAT-U1): the existing form is r * raw with r = s0/(s0 + K3)
            (Stage B: s0 = sum of 2^(-age/2 weeks) over earlier box-score matches, K3 = 10 men, 20 women), so
            form* = l + r (raw - l) = form + (1 - r) l and, given Delta form and Delta l, the new column is
            Delta[(1 - r) l]. l = the 52-week level of the same z (z_adjperf_tpw, ufc_ideas/stageB_adj), sum z / (n + K3)
            over box-score matches released (lf + 1) by the match's es. One composite (the points form), per the audit.
  I-032 (+) the evidence behind the IOS (MAT-U2): x = (rbar - mean_disc rbar) * Delta(O^spw + D^spw), rbar the harmonic
            mean of n/(n + 20), n = rated surface matches (Elo's NS), K = 20 fixed by the audit.
  I-048 (-) a stale surface profile (BOD-21): two member columns, Delta[(1 - w) E] and Delta[(1 - w) F], w = n/(n + 10)
            exp(-layoff/180), E, F the spw surface deviations (srf_E_spw, srf_F_spw), n = NS, layoff = days since the last
            match on the surface (constants fixed by the audit); (1 - w) centred at its pooled 2014-2021 mean (identical
            given the controls Delta E, Delta F).
  Controls (final family): unweighted Delta O^ace, Delta height, miss_height; form_s (adjperf_tpw_2w), Delta l, miss_l;
  Delta IOS (Delta O^spw, Delta D^spw); plain Delta E, Delta F; nearest inputs. eta-modulator: rbar (centred).
  Trait: slow (checkpoint 1, R-6 / F-2); trait_cols ["height"] kept for the batch's diagnostic permutation.
B-AGE, age changes what the long memory and recent form mean
  I-068 (-) Delta[(age - 28) shape], shape = (D^spw - Dbar_c) - (O^spw - Obar_c), cell means (tour x surface) over both
            players on 2014-2021 rows (MEC-14).
  I-070 (+) Delta[(Short - Long) h(age)], h = (25 - age)+ - 0.5 (age - 30)+, Short = adjperf_tpw_2w, Long = spw IOS O + D,
            each divided by its SD over both players on 2014-2021 rows (BOD-28 as the audit fixed it).
  Controls: age, age_sq, adjperf_tpw_2w, Delta O^spw, Delta D^spw, Delta Long, nearest inputs; eta-modulators: Sigma age,
  Sigma shape, Sigma h, Sigma(S - L).
Prechecks (result-free): CV(r) for I-031 (>= 0.2) and CV(rbar) for I-032 (>= 0.15), 2013-2021 model rows; I-023's ace
forecast (>= 0.05 milli per point); I-068's return-minus-serve residual drift after 29 (statistics only, 2013-2018).
Reads no result. Run (diagnostics): ./python.sh src/eda/feature_interactions/features/f07_evidence_age.py
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

from src.eda.feature_interactions.features import f01_structure_lib as S  # noqa: E402

STAGEB = ROOT / "data" / "studies" / "ufc_ideas" / "stageB_adj.parquet"
STAGEB_USED = ROOT / "data" / "studies" / "ufc_ideas" / "stageB_adj_summary.json"
STAGE3 = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage3_ratings.parquet"
REF_DAY = int(np.datetime64("2018-01-01", "D").astype("int64"))
# K_h tuned by k_h_tuning (result-free: next-match aces of thin histories, 2013-2018 pool matches, log loss per serve
# point): grid 25-8,000, minimum at 100 (0.181925 against 0.182323 for the plain IOS, a gain of 0.40 milli per point;
# the audit's 1,000 gives 0.182558)
TUNED = {"K_h": 100.0}
K_I032, K_I048, THETA_I048 = 20.0, 10.0, 180.0
STD_B7 = ("form_hold", "form_first_won")   # nearest to the five-member block after adjperf_tpw_2w (-0.124, -0.116)
STD_AGE = ("age_sq", "iosO_bp_saved")   # nearest to I-070 after age (diagnostics: age_sq 0.43, iosO_bp_saved 0.22)


def k3() -> dict:
    used = json.loads(STAGEB_USED.read_text(encoding="utf-8"))["used"]["adjperf_tpw"]
    return {t: float(used[t]["K3"]) for t in ("atp", "wta")}


def form_state(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    """Per model match and side: s0 (the two-week form's weight sum, Stage B's time rule) and l (the 52-week level of
    z_adjperf_tpw on the clock). Own earlier box-score matches only."""
    from src.eda.predictability_diagnostic import common as PC
    L = S.cut_history(L, P)
    z = pd.read_parquet(STAGEB, columns=["match_id", "player_id", "z_adjperf_tpw"])
    z["match_id"], z["player_id"] = z["match_id"].astype(str), z["player_id"].astype(str)
    info = L[["match_id", "player_id", "tour", "tournament_date", "tournament_id", "round_order", "es", "lf"]].copy()
    info["match_id"], info["player_id"] = info["match_id"].astype(str), info["player_id"].astype(str)
    box = info.merge(z, on=["match_id", "player_id"], how="inner")
    box = box[np.isfinite(box["z_adjperf_tpw"].to_numpy(float))]
    q = []
    for side, col in (("a", "player_a_id"), ("b", "player_b_id")):
        q.append(pd.DataFrame({"match_id": P["match_id"].astype(str).to_numpy(), "player_id": P[col].astype(str).to_numpy(),
                               "tour": P["tour"].astype(str).to_numpy(), "_side": side}))
    q = pd.concat(q, ignore_index=True).merge(info.drop(columns=["player_id", "tour"]).drop_duplicates("match_id"),
                                              on="match_id", how="left")
    allr = pd.concat([box.assign(_side="box"), q], ignore_index=True)
    day = pd.to_datetime(allr["tournament_date"]).to_numpy().astype("datetime64[D]").astype("int64")
    f = np.exp2((day - REF_DAY) / 14.0)
    isbox = (allr["_side"] == "box").to_numpy()
    allr["s0"] = np.where(isbox, f, 0.0)
    allr["s1"] = np.where(isbox, np.nan_to_num(allr["z_adjperf_tpw"].to_numpy(float)) * f, 0.0)
    sums = PC.asof_sums(allr, ["s0", "s1"]).to_numpy()
    s0, s1 = sums[:, 0] / f, sums[:, 1] / f
    pid = pd.factorize(allr["player_id"])[0]
    bx = np.flatnonzero(isbox)
    w52 = S.clock_sum(pid[bx], allr["lf"].to_numpy(float)[bx] + 1.0,
                      np.column_stack([allr["z_adjperf_tpw"].to_numpy(float)[bx], np.ones(len(bx))]),
                      pid, allr["es"].to_numpy(float), window=364.0)
    K = allr["tour"].map(k3()).to_numpy(dtype=float)
    ell = np.where(w52[:, 1] > 0.5, w52[:, 0] / (w52[:, 1] + K), np.nan)
    out = {}
    for side in ("a", "b"):
        m = (allr["_side"] == side).to_numpy()
        key = allr.loc[m, "match_id"].to_numpy()
        for name, v in (("s0", s0), ("form_rebuilt", s1 / (s0 + K)), ("ell", ell), ("k3", K)):
            ser = pd.Series(v[m], index=key)
            out[f"f07_{name}_{side}"] = ser[~ser.index.duplicated()].reindex(P["match_id"].astype(str)).to_numpy(dtype=float)
    return out


def beta_h(P: pd.DataFrame) -> dict:
    """Per tour: (beta_h, hbar) from O^ace on height over players with >= 5,000 rated serve points, 2013-2018 panel rows
    (both sides pooled; statistics only, no result)."""
    m = P["season"].between(2013, 2018).to_numpy()
    out = {}
    for t in ("atp", "wta"):
        k = m & (P["tour"].astype(str) == t).to_numpy()
        h = np.r_[S.num(P, "height_a")[k], S.num(P, "height_b")[k]]
        o = np.r_[S.ios(P, "srfO", "ace", "a")[k], S.ios(P, "srfO", "ace", "b")[k]]
        n = np.r_[S.num(P, "s3_serve_pts_a")[k], S.num(P, "s3_serve_pts_b")[k]]
        ok = np.isfinite(h) & np.isfinite(o) & (n >= 5000)
        hbar = float(np.mean(h[ok]))
        out[t] = (float(np.polyfit(h[ok] - hbar, o[ok], 1)[0]), hbar)
    return out


def i023_side(P: pd.DataFrame, side: str, bh: dict, K: float) -> np.ndarray:
    t = P["tour"].astype(str).to_numpy()
    b = np.array([bh[x][0] for x in t])
    hb = np.array([bh[x][1] for x in t])
    n = S.num(P, f"s3_serve_pts_{side}")
    prior = b * (S.num(P, f"height_{side}") - hb)
    return K / (n + K) * (prior - S.ios(P, "srfO", "ace", side))


def x_i023(P: pd.DataFrame) -> np.ndarray:
    bh = beta_h(P)
    return i023_side(P, "a", bh, TUNED["K_h"]) - i023_side(P, "b", bh, TUNED["K_h"])


def r_side(P: pd.DataFrame, side: str) -> np.ndarray:
    s0, K = S.num(P, f"f07_s0_{side}"), S.num(P, f"f07_k3_{side}")
    return s0 / (s0 + K)


def _pooled_mean_disc(P: pd.DataFrame, a: np.ndarray, b: np.ndarray) -> float:
    d = S.disc(P)
    return float(np.nanmean(np.r_[a[d], b[d]]))


def x_i031(P: pd.DataFrame) -> np.ndarray:
    """Delta[((1 - r) - c) l], c = the mean of 1 - r over both players on 2014-2021 rows: given the control Delta l this
    is Delta[(1 - r) l] exactly; the centring only keeps Delta l from dominating the member's scale inside the block."""
    ua, ub = 1 - r_side(P, "a"), 1 - r_side(P, "b")
    c = _pooled_mean_disc(P, ua, ub)
    return (ua - c) * S.num(P, "f07_ell_a") - (ub - c) * S.num(P, "f07_ell_b")


def rbar(P: pd.DataFrame) -> np.ndarray:
    ra, rb = [S.num(P, f"elo_NS_{s}") / (S.num(P, f"elo_NS_{s}") + K_I032) for s in "ab"]
    return 2 * ra * rb / np.maximum(ra + rb, 1e-9)


def d_net_spw(P: pd.DataFrame) -> np.ndarray:
    return (S.ios(P, "srfO", "spw", "a") + S.ios(P, "srfD", "spw", "a")) - (S.ios(P, "srfO", "spw", "b") + S.ios(P, "srfD", "spw", "b"))


def x_i032(P: pd.DataFrame) -> np.ndarray:
    return S.centre_disc(P, rbar(P), None) * d_net_spw(P)


def stale_w(P: pd.DataFrame, side: str) -> np.ndarray:
    n = S.num(P, f"elo_NS_{side}")
    lay = np.nan_to_num(S.num(P, f"surf_days_since_{side}"), nan=1095.0)
    return n / (n + K_I048) * np.exp(-lay / THETA_I048)


def i048_parts(P: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Delta[((1 - w) - c) E] and Delta[((1 - w) - c) F], c = the mean of 1 - w over both players on 2014-2021 rows
    (identical given the controls Delta E, Delta F; see x_i031)."""
    wa, wb = stale_w(P, "a"), stale_w(P, "b")
    c = 1 - _pooled_mean_disc(P, wa, wb)
    wa, wb = wa + c, wb + c                                  # (1 - w) - c = 1 - (w + c)
    e = (1 - wa) * S.ios(P, "srfE", "spw", "a") - (1 - wb) * S.ios(P, "srfE", "spw", "b")
    f = (1 - wa) * S.ios(P, "srfF", "spw", "a") - (1 - wb) * S.ios(P, "srfF", "spw", "b")
    return e, f


def prepare_b7(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    """The form state (I-031) and the fixed trait height as <trait>_a/_b, so the batch can permute it (critique M4)."""
    return form_state(P, L) | {"height_a": S.num(P, "height_a"), "height_b": S.num(P, "height_b")}


def combine_b7(P: pd.DataFrame) -> dict:
    e48, f48 = i048_parts(P)
    x23, x31, x32 = x_i023(P), x_i031(P), x_i032(P)
    # five member columns, as the final family lists them: I-048's offence and defence parts enter separately
    x = S.signed_block(P, [(x23, "+"), (x31, "+"), (x32, "+"), (e48, "-"), (f48, "-")])
    ha, hb = S.ab(P, "height")
    la, lb = S.ab(P, "f07_ell")
    cols = [(f"in_{n}", S.num(P, f"in_{n}")) for n in ("iosO_ace", "adjperf_tpw_2w") + STD_B7]
    cols += [("d_height", ha - hb), ("miss_height", S.miss_diff(ha, hb)), ("d_ell", la - lb),
             ("miss_ell", S.miss_diff(la, lb)),
             ("dO_spw", S.ios(P, "srfO", "spw", "a") - S.ios(P, "srfO", "spw", "b")),
             ("dD_spw", S.ios(P, "srfD", "spw", "a") - S.ios(P, "srfD", "spw", "b")),
             ("dE_spw", S.ios(P, "srfE", "spw", "a") - S.ios(P, "srfE", "spw", "b")),
             ("dF_spw", S.ios(P, "srfF", "spw", "a") - S.ios(P, "srfF", "spw", "b"))]
    Cm, names = S.pack(cols)
    # the final family's eta-modulator control: rbar * eta (I-032); Sigma(raw - l) and Sigma r (round-1 card) dropped
    E = np.nan_to_num(S.centre_disc(P, rbar(P), None))[:, None]
    tab = {"f07_height_prior": (x23, "diff", None), "f07_reanchor": (x31, "diff", None),
           "f07_ios_x_rbar": (x32, "diff", None), "f07_stale_E": (e48, "diff", None), "f07_stale_F": (f48, "diff", None)}
    return {"x": x, "controls": Cm, "control_names": names, "eta_mod_controls": E, "tabpfn": tab}


def _pooled_cell_mean(P: pd.DataFrame, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    d = S.disc(P)
    k = S.cell_keys(P)
    means = pd.Series(np.r_[a[d], b[d]]).groupby(np.r_[k[d], k[d]]).mean()
    return pd.Series(k).map(means).to_numpy(dtype=float)


def shape_side(P: pd.DataFrame, side: str) -> np.ndarray:
    """Return-heaviness of the spw surface IOS: (D - Dbar_c) - (O - Obar_c), cell means over both players, 2014-2021."""
    Oa, Ob = S.ios(P, "srfO", "spw", "a"), S.ios(P, "srfO", "spw", "b")
    Da, Db = S.ios(P, "srfD", "spw", "a"), S.ios(P, "srfD", "spw", "b")
    Om, Dm = _pooled_cell_mean(P, Oa, Ob), _pooled_cell_mean(P, Da, Db)
    O, D = (Oa, Da) if side == "a" else (Ob, Db)
    return (D - Dm) - (O - Om)


def x_i068(P: pd.DataFrame) -> np.ndarray:
    return (S.num(P, "age_a") - 28) * shape_side(P, "a") - (S.num(P, "age_b") - 28) * shape_side(P, "b")


def _pooled_sd(P: pd.DataFrame, a: np.ndarray, b: np.ndarray) -> float:
    d = S.disc(P)
    return float(np.nanstd(np.r_[a[d], b[d]]))


def h_age(age: np.ndarray) -> np.ndarray:
    return np.clip(25 - age, 0, None) - 0.5 * np.clip(age - 30, 0, None)


def short_long(P: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    sa, sb = S.ab(P, "adjperf_tpw_2w")
    La = S.ios(P, "srfO", "spw", "a") + S.ios(P, "srfD", "spw", "a")
    Lb = S.ios(P, "srfO", "spw", "b") + S.ios(P, "srfD", "spw", "b")
    ss, sl = _pooled_sd(P, sa, sb), _pooled_sd(P, La, Lb)
    return sa / ss - La / sl, sb / ss - Lb / sl


def x_i070(P: pd.DataFrame) -> np.ndarray:
    ga, gb = short_long(P)
    return ga * h_age(S.num(P, "age_a")) - gb * h_age(S.num(P, "age_b"))


# I-068's result-free precheck failed (age_drift_precheck, 2013-2018 pool matches): after 29 the return residual does
# not drift below the serve residual (slope of return-minus-serve on (age - 29)+: men +0.0011, SE 0.0008; women +0.0005,
# SE 0.0013; the mechanism needs a negative slope; binned means flat at -0.016 to -0.025 for men aged 29-45). By the
# block rule the member is dropped; B-AGE keeps I-070. Set True to restore it.
KEEP_I068 = False


def combine_age(P: pd.DataFrame) -> dict:
    x68, x70 = x_i068(P), x_i070(P)
    x = S.signed_block(P, ([(x68, "-")] if KEEP_I068 else []) + [(x70, "+")])
    La = S.ios(P, "srfO", "spw", "a") + S.ios(P, "srfD", "spw", "a")
    Lb = S.ios(P, "srfO", "spw", "b") + S.ios(P, "srfD", "spw", "b")
    # I-070's controls (age, Delta Short through adjperf_tpw_2w, Delta Long); I-068's (age_sq, Delta O^spw, Delta D^spw)
    # only while it is kept
    cols = [(f"in_{n}", S.num(P, f"in_{n}")) for n in ("age", "adjperf_tpw_2w") + STD_AGE] + [("d_long", La - Lb)]
    if KEEP_I068:
        cols += ([("in_age_sq", S.num(P, "in_age_sq"))] if "age_sq" not in STD_AGE else []) + [
                 ("dO_spw", S.ios(P, "srfO", "spw", "a") - S.ios(P, "srfO", "spw", "b")),
                 ("dD_spw", S.ios(P, "srfD", "spw", "a") - S.ios(P, "srfD", "spw", "b"))]
    Cm, names = S.pack(cols)
    ga, gb = short_long(P)
    aa, abb = S.num(P, "age_a"), S.num(P, "age_b")
    sums = [aa + abb, h_age(aa) + h_age(abb), ga + gb] + ([shape_side(P, "a") + shape_side(P, "b")] if KEEP_I068 else [])
    E = np.nan_to_num(np.column_stack([S.centre_disc(P, s_) for s_ in sums]))
    return {"x": x, "controls": Cm, "control_names": names, "eta_mod_controls": E,
            "tabpfn": {"f07_age_trust_form": (x70, "diff", None)} | ({"f07_age_x_shape": (x68, "diff", None)}
                                                                       if KEEP_I068 else {})}


HYPOTHESES = [
    # trait slow: B7 gates on the slow-trait widening (meta-auditor checkpoint 1, R-6 / F-2); height stays in trait_cols
    # for the batch's diagnostic height permutation only (it enters I-023 alone, so it would test that member)
    {"hid": "B7", "master": "I-023+I-031+I-032+I-048", "kind": "U", "sign": "+", "weight": 1.0, "trait": "slow",
     "trait_cols": ["height"],
     "deployment": "diff", "family": "04/07/10", "prepare": prepare_b7, "combine": combine_b7},
    {"hid": "B-AGE", "master": "I-068+I-070" if KEEP_I068 else "I-070", "kind": "W", "sign": "+", "weight": 0.5, "trait": "slow",
     "deployment": "diff", "family": "13", "prepare": None, "combine": combine_age},
]


def k_h_tuning(P: pd.DataFrame, L: pd.DataFrame, grid=(0.0, 25.0, 50.0, 100.0, 150.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0)) -> dict:
    """I-023's constant and precheck (result-free, statistic level): on 2013-2018 pool matches of thin histories (fewer
    than 1,000 rated serve points), forecast the row player's aces per serve point with the surface IOS, the server's
    O^ace replaced by the height-blended O~ = (n O + K_h prior)/(n + K_h). Log loss per serve point (lower is better);
    K_h = 0 is the plain IOS. The chosen K_h minimises the pooled log loss; the gain must reach 0.05 milli per point."""
    from scipy.special import expit
    L = S.cut_history(L, P)
    yr = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    tour, surf = L["tour"].astype(str).to_numpy(), L["surface"].astype(str).to_numpy()
    H = S.history_ios(L, ["srf_O_eff_ace", "srf_D_eff_ace"])
    n_pts = S.history_pair(L, STAGE3, ["serve_pts"])[("own", "serve_pts")]
    h = L["player_id"].astype(str).map(S.player_heights()).to_numpy(dtype=float)
    bh = beta_h(P)
    b = np.array([bh.get(t, (np.nan, np.nan))[0] for t in tour])
    hb = np.array([bh.get(t, (np.nan, np.nan))[1] for t in tour])
    aces, sv = S.history_stat(L, "ace")
    O, D = H[("own", "srf_O_eff_ace")], H[("opp", "srf_D_eff_ace")]
    m = S.mu(L, "ace", tour, surf)
    ok = (yr >= 2013) & (yr <= 2018) & (n_pts < 1000) & np.isfinite(O) & np.isfinite(D) & np.isfinite(h) \
        & np.isfinite(aces) & (sv >= 10)
    prior = b * (h - hb)
    out = {"rows": int(ok.sum()), "rows_by_tour": {t: int((ok & (tour == t)).sum()) for t in ("atp", "wta")},
           "beta_h": {t: bh[t][0] for t in bh}, "hbar": {t: bh[t][1] for t in bh}, "grid": {}}
    for K in grid:
        Ot = (n_pts * O + K * prior) / (n_pts + K) if K > 0 else O
        p = expit(m + Ot - D)
        out["grid"][str(int(K))] = {t: S.binom_ll(aces[ok & (tour == t)], sv[ok & (tour == t)], p[ok & (tour == t)])
                                    for t in ("atp", "wta")} | {"pooled": S.binom_ll(aces[ok], sv[ok], p[ok])}
    best = min((k for k in out["grid"] if k != "0"), key=lambda k: out["grid"][k]["pooled"])
    out["chosen_K_h"] = float(best)
    out["gain_milli_per_point"] = {t: 1000 * (out["grid"]["0"][t] - out["grid"][best][t]) for t in ("atp", "wta", "pooled")}
    out["passes_0.05"] = bool(out["gain_milli_per_point"]["pooled"] >= 0.05)
    return out


def age_drift_precheck(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    """I-068's outcome-free precheck: on 2013-2018 pool matches, the return residual minus the serve residual (logit,
    against the surface IOS on spw) regressed on (age - 29)+ and (29 - age)+, weighted, player-clustered: MEC-14 expects
    a negative slope after 29 (return decays faster than the lagging long-memory profile says)."""
    L = S.cut_history(L, P)
    yr = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    tour, surf = L["tour"].astype(str).to_numpy(), L["surface"].astype(str).to_numpy()
    H = S.history_ios(L, ["srf_O_eff_spw", "srf_D_eff_spw"])
    m = S.mu(L, "spw", tour, surf)
    sn, sd_ = S.num(L, "spw_n"), S.num(L, "spw_d")
    rn, rd = S.num(L, "rpw_n"), S.num(L, "rpw_d")
    r_s = S.lg((sn + 0.5) / (sd_ + 1)) - (m + H[("own", "srf_O_eff_spw")] - H[("opp", "srf_D_eff_spw")])
    # the opponent's serve residual, negated: the row player's return residual
    r_r = -(S.lg((rd - rn + 0.5) / (rd + 1)) - (m + H[("opp", "srf_O_eff_spw")] - H[("own", "srf_D_eff_spw")]))
    age = S.num(L, "age")
    ok = (yr >= 2013) & (yr <= 2018) & np.isfinite(r_s) & np.isfinite(r_r) & np.isfinite(age) & (sd_ >= 20) & (rd >= 20)
    out = {}
    for t in ("atp", "wta"):
        k = ok & (tour == t)
        y = r_r[k] - r_s[k]
        X = np.column_stack([np.ones(k.sum()), np.clip(age[k] - 29, 0, None), np.clip(29 - age[k], 0, None)])
        b, se = S.wls_clustered(X, y, np.ones(k.sum()), L["player_id"].astype(str).to_numpy()[k])
        out[t] = {"rows": int(k.sum()), "slope_after_29": float(b[1]), "se": float(se[1]), "z": float(b[1] / se[1]),
                  "slope_before_29_per_year_younger": float(b[2]), "se_before": float(se[2])}
    return out


def diagnostics(P: pd.DataFrame, L: pd.DataFrame | None = None) -> dict:
    d = S.disc(P)
    m13_21 = P["season"].between(2013, 2021).to_numpy()
    r_all = np.r_[r_side(P, "a")[m13_21], r_side(P, "b")[m13_21]]
    rb = rbar(P)[m13_21]
    e48, f48 = i048_parts(P)
    mem = {"I-023": x_i023(P), "I-031": x_i031(P), "I-032": x_i032(P), "I-048 E+F": e48 + f48,
           "I-068": x_i068(P), "I-070": x_i070(P)}
    out = {"prechecks": {"I-031 CV(r) 2013-2021": float(np.nanstd(r_all) / np.nanmean(r_all)),
                         "I-032 CV(rbar) 2013-2021": float(np.nanstd(rb) / np.nanmean(rb)),
                         "I-032 rbar quantiles": np.nanquantile(rb, [0.1, 0.5, 0.9]).round(3).tolist()},
           "members": {}}
    for k, v in mem.items():
        out["members"][k] = {"r2_on_58": S.r2_on_58(P, v), "nearest": S.nearest(P, v, 4),
                             "coverage_disc": float(np.isfinite(v[d]).mean())}
    out["I-048 corr(E part, F part)"] = float(np.corrcoef(np.nan_to_num(e48[d]), np.nan_to_num(f48[d]))[0, 1])
    names = list(mem)
    Mx = np.column_stack([np.nan_to_num(mem[k][d]) for k in names])
    out["member_corr"] = {f"{names[i]} ~ {names[j]}": round(float(np.corrcoef(Mx[:, i], Mx[:, j])[0, 1]), 3)
                          for i in range(len(names)) for j in range(i + 1, len(names))}
    for hid, comb in (("B7", combine_b7), ("B-AGE", combine_age)):
        x = comb(P)["x"]
        out[hid] = {"r2_on_58": S.r2_on_58(P, x), "nearest": S.nearest(P, x, 4)}
    if L is not None:
        out["prechecks"]["I-023 K_h tuning and ace forecast"] = k_h_tuning(P, L)
        out["prechecks"]["I-068 age drift"] = age_drift_precheck(P, L)
    return out


if __name__ == "__main__":
    import warnings
    warnings.simplefilter("ignore")
    from src.eda.feature_interactions.history import long_table
    from src.eda.feature_interactions.panel import panel
    P = panel(max_season=2024)
    L = long_table()
    Q = P.assign(**prepare_b7(P, L))
    res = diagnostics(Q, L)
    print(S.write_diag("f07_evidence_age", res))
    print(json.dumps(res, indent=1, default=str)[:6000])
