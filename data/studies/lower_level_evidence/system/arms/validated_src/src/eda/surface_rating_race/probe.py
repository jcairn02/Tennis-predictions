"""The real-date leak probe of the surface-offset TTT (the project's rule for any cross-player feature; the method of
src/eda/match_timing/probe.py).

On a slice of history (every level, 2023-2024, history inside the slice), per tour and cut day D (match_timing's cuts:
a Grand Slam's second Wednesday and the day Cincinnati 2024 started while Montreal finished): every match that surely
started after D (earliest possible start > D) has its result reversed, the pass is rerun at the chosen constants, and
every output of every match that surely finished by D (latest possible finish <= D) is compared with the unchanged run.
Nothing may move. Matches whose window straddles D are neither changed nor checked.

Writes data/studies/surface_rating_race/probe.json. Run: ./python.sh src/eda/surface_rating_race/probe.py
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.match_timing import common as MT  # noqa: E402
from src.eda.rating_systems import common as RC  # noqa: E402
from src.eda.surface_rating_race import common as C  # noqa: E402
from src.eda.surface_rating_race import runs as RU  # noqa: E402

SLICE = ("2023-01-01", "2024-12-31")
CUTS = ("2023-09-06", "2024-01-24", "2024-07-10", "2024-08-14")


def chosen() -> dict:
    ch = json.loads((C.OUT / "tuning_choice.json").read_text())
    return {t: dict(RU.frozen_constants()[t], sigma_o=ch[t]["sigma_o"], gamma_o=ch[t]["gamma_o"]) for t in C.TOURS}


def slice_history(tour: str) -> tuple[pd.DataFrame, dict]:
    m = RC.load_table()
    t = m[m["tour"].eq(tour) & m["tournament_date"].between(pd.Timestamp(SLICE[0]), pd.Timestamp(SLICE[1]))]
    t = t.reset_index(drop=True)
    h = RC.history(t)
    tm = pd.read_parquet(C.TIMING, columns=["match_id", "es", "lf"]).set_index("match_id")
    h["es"] = t["match_id"].map(tm["es"]).astype(int).tolist()
    h["lf"] = t["match_id"].map(tm["lf"]).astype(int).tolist()
    return t, h


def job(spec: dict) -> dict:
    t, h = slice_history(spec["tour"])
    if spec["cut"] is not None:
        D = float(MT.to_day([spec["cut"]])[0])
        h["a_won"] = [(not w) if e > D else w for w, e in zip(h["a_won"], h["es"])]
    o = RU.run_pass(h, chosen()[spec["tour"]])
    return {**spec, "out": o.to_numpy(), "es": np.array(h["es"]), "lf": np.array(h["lf"])}


def main() -> int:
    t0 = time.time()
    specs = [{"tour": tour, "cut": cut} for tour in C.TOURS for cut in (None,) + CUTS]
    with ProcessPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(job, specs))
    base = {r["tour"]: r for r in res if r["cut"] is None}
    out = []
    for r in res:
        if r["cut"] is None:
            continue
        b = base[r["tour"]]
        D = float(MT.to_day([r["cut"]])[0])
        earlier, later = b["lf"] <= D, b["es"] > D
        x, y = b["out"], r["out"]
        moved = ~np.isclose(x, y, rtol=0, atol=1e-12, equal_nan=True)
        out.append({"tour": r["tour"], "cut": r["cut"], "changed_matches": int(later.sum()),
                    "checked_matches": int(earlier.sum()), "straddling_unchecked": int((~earlier & ~later).sum()),
                    "moved_checked_matches": int(moved[earlier].any(axis=1).sum()),
                    "largest_difference_checked": float(np.nanmax(np.where(np.isfinite(x) & np.isfinite(y),
                                                                           np.abs(x - y), 0.0)[earlier])),
                    "moved_later_matches": int(moved[later].any(axis=1).sum())})
        C.log(f"{r['tour']} cut {r['cut']}: moved {out[-1]['moved_checked_matches']} of {out[-1]['checked_matches']:,} "
              f"earlier matches (later matches moved: {out[-1]['moved_later_matches']:,})")
    verdict = ("PASS: no output of a match that surely finished by the cut moved"
               if all(o["moved_checked_matches"] == 0 for o in out) else "FAIL")
    C.write_json(C.OUT / "probe.json", {"slice": SLICE, "cuts": out, "constants": chosen(), "verdict": verdict,
                                        "seconds": round(time.time() - t0, 1)})
    C.log(verdict)
    return 0 if verdict.startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
