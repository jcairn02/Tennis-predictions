"""Does the backfill change any live forecast input? The live panel and a day's 28-day speed form, built twice in a
temporary folder (the live folder is not written): on the corrected history and on the backfilled one, with the same
linked daily rows (live/linked.parquet). Reads no match result.

Expected: no player's form moves, because every backfilled row is from 17 Oct 2021 or earlier, outside the form's
364-day history and the as-of offsets' window for any day after 16 Oct 2022.

Writes data/studies/infosys_atp_backfill/live_check.json.
Run: ./python.sh src/eda/infosys_atp_backfill/live_check.py [--day 2026-10-08]
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.live import common as LC  # noqa: E402
from src.eda.serve_speed_tabpfn.live import form as FM  # noqa: E402
from src.eda.serve_speed_tabpfn.live import live_panel as LP  # noqa: E402

OUT = ROOT / "data" / "studies" / "infosys_atp_backfill"


def live_form(history: pd.DataFrame, linked: pd.DataFrame, day: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    keep = LP.frozen_panel
    LP.frozen_panel = lambda: history
    try:
        with tempfile.TemporaryDirectory() as tmp:
            live, _ = LP.build(linked, out=Path(tmp))
    finally:
        LP.frozen_panel = keep
    return live, FM.form_as_of(day, live)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default="2026-10-08")
    day = LC.day_of(ap.parse_args().day)
    linked = pd.read_parquet(LC.LINKED)
    a_live, a = live_form(pd.read_parquet(LP.CORRECTED), linked, day)
    b_live, b = live_form(pd.read_parquet(LP.BACKFILLED), linked, day)
    j = a.merge(b, on="player_id", how="outer", suffixes=("_corrected", "_backfilled"), indicator=True)
    both = j[j["_merge"].eq("both")]
    moved = both[~np.isclose(both["f_hat_corrected"], both["f_hat_backfilled"], rtol=0, atol=1e-12)]
    # a player listed on one side only (his only rows are backfilled) has form 0, as an absent player is given
    one = j[j["_merge"].ne("both")]
    f_one = one["f_hat_backfilled"].fillna(one["f_hat_corrected"]).to_numpy(float)
    res = {"day": LC.date_of(day), "live_rows_corrected": int(len(a_live)), "live_rows_backfilled": int(len(b_live)),
           "players_corrected": int(len(a)), "players_backfilled": int(len(b)),
           "players_only_in_one": int(len(one)), "their_f_hat": [float(x) for x in f_one],
           "players_whose_form_moved": int(len(moved)) + int((np.abs(f_one) > 1e-12).sum()),
           "max_abs_f_hat_change_kmh": float((both["f_hat_corrected"] - both["f_hat_backfilled"]).abs().max()),
           "latest_backfilled_row": LC.date_of(int(b_live.loc[b_live["source"].isin(["infosys_atp", "infosys_atp_ks"]),
                                                             "obs"].max()))}
    (OUT / "live_check.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0 if res["players_whose_form_moved"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
