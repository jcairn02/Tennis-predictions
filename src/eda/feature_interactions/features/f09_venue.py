"""Block B-VENUE, venue conditions x serve profile (I-072 with I-077 folded in, I-073): a signed sum, sign +, weight 0.5,
trait slow. Both members are field statistics built on the leak-proof clock (a result counts from lf + 1; a target
reads the state as of its es); probe() is their probe-equivalent.

I-072 (+)  leak-proof venue pace x ace offence (MEC-03): x = v_e * Delta O^ace, v_e = sum_j w_j u_j / (sum_j w_j n_j +
           2,000) over the venue's serves released by es (earlier editions and the current edition's earlier days,
           qualifying included), u_j = (aces_j - pi_j n_j) / (pi_j (1 - pi_j)) (the logit-scale ace excess of a serve row,
           pi = expit(mu_ace + O^ace_S - D^ace_R) from the surface IOS as of that match), n_j its serve points,
           w_j = 2^(-years/2) (MEC-03's constants). Venue = tour x normalised tournament name x surface.
I-073 (+)  per-player indoor deviations (MEC-13): x = I * [(G_A - H_B) - (G_B - H_A)] = I * (Delta G + Delta H): G_S =
           sum n r / (sum n + K_G) over S's indoor serves, H_R = -sum n r / (sum n + K_H) over serves to R indoors (a
           two-stage version of the extended IOS y = mu + O - D + I (G_S - H_R), the base IOS fixed), r the serve-point
           logit residual against the surface IOS. Indoor: Stage 0's flag (men's main tour), else tennis-data.co.uk's
           Court (both tours' main tour; f25_switch's join), else the event's majority; I of the match the same way.
Controls (final family, plus the S-type main effect of I-073 from its round-1 card): Delta O^ace; Delta G + Delta H;
nearest inputs; eta-modulators v_e and I (centred).
Constants: 2,000 points and the 2-year half-life (MEC-03); K_G, K_H by method of moments on 2010-2018 statistics.
Gates (result-free): I-072 venue carry-over, the pace from earlier editions against the edition's own residual, r >=
0.3 (2014-2021 editions); I-073 odd/even-season carry-over of G and H >= 0.15. Reads no result.
Run (diagnostics, gates, probe): ./python.sh src/eda/feature_interactions/features/f09_venue.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.features import f01_structure_lib as S  # noqa: E402

K_V, TAU_V = 2000.0, 730.5 / np.log(2.0)
# eb_indoor (2010-2018 indoor serve rows): tau^2 of G 0.00080 (men) / 0.00024 (women), of H 0.00073 / below 0 (capped)
K_IND = {"G": {"atp": 12102.0, "wta": 41269.0}, "H": {"atp": 13250.0, "wta": 100000.0}}
# Gates (result-free; diagnostics): I-072's venue carry-over r = 0.661 (men, 1,356 editions of 2014-2021 with 2,000+
# serve points) and 0.566 (women, 300): passes (>= 0.3). I-073's odd/even-season carry-over: G -0.006 (men, 177
# players) / -0.083 (women, 83), H 0.124 / 0.077, all below 0.15: I-073 drops; B-VENUE keeps I-072.
KEEP = {"I-072": True, "I-073": False}
STD_VENUE = ("prod_hold", "prod_first_won", "prod_bp_saved")   # nearest to v_e x Delta O^ace, 2014-2021 (-0.11, -0.10, -0.09)
STAT_COLS = ["spw_n", "spw_d", "rpw_n", "rpw_d", "ace", "df", "svpt", "first_in", "first_won", "second_won", "won"]


def venue_key(tour, name, surface) -> np.ndarray:
    nm = pd.Series(np.asarray(name, dtype=object)).astype(str).str.lower().map(lambda s: re.sub(r"[^a-z0-9]", "", s))
    return (pd.Series(np.asarray(tour, dtype=object)).astype(str) + "|" + nm + "|"
            + pd.Series(np.asarray(surface, dtype=object)).astype(str)).to_numpy()


def indoor_rows(L: pd.DataFrame, max_season: int) -> np.ndarray:
    """1 indoor, 0 outdoor, NaN unknown per history row: Stage 0's flag, else tennis-data's Court, else the event's
    majority among its known rows."""
    from src.eda.feature_interactions.features.f25_switch import _court_by_match
    s0 = L["indoor"].map({True: 1.0, False: 0.0, "True": 1.0, "False": 0.0}).astype(float).to_numpy()
    court = L["match_id"].astype(str).map(_court_by_match(max_season)).to_numpy(float)
    known = np.where(np.isfinite(s0), s0, court)
    ev = pd.Series(known).groupby(L["tournament_id"].astype(str).to_numpy()).transform("mean").to_numpy()
    return np.where(np.isfinite(known), known, np.where(np.isfinite(ev), np.round(ev), np.nan))


def serve_rows(L: pd.DataFrame, max_season: int) -> pd.DataFrame:
    """One row per (pool match, server) with a box score: the ace excess (u, n) and the serve-point residual r."""
    H = S.history_ios(L, ["srf_O_eff_ace", "srf_D_eff_ace", "srf_O_eff_spw", "srf_D_eff_spw"])
    tour, surf = L["tour"].astype(str).to_numpy(), L["surface"].astype(str).to_numpy()
    pi = expit(S.mu(L, "ace", tour, surf) + H[("own", "srf_O_eff_ace")] - H[("opp", "srf_D_eff_ace")])
    a, n = S.history_stat(L, "ace")
    off = S.mu(L, "spw", tour, surf) + H[("own", "srf_O_eff_spw")] - H[("opp", "srf_D_eff_spw")]
    sn, sd = S.num(L, "spw_n"), S.num(L, "spw_d")
    good = L["status"].astype(str).isin(["completed", "retired"]).to_numpy()
    R = pd.DataFrame({"srv": L["player_id"].astype(str).to_numpy(), "ret": L["opponent_id"].astype(str).to_numpy(),
                      "tour": tour, "year": pd.to_datetime(L["tournament_date"]).dt.year.to_numpy(),
                      "venue": venue_key(tour, L["tournament_name"], surf), "edition": L["tournament_id"].astype(str).to_numpy(),
                      "es": S.num(L, "es"), "lf": S.num(L, "lf"), "indoor": indoor_rows(L, max_season),
                      "u": np.where(good & (n >= 20) & np.isfinite(pi) & np.isfinite(a), (a - pi * n) / (pi * (1 - pi)), np.nan),
                      "n_ace": np.where(good & (n >= 20) & np.isfinite(pi) & np.isfinite(a), n, np.nan),
                      "r": np.where(good & (sd >= 20) & np.isfinite(off), S.lg((sn + 0.5) / (sd + 1)) - off, np.nan),
                      "n": np.where(good & (sd >= 20) & np.isfinite(off), sd, np.nan)})
    R = R[np.isfinite(R["u"]) | np.isfinite(R["r"])]
    R = R.assign(_m=L["match_id"].astype(str).to_numpy()[R.index.to_numpy()])
    R = R.sort_values(["_m", "srv"], kind="stable").drop(columns="_m")   # canonical order: sums independent
    return R.reset_index(drop=True)                                     # of the history table's row order


def venue_state(P: pd.DataFrame, R: pd.DataFrame) -> np.ndarray:
    ok = np.isfinite(R["u"].to_numpy(float))
    keys = pd.Index(pd.unique(np.r_[R["venue"].to_numpy()[ok],
                                    venue_key(P["tour"], P["tournament_name"], P["surface"])]))
    sm = S.clock_sum(keys.get_indexer(R["venue"].to_numpy()[ok]), R["lf"].to_numpy(float)[ok] + 1.0,
                     np.column_stack([R["u"].to_numpy(float)[ok], R["n_ace"].to_numpy(float)[ok]]),
                     keys.get_indexer(venue_key(P["tour"], P["tournament_name"], P["surface"])), S.num(P, "es"), tau=TAU_V)
    return sm[:, 0] / (sm[:, 1] + K_V)


def indoor_state(P: pd.DataFrame, R: pd.DataFrame) -> dict:
    ok = np.isfinite(R["r"].to_numpy(float)) & (R["indoor"].to_numpy(float) == 1.0)
    ids = pd.Index(pd.unique(np.r_[R["srv"].to_numpy(), R["ret"].to_numpy(), P["player_a_id"].astype(str).to_numpy(),
                                   P["player_b_id"].astype(str).to_numpy()]))
    V = np.column_stack([(R["n"] * R["r"]).to_numpy(float)[ok], R["n"].to_numpy(float)[ok]])
    rel = R["lf"].to_numpy(float)[ok] + 1.0
    out = {}
    for side, col in (("a", "player_a_id"), ("b", "player_b_id")):
        tgt = ids.get_indexer(P[col].astype(str))
        g = S.clock_sum(ids.get_indexer(R["srv"].to_numpy()[ok]), rel, V, tgt, S.num(P, "es"))
        h = S.clock_sum(ids.get_indexer(R["ret"].to_numpy()[ok]), rel, V, tgt, S.num(P, "es"))
        KG = P["tour"].astype(str).map(K_IND["G"]).to_numpy(dtype=float)
        KH = P["tour"].astype(str).map(K_IND["H"]).to_numpy(dtype=float)
        out[f"f09_G_{side}"] = g[:, 0] / (g[:, 1] + KG)
        out[f"f09_H_{side}"] = -h[:, 0] / (h[:, 1] + KH)
    return out


def match_indoor(P: pd.DataFrame, L: pd.DataFrame) -> np.ndarray:
    ind = pd.Series(indoor_rows(L, int(P["season"].max())), index=L["match_id"].astype(str).to_numpy())
    ind = ind[~ind.index.duplicated()]
    return P["match_id"].astype(str).map(ind).to_numpy(dtype=float)


def prepare_venue(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    Lc = S.cut_history(L, P)
    R = serve_rows(Lc, int(P["season"].max()))
    return {"f09_ve": venue_state(P, R), "f09_indoor": match_indoor(P, Lc)} | indoor_state(P, R)


def x_i072(P: pd.DataFrame) -> np.ndarray:
    return S.num(P, "f09_ve") * (S.ios(P, "srfO", "ace", "a") - S.ios(P, "srfO", "ace", "b"))


def d_i073(P: pd.DataFrame) -> np.ndarray:
    return (S.num(P, "f09_G_a") - S.num(P, "f09_G_b")) + (S.num(P, "f09_H_a") - S.num(P, "f09_H_b"))


def x_i073(P: pd.DataFrame) -> np.ndarray:
    return S.num(P, "f09_indoor") * d_i073(P)


def combine_venue(P: pd.DataFrame) -> dict:
    members, cols, mods, tab = [], [], [], {}
    if KEEP["I-072"]:
        x72 = x_i072(P)
        members.append((x72, "+"))
        cols.append(("in_iosO_ace", S.num(P, "in_iosO_ace")))
        mods.append(np.nan_to_num(S.centre_disc(P, S.num(P, "f09_ve"), None)))
        tab["f09_venue_pace_x_ace"] = (x72, "diff", None)
    if KEEP["I-073"]:
        x73 = x_i073(P)
        members.append((x73, "+"))
        cols.append(("d_indoor_dev", np.nan_to_num(d_i073(P))))
        mods.append(np.nan_to_num(S.centre_disc(P, S.num(P, "f09_indoor"), ("tour",))))
        tab["f09_indoor_dev"] = (x73, "diff", None)
    Cm, names = S.pack(cols + [(f"in_{n}", S.num(P, f"in_{n}")) for n in STD_VENUE])
    return {"x": S.signed_block(P, members), "controls": Cm, "control_names": names,
            "eta_mod_controls": np.column_stack(mods) if mods else None, "tabpfn": tab}


HYPOTHESES = [
    {"hid": "B-VENUE", "master": "+".join(k for k, v in KEEP.items() if v), "kind": "S", "sign": "+", "weight": 0.5,
     "trait": "slow", "deployment": "diff", "family": "14", "prepare": prepare_venue, "combine": combine_venue},
]


def gate_i072(R: pd.DataFrame, years=(2014, 2021), min_points: float = 2000.0) -> dict:
    """Venue carry-over (MEC-03's kill test 1): for each main-tour edition (tournament id) of 2014-2021, the venue pace
    as of the edition's first day (earlier editions only) against the edition's own ace residual sum u / sum n."""
    ok = np.isfinite(R["u"].to_numpy(float))
    Rk = R[ok]
    ed = Rk.groupby("edition").agg(venue=("venue", "first"), tour=("tour", "first"), year=("year", "first"),
                                   start=("es", "min"), u=("u", "sum"), n=("n_ace", "sum")).reset_index()
    ed = ed[ed["n"] >= min_points]
    keys = pd.Index(pd.unique(np.r_[Rk["venue"].to_numpy(), ed["venue"].to_numpy()]))
    sm = S.clock_sum(keys.get_indexer(Rk["venue"].to_numpy()), Rk["lf"].to_numpy(float) + 1.0,
                     Rk[["u", "n_ace"]].to_numpy(float), keys.get_indexer(ed["venue"].to_numpy()),
                     ed["start"].to_numpy(float), tau=TAU_V)
    ed["v_prev"], ed["n_prev"] = sm[:, 0] / (sm[:, 1] + K_V), sm[:, 1]
    ed["own"] = ed["u"] / ed["n"]
    out = {}
    for t in ("atp", "wta"):
        x = ed[(ed["tour"] == t) & ed["year"].between(*years) & (ed["n_prev"] > 0)]
        out[t] = {"editions": int(len(x)), "r": float(np.corrcoef(x["v_prev"], x["own"])[0, 1]),
                  "sd_own": float(x["own"].std()), "sd_v_prev": float(x["v_prev"].std())}
    out["passes_0.3"] = bool(min(v["r"] for k, v in out.items() if isinstance(v, dict)) >= 0.3)
    return out


def eb_indoor(R: pd.DataFrame, years=(2010, 2018)) -> dict:
    """Method of moments for K_G, K_H (serve points) on indoor serve rows, 2010-2018 (as f05_matchup.eb_hand)."""
    out = {}
    m0 = (R["indoor"].to_numpy(float) == 1.0) & np.isfinite(R["r"].to_numpy(float)) & R["year"].between(*years).to_numpy()
    for kind, key in (("G", "srv"), ("H", "ret")):
        out[kind] = {}
        for t in ("atp", "wta"):
            m = m0 & (R["tour"].to_numpy() == t)
            n, r = R["n"].to_numpy(float)[m], R["r"].to_numpy(float)[m]
            df = pd.DataFrame({"p": R[key].to_numpy()[m], "nr": n * r, "n": n, "n2r2": (n * r) ** 2, "r2": r * r})
            g = df.groupby("p").agg(nr=("nr", "sum"), n=("n", "sum"), n2r2=("n2r2", "sum"), k=("n", "size"))
            g = g[g["k"] >= 5]
            mp, sv = g["nr"] / g["n"], g["n2r2"] / g["n"] ** 2
            mbar = float(np.average(mp, weights=g["n"]))
            tau2 = float(np.average((mp - mbar) ** 2, weights=g["n"]) - np.average(sv, weights=g["n"]))
            v, nb = float(df["r2"].mean()), float(df["n"].mean())
            out[kind][t] = {"players": int(len(g)), "tau2": tau2, "K": float(v * nb / tau2) if tau2 > 0 else float("inf")}
    return out


def gate_i073(R: pd.DataFrame, years=(2010, 2021), min_pts: float = 1500.0) -> dict:
    """Odd/even-season carry-over of G (indoor serve deviation) and H (indoor return deviation), players with 1,500+
    indoor points in each half (MEC-13's kill below 0.15)."""
    m0 = (R["indoor"].to_numpy(float) == 1.0) & np.isfinite(R["r"].to_numpy(float)) & R["year"].between(*years).to_numpy()
    out = {}
    for kind, key, sgn in (("G", "srv", 1.0), ("H", "ret", -1.0)):
        df = pd.DataFrame({"p": R[key].to_numpy()[m0], "t": R["tour"].to_numpy()[m0], "odd": R["year"].to_numpy()[m0] % 2,
                           "nr": (R["n"] * R["r"]).to_numpy()[m0], "n": R["n"].to_numpy()[m0]})
        g = df.groupby(["t", "p", "odd"])[["nr", "n"]].sum().unstack("odd").dropna()
        g = g[(g[("n", 0)] >= min_pts / 2) & (g[("n", 1)] >= min_pts / 2)]
        for t in ("atp", "wta"):
            if t not in g.index.get_level_values(0):
                continue
            x = g.loc[t]
            a, b = sgn * x[("nr", 0)] / x[("n", 0)], sgn * x[("nr", 1)] / x[("n", 1)]
            out[f"{kind} {t}"] = {"players": int(len(x)), "odd_even_r": float(np.corrcoef(a, b)[0, 1]) if len(x) > 10 else np.nan}
    vals = [v["odd_even_r"] for v in out.values() if np.isfinite(v["odd_even_r"])]
    out["passes_0.15"] = bool(len(vals) > 0 and min(vals) >= 0.15)
    return out


def probe(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    """Probe-equivalent of the venue pace and the indoor deviations: later results reversed; nothing about a panel match
    starting by the cut may move."""
    Lc = S.cut_history(L, P)
    ms = int(P["season"].max())

    def build(LL):
        R = serve_rows(LL, ms)
        st = indoor_state(P, R)
        return np.column_stack([venue_state(P, R)] + [st[k] for k in sorted(st)])
    return S.probe_check(build, Lc, P, STAT_COLS)


def diagnostics(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    R = serve_rows(S.cut_history(L, P), int(P["season"].max()))
    d = S.disc(P)
    out = {"gate_I-072": gate_i072(R), "eb_indoor": eb_indoor(R), "gate_I-073": gate_i073(R),
           "venues": int(pd.Series(venue_key(P["tour"], P["tournament_name"], P["surface"])).nunique()),
           "v_e_disc": {t: float(np.nanstd(S.num(P, "f09_ve")[d & (P["tour"] == t).to_numpy()])) for t in ("atp", "wta")}}
    mem = {"I-072": x_i072(P), "I-073": x_i073(P)}
    out["members"] = {k: {"r2_on_58": S.r2_on_58(P, v), "nearest": S.nearest(P, v, 4),
                          "coverage_disc": float(np.isfinite(v[d]).mean())} for k, v in mem.items()}
    x = combine_venue(P)["x"]
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
    res = diagnostics(P.assign(**prepare_venue(P, L)), L)
    print(S.write_diag("f09_venue", res))
    print(json.dumps(res, indent=1, default=str)[:4000])
