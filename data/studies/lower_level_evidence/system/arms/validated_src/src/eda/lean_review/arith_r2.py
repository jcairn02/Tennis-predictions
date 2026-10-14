# The lean review's debate (docs/studies/lean_review/), the reviewer's arith_r2.py, copied verbatim from the session's scratch folder.
# Arithmetic on documented numbers only; no data is read. Output: data/studies/lean_review/arith_r2.out
# Round-2 arithmetic on documented numbers only.
from math import sqrt
se = lambda lo, hi: (hi-lo)/3.92
k = 0.24
eff = {2019:(0.20,-0.22,0.61),2020:(-0.01,-0.46,0.44),2021:(-0.05,-0.22,0.12),2022:(0.15,0.03,0.27),
       2023:(-0.05,-0.14,0.04),2024:(0.02,-0.06,0.09),2025:(0.08,-0.04,0.19),2026:(0.10,0.00,0.20)}
def post(years, tau_b, shift=None):
    W=0; S=0
    for y in years:
        m,lo,hi = eff[y]
        if shift and y in shift: m += shift[y]
        w = 1/(tau_b**2 + se(lo,hi)**2); W += w; S += m*w
    mu = S/W; semu = sqrt(1/W); B = 0.05**2/(0.05**2+semu**2)
    return mu, semu, B*mu
gain = lambda b, mu: 1000*k*(b*mu - b*b/2)
for lab, yrs, tb, sh in (("strict 2019-24", range(2019,2025), 0.063, None),
                         ("2019-26 as documented", range(2019,2027), 0.055, None),
                         ("2019-26, 2025-26 cut by 0.01 (memory pick)", range(2019,2027), 0.055, {2025:-0.01,2026:-0.01}),
                         ("2019-26, 2025-26 cut by 0.03", range(2019,2027), 0.055, {2025:-0.03,2026:-0.03})):
    mu, s, pm = post(yrs, tb, sh)
    print(f"{lab}: RE mean {mu:+.4f} SE {s:.4f} posterior {pm:.4f} -> E[gain] at b=posterior {gain(pm,pm):+.3f}; at b=.032 {gain(.032,pm):+.3f}")
# attenuation r on the PF base: posterior from documented 2019-26 scaled by r
mu, s, pm = post(range(2019,2027), 0.055, {2025:-0.01,2026:-0.01})
for r in (1.0, 0.75, 0.5, 0.4, 0.25):
    m = pm*r
    print(f"r {r}: mu_post {m:.4f} E[gain] at b=mu {gain(m,m):+.3f}")
# thresholds for B*est + c > 0
def thr(tau, s, c): B = tau**2/(tau**2+s**2); return -c/B, B
for lab, tau, s, c in (("profile", 0.1, 0.05, 0.05), ("profile", 0.1, 0.08, 0.05), ("short", 0.03, 0.02, 0.01), ("short", 0.03, 0.03, 0.01), ("both", 0.1, 0.08, 0.06), ("surface keep (c +0.01)", 0.05, 0.06, -0.01)):
    t, B = thr(tau, s, c); print(f"{lab}: tau {tau} s {s} c {c}: B {B:.2f}, remove iff est > {t:+.3f}")
# lead's P<=0.2 rule equivalent est at various SE
for s in (0.02, 0.03, 0.05, 0.08): print(f"P(better)<=0.2 fires at est <= {-0.8416*s:+.3f} (SE {s})")
