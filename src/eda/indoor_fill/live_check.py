"""Can a prediction run reproduce the indoor input? The rule (status.py) on every model match as if it were live.

A live match has no tennis-data row: tennis-data publishes a match after it is played, and a prediction run's Stage 1
row for it carries no link (prediction_run/inject.py). Its event's earlier rounds may not be published either. So, season
by season, this check drops every tennis-data link of the season (the worst case: nothing of the season published) and
runs the rule again. A model match passes when the value equals the one the frame trains on, the rule with every link.

Stage 0's flag is kept as it stands: a live row carries TML's event field as the event's played rows do
(prediction_run/live_rows.py). No result is read.

Writes data/studies/indoor_fill/live_check.json and live_check.csv (by tour, season and the source the live value
comes from).
Run: ./python.sh src/eda/indoor_fill/live_check.py
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

from src.eda.indoor_fill import status as ST  # noqa: E402

OUT = ROOT / "data" / "studies" / "indoor_fill"
FRAME = ROOT / "data" / "studies" / "current_best_model" / "pinnacle_first_2026-10-09" / "model_frame.parquet"


def main() -> int:
    f = pd.read_parquet(FRAME, columns=["match_id", "tour", "season"])
    f["match_id"] = f["match_id"].astype(str)
    m = ST.stage0_rows()
    td = ST.td_fields(m["match_id"], ["Court", "Location"])
    court, loc = ST.court_flag(td["Court"]), td["Location"]
    full = ST.rule(m, court, loc, ST.wta_editions).set_index("match_id")["indoor"]
    rows = []
    for season in sorted(f["season"].unique()):
        drop = set(m.loc[m["year"].eq(season), "match_id"])
        live = ST.rule(m, court[~court.index.isin(drop)], loc[~loc.index.isin(drop)], ST.wta_editions)
        live = live.set_index("match_id")
        ids = f.loc[f["season"].eq(season), "match_id"]
        got, want = live.loc[ids, "indoor"], full.loc[ids]
        same = (got.to_numpy() == want.to_numpy())
        t = pd.DataFrame({"tour": f.loc[ids.index, "tour"].to_numpy(), "source": live.loc[ids, "source"].to_numpy(),
                          "same": same, "unknown": ~np.isfinite(got.to_numpy())})
        g = t.groupby(["tour", "source"]).agg(matches=("same", "size"), same=("same", "sum"),
                                              unknown=("unknown", "sum")).reset_index()
        rows.append(g.assign(season=int(season)))
    table = pd.concat(rows, ignore_index=True)[["tour", "season", "source", "matches", "same", "unknown"]]
    OUT.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT / "live_check.csv", index=False)
    tot = table.groupby("tour")[["matches", "same", "unknown"]].sum()
    differ = table[table["same"] < table["matches"]]
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "scenario": "each season with every tennis-data link of the season dropped",
               "totals": tot.reset_index().to_dict("records"), "cells_that_differ": differ.to_dict("records"),
               "by_source": table.groupby(["tour", "source"])[["matches", "same", "unknown"]].sum().reset_index()
               .to_dict("records")}
    (OUT / "live_check.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(tot.to_string())
    print(table.groupby(["tour", "source"])[["matches", "same", "unknown"]].sum().to_string())
    print(differ.to_string(index=False) if len(differ) else "every live value equals the frame's")
    return 0


if __name__ == "__main__":
    sys.exit(main())
