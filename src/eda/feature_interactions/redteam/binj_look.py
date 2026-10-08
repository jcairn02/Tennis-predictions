"""Red team (S3), the ONE allowed look (diagnosis only, 2014-2024, never 2025-2026): is B-INJ's screen signal
concentrated in 2020-2021 (the pandemic break)? The screen's own machinery (screen_batch.screen_one -> screen.run, model
base, n_p1 = 0; the batch's widening for B-INJ was 1.0, so n_p1 = 0 changes nothing) on
    full        2014-2024 as screened (must reproduce the published z1 +3.505, z2 +1.927: a machinery check)
    ex2020_21   2014-2019 (discovery) and 2022-2024 (replication), 2020 and 2021 removed
It cannot change a claim or the bundle (plan.md F-6). Logged as one look-ledger row.
Writes data/studies/feature_interactions/redteam/look_ex2020_2021.json.
Run once: ./python.sh src/eda/feature_interactions/redteam/binj_look.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402
from src.eda.feature_interactions import screen_batch as B  # noqa: E402
from src.eda.feature_interactions.g5_build import spec_of  # noqa: E402
from src.eda.feature_interactions.history import long_table  # noqa: E402
from src.eda.feature_interactions.panel import panel  # noqa: E402

KEEP = ("z1", "z2", "n1", "n2", "z1_adj", "z2_adj", "z_joint", "p_joint", "widen", "filter_pass", "replicates")


def main() -> int:
    warnings.simplefilter("ignore")
    spec = spec_of("B-INJ")
    P = panel(max_season=2024)
    Pn = P.drop(columns=["a_won"])
    L = long_table()
    new = spec["prepare"](Pn, L)
    r = B.evaluate(spec, Pn.assign(**new))
    x = np.asarray(r["x"], float)
    frozen = pd.read_csv(B.HYP / "hypothesis_table.csv").set_index("hid").loc["B-INJ", "x_sha256"]
    assert B.sha_array(x) == frozen, "B-INJ's x is not the frozen column"
    Cm = None if r.get("controls") is None else np.asarray(r["controls"], float).reshape(len(Pn), -1)
    names = r.get("control_names", [])
    F = S.load(with_model=True)
    assert F["season"].between(2014, 2024).all()
    pos = pd.Series(np.arange(len(Pn)), index=Pn["match_id"].astype(str)).reindex(F["match_id"]).to_numpy().astype(int)
    eta = {b: F[f"z_{b}"].to_numpy(float) for b in ("model", "market")}
    out = {}
    for tag, keep in (("full", np.ones(len(F), bool)), ("ex2020_21", ~F["season"].isin([2020, 2021]).to_numpy())):
        Fk = F[keep].reset_index(drop=True)
        ek = {b: v[keep] for b, v in eta.items()}
        res = B.screen_one(Fk, Pn, pos[keep], ek, "B-INJ", x, Cm, names, {**spec, "_r": r}, new, "model", n_p1=0)
        out[tag] = {k: (float(res[k]) if not isinstance(res[k], (bool, np.bool_)) else bool(res[k])) for k in KEEP}
        out[tag].update({k: float(v) for k, v in res.items() if k.startswith(("gain_", "lo_", "hi_"))})
        out[tag]["seasons"] = sorted(int(s) for s in Fk["season"].unique())
        C.log(f"{tag}: z1 {res['z1']:+.3f} (n {res['n1']}) z2 {res['z2']:+.3f} (n {res['n2']}) joint {res['z_joint']:+.3f}")
    C.write_json(C.OUT / "redteam" / "look_ex2020_2021.json", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
