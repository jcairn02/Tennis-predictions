# Which is sharper: Pinnacle's last price (TennisExplorer) or BetOnline's close?

Written by `src/eda/pinnacle_gap/sharpness.py`. Log loss in mLL (thousandths of a nat): lower is sharper. "A − B": + = A worse. 95% intervals over four-week blocks. Reads results.

| Reading | A | B | Matches | A's log loss | B's log loss | A − B | Verdict |
|---|---|---|---:|---:|---:|---|---|
| Nov 2025 - Oct 2026 (declared primary) | site's Pinnacle (all rows) | BetOnline's close | 4,371 | 588.3 | 588.2 | +0.13 [-0.75, +1.02] | unresolved (P(te_all better) 0.37) |
| 2026 (Jan - Oct) | site's Pinnacle (all rows) | BetOnline's close | 4,288 | 588.6 | 588.5 | +0.11 [-0.81, +1.02] | unresolved (P(te_all better) 0.40) |
| Nov 2025 - Oct 2026, the price the model will use | site's Pinnacle (as the model uses it) | BetOnline's close | 4,302 | 588.1 | 588.4 | -0.28 [-1.24, +0.67] | unresolved (P(te_rule better) 0.74) |
| 2026 (Jan - Oct), the price the model will use | site's Pinnacle (as the model uses it) | BetOnline's close | 4,229 | 588.2 | 588.5 | -0.30 [-1.28, +0.69] | unresolved (P(te_rule better) 0.75) |
| Nov 2025 - Oct 2026, ATP, the price the model will use | site's Pinnacle (as the model uses it) | BetOnline's close | 2,239 | 597.2 | 597.2 | +0.07 [-1.12, +1.25] | unresolved (P(te_rule better) 0.45) |
| Nov 2025 - Oct 2026, WTA, the price the model will use | site's Pinnacle (as the model uses it) | BetOnline's close | 2,063 | 578.2 | 578.9 | -0.66 [-2.27, +0.94] | unresolved (P(te_rule better) 0.82) |
| 1 Jan - 23 Jul 2025: the site's last price - Pinnacle's own close | site's Pinnacle (as the model uses it) | Pinnacle's own close | 3,078 | 597.7 | 597.3 | +0.41 [-0.43, +1.26] | unresolved (P(te_rule better) 0.12) |
| 1 Jan - 23 Jul 2025: BetOnline's close - Pinnacle's own close | BetOnline's close | Pinnacle's own close | 3,078 | 598.2 | 597.3 | +0.84 [-0.21, +1.88] | unresolved (P(bol better) 0.03) |
| 1 Jan - 23 Jul 2025: the site's last price - BetOnline's close | site's Pinnacle (as the model uses it) | BetOnline's close | 3,078 | 597.7 | 598.2 | -0.43 [-1.11, +0.26] | unresolved (P(te_rule better) 0.93) |

**Encompassing, Nov 2025 – Oct 2026** (4,302 matches): the result fitted on both prices' log-odds. Weight on the site's Pinnacle 0.68 [-0.55, 1.92], on BetOnline's close 0.38 [-0.87, 1.63] (1 and 0: the first carries everything the second does).

Margins, median: the site's Pinnacle 2.81%, BetOnline 3.99%.
