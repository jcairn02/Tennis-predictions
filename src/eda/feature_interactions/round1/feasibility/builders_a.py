"""Primary columns of families 01-05 (I-001 ... I-027), built from the augmented panel for G2's result-free checks.
Each builder returns {name: (values, kind)}; the first entry is the primary column. Construction constants not stated by
the originators are fixed here (noted in the audit file) and do not read any result."""
from __future__ import annotations

import numpy as np
from scipy.special import expit

from src.eda.feature_interactions.round1.feasibility import base as B


def price(P):
    """De-vigged average-close log-odds that A wins, from each side's quote (swap-consistent)."""
    a, b = 1.0 / P["avg_a"].astype(float), 1.0 / P["avg_b"].astype(float)
    return B.lg(a / (a + b))


def io(P, kind, s, side):
    return P[f"ios_{kind}_{s}_{side}"].to_numpy(float)


def pt(P, s, server, returner, mean=None):
    """IOS point/statistic probability of `server` against `returner` on statistic s, at the tour x surface mean."""
    mu = B.mean_logit(P, s) if mean is None else mean
    return expit(mu + io(P, "srfO", s, server) - io(P, "srfD", s, returner))


def comp_serve(P, a, b):
    fi, fw, sw = pt(P, "first_in", a, b), pt(P, "first_won", a, b), pt(P, "second_won", a, b)
    return fi * fw + (1 - fi) * sw


def bo(P):
    return P["best_of"].to_numpy(float)


def lev(m, best_of, h=0.05):
    """d logit P(match) / d(point log-odds gap) at pair dominance m (logit scale), central difference."""
    up = B.lg(B.iid_match(expit(m + h / 2), expit(m - h / 2), best_of))
    dn = B.lg(B.iid_match(expit(m - h / 2), expit(m + h / 2), best_of))
    return (up - dn) / (2 * h)


def cellmean(P, x, keys=("tour", "surface")):
    df = P[list(keys)].copy()
    df["x"] = x
    train = P["season"].between(*B.DISC).to_numpy()
    means = df[train].groupby(list(keys))["x"].mean()
    return df.set_index(list(keys)).index.map(means).to_numpy(float)


def m_pair(P):
    return 0.5 * (io(P, "srfO", "spw", "a") + io(P, "srfO", "spw", "b") - io(P, "srfD", "spw", "a") - io(P, "srfD", "spw", "b"))


def I001(P):
    mu = B.mean_logit(P, "spw")
    L_ = lev(mu + m_pair(P), bo(P))
    return {"x_lev": (price(P) * (L_ / cellmean(P, L_) - 1.0), "diff")}


def I002(P):
    pa, pb = pt(P, "spw", "a", "b"), pt(P, "spw", "b", "a")
    mu, g = expit(B.mean_logit(P, "spw")), pa - pb
    comp = B.lg(B.iid_match(pa, pb, bo(P))) - B.lg(B.iid_match(mu + g / 2, mu - g / 2, bo(P)))
    D = pa + pb - 2 * mu
    return {"comp": (comp, "diff"), "z_x_D": (price(P) * D, "diff")}


def I003(P):
    return {"m_pair": (m_pair(P), "context")}


def I004(P):
    out = {}
    for name, k, s in (("sig1_SO_spw", "srfO", "spw"), ("sig2_SD_spw", "srfD", "spw"), ("sig3_SO_ace", "srfO", "ace"),
                       ("sig4_SO_fi", "srfO", "first_in")):
        x = io(P, k, s, "a") + io(P, k, s, "b")
        out[name] = (x - cellmean(P, x), "context")
    return out


def I005(P):
    return {"sO_spw": (io(P, "srfO", "spw", "a") + io(P, "srfO", "spw", "b"), "context"),
            "dO_spw": (io(P, "srfO", "spw", "a") - io(P, "srfO", "spw", "b"), "diff"),
            "dD_spw": (io(P, "srfD", "spw", "a") - io(P, "srfD", "spw", "b"), "diff"),
            "sD_spw": (io(P, "srfD", "spw", "a") + io(P, "srfD", "spw", "b"), "context")}


