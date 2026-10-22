"""Power of a check on unseen matches for the cleaner candidates (serve/return-leads study), with timeline.py's
calendar and power functions. For each candidate: its seen 2025-26 reading (beta per RMS, se, n) and its 2013-24 beta,
from decompose_single.csv (raw, beyond the close) or, for the combined luck score, from the reading logged at 14:28
(mean of the oriented save and hold luck, RMS-scaled on 2013-24). Scenarios: the 2025-26 strength in full, 0.45 of it,
and the 2013-24 strength. One look at one-sided 0.05.

Writes data/studies/serve_return_leads/timeline_clean.csv.
Run: ./python.sh src/eda/serve_return_leads/timeline_clean.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_return_leads import common as C  # noqa: E402
from src.eda.serve_return_leads import timeline as T  # noqa: E402
from src.eda.unpriced_leads import screen as H  # noqa: E402

LUCK_SCORE = {"beta_2025_26": 0.0897, "se_2025_26": 0.0337, "n_2025_26": 4394, "beta_2013_24": 0.0426}


def main() -> int:
    cal, _ = T.unseen_calendar()
    blk = H.blocks(cal["d"].to_numpy(), 28)
    d = pd.read_csv(C.OUT / "decompose_single.csv")
    d = d[(d["form"] == "raw") & (d["base"] == "L")].set_index(["candidate", "window"])
    cands = {"luck score": LUCK_SCORE}
    for k in ("ST", "PS03_save", "PS03_hold", "R0"):
        cands[k] = {"beta_2025_26": float(d.loc[(k, "2025-26"), "beta"]), "se_2025_26": float(d.loc[(k, "2025-26"), "se"]),
                    "n_2025_26": int(d.loc[(k, "2025-26"), "n"]), "beta_2013_24": float(d.loc[(k, "2013-24"), "beta"])}
    rows = []
    for name, c in cands.items():
        for date in ("2027-01-31", "2027-05-31", "2027-08-31", "2027-12-31"):
            k = (cal["d"] <= pd.Timestamp(date)).to_numpy()
            N, G = int(k.sum()), int(len(np.unique(blk[k])))
            se = c["se_2025_26"] * np.sqrt(c["n_2025_26"] / N)
            row = {"candidate": name, "date": date, "unseen_men": N, "blocks": G}
            for scn, b in (("2025-26 in full", c["beta_2025_26"]), ("0.45 of 2025-26", 0.45 * c["beta_2025_26"]),
                           ("2013-24 strength", c["beta_2013_24"])):
                row[scn] = T.power(b / se, G, 0.05)
            rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(C.OUT / "timeline_clean.csv", index=False)
    print(out.round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
