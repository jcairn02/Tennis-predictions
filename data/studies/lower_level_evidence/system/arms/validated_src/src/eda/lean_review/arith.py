# The lean review's debate (docs/studies/lean_review/), the reviewer's arith.py, copied verbatim from the session's scratch folder.
# Arithmetic on documented numbers only; no data is read. Output: data/studies/lean_review/arith.out
# Arithmetic on documented numbers only (no outcome data read).
from math import sqrt, erf
Phi = lambda z: 0.5*(1+erf(z/sqrt(2)))
se = lambda lo, hi: (hi-lo)/3.92

print("== Stage 2: walk-forward record 2020-26, men (+ = adjustment helps) ==")
# 2020-24 paired: seed_term_check.out line 5
e1, s1, n1 = -0.2641, 0.1618, 11672
# 2025, 2026 (to 28 Jul): infosys_atp_backfill README s5; counts from serve_speed_tabpfn s6.1 (2,620; 1,774)
e25, s25, n25 = 0.32, se(-0.14, 0.78), 2620
e26, s26, n26 = 0.73, se(0.09, 1.38), 1774
n2 = n25+n26
e2 = (e25*n25 + e26*n26)/n2
s2 = sqrt((n25*s25)**2 + (n26*s26)**2)/n2
print(f"2025-26: {e2:+.3f} SE {s2:.3f}")
n = n1+n2
e = (e1*n1 + e2*n2)/n
s = sqrt((n1*s1)**2 + (n2*s2)**2)/n
print(f"2020-26: {e:+.3f} [{e-1.96*s:+.2f}, {e+1.96*s:+.2f}] P(better) {Phi(e/s):.2f}")
# dense era 2022-26 (approx equal season sizes 2022-24 ~ (11672-1400-2500)/3)
w = (11672-1400-2500)/3
g = {2022:0.16, 2023:-1.26, 2024:0.00}
dense = (sum(v*w for v in g.values()) + e25*n25 + e26*n26)/(3*w+n2)
print(f"dense era 2022-26 approx: {dense:+.3f}")

print("\n== Stage 2: expected gain next season, gain = 1000*k*(b*mu - b^2/2), k=0.24 (backfill s5) ==")
k=0.24
for b in (0.0444, 0.032, 0.035):
    for mu,lab in ((0.049,'RE 2019-26 w/ backfill'),(0.044,'RE 2019-26'),(0.035,'RE shrunk'),(0.029,'2019-24 used for 2025'),(0.024,'RE 2019-24'),(0.0,'no signal')):
        print(f"b {b:.4f} mu {mu:.3f} ({lab}): {1000*k*(b*mu-b*b/2):+.2f}")
for b in (0.07, 0.0444, 0.032, 0.035):
    print(f"bad season beta -0.05, b {b}: {1000*k*(b*-0.05-b*b/2):+.2f}")

print("\n== Stage 2: heterogeneity-aware coefficient (posterior mean of the season mean, prior N(0,0.05^2)) ==")
# per-season information effects, backfill s5 'now' column
eff = {2019:(0.20,-0.22,0.61),2020:(-0.01,-0.46,0.44),2021:(-0.05,-0.22,0.12),2022:(0.15,0.03,0.27),
       2023:(-0.05,-0.14,0.04),2024:(0.02,-0.06,0.09),2025:(0.08,-0.04,0.19),2026:(0.10,0.00,0.20)}
def re_b(years, tau_b):
    ws = []; 
    for y in years:
        m,lo,hi = eff[y]; s_=se(lo,hi); ws.append((m, 1/(tau_b**2+s_**2)))
    W = sum(w for _,w in ws); mu = sum(m*w for m,w in ws)/W; semu = sqrt(1/W)
    B = 0.05**2/(0.05**2+semu**2)
    return mu, semu, B*mu
for yrs,tb,lab in (((2019,2020,2021,2022),0.063,'for 2023'),(tuple(range(2019,2027)),0.055,'for 2027')):
    mu,semu,bstar = re_b(yrs,tb)
    print(f"{lab}: RE mean {mu:+.3f} SE {semu:.3f} -> b* {bstar:.3f}")
mu23 = -0.05
for b in (0.07, re_b((2019,2020,2021,2022),0.063)[2]):
    print(f"2023 with b {b:.3f}: {1000*k*(b*mu23-b*b/2):+.2f}")

print("\n== Stage 2 framework line, 2024-26 reading (today's sources, 28-day) ==")
est, s_ = 0.38, se(0.11,0.64); sel = 0.20
for tau in (0.03, 0.1, 0.3):
    B = tau**2/(tau**2+s_**2); print(f"tau {tau}: B {B:.2f}, B*(est-sel) {B*(est-sel):+.3f}")

print("\n== Per-surface vs pooled, offset Elo in (composed_results.csv; + = per-surface better) ==")
rows = {"men close":(0.0018,-0.1481,0.1517),"men no price":(0.1854,-0.0515,0.4224),"men 24h":(-0.1062,-0.5946,0.3821),
        "women close":(-0.0291,-0.1381,0.0799),"women no price":(-0.0562,-0.2509,0.1385),"women 24h":(-0.0037,-0.4536,0.4462),
        "both close":(-0.0130,-0.1018,0.0757),"both no price":(0.0695,-0.0666,0.2055),"both 24h":(-0.0595,-0.4335,0.3145)}
for k_,(m,lo,hi) in rows.items():
    s_=se(lo,hi); print(f"{k_:15s} {m:+.3f} [{lo:+.2f}, {hi:+.2f}] SE {s_:.3f} P(better) {Phi(m/s_):.2f}")
for k_,tau in (("both close",0.03),("men close",0.03),("men no price",0.1),("women no price",0.1)):
    m,lo,hi = rows[k_]; s_=se(lo,hi); B=tau**2/(tau**2+s_**2); print(f"B*est {k_} tau {tau}: {B*m:+.3f} (B {B:.2f})")

print("\n== Short IOS (repairs.md; + = with the input better) ==")
for k_,(m,lo,hi) in {"men":(-0.013,-0.091,0.066),"women":(-0.052,-0.139,0.035)}.items():
    s_=se(lo,hi); B=0.03**2/(0.03**2+s_**2); print(f"{k_}: P {Phi(m/s_):.2f}, B(tau .03) {B:.2f}, B*est {B*m:+.4f}")

print("\n== Sealed read power for item 7's P<=0.2 cut-off (per-match sd 16, 02 s3) ==")
for nm in (300, 1000, 2000, 2500):
    sem = 16/sqrt(nm); cut = -0.84*sem
    for truth in (0.15, -0.12, -0.77):
        print(f"n {nm}: SE {sem:.2f}, cut {cut:+.2f}, truth {truth:+.2f}: P(removed) {Phi((cut-truth)/sem):.2f}")
