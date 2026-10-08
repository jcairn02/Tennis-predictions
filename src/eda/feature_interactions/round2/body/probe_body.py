"""Round 2, the body analyst's probe-equivalent check of f20-f28 (CLAUDE.md feature timing; the logic of
src/eda/match_timing/probe.py applied to these builders): for each cut day D, every match that could have started after
D (es > D) is either REVERSED (the winner flag flipped and the two players' box scores exchanged, as probe.py's flip) or
REMOVED from the history; every builder's prepare() is rerun, and every prepared per-player value and every combined
column of each model match that surely finished by D (lf <= D) is compared with the unchanged build. Nothing may move.

The blocks' 2014-2021 standardisation constants and the modulators' centring means are recorded on the unchanged
build and replayed (class Freeze): they rescale a column uniformly and carry no match's information.

Upstream inputs (the panel's leak-proof IOS, Elo, Stage 3 ratings, surface-IOS states) are held: they carry their own
probes. What this checks is each builder's own construction: own-sequence windows, the walk-forward field tables (pace
constants, the odometer's and the layoff's expected values, the field means of the serve-decay z-scores), the event
segments and the uncounted-match windows.

Writes data/studies/feature_interactions/round2/body/probe_body.json.
Run: ./python.sh src/eda/feature_interactions/round2/body/probe_body.py
"""
from __future__ import annotations

import importlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions.features import f20_fatigue as F  # noqa: E402

OUT = C.OUT / "round2" / "body"
MODULES = ["f20_fatigue", "f21_constitution", "f22_demand", "f23_arrival", "f24_onsite", "f25_switch",
           "f26_impairment", "f27_home", "f28_state"]
# Slam second-week Wednesdays (US Open 2016, Australian Open 2019, US Open 2023) and Cincinnati 2024's third day
CUTS = {"reverse": ("2016-09-07", "2019-01-23", "2023-09-06", "2024-08-14"), "remove": ("2016-09-07", "2023-09-06")}
SWAP = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced", "tpw_n",
        "spw_n", "spw_d", "rpw_n", "rpw_d"]


class Freeze:
    """Records the blocks' standardisation constants (clip and SD of each member) and the modulators' centring means on
    the base build, and replays them, in call order, on every altered build. They are global constants of the 2014-2021
    rows, not information about a match; held fixed, an early match's column can move only through its own inputs."""

    def __init__(self):
        self.mode, self.std, self.cen, self.i_std, self.i_cen = "record", [], [], 0, 0

    def standardise(self, P, x, q: float = 0.99):
        x = np.asarray(x, float)
        if self.mode == "record":
            d = F.disc(P) & np.isfinite(x)
            if not d.any():
                self.std.append(None)
                return x
            clip = float(np.quantile(np.abs(x[d]), q)) or 1.0
            xc = np.clip(x, -clip, clip)
            sd = float(np.std(xc[d])) or 1.0
            self.std.append((clip, sd))
            return xc / sd
        c = self.std[self.i_std]
        self.i_std += 1
        return x if c is None else np.clip(x, -c[0], c[0]) / c[1]

    def centre(self, P, s):
        s = np.asarray(s, float)
        if self.mode == "record":
            m = float(np.nanmean(s[F.disc(P)]))
            self.cen.append(m)
            return s - m
        m = self.cen[self.i_cen]
        self.i_cen += 1
        return s - m

    def replay(self):
        self.mode, self.i_std, self.i_cen = "replay", 0, 0


FZ = Freeze()
F.standardise, F.centre = FZ.standardise, FZ.centre


def reverse_after(L: pd.DataFrame, day: float) -> pd.DataFrame:
    out = L.copy()
    sel = (out["es"].to_numpy(float) > day)
    key = out["match_id"].astype(str) + "|" + out["side"].astype(str)
    other = out["match_id"].astype(str) + "|" + np.where(out["side"].to_numpy() == "A", "B", "A")
    for c in SWAP:
        v = pd.Series(out[c].to_numpy(float), index=key.to_numpy())
        v = v[~v.index.duplicated()]
        partner = other.map(v).to_numpy(float)
        out[c] = np.where(sel, partner, out[c].to_numpy(float))
    won = out["won"].to_numpy(bool)
    out["won"] = np.where(sel, ~won, won)
    out["retired_self"] = (out["status"] == "retired").to_numpy() & ~out["won"].to_numpy(bool)
    return out


def build(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    F.clear_cache()
    res = {}
    for name in MODULES:
        mod = importlib.import_module(f"src.eda.feature_interactions.features.{name}")
        for spec in mod.HYPOTHESES:
            new = spec["prepare"](P, L)
            x = np.asarray(spec["combine"](P.assign(**new))["x"], float).reshape(len(P), -1)
            res[spec["hid"]] = ({k: np.asarray(v) for k, v in new.items()}, x)
    return res


def same(a, b) -> np.ndarray:
    a, b = np.asarray(a), np.asarray(b)
    if a.dtype == object or b.dtype == object:
        return (a.astype(str) == b.astype(str))
    a, b = a.astype(float), b.astype(float)
    return (np.isnan(a) & np.isnan(b)) | (np.abs(a - b) <= 1e-9)


def main() -> int:
    warnings.simplefilter("ignore")
    from src.eda.feature_interactions.history import long_table
    from src.eda.feature_interactions.panel import panel
    P = panel(max_season=C.REPLICATION[-1]).drop(columns=["a_won"])
    L0 = long_table()
    L0 = L0[pd.to_datetime(L0["tournament_date"]) < F.season_cut(P)].reset_index(drop=True)
    base = build(P, L0)
    lf = P["lf"].to_numpy(float)
    report = {}
    for mode, cuts in CUTS.items():
        for cut in cuts:
            day = float((pd.Timestamp(cut) - F.DAY0).days)
            L1 = reverse_after(L0, day) if mode == "reverse" else L0[L0["es"].to_numpy(float) <= day].reset_index(drop=True)
            FZ.replay()
            alt = build(P, L1)
            assert FZ.i_std == len(FZ.std) and FZ.i_cen == len(FZ.cen), "the replay did not follow the record"
            early = lf <= day
            for hid, (cols, x) in base.items():
                cols1, x1 = alt[hid]
                moved_cols = {k: int((~same(v[early], cols1[k][early])).sum()) for k, v in cols.items()}
                moved_x = int((~same(x[early], x1[early])).any(axis=1).sum())
                later = ~early
                changed_later = int((~same(x[later], x1[later])).any(axis=1).sum())
                report[f"{mode} {cut} {hid}"] = {"early_rows": int(early.sum()), "moved_x": moved_x,
                                                 "moved_cols": {k: v for k, v in moved_cols.items() if v},
                                                 "later_rows_changed": changed_later}
                C.log(f"{mode} {cut} {hid}: early {int(early.sum())}, moved x {moved_x}, cols "
                      f"{ {k: v for k, v in moved_cols.items() if v} }, later changed {changed_later}")
            F.clear_cache()
    passed = all(v["moved_x"] == 0 and not v["moved_cols"] for v in report.values())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "probe_body.json").write_text(json.dumps({"passed": passed, "cuts": CUTS, "results": report}, indent=1))
    C.log(f"probe passed: {passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
