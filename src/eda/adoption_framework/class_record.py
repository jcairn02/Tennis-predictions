"""The pooled record of readings by kind of change (the adoption framework, section 10; the owner's decision of 9 Oct
2026, docs/decisions/2026-10-09-adoption-by-change-class.md).

Reads data/studies/adoption_framework/class_record.csv: one row per reading, copied from the cited document (no data
file is read). For each kind, it pools the rows marked pool = yes: one row per change, on seasons <= 2024 only, with an
interval. A row's SE is (hi - lo) / 3.92. It prints:
    * the fixed-effect (inverse-variance) mean and its 95% interval;
    * the DerSimonian-Laird spread of true effects (tau) and the random-effects mean.
These replace the framework's section 0 starting values for mu0 and tau as they firm up. With one or two readings a
kind's numbers are anecdotes, and are printed as such. Signs follow each row's own direction key; every pooled row reads
"+ = the change better" (removals and tuning rows are kept out of the pool, since their signs are not comparable).

Run: ./python.sh src/eda/adoption_framework/class_record.py > data/studies/adoption_framework/class_record.out
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RECORD = ROOT / "data" / "studies" / "adoption_framework" / "class_record.csv"


def pool(est: np.ndarray, se: np.ndarray) -> dict:
    """Inverse-variance mean, and DerSimonian-Laird tau with the random-effects mean."""
    w = 1.0 / se ** 2
    mean = float(np.sum(w * est) / np.sum(w))
    se_mean = float(np.sqrt(1.0 / np.sum(w)))
    k = len(est)
    q = float(np.sum(w * (est - mean) ** 2))
    tau2 = 0.0
    if k > 1:
        c = float(np.sum(w) - np.sum(w ** 2) / np.sum(w))
        tau2 = max(0.0, (q - (k - 1)) / c) if c > 0 else 0.0
    w_re = 1.0 / (se ** 2 + tau2)
    mean_re = float(np.sum(w_re * est) / np.sum(w_re))
    se_re = float(np.sqrt(1.0 / np.sum(w_re)))
    return {"k": k, "mean": mean, "lo": mean - 1.96 * se_mean, "hi": mean + 1.96 * se_mean, "Q": q,
            "tau": float(np.sqrt(tau2)), "mean_re": mean_re, "lo_re": mean_re - 1.96 * se_re,
            "hi_re": mean_re + 1.96 * se_re}


def main() -> int:
    rec = pd.read_csv(RECORD)
    rec["se"] = (rec["hi"] - rec["lo"]) / 3.92
    print(f"The pooled record: {len(rec)} readings in {RECORD.relative_to(ROOT)} (mLL per match).")
    print("Each row's own direction key applies; pooled rows all read '+ = the change better'.\n")
    for kind, g in rec.groupby("kind", sort=False):
        print(f"== {kind} ({len(g)} readings)")
        for _, r in g.iterrows():
            ci = "" if pd.isna(r["lo"]) else f" [{r['lo']:+.3f}, {r['hi']:+.3f}]"
            tags = [t for t, on in (("pooled", r["pool"] == "yes"), ("holdout seasons", r["holdout_seasons"] == "yes"),
                                    (f"seeds paired: {r['seeds_paired']}", True)) if on]
            print(f"   {r['id']:<32} {r['estimate']:+.3f}{ci}  {r['seasons']}, {r['target']}; {r['direction']}"
                  f"  ({'; '.join(tags)})")
        p = g[(g["pool"] == "yes") & (g["holdout_seasons"] == "no") & g["lo"].notna()]
        if len(p) == 0:
            print("   pooled: none\n")
            continue
        s = pool(p["estimate"].to_numpy(float), p["se"].to_numpy(float))
        note = " (one or two readings: an anecdote, not a prior)" if s["k"] < 3 else ""
        print(f"   pooled over {s['k']}{note}: fixed {s['mean']:+.3f} [{s['lo']:+.3f}, {s['hi']:+.3f}]; "
              f"tau {s['tau']:.3f}; random effects {s['mean_re']:+.3f} [{s['lo_re']:+.3f}, {s['hi_re']:+.3f}]\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
