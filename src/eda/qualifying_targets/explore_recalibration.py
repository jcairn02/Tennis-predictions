"""EXPLORATORY, NOT PRE-REGISTERED (added 22 Oct 2026, 09:35, after the pre-registered scores were read): is the
model's gain over the calibrated close only a curved recalibration of the close?

The pre-registered baseline recalibrates the close with one slope per tour (compare.close_forecast). If the closes'
error on qualifying is curved (e.g. concentrated on heavy favourites), a model that takes the close as an input could
win by bending it, without its other inputs. Here the close gets a flexible recalibration, fitted the same way (per tour,
walk-forward on 2019 .. Y - 1, debut seasons out): logistic regression of the result on z, z^3 and z * |z| (z = the
close's log-odds; odd functions, as side A is random), and M1 and M0 are scored against it on the same matches with
compare.paired (unmatched).

Writes data/studies/qualifying_targets/exploratory_recalibration.json.
Run: ./python.sh src/eda/qualifying_targets/explore_recalibration.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.qualifying_targets import common as C  # noqa: E402
from src.eda.qualifying_targets import score as S  # noqa: E402
from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402


def basis(z: np.ndarray) -> np.ndarray:
    return np.column_stack([z, z ** 3, z * np.abs(z)])


def curved_close(info: pd.DataFrame, ids: pd.Index):
    out = pd.Series(np.nan, index=ids)
    for Y in S.TEST:
        hist = info.index[(info["season"] < Y) & ~info["debut"]]
        for tour in ("atp", "wta"):
            h = hist[(info.loc[hist, "tour"] == tour).to_numpy()]
            beta, _ = SC.fit_logistic(basis(SC.lg(info.loc[h, "p_close"].to_numpy())), info.loc[h, "y"].to_numpy(float))
            t = ids[((info.loc[ids, "season"] == Y) & (info.loc[ids, "tour"] == tour)).to_numpy()]
            out.loc[t] = expit(basis(SC.lg(info.loc[t, "p_close"].to_numpy())) @ beta)
    q = out.to_numpy(float)
    return q, q[:, None]


def main() -> int:
    info, z = S.qual_info()
    keep = ~info["debut"].to_numpy() & info["season"].isin(S.TEST).to_numpy()
    rows = []
    for arm in ("M1", "M0"):
        m = S.model(S.seed_table(arm, "qual"), info, z)
        for name, mask in (("both tours", keep), ("2020-2024", keep & info["season"].isin(S.PERIODS["2020-2024"]).to_numpy()),
                           ("2025-2026", keep & info["season"].isin(S.PERIODS["2025-2026"]).to_numpy())):
            ids = info.index[mask]
            base = curved_close(info, ids)
            lin = CMP.close_forecast(info, "p_close", S.TEST, ids)
            a = S.fc(m, "s2", info, ids)
            rows.append(S.row(info, ids, base, a, False, comparison=f"{arm} vs curved close", population=name))
            rows.append(S.row(info, ids, lin, base, False, comparison="curved close vs calibrated close",
                              population=name))
    t = pd.DataFrame(rows).drop_duplicates(["comparison", "population"])
    C.write_json(C.OUT / "exploratory_recalibration.json", {"note": "exploratory, not pre-registered",
                                                            "rows": t.to_dict("records")})
    t["ci"] = t.apply(lambda r: f"{r['estimate']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}] P{r['p_better']:.2f}", axis=1)
    print(t.pivot_table(index="comparison", columns="population", values="ci", aggfunc="first").to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
