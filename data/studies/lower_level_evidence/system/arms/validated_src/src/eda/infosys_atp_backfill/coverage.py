"""How much recent speed the backfill gives the model's matches: the share of men's frame matches whose players have a
usable speed reading in the 28 days before the match, on the corrected and the augmented histories. Reads no result.

This is the quantity the serve-speed study named as the likely reason TabPFN used only about 8% of the speed column's
information: "In the 2024 fit's training rows, only 24% of men's matches have both players timed within 28 days (42% at
least one)" (docs/studies/serve_speed_tabpfn/README.md, section 6.3), with "decrypt the ATP's 2015-20 files" proposed
to lift it. A side has a reading when one of the player's usable panel rows finished before the match could start
(lf + 1 <= es, the build's release) and was observed in the 28 days before (obs >= es - 28).

Writes data/studies/infosys_atp_backfill/coverage.json.
Run: ./python.sh src/eda/infosys_atp_backfill/coverage.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.live import live_panel as LP  # noqa: E402

OUT = ROOT / "data" / "studies" / "infosys_atp_backfill"
AUGMENTED = LP.BACKFILLED
WINDOW = 28


def side_has_reading(panel: pd.DataFrame, pid: np.ndarray, es: np.ndarray) -> np.ndarray:
    """True where the player has a usable row with lf + 1 <= es and obs >= es - WINDOW (and obs < es)."""
    u = panel[panel["use"].astype(bool) & panel["tour"].eq("atp")]
    rel = (u["lf"].to_numpy(np.int64) + 1)
    obs = u["obs"].to_numpy(np.int64)
    groups = pd.Series(np.arange(len(u))).groupby(u["player_id"].to_numpy()).indices
    out = np.zeros(len(pid), bool)
    order = pd.Series(np.arange(len(pid))).groupby(pid).indices
    for p, ti in order.items():
        r = groups.get(p)
        if r is None:
            continue
        e = es[ti][:, None]
        ok = (rel[r][None, :] <= e) & (obs[r][None, :] >= e - WINDOW) & (obs[r][None, :] < e)
        out[ti] = ok.any(1)
    return out


def main() -> int:
    fk = P.load_frame_keys()
    men = fk[fk["tour"].eq("atp")].reset_index(drop=True)
    es = men["es"].to_numpy(np.int64)
    res = {}
    for name, path in (("corrected", LP.CORRECTED), ("augmented", AUGMENTED)):
        pan = pd.read_parquet(path)
        a = side_has_reading(pan, men["player_a_id"].to_numpy(), es)
        b = side_has_reading(pan, men["player_b_id"].to_numpy(), es)
        g = pd.DataFrame({"season": men["season"], "both": a & b, "one": a | b})
        res[name] = {"by_season": {int(s): {"matches": int(len(x)), "both_28d": int(x["both"].sum()),
                                            "at_least_one_28d": int(x["one"].sum())} for s, x in g.groupby("season")},
                     "training_rows_of_the_2024_fit": {"matches": int((g["season"] <= 2023).sum()),
                                                       "both_share": float(g.loc[g["season"] <= 2023, "both"].mean()),
                                                       "one_share": float(g.loc[g["season"] <= 2023, "one"].mean())},
                     "training_rows_of_the_2026_fit": {"matches": int((g["season"] <= 2025).sum()),
                                                       "both_share": float(g.loc[g["season"] <= 2025, "both"].mean()),
                                                       "one_share": float(g.loc[g["season"] <= 2025, "one"].mean())}}
    c, a = res["corrected"], res["augmented"]
    res["gained"] = {s: {"both_28d": a["by_season"][s]["both_28d"] - c["by_season"][s]["both_28d"],
                         "at_least_one_28d": a["by_season"][s]["at_least_one_28d"]
                         - c["by_season"][s]["at_least_one_28d"]} for s in c["by_season"]}
    res["note"] = ("men's frame matches (the model frame the speed columns were built for: no men's 2018); a side has a "
                   "reading when a usable panel row has lf + 1 <= es and es - 28 <= obs < es")
    (OUT / "coverage.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    for k in ("training_rows_of_the_2024_fit", "training_rows_of_the_2026_fit"):
        print(k, "corrected", c[k], "augmented", a[k])
    print({s: v for s, v in res["gained"].items() if v["both_28d"] or v["at_least_one_28d"]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
