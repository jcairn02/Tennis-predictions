"""Design scratch (agent 2): does it matter whether the state is projected to the target match's best-estimate day
(`obs`, as x_raw does) or to its earliest possible start (`es`, the leak-proof clock's reading day)? Feature values only
(men's model-frame matches 2022-2026): the correlation and the mean ratio of |f_hat| between the two versions.

Run: ./python.sh src/eda/serve_speed_tabpfn/design/modeller_esobs.py
Writes data/studies/serve_speed_tabpfn/design/modeller_esobs.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.design import modeller_common as M  # noqa: E402
from src.eda.serve_speed_tabpfn.design import modeller_state as S  # noqa: E402
from src.eda.serve_speed_tabpfn.design.modeller_features import side_targets  # noqa: E402


def main() -> None:
    st = json.loads((M.OUT / "modeller_state_ks_first.json").read_text(encoding="utf-8"))["tours"]["atp"]
    prm, nu = st["kalman_tuned"]["params"], st["kalman_tuned"]["nu"]
    p = M.panel("ks_first")
    p = p[p["tour"] == "atp"]
    p = S.centre(p, S.offsets(p, 2023), nu)
    tg = side_targets()
    tg = tg[(tg["tour"] == "atp") & tg["season"].between(2022, 2026) & tg["obs"].notna() & tg["es"].notna()]
    a = S.kalman(p, tg[["tour", "player_id", "tdate", "tournament_id", "round_order", "obs"]], prm)["f_hat"]
    tg_es = tg.assign(obs=tg["es"])
    b = S.kalman(p, tg_es[["tour", "player_id", "tdate", "tournament_id", "round_order", "obs"]], prm)["f_hat"]
    out = {"rows": int(len(tg)), "corr_obs_es": float(np.corrcoef(a, b)[0, 1]),
           "mean_abs_obs": float(a.abs().mean()), "mean_abs_es": float(b.abs().mean()),
           "median_obs_minus_es_days": float((tg["obs"] - tg["es"]).median())}
    (M.OUT / "modeller_esobs.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