def I006(P):
    pa, pb = P["s3_p_serve_a"].to_numpy(float), P["s3_p_serve_b"].to_numpy(float)
    u, v = B.lg(B.iid_match(pa, pb, bo(P))), B.lg(B.iid_match(pa, pb, np.full(len(P), 3.0)))
    return {"L_bo5": ((bo(P) == 5) * (u - v), "diff")}


def I008(P):
    return {"z_C1": (B.lg(B.iid_match(comp_serve(P, "a", "b"), comp_serve(P, "b", "a"), bo(P))), "diff")}


def I009(P):
    from src.eda.predictability_diagnostic.stage4_features import serve_rate_for_hold
    ha, hb = pt(P, "hold", "a", "b"), pt(P, "hold", "b", "a")
    z2 = B.lg(B.iid_match(serve_rate_for_hold(ha), serve_rate_for_hold(hb), bo(P)))
    return {"r_games_minus_points": (z2 - I008(P)["z_C1"][0], "diff")}


def I010(P, V=0.04):
    mu = B.mean_logit(P, "spw") + m_pair(P)
    delta = (io(P, "srfO", "spw", "a") - io(P, "srfD", "spw", "b")) - (io(P, "srfO", "spw", "b") - io(P, "srfD", "spw", "a"))
    nodes, w = np.polynomial.hermite_e.hermegauss(9)
    acc = np.zeros(len(P))
    for u, wt in zip(nodes * np.sqrt(V), w / w.sum()):
        acc += wt * B.iid_match(expit(mu + (delta + u) / 2), expit(mu - (delta + u) / 2), bo(P))
    return {"z_C4": (B.lg(acc), "diff")}


def I011(P):
    mu = B.mean_logit(P, "spw") + m_pair(P)
    z = price(P)
    lo, hi = np.full(len(P), -4.0), np.full(len(P), 4.0)
    for _ in range(40):                                   # invert the iid map: z = logit P(mu + d/2, mu - d/2)
        mid = (lo + hi) / 2
        f = B.lg(B.iid_match(expit(mu + mid / 2), expit(mu - mid / 2), bo(P)))
        lo, hi = np.where(f < z, mid, lo), np.where(f < z, hi, mid)
    dprof = (io(P, "srfO", "spw", "a") - io(P, "srfD", "spw", "b")) - (io(P, "srfO", "spw", "b") - io(P, "srfD", "spw", "a"))
    return {"d_pt": (dprof - (lo + hi) / 2, "diff")}


def I012(P):
    return {"shield_x": (io(P, "srfO", "ace", "a") * io(P, "srfD", "spw", "b")
                         - io(P, "srfO", "ace", "b") * io(P, "srfD", "spw", "a"), "diff")}


def I013(P):
    out = {}
    for s in ("ace", "hold", "df", "first_won"):
        out[f"sq_{s}"] = ((io(P, "srfO", s, "a") ** 2 - io(P, "srfO", s, "b") ** 2)
                          - (io(P, "srfD", s, "a") ** 2 - io(P, "srfD", s, "b") ** 2), "diff")
    return out


def I014(P):
    fbar = expit(B.mean_logit(P, "first_in"))
    Ea, Eb = fbar - pt(P, "first_in", "a", "b"), fbar - pt(P, "first_in", "b", "a")
    ca = io(P, "srfD", "second_won", "a") - io(P, "srfD", "first_won", "a")
    cb = io(P, "srfD", "second_won", "b") - io(P, "srfD", "first_won", "b")
    return {"x_exposure": (Eb * ca - Ea * cb, "diff")}


def I015(P):
    e2 = (1 - pt(P, "first_in", "a", "b")) * (1 - pt(P, "second_won", "a", "b")) \
        - (1 - pt(P, "first_in", "b", "a")) * (1 - pt(P, "second_won", "b", "a"))
    return {"E2": (e2, "diff")}


