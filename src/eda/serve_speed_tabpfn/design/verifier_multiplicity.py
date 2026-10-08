"""R4 test verifier: the null distribution of the multiplicity count (pre-registration section 9), synthetic outcomes.

The world is verifier_signs.full_world with no speed term anywhere (BETA = GAMMA = 0): every arm is the base plus its
own independent seed noise (the no-odds pair: 0.85 mu plus noise), the prices are synthetic, the truth is a_tour mu.
score.evaluate() runs in full; per replicate: which of the S0-S14 intervals exclude 0, and the count
(results.json -> multiplicity). S13 (the base against the close) is expected to exclude 0 by construction.

Writes data/studies/serve_speed_tabpfn/design/verifier_multiplicity/null_s<seed>.json.
Run: ./python.sh src/eda/serve_speed_tabpfn/design/verifier_multiplicity.py --reps 100 --seed 1
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402
from src.eda.serve_speed_tabpfn.design import verifier_signs as VS  # noqa: E402
from src.eda.serve_speed_tabpfn.design import verifier_worlds as V  # noqa: E402

OUT = C.OUT / "design" / "verifier_multiplicity"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=100)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--tag", default=None, help="file prefix, e.g. reverify (the re-run after V1)")
    a = ap.parse_args()
    VS.BETA, VS.GAMMA = 0.0, 0.0                     # the null: no speed term in the truth or in any arm
    t0 = time.time()
    W = V.World()
    rng = np.random.default_rng(9000 + a.seed)
    reps = []
    for r in range(a.reps):
        bank, info, y, _ = VS.full_world(W, rng, reverse_test=False)
        res = S.evaluate(S.Scorer(bank, info, y))
        rows = S.secondary_rows(res)
        reps.append({"rep": r, "count": res["multiplicity"]["excluding_0"],
                     "intervals": res["multiplicity"]["secondary_intervals"], "which": res["multiplicity"]["which"],
                     "P2_excludes_0": bool(res["P2"]["lo"] > 0 or res["P2"]["hi"] < 0),
                     "decision_row": res["decision"]["row"],
                     "estimates": {x["cid"]: [x["estimate"], x["lo"], x["hi"]] for x in rows}})
    name = f"{a.tag}_null_s{a.seed}.json" if a.tag else f"null_s{a.seed}.json"
    C.write_json(OUT / name, {"what": "multiplicity count under the null (no speed term); synthetic outcomes and prices; "
                                      "no match result read", "reps": a.reps, "seed": a.seed, "tag": a.tag,
                              "scorer_code_sha256": C.code_hash(), "seconds": round(time.time() - t0, 1),
                              "replicates": reps})
    print(f"null multiplicity seed {a.seed}: {a.reps} reps, {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
