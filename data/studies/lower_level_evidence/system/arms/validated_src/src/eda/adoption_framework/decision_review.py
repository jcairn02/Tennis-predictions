"""Review computations for the adoption-threshold logic (no tennis result is scored here except reading the
feature-interactions screen's already-written 2014-2024 gains). mLL per match, + = candidate better.
Run from the repo root: ./python.sh <this file>
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import integrate, optimize
from scipy.stats import norm

rng = np.random.default_rng(20261009)
P = lambda z: norm.cdf(z)  # noqa: E731


def hdr(s):
    print("\n" + "=" * 100 + "\n" + s + "\n" + "=" * 100)


# ---------------------------------------------------------------------------------------------------------------
hdr("A. Empirical-Bayes spread of true effects (tau) for increments tested against the model / with the close")


def dl_tau2(est, se):
    """DerSimonian-Laird between-effect variance and the weighted mean."""
    est, se = np.asarray(est, float), np.asarray(se, float)
    w = 1 / se ** 2
    mu = np.sum(w * est) / np.sum(w)
    Q = np.sum(w * (est - mu) ** 2)
    k = len(est)
    t2 = max(0.0, (Q - (k - 1)) / (np.sum(w) - np.sum(w ** 2) / np.sum(w)))
    return t2, mu, Q, k


def ml_tau(est, se):
    est, se = np.asarray(est, float), np.asarray(se, float)

    def nll(par):
        mu, lt = par
        v = se ** 2 + np.exp(lt) ** 2
        return 0.5 * np.sum(np.log(v) + (est - mu) ** 2 / v)
    r = optimize.minimize(nll, [0.0, np.log(0.05)], method="Nelder-Mead")
    return r.x[0], np.exp(r.x[1])


d = pd.read_csv("data/studies/feature_interactions/hypotheses/screen_results.csv")
m = d[(d.base == "model") & d.gain_repl_both.notna()].copy()
for win in ("disc", "repl"):
    e = m[f"gain_{win}_both"].to_numpy()
    se = (m[f"hi_{win}_both"] - m[f"lo_{win}_both"]).to_numpy() / (2 * 1.96)
    t2, mu, Q, k = dl_tau2(e, se)
    mu_ml, tau_ml = ml_tau(e, se)
    print(f"screen members' out-of-sample gains vs the model, {win}: k {k}, mean {np.mean(e):+.3f}, SD {np.std(e, ddof=1):.3f}, "
          f"median SE {np.median(se):.3f}; DL tau {np.sqrt(t2):.3f} (Q {Q:.1f} on {k-1} df); ML mu {mu_ml:+.3f} tau {tau_ml:.3f}")
z = d[(d.base == "model")].z_joint.dropna().to_numpy()
print(f"screen joint z (declared direction), k {len(z)}: mean {z.mean():+.2f}, SD {z.std(ddof=1):.2f}, "
      f"#|z|>1.96 {(np.abs(z) > 1.96).sum()} (null expects {0.05 * len(z):.1f}); var(z)-1 = {z.var(ddof=1) - 1:.2f}")

docs = [  # with-close increments quoted in the docs (est, lo, hi); not independent, rough
    ("backfill, both (doc SE)", 0.014, -0.073, 0.102),
    ("rebuilt vs previous, both 2022-26", 0.03, -0.13, 0.20),
    ("surface IOS, close, both", 0.01, -0.10, 0.13),
    ("offset Elo swap, close, both (race)", -0.05, -0.24, 0.14),
    ("surface IOS given offset Elo, close", -0.01, -0.10, 0.08),
    ("event share 59th input, both", 0.06, -0.10, 0.23),
    ("speed as TabPFN column, men 24-26", 0.07, -0.05, 0.18),
    ("B-INJ column arm 2020-24", 0.044, -0.157, 0.245),
    ("+Challenger rows, both", -0.48, -1.09, 0.14),
]
e = np.array([r[1] for r in docs]); se = np.array([(r[3] - r[2]) / 3.92 for r in docs])
t2, mu, Q, k = dl_tau2(e, se)
print(f"docs' with-close increments, k {k}: DL tau {np.sqrt(t2):.3f}, Q {Q:.1f} on {k-1} df; mean {mu:+.3f}")
e2, se2 = e[:-1], se[:-1]
t2b, mub, Qb, kb = dl_tau2(e2, se2)
print(f"  without Challenger rows: DL tau {np.sqrt(t2b):.3f}, Q {Qb:.1f} on {kb-1} df; "
      f"SD of estimates {np.std(e2, ddof=1):.3f}, RMS SE {np.sqrt(np.mean(se2**2)):.3f}")

# ---------------------------------------------------------------------------------------------------------------
hdr("B. Section 2's five readings under a prior instead of a flat one")
rows = [("backfill men (doc SE)", 0.027, 0.0501), ("backfill men (paired SE)", 0.0271, 0.0194),
        ("surface IOS both", 0.01, 0.0575), ("men profile vs close 22-26", 0.93, 0.465),
        ("offset Elo women close", -0.21, 0.1375), ("Challenger rows men", -0.91, 0.4925)]
for tau in (0.05, 0.10, 0.30):
    print(f"-- prior N(0, {tau}^2) on the true gain (note: the profile-vs-close row is a different quantity; tau does not fit it)")
    for lab, est, s in rows:
        B = tau ** 2 / (tau ** 2 + s ** 2)
        pm, psd = B * est, np.sqrt(B) * s
        print(f"   {lab:28s} flat P {P(est / s):.2f} | shrink B {B:.2f}: posterior mean {pm:+.3f}, P(>0) {P(pm / psd):.2f}")

# ---------------------------------------------------------------------------------------------------------------
hdr("C. Bayes adoption threshold: adopt iff mu0 + B(est - mu0) > c, B = tau^2/(tau^2+s^2)")
print("   z* = est*/s and the flat-prior P* that it corresponds to")
for mu0 in (0.0, 0.02, -0.02):
    for tau in (0.03, 0.05, 0.10):
        for s in (0.02, 0.05, 0.08):
            B = tau ** 2 / (tau ** 2 + s ** 2)
            out = []
            for c in (0.0, 0.01, 0.02, 0.05):
                est_star = (c - (1 - B) * mu0) / B
                out.append(f"c {c:.2f}: z* {est_star / s:+5.2f} P* {P(est_star / s):.2f}")
            print(f"   mu0 {mu0:+.2f} tau {tau:.2f} s {s:.2f} (B {B:.2f}) | " + " | ".join(out))

# ---------------------------------------------------------------------------------------------------------------
hdr("D. Threshold rules vs the Bayes rule, cost charged on EVERY adoption, 20 candidates, Monte Carlo")
RULES = [("95% (z>1.96)", 1.96), ("P>0.90", 1.2816), ("P>0.80", 0.8416), ("P>0.50", 0.0)]


def simulate(draw_theta, s, c, n=20, reps=40000, bayes_post=None, label=""):
    th = draw_theta((reps, n))
    sv = s if np.isscalar(s) else s((reps, n))
    est = th + sv * rng.standard_normal((reps, n))
    res = []
    for name, zc in RULES:
        a = est / sv > zc
        res.append((name, a.sum(1).mean(), ((th - c) * a).sum(1).mean(), (est * a).sum(1).mean()))
    if bayes_post is not None:
        a = bayes_post(est, sv) > c
        res.append(("Bayes (oracle prior)", a.sum(1).mean(), ((th - c) * a).sum(1).mean(), (est * a).sum(1).mean()))
    print(f"-- {label}; cost {c} per adoption")
    for name, na, tg, bt in res:
        print(f"   {name:22s} adopted {na:5.1f}  true net {tg:+.3f}  backtest {bt:+.3f}  inflation {bt - tg - na * c:+.3f}")
    return res


def normal_post(mu0, tau):
    return lambda est, s: mu0 + tau ** 2 / (tau ** 2 + s ** 2) * (est - mu0)


def spike_slab_post(pi0, mu1, tau1):
    def f(est, s):
        v1 = tau1 ** 2 + s ** 2
        l0 = pi0 * norm.pdf(est, 0, s)
        l1 = (1 - pi0) * norm.pdf(est, mu1, np.sqrt(v1))
        w1 = l1 / (l0 + l1)
        m1 = mu1 + tau1 ** 2 / v1 * (est - mu1)
        return w1 * m1
    return f


for s in (0.08, 0.03):
    for c in (0.0, 0.01, 0.02):
        simulate(lambda sh: 0.05 * rng.standard_normal(sh), s, c, bayes_post=normal_post(0, 0.05),
                 label=f"normal prior N(0, 0.05^2), SE {s}")
for c in (0.0, 0.02):
    def ss(sh, pi0=0.7, mu1=0.03, tau1=0.08):
        slab = rng.random(sh) > pi0
        return np.where(slab, mu1 + tau1 * rng.standard_normal(sh), 0.0)
    simulate(ss, 0.08, c, bayes_post=spike_slab_post(0.7, 0.03, 0.08),
             label="spike-and-slab: 70% exactly 0, 30% N(+0.03, 0.08^2), SE 0.08")
# the assistant's scenarios, but with the cost on every adoption
for lab, mix in {"A": [(6, 1.0), (12, 0.0), (2, -1.0)], "C": [(2, 1.0), (16, 0.0), (2, -1.0)]}.items():
    for c in (0.02,):
        sig = 0.08
        out = []
        for name, zc in RULES:
            tg = ad = 0.0
            for n_, mm in mix:
                pa = 1 - norm.cdf(zc - mm)
                ad += n_ * pa
                tg += n_ * pa * (sig * mm - c)
            out.append(f"{name}: adopted {ad:4.1f} true net {tg:+.3f}")
        print(f"-- assistant's scenario {lab}, cost {c} on every adoption: " + " | ".join(out))

# ---------------------------------------------------------------------------------------------------------------
hdr("E. Best of K variants on the same seasons: expected max of K equicorrelated N(0,1)")


def emax(K, n=400000):
    return float(np.max(rng.standard_normal((n, K)), axis=1).mean())


for K in (2, 3, 4, 6, 10):
    mk = emax(K)
    print(f"   K {K:2d}: m_K {mk:.2f}; with noise correlation 0.5 -> {np.sqrt(0.5) * mk:.2f} SE; 0.8 -> {np.sqrt(0.2) * mk:.2f} SE")
print("   men's 16-input profile: flat z 2.00 (2022-26 window); all scored seasons 0.51/0.285 = "
      f"{0.51 / 0.2857:.2f}; minus 0.9 SE for best-of-6 at rho 0.5 -> P {P(0.51 / 0.2857 - 0.9):.2f}; repaired build z "
      f"{0.28 / 0.393:.2f} P {P(0.28 / 0.393):.2f}")
print("   incumbency: a challenger to an adopted part is handicapped by (1 - rho) x the incumbent's selection inflation.")
for zc in (1.96, 0.8416, 0.0):
    # E[noise | adopted] for a null incumbent at threshold zc, in SE units
    infl = norm.pdf(zc) / (1 - norm.cdf(zc))
    print(f"   null incumbent adopted at z>{zc:.2f}: E[noise|adopted] {infl:.2f} SE; challenger handicap at rho 0.5: {0.5 * infl:.2f} SE")

# ---------------------------------------------------------------------------------------------------------------
hdr("F. Kelly: quadratic approximation vs exact log growth for a binary bet at a fair price")
print("   quadratic: G(c f*)/G* = 2c - c^2 -> c=0.5: 0.75, c=1.5: 0.75, c=2: 0")
for p, pi in ((0.50, 0.53), (0.50, 0.60), (0.25, 0.28), (0.20, 0.30)):
    fstar = (pi - p) / (1 - p)

    def g(f):
        return pi * np.log(1 + f * (1 - p) / p) + (1 - pi) * np.log(1 - f)
    G = g(fstar)
    out = " ".join(f"c={c}: {g(c * fstar) / G:+.2f}" for c in (0.5, 1.5, 2.0, 2.5))
    ll_edge = pi * np.log(pi / p) + (1 - pi) * np.log((1 - pi) / (1 - p))
    print(f"   price {p:.2f}, truth {pi:.2f}: full-Kelly growth {1000 * G:.3f} mnats = KL {1000 * ll_edge:.3f} mLL; ratios {out}")
print("   uncertain edge: true/estimated edge ratio k; optimal stake multiplier under quadratic growth = E[k].")
for kbar, ksd in ((0.7, 0.3), (0.5, 0.5), (1.0, 0.5)):
    ks = kbar + ksd * rng.standard_normal(200000)
    cs = np.linspace(0, 2, 401)
    eg = [np.mean(2 * c * ks - c ** 2) for c in cs]
    print(f"   k ~ N({kbar}, {ksd}^2): best c {cs[int(np.argmax(eg))]:.2f}; growth at c=1 {np.mean(2 * ks - 1):+.2f} G*, "
          f"at best {max(eg):+.2f} G*")
print("   bet selection (optimizer's curse): truth-minus-market a~N(0,A^2), model error ~N(0,Bm^2) in logit;")
for A, Bm in ((0.10, 0.10), (0.10, 0.20)):
    a = A * rng.standard_normal(400000); q = a + Bm * rng.standard_normal(400000)
    lam = A ** 2 / (A ** 2 + Bm ** 2)
    for thr in (0.0, 0.1, 0.2):
        sel = np.abs(q) > thr
        print(f"   A {A} B {Bm} (realisation {lam:.2f}) |model-market|>{thr}: share bet {sel.mean():.2f}, true/estimated edge "
              f"{np.mean(a[sel] * np.sign(q[sel])) / np.mean(np.abs(q[sel])):.2f}")

# ---------------------------------------------------------------------------------------------------------------
hdr("G. Live power: years until a true gain reaches z = 2, from per-year SEs")
cases = [
    ("whole model vs avg close (sd 46/match, 5,000/yr)", 46 / np.sqrt(5000), (1.46, 1.0, 0.5, 0.2)),
    ("whole model vs Polymarket close (2026: 2,933, +-2.7)", 1.38 * np.sqrt(2933 / 4000), (1.46, 1.0, 0.5, 0.2)),
    ("backfill, doc SE scaled to 1 yr (men)", 0.0501 * np.sqrt(5), (0.027,)),
    ("backfill, paired SE scaled to 1 yr (men)", 0.0194 * np.sqrt(5), (0.027,)),
    ("speed adjustment, men, ~0.35/season", 0.35, (0.28, 0.10)),
    ("a same-model input swap at the close, SE 0.06 per 5 yrs", 0.06 * np.sqrt(5), (0.1, 0.05)),
]
for lab, s1, effs in cases:
    print(f"   {lab}: SE/yr {s1:.3f} (95% +-{1.96 * s1:.2f}); " +
          "; ".join(f"true {e:+.3f}: {(2 * s1 / e) ** 2:.1f} yr" for e in effs))
print(f"   identity check: per-match sd 46 -> SE for 22,265 = {46 / np.sqrt(22265):.3f}; "
      f"doc 1.46 [0.84, 2.08] -> SE {(2.08 - 0.84) / 3.96:.3f}; for 5,000: {(2.08 - 0.84) / 3.96 * np.sqrt(22265 / 5000):.3f}")

# ---------------------------------------------------------------------------------------------------------------
hdr("H. Multiplicity of the proposed labels under the global null (P(better) ~ Uniform)")
for K in (9, 13):
    print(f"   {K} cells: expected 'better/worse' (P>0.975 or <0.025) {K * 0.05:.2f}; 'leans' (0.8-0.975 either side) "
          f"{K * 0.35:.2f}; any directional label {K * 0.40:.1f}; P(>=1 cell beyond 0.95 either tail) {1 - 0.9 ** K:.2f}; "
          f"expected cells P>=0.95 one tail {K * 0.05:.2f}")
