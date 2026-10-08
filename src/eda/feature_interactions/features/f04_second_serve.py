"""Block B3, second-serve style matchups (I-016, I-022): a 2-df Wald block (I-016 is two-sided), weight 0.5.

I-016 (two-sided)  risky second servers against second-serve attackers (MEC-07): x = rho_A * D^sw_B - rho_B * D^sw_A,
                   rho = z(O^df) + z(O^sw), each z = the surface-IOS offence (srf_O_eff) centred within tour x surface
                   and divided by its SD, both players' values pooled over 2014-2021 rows (result-free constants).
I-022 (+)          kick second serve against a short returner (MEC-12): x = O^sw_A (hbar - h_B) - O^sw_B (hbar - h_A),
                   heights in cm, hbar = the tour's mean height over both players on 2014-2021 rows. Pooled over tours
                   (the audit: women's heights cover 64% in 2022-24). Trait: fixed (height), trait_cols ["height"].
Controls (union of the members'): iosO_df, iosO_second_won, iosD_second_won, prod_df, prod_second_won, Delta height,
miss_height_A - miss_height_B and the nearest inputs; eta-modulator controls: Sigma rho, Sigma D^sw, Sigma O^sw,
Sigma height (centred within tour x surface on 2014-2021 rows). Deployment: TabPFN difference columns.

Prechecks (result-free, statistic level, 2013-2018 pool matches with box scores, serve points of the row player):
I-016  the residuals of second-serve points won and of double faults (logit, against the additive surface IOS) on
       rho_server x D^sw_returner with both main effects (MEC-07: kill if both intervals include 0);
I-022  the second-serve residual on O^sw_server x (hbar - h_returner) with both main effects (MEC-12: kill if the interval
       includes 0). Player-clustered SEs.
Constants: none tuned. Reads no result. Run (diagnostics): ./python.sh src/eda/feature_interactions/features/f04_second_serve.py
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions.features import f01_structure_lib as S  # noqa: E402

C_B3 = ("iosO_df", "iosO_second_won", "iosD_second_won", "prod_df", "prod_second_won")
# nearest inputs beyond C_B3 (2014-2021 rows): I-016 iosO_first_won +0.47, iosO_hold +0.46; I-022 prod_first_won -0.57,
# iosO_ace +0.55 (diagnostics)
STD_B3 = ("iosO_first_won", "iosO_hold", "prod_first_won", "iosO_ace")
KEEP = {"I-016": True, "I-022": True}       # members kept after the prechecks (see the build note)


def _z_constants(P: pd.DataFrame, stat: str) -> tuple[dict, float]:
    """Cell means (tour x surface) and the pooled SD of the surface-IOS offence over both players, 2014-2021 rows."""
    d = S.disc(P)
    v = np.concatenate([S.ios(P, "srfO", stat, "a")[d], S.ios(P, "srfO", stat, "b")[d]])
    k = np.concatenate([S.cell_keys(P)[d]] * 2)
    means = pd.Series(v).groupby(k).mean().to_dict()
    sd = float(np.nanstd(v - pd.Series(k).map(means).to_numpy(dtype=float)))
    return means, sd


def rho_side(P: pd.DataFrame, side: str, consts=None) -> np.ndarray:
    consts = consts or {s: _z_constants(P, s) for s in ("df", "second_won")}
    k = pd.Series(S.cell_keys(P))
    out = np.zeros(len(P))
    for s in ("df", "second_won"):
        means, sd = consts[s]
        out = out + (S.ios(P, "srfO", s, side) - k.map(means).to_numpy(dtype=float)) / sd
    return out


def x_i016(P: pd.DataFrame) -> np.ndarray:
    consts = {s: _z_constants(P, s) for s in ("df", "second_won")}
    ra, rb = rho_side(P, "a", consts), rho_side(P, "b", consts)
    return ra * S.ios(P, "srfD", "second_won", "b") - rb * S.ios(P, "srfD", "second_won", "a")


def hbar(P: pd.DataFrame) -> np.ndarray:
    d = S.disc(P)
    t = P["tour"].astype(str).to_numpy()
    h = pd.DataFrame({"t": np.r_[t[d], t[d]], "h": np.r_[S.num(P, "height_a")[d], S.num(P, "height_b")[d]]})
    return pd.Series(t).map(h.groupby("t")["h"].mean()).to_numpy(dtype=float)


def x_i022(P: pd.DataFrame) -> np.ndarray:
    hb = hbar(P)
    ha, hbb = S.ab(P, "height")
    return S.ios(P, "srfO", "second_won", "a") * (hb - hbb) - S.ios(P, "srfO", "second_won", "b") * (hb - ha)


def prepare_b3(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    """The fixed trait as <trait>_a/_b (the panel's Stage 0 heights), so the batch can permute it (critique M4)."""
    return {"height_a": S.num(P, "height_a"), "height_b": S.num(P, "height_b")}


def combine_b3(P: pd.DataFrame) -> dict:
    cols, tab = [], {}
    if KEEP["I-016"]:
        cols.append(x_i016(P))
        tab["f04_risky_second"] = (cols[-1], "diff", None)
    if KEEP["I-022"]:
        cols.append(x_i022(P))
        tab["f04_kick_short"] = (cols[-1], "diff", None)
    ha, hb = S.ab(P, "height")
    Cm, names = S.pack([(f"in_{n}", S.num(P, f"in_{n}")) for n in C_B3 + STD_B3]
                       + [("d_height", ha - hb), ("miss_height", S.miss_diff(ha, hb))])
    consts = {s: _z_constants(P, s) for s in ("df", "second_won")}
    sums = [rho_side(P, "a", consts) + rho_side(P, "b", consts),
            S.ios(P, "srfD", "second_won", "a") + S.ios(P, "srfD", "second_won", "b"),
            S.ios(P, "srfO", "second_won", "a") + S.ios(P, "srfO", "second_won", "b"), ha + hb]
    E = np.column_stack([S.centre_disc(P, s_) for s_ in sums])
    E = np.nan_to_num(E)                                   # a missing height sum enters as the centre
    return {"x": np.column_stack(cols), "controls": Cm, "control_names": names, "eta_mod_controls": E,
            "tabpfn": tab}


# The final family's trait: fixed (height). A Wald block has no permutation null (verifier B9), so the batch screens a
# Wald block with a fixed-trait member with the slow-trait widening, covariance x 1.25 (plan.md, orchestrator decision
# of 6 Oct 2026); trait_cols stays declared.
B3_TRAIT = "fixed"

HYPOTHESES = [
    {"hid": "B3", "master": "I-016+I-022", "kind": "X", "sign": "two", "weight": 0.5, "trait": B3_TRAIT,
     "trait_cols": ["height"], "wald": True, "deployment": "diff", "family": "03/04",
     "prepare": prepare_b3, "combine": combine_b3},
]


def prechecks(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    """Statistic-level prechecks on 2013-2018 pool matches (see the module docstring)."""
    L = S.cut_history(L, P)
    yr = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    tour, surf = L["tour"].astype(str).to_numpy(), L["surface"].astype(str).to_numpy()
    H = S.history_ios(L, ["srf_O_eff_df", "srf_O_eff_second_won", "srf_D_eff_second_won", "srf_D_eff_df"])
    keys = pd.Series(np.char.add(np.char.add(tour.astype(str), "|"), surf.astype(str)))
    rho = np.zeros(len(L))
    for s in ("df", "second_won"):
        means, sd = _z_constants(P, s)
        rho = rho + (H[("own", f"srf_O_eff_{s}")] - keys.map(means).to_numpy(dtype=float)) / sd
    Dsw = H[("opp", "srf_D_eff_second_won")]
    Osw = H[("own", "srf_O_eff_second_won")]
    hb_t = {t: v for t, v in zip(P["tour"].astype(str), hbar(P))}
    h_opp = L["opponent_id"].astype(str).map(S.player_heights()).to_numpy(dtype=float)
    gap = np.array([hb_t.get(t, np.nan) for t in tour]) - h_opp
    grp = L["player_id"].astype(str).to_numpy()
    out = {}
    for stat, dstat in (("second_won", "second_won"), ("df", "df")):
        n, d = S.history_stat(L, stat)
        res = S.lg((n + 0.5) / (d + 1)) - (S.mu(L, stat, tour, surf) + H[("own", f"srf_O_eff_{stat}")]
                                            - H[("opp", f"srf_D_eff_{dstat}")])
        base_ok = (yr >= 2013) & (yr <= 2018) & np.isfinite(res) & (d >= 10)
        for t in ("atp", "wta"):
            k = base_ok & (tour == t) & np.isfinite(rho) & np.isfinite(Dsw)
            X = np.column_stack([np.ones(k.sum()), rho[k], Dsw[k], rho[k] * Dsw[k]])
            b, se = S.wls_clustered(X, res[k], d[k], grp[k])
            out[f"I-016 {stat} {t}"] = {"rows": int(k.sum()), "b_rho_x_Dsw": float(b[3]), "se": float(se[3]),
                                        "z": float(b[3] / se[3])}
            if stat == "second_won":
                k2 = base_ok & (tour == t) & np.isfinite(Osw) & np.isfinite(gap)
                X2 = np.column_stack([np.ones(k2.sum()), Osw[k2], gap[k2], Osw[k2] * gap[k2]])
                b2, se2 = S.wls_clustered(X2, res[k2], d[k2], grp[k2])
                out[f"I-022 second_won {t}"] = {"rows": int(k2.sum()), "b_Osw_x_gap": float(b2[3]),
                                                "se": float(se2[3]), "z": float(b2[3] / se2[3])}
    return out


def diagnostics(P: pd.DataFrame, L: pd.DataFrame | None = None) -> dict:
    d = S.disc(P)
    x16, x22 = x_i016(P), x_i022(P)
    out = {"I-016": {"r2_on_58": S.r2_on_58(P, x16), "nearest": S.nearest(P, x16, 4)},
           "I-022": {"r2_on_58": S.r2_on_58(P, x22), "nearest": S.nearest(P, x22, 4)}}
    ok = d & np.isfinite(x16) & np.isfinite(x22)
    out["corr_members"] = float(np.corrcoef(x16[ok], x22[ok])[0, 1])
    if L is not None:
        out["prechecks_2013_2018"] = prechecks(P, L)
    return out


if __name__ == "__main__":
    import warnings
    warnings.simplefilter("ignore")
    from src.eda.feature_interactions.history import long_table
    from src.eda.feature_interactions.panel import panel
    P = panel(max_season=2024)
    res = diagnostics(P, long_table())
    print(S.write_diag("f04_second_serve", res))
    for k, v in res.items():
        print(k, v)
