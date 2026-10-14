"""DROPPED (orchestrator decision, 6 Oct 2026; every member failed a pre-declared result-free gate): no row in HYPOTHESES.
Block B4, matchup-specific serve-point deviations (I-018, I-019, I-021): a signed sum, sign +, weight 0.5, trait fixed
(hand, permuted within tour by the batch). Men-only in substance (rulings N10); pooled. Every member is a field statistic
built on the leak-proof clock: a match's residual counts from lf + 1, a target reads the state as of its es; probe().

Residual of a serve: r = logit((spw_n + 1/2)/(spw_d + 1)) - (mu + O^spw_S - D^spw_R), the surface-IOS expectation
(srf_O_eff_spw, srf_D_eff_spw, leak-proof, as of that match), on pool matches (main tour, qualifying, Challengers) with
a box score (at least 20 serve points, completed or retired).

I-018 (+)  style-pair residual table (MEC-10): k = 6 styles per tour by k-means (fixed seed) on standardised pooled IOS
           (cur_O_spw, cur_D_spw, cur_O_ace, cur_O_first_in, cur_O_df) and hand (1 = left), fitted on 2010-2016 rows and
           frozen; each player's style at each match is the nearest centroid. tau_ij = sum n r / (sum n + 20,000) over
           serves of style i to style j released by es (per tour; the 36 cells ride as context columns). x =
           tau_{s(A)s(B)} - tau_{s(B)s(A)}, the styles recomputed in combine from the panel's IOS and hand.
I-019 (+)  points-based head-to-head residual (MEC-11): r_AB = sum_k (u^A_k - u^B_k) / (sum_k points_k + 1,000) over
           the pair's earlier meetings, u = serve points won - the IOS expectation x serve points; 0 without a meeting.
I-021 (+)  left-hand deviation (MEC-09): G_A L_B - G_B L_A, L = 1 for a left-hander, G = E + F: E_S = sum n r /
           (sum n + K_E) over S's serves to left-handed returners, F_R = -sum n r / (sum n + K_F) over left-handed
           servers' serves to R (a two-stage version of the extended IOS's ridge-shrunk deviations, the base IOS fixed).
Controls (per member, final family): style-indicator and clustering-input differences (I-018); Delta O^spw, Delta D^spw
and 1[no earlier meeting] x eta (I-019); Delta G, Delta L, Sigma G x eta, Sigma L x eta, miss_hand (I-021); nearest inputs.
Constants: k = 6 and the 2010-2016 fit (MEC-10); 1,000 points (MEC-11); K_tau = 20,000 points (fixed in advance; cells
hold 10^5-10^6 points); K_E, K_F by method of moments on 2010-2018 statistics (eb_hand). Gates (result-free): I-018
2010-2016 against 2017-2021 cell-by-cell corr >= 0.3; I-019 meeting-to-meeting corr >= 0.05 (pairs with 3+ meetings);
I-021 odd/even-season corr of F_R >= 0.15 for right-handed returners with 1,500+ return points against left-handers,
above a shuffled-hand placebo. Reads no result. Run: ./python.sh src/eda/feature_interactions/features/f05_matchup.py
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.features import f01_structure_lib as S  # noqa: E402

K_STYLES, STYLE_YEARS, SEED = 6, (2010, 2016), 20261006
STYLE_IOS = ("cur_O_spw", "cur_D_spw", "cur_O_ace", "cur_O_first_in", "cur_O_df")
PANEL_IOS = {"cur_O_spw": "ios_curO_spw", "cur_D_spw": "ios_curD_spw", "cur_O_ace": "ios_curO_ace",
             "cur_O_first_in": "ios_curO_first_in", "cur_O_df": "ios_curO_df"}
K_TAU, K_H2H = 20000.0, 1000.0
# eb_hand (2010-2018): tau^2 of E 0.00034 (men) / 0.00082 (women), of F 0.00025 / 0.00028 (logit^2), so K in serve points:
K_HAND = {"E": {"atp": 29739.0, "wta": 11483.0}, "F": {"atp": 39987.0, "wta": 36047.0}}
# Gates (result-free; diagnostics): I-021's F_R odd/even-season r 0.071 (men, 423 right-handed returners with 1,500+
# return points against left-handers; shuffled-hand placebo 95th percentile 0.086) and 0.026 (women, 98; placebo 0.207):
# below 0.15 and not above the placebo, so I-021 drops. I-019: the meeting-to-meeting corr is 0.032 (men, 5,590 pairs)
# and 0.043 (women, 2,186), 2010-2018 (0.033 / 0.045 on 2010-2021), below 0.05: I-019 drops. I-018: the 2010-2016
# against 2017-2021 cell-by-cell corr is 0.528 for men (contrast 0.466) and -0.065 for women (0.014): the audit's gate
# (>= 0.3) passes for men only, so the member is kept for men's rows (MEN_ONLY_I018; women's rows 0), in line with the
# rulings' "B4 is men-only in substance (N10)". The originator's second condition, an out-of-sample serve-point gain of
# 0.02 milli per point, is not met (men +0.002, women -0.016): flagged for the auditor, not applied (the audit's card
# kept only the stability gate).
KEEP = {"I-018": True, "I-019": False, "I-021": False}
MEN_ONLY_I018 = True
STD_B4 = ("iosO_hold", "iosO_first_won", "elo_overall")   # nearest to the kept block, 2014-2021 (0.34, 0.33, 0.30)
STAT_COLS = ["spw_n", "spw_d", "rpw_n", "rpw_d", "won"]


def hand_num(h) -> np.ndarray:
    h = pd.Series(np.asarray(h, dtype=object)).astype(str)
    return np.where(h == "L", 1.0, np.where(h == "R", 0.0, np.nan))


def serve_rows(L: pd.DataFrame) -> pd.DataFrame:
    """One row per (pool match, server) with a usable box score: the residual against the surface IOS, the clock days,
    both players' pooled IOS (for styles) and hands, the pair key."""
    H = S.history_ios(L, ["srf_O_eff_spw", "srf_D_eff_spw"] + list(STYLE_IOS))
    tour, surf = L["tour"].astype(str).to_numpy(), L["surface"].astype(str).to_numpy()
    off = S.mu(L, "spw", tour, surf) + H[("own", "srf_O_eff_spw")] - H[("opp", "srf_D_eff_spw")]
    n, d = S.num(L, "spw_n"), S.num(L, "spw_d")
    ok = np.isfinite(off) & (d >= 20) & np.isfinite(n) & L["status"].astype(str).isin(["completed", "retired"]).to_numpy()
    hands = S.player_hands()
    R = pd.DataFrame({"match_id": L["match_id"].astype(str).to_numpy(), "srv": L["player_id"].astype(str).to_numpy(),
                      "ret": L["opponent_id"].astype(str).to_numpy(), "tour": tour,
                      "year": pd.to_datetime(L["tournament_date"]).dt.year.to_numpy(),
                      "es": S.num(L, "es"), "lf": S.num(L, "lf"), "n": d, "won": n,
                      "r": S.lg((n + 0.5) / (d + 1)) - off, "pi": expit(off)})
    for c in STYLE_IOS:
        R[f"own_{c}"], R[f"opp_{c}"] = H[("own", c)], H[("opp", c)]
    R["L_srv"] = hand_num(R["srv"].map(hands))
    R["L_ret"] = hand_num(R["ret"].map(hands))
    # a canonical row order (match, server), so that the frozen k-means fit and every sum are independent of the
    # history table's own row order
    return R[ok].sort_values(["match_id", "srv"], kind="stable").reset_index(drop=True)


