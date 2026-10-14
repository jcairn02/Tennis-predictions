"""Harness verifier: screen.weighted_holm and screen.weighted_bh against brute-force rejection rules, on random p-values
and weights (no data). Holm (weighted step-down): order by p/w; at each step reject while p_(j) <= alpha * w_(j) /
(sum of the weights not yet rejected). BH (Genovese, Roeder, Wasserman 2006): q = p / w with weights of mean 1; reject the
k smallest q, k = max{i: q_(i) <= alpha * i / m}.

Run: ./python.sh src/eda/feature_interactions/verify/multiplicity_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import screen as S  # noqa: E402


def holm_reject(p, w, alpha):
    order = np.argsort(p / w)
    remaining, rej = w.sum(), np.zeros(len(p), bool)
    for j in order:
        if p[j] <= alpha * w[j] / remaining:
            rej[j] = True
            remaining -= w[j]
        else:
            break
    return rej


def bh_reject(p, w, alpha):
    q = p / (w / w.mean())
    order = np.argsort(q)
    m = len(p)
    ok = np.flatnonzero(q[order] <= alpha * np.arange(1, m + 1) / m)
    rej = np.zeros(m, bool)
    if len(ok):
        rej[order[: ok.max() + 1]] = True
    return rej


def main() -> int:
    rng = np.random.default_rng(0)
    bad_h = bad_b = 0
    for _ in range(20000):
        m = int(rng.integers(2, 60))
        p = np.where(rng.random(m) < 0.3, rng.random(m) * 0.002, rng.random(m))
        p[rng.random(m) < 0.2] = 1.0                        # filtered hypotheses count p = 1
        w = rng.choice([0.5, 1.0, 2.0], m)
        for alpha in (0.05, 0.10):
            bad_h += int((holm_reject(p, w, alpha) != (S.weighted_holm(p, w) <= alpha)).any())
            bad_b += int((bh_reject(p, w, alpha) != (S.weighted_bh(p, w) <= alpha)).any())
    print(f"weighted Holm disagreements: {bad_h} of 40000; weighted BH disagreements: {bad_b} of 40000")
    return 0


if __name__ == "__main__":
    sys.exit(main())
