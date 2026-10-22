"""Robustness of the serve/return-leads scores on seen matches (the readings logged at 14:30 and 14:32 on 16 Oct 2026,
first run inline, saved here to reproduce them).

    subsets   all; completed matches only (Stage 0's status); the Slams left out (best of five); in 2025-26 also the
              Pinnacle months (the odds input from Pinnacle, to 7 Sep 2025) and the BetOnline months
    books     the same matches priced by both books (2025; 2023-24): each score beyond Pinnacle's own margin-free close
              and beyond BetOnline's, from the instance's book prices
Scores: R0 and T4 (the lock-in), the luck score (save and hold luck, each over its 2013-24 RMS), ST (the balance),
T1 and T3. Raw, beyond the base, the registered fit.

Writes data/studies/serve_return_leads/robustness.csv and same_matches_books.csv.
Run: ./python.sh src/eda/serve_return_leads/robustness.py
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
from src.eda.serve_return_leads import decompose as D  # noqa: E402
from src.eda.serve_return_leads import readings as R  # noqa: E402
from src.eda.unpriced_leads import screen as H  # noqa: E402


def unit(v: np.ndarray, m: np.ndarray) -> np.ndarray:
    v = np.nan_to_num(v)
    return v / np.sqrt(np.mean(v[m] ** 2))


def main() -> int:
    f = R.seen_frame("atp")
    s = C.scores(f, C.scales(f))
    c, _ = D.candidates(f)
    m24 = f["season"].between(2013, 2024).to_numpy()
    luck = (-unit(c["PS03_save"], m24) - unit(c["PS03_hold"], m24)) / 2
    X = {"R0": s["R0"], "ST": -np.nan_to_num(c["ST"]), "T4 speed": s["T4"], "luck score": luck, "T1": s["T1"],
         "T3": s["T3"]}
    st = pd.read_parquet(H.STAGE0_M, columns=["match_id", "status"]).astype({"match_id": str})
    st = st.drop_duplicates("match_id").set_index("match_id")["status"].reindex(f["match_id"])
    retired = (st.astype(str).str.lower() == "retired").to_numpy()
    slam = f["in_best_of"].to_numpy(float) == 5
    src = f["odds_input"].astype(str).str.lower()
    rows = []
    for name in ("luck score", "ST", "R0", "T4 speed"):
        x = X[name]
        for w, (a, b) in {"2013-24": (2013, 2024), "2025-26": (2025, 2026)}.items():
            base = f["season"].between(a, b).to_numpy()
            subsets = {"all": base, "completed only": base & ~retired, "Slams out": base & ~slam}
            if w == "2025-26":
                subsets["Pinnacle months"] = base & src.str.contains("pinn").to_numpy()
                subsets["BetOnline months"] = base & src.str.contains("betonline").to_numpy()
            for sn, m in subsets.items():
                r = C.fit(f[m].reset_index(drop=True), x[m])
                rows.append({"score": name, "window": w, "subset": sn, "n": r["n"], "z": r["z"], "beta": r["beta"]})
    out = pd.DataFrame(rows)
    out.to_csv(C.OUT / "robustness.csv", index=False)
    bp = pd.read_parquet(C.INSTANCE / "book_prices.parquet", columns=["match_id", "pin_a", "pin_b", "bol_a", "bol_b"])
    bp = bp.astype({"match_id": str}).drop_duplicates("match_id").set_index("match_id").reindex(f["match_id"])
    for book in ("pin", "bol"):
        ia, ib = 1 / bp[f"{book}_a"].to_numpy(float), 1 / bp[f"{book}_b"].to_numpy(float)
        L = H.lg(ia / (ia + ib))
        L[~(np.isfinite(ia) & np.isfinite(ib))] = np.nan
        f[f"L_{book}"] = L
    rows = []
    for w, (a, b) in {"2025 both books": (2025, 2025), "2023-24 both books": (2023, 2024)}.items():
        m = f["season"].between(a, b).to_numpy() & np.isfinite(f["L_pin"].to_numpy()) & np.isfinite(f["L_bol"].to_numpy())
        g = f[m].reset_index(drop=True)
        for name, x in X.items():
            for base in ("L_pin", "L_bol"):
                r = C.fit(g, x[m], base=base)
                rows.append({"window": w, "score": name, "base": base, "n": r["n"], "z": r["z"], "beta": r["beta"]})
    books = pd.DataFrame(rows)
    books.to_csv(C.OUT / "same_matches_books.csv", index=False)
    pd.set_option("display.width", 250)
    print(out.pivot_table(index=["score", "window"], columns="subset", values="z").round(2).to_string())
    print(books.pivot_table(index=["window", "score"], columns="base", values="z").round(2).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