def style_model(R: pd.DataFrame) -> dict:
    """Per tour: (mean, sd, centroids) of the k-means styles on standardised (pooled IOS, hand), 2010-2016 serve rows
    (each row's server), fixed seed. Frozen: later matches are only assigned to the nearest centroid."""
    from sklearn.cluster import KMeans
    out = {}
    for t in ("atp", "wta"):
        k = (R["tour"].to_numpy() == t) & R["year"].between(*STYLE_YEARS).to_numpy()
        X = np.column_stack([R[f"own_{c}"].to_numpy(float)[k] for c in STYLE_IOS] + [R["L_srv"].to_numpy(float)[k]])
        X = X[np.isfinite(X).all(axis=1)]
        mean, sd = X.mean(axis=0), X.std(axis=0)
        km = KMeans(n_clusters=K_STYLES, n_init=20, random_state=SEED).fit((X - mean) / sd)
        order = np.argsort(km.cluster_centers_[:, 0])               # styles numbered by serve-point offence
        out[t] = (mean, sd, km.cluster_centers_[order])
    return out


def style_dist(model: dict, tour: np.ndarray, ios: np.ndarray, hand: np.ndarray) -> np.ndarray:
    """Squared distances (n, k) of each (IOS row, hand) to its tour's centroids; NaN where an input is missing."""
    out = np.full((len(tour), K_STYLES), np.nan)
    for t, (mean, sd, cen) in model.items():
        m = tour == t
        Z = (np.column_stack([ios[m], hand[m]]) - mean) / sd
        out[m] = ((Z[:, None, :] - cen[None, :, :]) ** 2).sum(axis=2)
    return out