def I016(P):
    n = len(P)
    m2 = np.tile(P["season"].between(*B.DISC).to_numpy(), 2)

    def z(s):                                  # standardised over both players' values, 2014-2021
        x = np.concatenate([io(P, "srfO", s, "a"), io(P, "srfO", s, "b")])
        return (x - np.nanmean(x[m2])) / np.nanstd(x[m2])
    rho = z("df") + z("second_won")
    ra, rb = rho[:n], rho[n:]
    return {"x_risky": (ra * io(P, "srfD", "second_won", "b") - rb * io(P, "srfD", "second_won", "a"), "diff")}


def I017(P):
    return {"dY_ace": (P["in_iosO_ace"].to_numpy(float) - P["in_iosD_ace"].to_numpy(float), "diff")}


def I019(P):
    n = P["h2h_n_a"].to_numpy(float)
    return {"h2h_any": ((n > 0).astype(float), "context")}


def I020(P):
    return {"x_speed": (P["sh_spd1_change_a"] * io(P, "srfD", "spw", "b") - P["sh_spd1_change_b"] * io(P, "srfD", "spw", "a"),
                        "diff")}


def I022(P):
    ha, hb = P["height_a"].astype(float).to_numpy(), P["height_b"].astype(float).to_numpy()
    hbar = cellmean(P, 0.5 * (ha + hb), ("tour",))
    return {"x_kick": (io(P, "srfO", "second_won", "a") * (hbar - hb) - io(P, "srfO", "second_won", "b") * (hbar - ha), "diff")}


def I023(P, K=5000.0):
    m = P["season"].between(2014, 2018).to_numpy() & (P["tour"] == "atp").to_numpy()
    h = np.concatenate([P["height_a"].astype(float), P["height_b"].astype(float)])
    o = np.concatenate([io(P, "srfO", "ace", "a"), io(P, "srfO", "ace", "b")])
    mm = np.concatenate([m, m]) & np.isfinite(h) & np.isfinite(o)
    beta = np.polyfit(h[mm] - np.nanmean(h[mm]), o[mm], 1)[0]           # height -> ace offence, no outcome involved
    hbar = np.nanmean(h[mm])
    out = []
    for s in ("a", "b"):
        n = P[f"s3_serve_pts_{s}"].to_numpy(float)
        prior = beta * (P[f"height_{s}"].astype(float).to_numpy() - hbar)
        out.append(K / (n + K) * (prior - io(P, "srfO", "ace", s)))
    return {"x_height_prior": (out[0] - out[1], "diff")}


def I024(P):
    def w(s):
        return P[f"height_{s}"].astype(float).to_numpy() * np.maximum(P[f"age_{s}"].astype(float).to_numpy() - 28, 0)
    from src.eda.feature_interactions.round1.feasibility.builders_c import fat
    return {"h_x_fat": (P["height_a"].astype(float).to_numpy() * fat(P, "a") - P["height_b"].astype(float).to_numpy() * fat(P, "b"),
                        "diff"),
            "h_x_age28": (w("a") - w("b"), "diff")}


def I026(P):
    ha, hb = pt(P, "hold", "a", "b"), pt(P, "hold", "b", "a")
    brk = (2 - ha - hb) / 2
    return {"x_bigpoint": (P["d_bigpoint"].to_numpy(float) * cellmean(P, brk) / brk, "diff")}


def I027(P):
    ra = P["sh_break_back_a"] + P["sh_consolidate_a"]
    rb = P["sh_break_back_b"] + P["sh_consolidate_b"]
    return {"x_resilience": ((ra - rb).to_numpy(float), "diff")}


BUILDERS = {"I-001": I001, "I-002": I002, "I-003": I003, "I-004": I004, "I-005": I005, "I-006": I006, "I-008": I008,
            "I-009": I009, "I-010": I010, "I-011": I011, "I-012": I012, "I-013": I013, "I-014": I014, "I-015": I015,
            "I-016": I016, "I-017": I017, "I-019": I019, "I-020": I020, "I-022": I022, "I-023": I023, "I-024": I024,
            "I-026": I026, "I-027": I027}
