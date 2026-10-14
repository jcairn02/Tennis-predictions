"""Round-2 feasibility of the geography rebuttals (I-060, I-074, I-075), both windows (result-free).

Event country: the Stage 4 table for evaluation events, else the IOC code in an ITF tournament id; continent from the
body brainstormer's map (round0/body/counts.CONTINENT plus round2/body/calc_report.EXTRA, imported read-only), and its
continent-level clock offsets. Indoor: Stage 0 (men's main tour) or tennis-data.co.uk's Court for priced matches.
Each player's own previous rows only. Writes data/studies/feature_interactions/round2/feasibility/r2_geo.json.
Run: ./python.sh src/eda/feature_interactions/round2/feasibility/r2_geo.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from src.eda.feature_interactions.round1.feasibility import base as B  # noqa: E402
from src.eda.feature_interactions.round0.body.counts import CONTINENT  # noqa: E402
from src.eda.feature_interactions.round2.body.calc_report import EXTRA, OFFSET  # noqa: E402
from src.eda.feature_interactions.round2.body.calc_core import ITF_CODE  # noqa: E402
from src.eda.feature_interactions.round2.feasibility.r2_checks import by_cell  # noqa: E402
from src.eda.predictability_diagnostic import stage4_country as SC  # noqa: E402

OUT = B.C.OUT / "round2" / "feasibility"
OLD = B.ROOT / "data" / "studies" / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" / "studies"


def td_court() -> pd.Series:
    o = pd.read_parquet(OLD / "predictability_diagnostic" / "stage1_odds.parquet", columns=["match_id", "td_file", "td_row"])
    o = o.dropna(subset=["td_file"])
    parts = []
    for f, g in o.groupby("td_file"):
        r = pd.read_parquet(B.ROOT / f, columns=["Court"]).reset_index(drop=True)
        r["_pos"] = np.arange(len(r))
        parts.append(g[["match_id", "td_row"]].astype({"td_row": "int64"}).merge(r, left_on="td_row", right_on="_pos"))
    c = pd.concat(parts).drop_duplicates("match_id").set_index("match_id")["Court"]
    return c.astype(str).str.lower().map({"indoor": 1.0, "outdoor": 0.0})


def main() -> int:
    P = pd.read_parquet(B.OUT / "_panel_aug.parquet").drop(columns=["a_won"])
    L = B.get_history()
    L["year"] = pd.to_datetime(L["tournament_date"]).dt.year
    ctry = SC.event_country(L).astype(object)
    ctry = ctry.where(ctry.notna(), L["tournament_id"].astype(str).str.extract(ITF_CODE, expand=False))
    L["cont"] = ctry.map({**CONTINENT, **EXTRA})
    court = td_court()
    ind = L["indoor"].map({True: 1.0, False: 0.0}).astype(float)
    L["indoor_any"] = ind.where(ind.notna(), L["match_id"].map(court))
    g = L.groupby("player_id", sort=False)
    first = L.groupby(["player_id", "tournament_id"], sort=False).cumcount().to_numpy() == 0
    prev_cont = g["cont"].shift(1)
    known_change = first & L["cont"].notna().to_numpy() & prev_cont.notna().to_numpy()
    o1, o2 = L["cont"].map(OFFSET), prev_cont.map(OFFSET)
    dz = (o1 - o2).abs()
    zone5 = np.minimum(dz, 24 - dz) >= 5
    trig = first & zone5.fillna(False).to_numpy() & (L["rest_min"].to_numpy(float) <= 5)
    # I-060: every row of the player's previous 42 days has a known continent
    obs = L["obs"].to_numpy(float)
    unk = L["cont"].isna().astype(float).groupby(L["player_id"]).cumsum().to_numpy()
    tmp = pd.DataFrame({"pid": L["player_id"].to_numpy(), "obs": obs, "unk": unk})
    starts = np.zeros(len(L))
    for pid, idx in tmp.groupby("pid").indices.items():
        o = obs[idx]
        j = np.searchsorted(o, o - 42, side="left")
        u = unk[idx]
        prev_unk = np.where(j > 0, u[np.maximum(j - 1, 0)], 0.0)
        before = np.r_[0.0, u[:-1]]
        starts[idx] = before - prev_unk                       # unknown-continent rows in the last 42 days, excluding this
    known42 = starts < 0.5
    prev_ind = g["indoor_any"].shift(1)
    switch_def = first & L["indoor_any"].notna().to_numpy() & prev_ind.notna().to_numpy()
    res = {"unmapped_country_share_rows": round(float(L["cont"].isna().mean()), 4)}
    for name, v in (("i060_known42", known42), ("i074_defined_first", known_change), ("i074_trigger", trig),
                    ("i075_indoor_switch_defined_first", switch_def)):
        a, b = B.at_model(L, v.astype(float), P)
        res[f"{name}_both"] = by_cell(P, (a > 0.5) & (b > 0.5))
        if name in ("i074_trigger",):
            res[f"{name}_either"] = by_cell(P, (a > 0.5) | (b > 0.5))
    fa, fb = B.at_model(L, first.astype(float), P)
    for name, v in (("i074_defined_first", known_change), ("i075_indoor_switch_defined_first", switch_def)):
        a, b = B.at_model(L, v.astype(float), P)
        m = (fa > 0.5) & (fb > 0.5)
        res[f"{name}_both_among_both_first"] = by_cell(P[m], ((a > 0.5) & (b > 0.5))[m])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "r2_geo.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