def assign(dist: np.ndarray) -> np.ndarray:
    ok = np.isfinite(dist).all(axis=1)
    return np.where(ok, np.argmin(np.nan_to_num(dist, nan=np.inf), axis=1), -1)


def _ids(*arrays) -> pd.Index:
    return pd.Index(pd.unique(np.concatenate([np.asarray(a, dtype=object) for a in arrays])))


def tau_state(P: pd.DataFrame, R: pd.DataFrame, model: dict) -> dict:
    """The 36 cells of each panel match's tour table as of its es (context columns f05_tau_ij)."""
    sv = assign(style_dist(model, R["tour"].to_numpy(), R[[f"own_{c}" for c in STYLE_IOS]].to_numpy(float),
                           R["L_srv"].to_numpy(float)))
    rt = assign(style_dist(model, R["tour"].to_numpy(), R[[f"opp_{c}" for c in STYLE_IOS]].to_numpy(float),
                           R["L_ret"].to_numpy(float)))
    ok = (sv >= 0) & (rt >= 0)
    toff = np.where(R["tour"].to_numpy() == "atp", 0, 100)
    key = (toff + sv * K_STYLES + rt)[ok]
    V = np.column_stack([R["n"].to_numpy(float) * R["r"].to_numpy(float), R["n"].to_numpy(float)])[ok]
    rel = R["lf"].to_numpy(float)[ok] + 1.0
    ptoff = np.where(P["tour"].astype(str).to_numpy() == "atp", 0, 100)
    out = {}
    for i in range(K_STYLES):
        for j in range(K_STYLES):
            sm = S.clock_sum(key, rel, V, ptoff + i * K_STYLES + j, S.num(P, "es"))
            out[f"f05_tau_{i}{j}"] = sm[:, 0] / (sm[:, 1] + K_TAU)
    return out


def hand_state(P: pd.DataFrame, R: pd.DataFrame) -> dict:
    """E (serving to left-handers) and F (returning against left-handed servers) per panel player, on the clock."""
    ids = _ids(R["srv"], R["ret"], P["player_a_id"].astype(str), P["player_b_id"].astype(str))
    rel = R["lf"].to_numpy(float) + 1.0
    nr, n = R["n"].to_numpy(float) * R["r"].to_numpy(float), R["n"].to_numpy(float)
    e_src = R["L_ret"].to_numpy(float) == 1.0
    f_src = R["L_srv"].to_numpy(float) == 1.0
    out = {}
    for side, col in (("a", "player_a_id"), ("b", "player_b_id")):
        tgt = ids.get_indexer(P[col].astype(str))
        KE = P["tour"].astype(str).map(K_HAND["E"]).to_numpy(dtype=float)
        KF = P["tour"].astype(str).map(K_HAND["F"]).to_numpy(dtype=float)
        e = S.clock_sum(ids.get_indexer(R["srv"][e_src]), rel[e_src], np.column_stack([nr[e_src], n[e_src]]), tgt,
                        S.num(P, "es"))
        f = S.clock_sum(ids.get_indexer(R["ret"][f_src]), rel[f_src], np.column_stack([nr[f_src], n[f_src]]), tgt,
                        S.num(P, "es"))
        out[f"f05_E_{side}"] = e[:, 0] / (e[:, 1] + KE)
        out[f"f05_F_{side}"] = -f[:, 0] / (f[:, 1] + KF)
        out[f"f05_nE_{side}"], out[f"f05_nF_{side}"] = e[:, 1], f[:, 1]
    return out


def h2h_state(P: pd.DataFrame, R: pd.DataFrame) -> dict:
    """Earlier meetings released by es: U_X = sum of X's serve-point excess (won - expected) against this opponent, the
    pair's total serve points and the number of meetings."""
    u = R["won"].to_numpy(float) - R["pi"].to_numpy(float) * R["n"].to_numpy(float)
    dkey = (R["srv"] + "|" + R["ret"]).to_numpy()
    ids = _ids(dkey, P["player_a_id"].astype(str) + "|" + P["player_b_id"].astype(str),
               P["player_b_id"].astype(str) + "|" + P["player_a_id"].astype(str))
    src = ids.get_indexer(dkey)
    rel = R["lf"].to_numpy(float) + 1.0
    V = np.column_stack([u, R["n"].to_numpy(float), np.ones(len(R))])
    ab = ids.get_indexer(P["player_a_id"].astype(str) + "|" + P["player_b_id"].astype(str))
    ba = ids.get_indexer(P["player_b_id"].astype(str) + "|" + P["player_a_id"].astype(str))
    sa = S.clock_sum(src, rel, V, ab, S.num(P, "es"))
    sb = S.clock_sum(src, rel, V, ba, S.num(P, "es"))
    return {"f05_u_a": sa[:, 0], "f05_u_b": sb[:, 0], "f05_h2h_pts": sa[:, 1] + sb[:, 1],
            "f05_h2h_n": np.maximum(sa[:, 2], sb[:, 2])}


def panel_style_dists(P: pd.DataFrame, model: dict) -> dict:
    """Per side and per hand value (0, 1): the squared distances to the k centroids from the panel's pooled IOS, so that
    combine can assign styles under any (permuted) hand."""
    out = {}
    tour = P["tour"].astype(str).to_numpy()
    for side in ("a", "b"):
        ios = np.column_stack([S.num(P, f"{PANEL_IOS[c]}_{side}") for c in STYLE_IOS])
        for h in (0, 1):
            dist = style_dist(model, tour, ios, np.full(len(P), float(h)))
            for k in range(K_STYLES):
                out[f"f05_sd{h}_{k}_{side}"] = dist[:, k]
    return out


def prepare_b4(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    R = serve_rows(S.cut_history(L, P))
    model = style_model(R)
    hand = {"hand_a": hand_num(P["hand_a"]), "hand_b": hand_num(P["hand_b"])}
    return hand | panel_style_dists(P, model) | tau_state(P, R, model) | hand_state(P, R) | h2h_state(P, R)


def styles(P: pd.DataFrame, side: str) -> np.ndarray:
    h = S.num(P, f"hand_{side}")
    d = np.column_stack([np.where(h == 1, S.num(P, f"f05_sd1_{k}_{side}"), S.num(P, f"f05_sd0_{k}_{side}"))
                         for k in range(K_STYLES)])
    d[~np.isfinite(h)] = np.nan
    return assign(d)


def x_i018(P: pd.DataFrame) -> np.ndarray:
    """tau_{s(A)s(B)} - tau_{s(B)s(A)}; 0 on women's rows while MEN_ONLY_I018 (the gate passes for men only)."""
    sa, sb = styles(P, "a"), styles(P, "b")
    T = np.column_stack([S.num(P, f"f05_tau_{i}{j}") for i in range(K_STYLES) for j in range(K_STYLES)])
    rows = np.arange(len(P))
    ok = (sa >= 0) & (sb >= 0)
    ia, ib = np.maximum(sa, 0), np.maximum(sb, 0)
    x = np.where(ok, T[rows, ia * K_STYLES + ib] - T[rows, ib * K_STYLES + ia], np.nan)
    return np.where(S.is_atp(P), x, 0.0) if MEN_ONLY_I018 else x


def x_i019(P: pd.DataFrame) -> np.ndarray:
    return (S.num(P, "f05_u_a") - S.num(P, "f05_u_b")) / (S.num(P, "f05_h2h_pts") + K_H2H)


def g_side(P: pd.DataFrame, side: str) -> np.ndarray:
    return S.num(P, f"f05_E_{side}") + S.num(P, f"f05_F_{side}")


def x_i021(P: pd.DataFrame) -> np.ndarray:
    return g_side(P, "a") * S.num(P, "hand_b") - g_side(P, "b") * S.num(P, "hand_a")


def combine_b4(P: pd.DataFrame) -> dict:
    La, Lb = S.num(P, "hand_a"), S.num(P, "hand_b")
    members, cols, mods, tab = [], [], [], {}
    if KEEP["I-018"]:
        x18 = x_i018(P)
        members.append((x18, "+"))
        sa, sb = styles(P, "a"), styles(P, "b")
        cols += [(f"style{k}", np.where((sa >= 0) & (sb >= 0), (sa == k).astype(float) - (sb == k).astype(float), 0.0))
                 for k in range(1, K_STYLES)]
        cols += [(f"d_{c}", S.num(P, f"{PANEL_IOS[c]}_a") - S.num(P, f"{PANEL_IOS[c]}_b")) for c in STYLE_IOS]
        tab["f05_style_pair"] = (x18, "diff", None)
    if KEEP["I-019"]:
        x19 = x_i019(P)
        members.append((x19, "+"))
        cols += [("dO_spw", S.ios(P, "srfO", "spw", "a") - S.ios(P, "srfO", "spw", "b")),
                 ("dD_spw", S.ios(P, "srfD", "spw", "a") - S.ios(P, "srfD", "spw", "b"))]
        mods.append(S.centre_disc(P, (S.num(P, "f05_h2h_n") < 0.5).astype(float), None))
        tab["f05_h2h_points"] = (x19, "diff", None)
    if KEEP["I-021"]:
        x21 = x_i021(P)
        members.append((x21, "+"))
        ga, gb = g_side(P, "a"), g_side(P, "b")
        cols += [("d_G", ga - gb), ("miss_hand", S.miss_diff(La, Lb))]
        mods += [np.nan_to_num(S.centre_disc(P, ga + gb, None)), np.nan_to_num(S.centre_disc(P, La + Lb, None))]
        tab["f05_lefty_dev"] = (x21, "diff", None)
    cols += [("d_hand", np.nan_to_num(La - Lb))] + [(f"in_{n}", S.num(P, f"in_{n}")) for n in STD_B4]
    Cm, names = S.pack(cols)
    return {"x": S.signed_block(P, members), "controls": Cm, "control_names": names,
            "eta_mod_controls": np.column_stack(mods) if mods else None, "tabpfn": tab}


# DROPPED (plan.md, orchestrator decision of 6 Oct 2026: pre-declared result-free gates are binding as declared). Every
# member failed one: I-019 and I-021 their persistence gates, I-018 MEC-10's out-of-sample serve-point condition on
# both tours (+0.002 and -0.016 milli per point, against 0.02). No row is registered; the builders, gates, probe and
# diagnostics stay importable (B4_SPEC is the row as it was built).
B4_SPEC = {"hid": "B4", "master": "+".join(k for k, v in KEEP.items() if v), "kind": "X", "sign": "+", "weight": 0.5,
           "trait": "fixed", "trait_cols": ["hand"], "deployment": "diff", "family": "03/04",
           "prepare": prepare_b4, "combine": combine_b4}
HYPOTHESES: list = []


def eb_hand(R: pd.DataFrame, years=(2010, 2018)) -> dict:
    """Method of moments for K_E and K_F (serve points), 2010-2018 statistics: per player, the points-weighted mean
    residual against left-handers, m_p = sum n r / N, with sampling variance sum n^2 r^2 / N^2; tau^2 = the between-
    player variance of m_p minus the mean sampling variance; K = the per-match variance x mean match points / tau^2."""
    out = {}
    yr = R["year"].to_numpy()
    for kind, key, mask in (("E", "srv", R["L_ret"].to_numpy(float) == 1.0), ("F", "ret", R["L_srv"].to_numpy(float) == 1.0)):
        out[kind] = {}
        for t in ("atp", "wta"):
            m = mask & (R["tour"].to_numpy() == t) & (yr >= years[0]) & (yr <= years[1])
            n, r = R["n"].to_numpy(float)[m], R["r"].to_numpy(float)[m]
            df = pd.DataFrame({"p": R[key].to_numpy()[m], "nr": n * r, "n": n, "n2r2": (n * r) ** 2, "r2": r * r})
            g = df.groupby("p").agg(nr=("nr", "sum"), n=("n", "sum"), n2r2=("n2r2", "sum"), k=("n", "size"))
            g = g[g["k"] >= 5]
            mp = g["nr"] / g["n"]
            sv = g["n2r2"] / g["n"] ** 2
            mbar = float(np.average(mp, weights=g["n"]))
            tau2 = float(np.average((mp - mbar) ** 2, weights=g["n"]) - np.average(sv, weights=g["n"]))
            v_match, nbar = float(df["r2"].mean()), float(df["n"].mean())
            out[kind][t] = {"players": int(len(g)), "var_per_match": v_match, "mean_points": nbar, "tau2": tau2,
                            "K": float(v_match * nbar / tau2) if tau2 > 0 else float("inf")}
    return out


def gate_i021(R: pd.DataFrame, years=(2010, 2021), min_pts: float = 1500.0, n_placebo: int = 20) -> dict:
    """F_R for right-handed returners against left-handed servers, odd against even seasons (players with 1,500+
    such return points in total); the same with server hands shuffled within tour (placebo)."""
    rng = np.random.default_rng(SEED)

    def corr(Lsrv):
        m = (Lsrv == 1.0) & (R["L_ret"].to_numpy(float) == 0.0) & R["year"].between(*years).to_numpy()
        df = pd.DataFrame({"p": R["ret"].to_numpy()[m], "t": R["tour"].to_numpy()[m], "odd": R["year"].to_numpy()[m] % 2,
                           "nr": (R["n"] * R["r"]).to_numpy()[m], "n": R["n"].to_numpy()[m]})
        g = df.groupby(["t", "p", "odd"])[["nr", "n"]].sum().unstack("odd").dropna()
        g = g[(g[("n", 0)] + g[("n", 1)]) >= min_pts]
        res = {}
        for t in ("atp", "wta"):
            if t not in g.index.get_level_values(0):
                continue
            x = g.loc[t]
            f0, f1 = -x[("nr", 0)] / x[("n", 0)], -x[("nr", 1)] / x[("n", 1)]
            res[t] = (int(len(x)), float(np.corrcoef(f0, f1)[0, 1]) if len(x) > 10 else np.nan)
        return res
    obs = corr(R["L_srv"].to_numpy(float))
    plac = {t: [] for t in ("atp", "wta")}
    srv_ids = R["srv"].to_numpy()
    for _ in range(n_placebo):
        Ls = R["L_srv"].to_numpy(float).copy()
        for t in ("atp", "wta"):
            m = R["tour"].to_numpy() == t
            u = pd.unique(srv_ids[m])
            hmap = pd.Series(R["L_srv"].to_numpy(float)[m], index=srv_ids[m]).groupby(level=0).first()
            perm = pd.Series(rng.permutation(hmap.reindex(u).to_numpy()), index=u)
            Ls[m] = pd.Series(srv_ids[m]).map(perm).to_numpy(dtype=float)
        for t, v in corr(Ls).items():
            plac[t].append(v[1])
    return {t: {"returners": obs[t][0], "odd_even_r": obs[t][1], "placebo_mean": float(np.nanmean(plac[t])),
                "placebo_q95": float(np.nanquantile(plac[t], 0.95)), "gate": 0.15,
                "passes": bool(obs[t][1] >= 0.15 and obs[t][1] > np.nanquantile(plac[t], 0.95))} for t in obs}


def _rows_styles(R: pd.DataFrame, model: dict) -> tuple[np.ndarray, np.ndarray]:
    t = R["tour"].to_numpy()
    sv = assign(style_dist(model, t, R[[f"own_{c}" for c in STYLE_IOS]].to_numpy(float), R["L_srv"].to_numpy(float)))
    rt = assign(style_dist(model, t, R[[f"opp_{c}" for c in STYLE_IOS]].to_numpy(float), R["L_ret"].to_numpy(float)))
    return sv, rt


def gate_i018(R: pd.DataFrame, model: dict) -> dict:
    """tau from 2010-2016 against tau from 2017-2021, cell by cell (36 cells per tour) and for the contrast tau_ij -
    tau_ji (15 pairs); and the serve-point log loss on 2017-2021 with the 2010-2016 table added (milli per point,
    lower is better; MEC-10 kills below a 0.02 gain)."""
    sv, rt = _rows_styles(R, model)
    yr, out = R["year"].to_numpy(), {}
    for t in ("atp", "wta"):
        base = (R["tour"].to_numpy() == t) & (sv >= 0) & (rt >= 0)
        tabs = []
        for lo, hi in ((2010, 2016), (2017, 2021)):
            m = base & (yr >= lo) & (yr <= hi)
            df = pd.DataFrame({"c": sv[m] * K_STYLES + rt[m], "nr": (R["n"] * R["r"]).to_numpy()[m], "n": R["n"].to_numpy()[m]})
            g = df.groupby("c")[["nr", "n"]].sum().reindex(range(K_STYLES ** 2)).fillna(0.0)
            tabs.append((g["nr"] / (g["n"] + K_TAU)).to_numpy())
        T1, T2 = tabs
        iu = [(i, j) for i in range(K_STYLES) for j in range(i + 1, K_STYLES)]
        c1 = np.array([T1[i * K_STYLES + j] - T1[j * K_STYLES + i] for i, j in iu])
        c2 = np.array([T2[i * K_STYLES + j] - T2[j * K_STYLES + i] for i, j in iu])
        m = base & (yr >= 2017) & (yr <= 2021)
        pi0 = R["pi"].to_numpy()[m]
        pi1 = expit(S.lg(pi0) + T1[sv[m] * K_STYLES + rt[m]])
        nn, ww = R["n"].to_numpy()[m], R["won"].to_numpy()[m]
        out[t] = {"cells_corr": float(np.corrcoef(T1, T2)[0, 1]), "contrast_corr": float(np.corrcoef(c1, c2)[0, 1]),
                  "tau_sd_2010_16": float(np.std(T1)), "contrast_sd_2010_16": float(np.std(c1)),
                  "oos_gain_milli_per_point": 1000 * (S.binom_ll(ww, nn, pi0) - S.binom_ll(ww, nn, pi1)),
                  "rows_2017_21": int(m.sum())}
    out["passes_0.3"] = bool(min(v["cells_corr"] for k, v in out.items() if isinstance(v, dict)) >= 0.3)
    return out


def gate_i019(R: pd.DataFrame, years=(2010, 2018)) -> dict:
    """Pairs with 3+ meetings: the correlation of each meeting's residual per point (min-id player's serve excess minus
    the other's) with the cumulative residual per point of the pair's earlier meetings (MEC-11's kill below 0.05)."""
    m = R["year"].between(*years).to_numpy()
    df = R[m][["match_id", "srv", "ret", "tour", "lf", "won", "pi", "n"]].copy()
    df["u"] = df["won"] - df["pi"] * df["n"]
    df["lo"] = np.where(df["srv"] < df["ret"], df["srv"], df["ret"])
    df["hi"] = np.where(df["srv"] < df["ret"], df["ret"], df["srv"])
    df["su"] = np.where(df["srv"] == df["lo"], df["u"], -df["u"])
    g = df.groupby(["match_id", "tour", "lo", "hi"]).agg(su=("su", "sum"), n=("n", "sum"), lf=("lf", "first"),
                                                        k=("su", "size")).reset_index()
    g = g[g["k"] == 2].sort_values(["lo", "hi", "lf"])
    g["cnt"] = g.groupby(["lo", "hi"])["su"].transform("size")
    g = g[g["cnt"] >= 3].copy()
    grp = g.groupby(["lo", "hi"])
    g["prev_su"], g["prev_n"] = grp["su"].cumsum() - g["su"], grp["n"].cumsum() - g["n"]
    h = g[g["prev_n"] > 0]
    out = {}
    for t in ("atp", "wta"):
        x = h[h["tour"] == t]
        out[t] = {"pairs": int(x[["lo", "hi"]].drop_duplicates().shape[0]), "meetings": int(len(x)),
                  "corr": float(np.corrcoef(x["prev_su"] / x["prev_n"], x["su"] / x["n"])[0, 1])}
    out["passes_0.05"] = bool(min(v["corr"] for k, v in out.items() if isinstance(v, dict)) >= 0.05)
    return out


def probe(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    """Probe-equivalent of the three field statistics (tau cells, E and F, the head-to-head sums): every later result
    reversed; no panel match starting by the cut may move. Constants (the frozen style centroids, K) held fixed."""
    Lc = S.cut_history(L, P)
    model = style_model(serve_rows(Lc))

    def build(LL):
        R = serve_rows(LL)
        st = tau_state(P, R, model) | hand_state(P, R) | h2h_state(P, R)
        return np.column_stack([st[k] for k in sorted(st)])
    return S.probe_check(build, Lc, P, STAT_COLS)


def diagnostics(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    R = serve_rows(S.cut_history(L, P))
    model = style_model(R)
    d = S.disc(P)
    out = {"style_sizes_2010_2016": {}, "eb_hand": eb_hand(R), "gate_I-018": gate_i018(R, model),
           "gate_I-019": gate_i019(R), "gate_I-019_2010_2021": gate_i019(R, (2010, 2021)), "gate_I-021": gate_i021(R)}
    sv, _ = _rows_styles(R, model)
    for t in ("atp", "wta"):
        m = (R["tour"].to_numpy() == t) & R["year"].between(*STYLE_YEARS).to_numpy() & (sv >= 0)
        out["style_sizes_2010_2016"][t] = np.bincount(sv[m], minlength=K_STYLES).tolist()
        out.setdefault("centroids", {})[t] = np.round(model[t][2], 2).tolist()
    members = {"I-018": x_i018(P), "I-019": x_i019(P), "I-021": x_i021(P)}
    out["members"] = {k: {"r2_on_58": S.r2_on_58(P, v), "nearest": S.nearest(P, v, 4),
                          "coverage_disc": float(np.isfinite(v[d]).mean()),
                          "share_nonzero_disc": float(np.mean(np.nan_to_num(v[d]) != 0))} for k, v in members.items()}
    x = combine_b4(P)["x"]
    out["block"] = {"r2_on_58": S.r2_on_58(P, x), "nearest": S.nearest(P, x, 5)}
    out["probe"] = probe(P, L)
    return out


if __name__ == "__main__":
    import json
    import warnings
    warnings.simplefilter("ignore")
    from src.eda.feature_interactions.history import long_table
    from src.eda.feature_interactions.panel import panel
    P = panel(max_season=2024)
    L = long_table()
    res = diagnostics(P.assign(**prepare_b4(P, L)), L)
    print(S.write_diag("f05_matchup", res))
    print(json.dumps(res, indent=1, default=str)[:5000])
